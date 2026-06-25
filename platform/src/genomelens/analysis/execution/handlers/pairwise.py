"""Pairwise MCscan 执行处理器（execution handler）"""

from __future__ import annotations

import logging
import os
import shutil
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import Any, cast

from genomelens.analysis.execution.artifact_builder import artifact_index as build_artifact_index
from genomelens.analysis.execution.resources.shared_runtime import PlanRunContext
from genomelens.analysis.execution.summary_builder import (
    build_run_summary,
    scoring_placeholder,
    species_summary,
    ui_block,
    write_run_summary,
)
from genomelens.analysis.planning.models import PairwiseArtifactInputs, SyntenyExecutionRequest
from genomelens.app.controller.state_machine import WorkflowState
from genomelens.app.errors.error_codes import ErrorCode
from genomelens.app.errors.exceptions import ToolchainError
from genomelens.artifacts.archive import archive_figures
from genomelens.contracts.extensions.mcscan import McscanSummaryExtension
from genomelens.contracts.species import PreparedGenomeInputSpec
from genomelens.contracts.summaries import RunSummary
from genomelens.data.logging.log_setup import close_logging, logger_name_for_path, setup_logging
from genomelens.data.logging.task_log import task_scope
from genomelens.data.workspace.output_layout import OutputLayout, build_output_layout, create_output_layout
from genomelens.engines.jcvi.adapter import JcviEngineAdapter
from genomelens.engines.jcvi.command_mapping import requires_precomputed_pairwise
from genomelens.engines.jcvi.manifest_builder import JcviManifestBuilder
from genomelens.engines.jcvi.models import JcviRunResult
from genomelens.preprocessing.annotation import write_preprocessing_summary
from genomelens.preprocessing.input_preparer import prepare_inputs
from genomelens.toolchain.runtime.resource_locator import LocatedResource
from genomelens.toolchain.runtime.toolchain_resolver import resolve_pairwise_toolchain
from genomelens.validation.execution_requests import validate_request


def _prepare_pairwise_inputs(
    set_state: Callable[[WorkflowState], None],
    request: SyntenyExecutionRequest,
    layout: OutputLayout,
    *,
    context: PlanRunContext | None = None,
) -> tuple[
    SyntenyExecutionRequest,
    PreparedGenomeInputSpec,
    PreparedGenomeInputSpec,
    list[dict[str, object]],
]:
    """校验并准备 pairwise 输入"""

    validate_request(request)
    if len(request.species) != 2:
        raise ToolchainError(
            "pairwise runner only accepts two species",
            code=ErrorCode.REQUEST_INVALID,
        )

    effective_request = request
    if request.target_gene_ids:
        effective_request = replace(request, engine_workflow="local_synteny")

    if context is None:
        set_state(WorkflowState.PREPARING_WORKSPACE)
        query, subject, preprocess_summaries = prepare_inputs(
            set_state,
            request,
            layout,
            preprocessing_state=WorkflowState.PREPROCESSING_ANNOTATIONS,
        )
        return effective_request, query, subject, preprocess_summaries

    query_record = context.prepared_for(request.query)
    subject_record = context.prepared_for(request.subject)
    if query_record is None or subject_record is None:
        raise RuntimeError("shared runtime is missing prepared species records")

    preprocess_summaries = [
        summary for summary in (query_record.summary, subject_record.summary) if summary is not None
    ]
    if preprocess_summaries:
        layout.preprocessing_summary.parent.mkdir(parents=True, exist_ok=True)
        write_preprocessing_summary(layout.preprocessing_summary, preprocess_summaries)

    return effective_request, query_record.prepared, subject_record.prepared, preprocess_summaries


def _prepare_pairwise_workspace(request: SyntenyExecutionRequest) -> tuple[OutputLayout, logging.Logger]:
    layout = create_output_layout(request.outdir, force=request.force)
    logger = setup_logging(
        layout.logs / "run.log",
        level=request.log_level,
        logger_name=logger_name_for_path(layout.logs / "run.log"),
        console=request.console_log,
        concise=True,
    )
    logger.info("Starting GenomeLens workflow")
    return layout, logger


def _resolve_pairwise_toolchain(
    request: SyntenyExecutionRequest,
    *,
    context: PlanRunContext | None = None,
) -> tuple[LocatedResource, LocatedResource, LocatedResource, str, str]:
    if context is not None:
        toolchain = context.toolchain
        return (
            toolchain.engine,
            toolchain.blastn,
            toolchain.makeblastdb,
            toolchain.lastal_path,
            toolchain.lastdb_path,
        )

    return resolve_pairwise_toolchain(
        jcvi_engine=request.jcvi_engine,
        blastn_path=request.blastn_path,
        makeblastdb_path=request.makeblastdb_path,
        lastal_path=request.lastal_path,
        lastdb_path=request.lastdb_path,
        align_soft=request.align_soft,
    )


def _prepare_pairwise_run(
    set_state: Callable[[WorkflowState], None],
    request: SyntenyExecutionRequest,
    *,
    context: PlanRunContext | None = None,
) -> tuple[
    OutputLayout,
    logging.Logger,
    SyntenyExecutionRequest,
    PreparedGenomeInputSpec,
    PreparedGenomeInputSpec,
    list[dict[str, object]],
]:
    layout, logger = _prepare_pairwise_workspace(request)
    with task_scope(
        logger,
        task_id=request.task_id,
        step="prepare_inputs",
        context={"outdir": str(layout.root), "species_count": len(request.species), "has_context": context is not None},
    ):
        effective_request, query, subject, preprocess_summaries = _prepare_pairwise_inputs(
            set_state,
            request,
            layout,
            context=context,
        )
    return layout, logger, effective_request, query, subject, preprocess_summaries


def _pairwise_artifacts_from_engine_result(engine_result: JcviRunResult) -> PairwiseArtifactInputs | None:
    def _artifact_path(name: str) -> Path | None:
        raw = engine_result.artifacts.get(name)
        if not isinstance(raw, str) or not raw.strip():
            return None
        return Path(raw).expanduser().resolve(strict=False)

    artifacts = PairwiseArtifactInputs(
        blast_table=_artifact_path("blast_table"),
        anchors=_artifact_path("anchors"),
        simple=_artifact_path("simple"),
        blocks=_artifact_path("blocks"),
        merged_bed=_artifact_path("merged_bed"),
        layout=_artifact_path("layout"),
    )
    return artifacts if artifacts.has_any else None


def _run_pairwise_compute_pass(
    adapter: JcviEngineAdapter,
    request: SyntenyExecutionRequest,
    layout: OutputLayout,
    query: PreparedGenomeInputSpec,
    subject: PreparedGenomeInputSpec,
    *,
    blastn_path: str,
    makeblastdb_path: str,
    lastal_path: str,
    lastdb_path: str,
    logger: logging.Logger,
) -> PairwiseArtifactInputs:
    """先跑一遍 ``pairwise`` 计算，产出渲染所需的共线性基础产物。

    渲染类 workflow（synteny/karyotype/dotplot/local_synteny）自身不再内置计算回退，
    因此当请求未携带预算产物时，由编排层在独立子目录里执行一次计算，再把产物注入渲染。
    """

    compute_request = replace(request, engine_workflow="pairwise", precomputed_artifacts=None)
    compute_manifest_path = layout.inputs / "pairwise_input_manifest.json"
    compute_outdir = layout.jcvi / "pairwise"
    with task_scope(
        logger,
        task_id=request.task_id,
        step="run_pairwise_compute",
        context={"engine_outdir": str(compute_outdir)},
    ):
        compute_manifest = JcviManifestBuilder().build_pairwise_manifest(
            compute_request,
            query=query,
            subject=subject,
            blastn_path=blastn_path,
            makeblastdb_path=makeblastdb_path,
            lastal_path=lastal_path,
            lastdb_path=lastdb_path,
        )
        adapter.write_manifest(compute_manifest, compute_manifest_path)
        compute_result = adapter.run_manifest(compute_manifest_path, compute_outdir)

    artifacts = _pairwise_artifacts_from_engine_result(compute_result)
    if artifacts is None:
        raise ToolchainError(
            "pairwise compute pass did not produce reusable synteny artifacts",
            code=ErrorCode.ENGINE_FAILED,
        )
    return artifacts


def _summary_extra_extensions(
    *,
    context: PlanRunContext | None,
    pairwise_cache_hit: bool,
    cache_key: str,
) -> dict[str, object]:
    data: dict[str, object] = {"pairwise_cache_hit": pairwise_cache_hit}
    if cache_key:
        data["pairwise_cache_key"] = cache_key
    if context is not None:
        data["toolchain_reused"] = True
        data["probe_reused"] = True
    return data


def _resolve_pairwise_task_and_species(
    engine_result: JcviRunResult,
    manifest: dict[str, object],
    request: SyntenyExecutionRequest,
) -> tuple[dict[str, object], list[dict[str, object]]]:
    task = engine_result.task or (
        cast(dict[str, object], manifest.get("task"))
        if isinstance(manifest.get("task"), dict)
        else request.task_spec.to_manifest_json()
    )
    species = engine_result.species or (
        cast(list[dict[str, object]], manifest.get("species"))
        if isinstance(manifest.get("species"), list)
        else species_summary(request)
    )
    return task, species


def _build_pairwise_run_summary(
    request: SyntenyExecutionRequest,
    effective_request: SyntenyExecutionRequest,
    layout: OutputLayout,
    engine_result: JcviRunResult,
    manifest: dict[str, object],
    engine: LocatedResource,
    probe: dict[str, object],
    query: PreparedGenomeInputSpec,
    subject: PreparedGenomeInputSpec,
    preprocess_summaries: list[dict[str, object]],
    final_figures: list[str],
    status: str,
    extra_extensions: dict[str, object] | None = None,
) -> RunSummary:
    run_log = layout.logs / "run.log"
    task, species = _resolve_pairwise_task_and_species(engine_result, manifest, request)
    artifact_index = build_artifact_index(
        effective_request,
        engine_result,
        final_figures,
        manifest_path=layout.manifest,
        run_log=run_log,
    )

    extension = McscanSummaryExtension(
        jcvi_backend="jcvi-genomelens-engine",
        jcvi_workflow=effective_request.jcvi_workflow,
        jcvi_engine_path=engine.path,
        jcvi_distribution=engine_result.distribution or str(probe.get("distribution", "")),
        jcvi_engine_version=engine_result.engine_version or str(probe.get("engine_version", "")),
        jcvi_upstream_version=engine_result.jcvi_upstream_version or str(probe.get("jcvi_upstream_version", "")),
        jcvi_patchset=engine_result.patchset or str(probe.get("patchset", "")),
        jcvi_runtime_mode=engine_result.runtime_mode or str(probe.get("runtime_mode", "")),
        jcvi_loaded_extensions=engine_result.loaded_extensions or cast(list[str], probe.get("loaded_extensions", [])),
        jcvi_missing_extensions=engine_result.missing_extensions
        or cast(list[str], probe.get("missing_extensions", [])),
        engine_summary_path=str(engine_result.summary_path),
        blast_table=str(engine_result.artifacts.get("blast_table", "")),
        anchors_path=str(engine_result.artifacts.get("anchors", "")),
        simple_path=str(engine_result.artifacts.get("simple", "")),
        blocks_path=str(engine_result.artifacts.get("blocks", "")),
        query_bed=str(query.bed),
        subject_bed=str(subject.bed),
        preprocess_summaries=preprocess_summaries,
        preprocessing_summary_path=str(layout.preprocessing_summary) if preprocess_summaries else "",
        simplified_fallback=bool(engine_result.artifacts.get("simplified_fallback", False)),
        species_a_name=request.query.name,
        species_b_name=request.subject.name,
        species_a_input_mode=request.query.mode,
        species_b_input_mode=request.subject.mode,
        species_a_bed=str(query.bed),
        species_b_bed=str(subject.bed),
    )
    extensions = extension.to_dict()
    if extra_extensions:
        extensions.update(extra_extensions)

    return build_run_summary(
        status=status,
        workflow="mcscan",
        method="mcscan",
        task=task,
        species=species,
        final_figures=final_figures,
        artifact_index=artifact_index,
        logs={"run_log": str(run_log)},
        ui=ui_block(status, final_figures, summary_path=layout.run_summary, log_path=run_log),
        scoring=scoring_placeholder(),
        extensions=extensions,
    )


def _run_pairwise_mcscan(
    set_state: Callable[[WorkflowState], None],
    request: SyntenyExecutionRequest,
    *,
    context: PlanRunContext | None = None,
) -> RunSummary:
    set_state(WorkflowState.VALIDATING_INPUTS)
    layout, logger, effective_request, query, subject, preprocess_summaries = _prepare_pairwise_run(
        set_state,
        request,
        context=context,
    )

    set_state(WorkflowState.CHECKING_TOOLCHAIN)
    with task_scope(logger, task_id=effective_request.task_id, step="resolve_toolchain"):
        engine, blastn, makeblastdb, lastal_path, lastdb_path = _resolve_pairwise_toolchain(
            effective_request,
            context=context,
        )

    adapter = JcviEngineAdapter(engine.path)
    if context is not None:
        probe = context.toolchain.probe
    else:
        with task_scope(
            logger,
            task_id=effective_request.task_id,
            step="probe_engine",
            context={"engine": engine.path},
        ):
            probe = adapter.probe()

    pairwise_cache_hit = False
    cache_key = ""
    request_for_manifest = effective_request
    if effective_request.precomputed_artifacts is None and context is not None:
        reuse_decision = context.resolve_pairwise_request(effective_request, logger)
        request_for_manifest = reuse_decision.request
        cache_key = reuse_decision.cache_key
        pairwise_cache_hit = reuse_decision.cache_hit
        if pairwise_cache_hit:
            with task_scope(
                logger,
                task_id=effective_request.task_id,
                step="reuse_pairwise_artifacts",
                context={"cache_key": cache_key},
            ):
                pass

    # 渲染类 workflow 不再自带计算回退：缺少共线性基础产物时，先独立跑一遍 pairwise 计算，
    # 再把产物注入渲染请求。pairwise 工作流自身则直接进入下方的单次引擎调用。
    if request_for_manifest.precomputed_artifacts is None and requires_precomputed_pairwise(
        effective_request.engine_workflow
    ):
        pairwise_artifacts = _run_pairwise_compute_pass(
            adapter,
            request_for_manifest,
            layout,
            query,
            subject,
            blastn_path=blastn.path,
            makeblastdb_path=makeblastdb.path,
            lastal_path=lastal_path,
            lastdb_path=lastdb_path,
            logger=logger,
        )
        request_for_manifest = replace(request_for_manifest, precomputed_artifacts=pairwise_artifacts)
        if context is not None and not pairwise_cache_hit:
            cache_key = context.store_pairwise_result(
                effective_request,
                pairwise_artifacts,
                logger,
                cache_key=cache_key,
            )

    set_state(WorkflowState.WRITING_MANIFEST)
    with task_scope(
        logger,
        task_id=request_for_manifest.task_id,
        step="write_manifest",
        context={"manifest": str(layout.manifest)},
    ):
        manifest = JcviManifestBuilder().build_pairwise_manifest(
            request_for_manifest,
            query=query,
            subject=subject,
            blastn_path=blastn.path,
            makeblastdb_path=makeblastdb.path,
            lastal_path=lastal_path,
            lastdb_path=lastdb_path,
        )
        adapter.write_manifest(manifest, layout.manifest)
        # inputs/ 下留一份 input_manifest.json 供测试与快照回查；与 canonical manifest 硬链接
        # 避免双份占用，跨卷/不支持时回退到复制
        input_manifest_path = layout.inputs / "input_manifest.json"
        try:
            os.link(layout.manifest, input_manifest_path)
        except OSError:
            shutil.copy2(layout.manifest, input_manifest_path)

    set_state(WorkflowState.RUNNING_ENGINE)
    with task_scope(
        logger,
        task_id=request_for_manifest.task_id,
        step="run_engine",
        context={"engine_outdir": str(layout.jcvi), "pairwise_cache_hit": pairwise_cache_hit},
    ):
        engine_result = adapter.run_manifest(layout.manifest, layout.jcvi)

    # 仅 pairwise 计算入口的 engine_result 才直接携带共线性产物；渲染类的产物已在计算回合存入缓存。
    if (
        context is not None
        and not pairwise_cache_hit
        and effective_request.precomputed_artifacts is None
        and not requires_precomputed_pairwise(effective_request.engine_workflow)
    ):
        artifacts_for_cache = _pairwise_artifacts_from_engine_result(engine_result)
        if artifacts_for_cache is not None:
            cache_key = context.store_pairwise_result(
                effective_request,
                artifacts_for_cache,
                logger,
                cache_key=cache_key,
            )

    set_state(WorkflowState.FINALIZING)
    with task_scope(logger, task_id=effective_request.task_id, step="archive_figures"):
        figures = cast(list[Any], engine_result.artifacts.get("figures") or [])
        final_figures = archive_figures([str(item) for item in figures], layout.figures)
        status = "SUCCEEDED" if engine_result.status == "ok" else "FAILED"

    with task_scope(logger, task_id=effective_request.task_id, step="write_summary", context={"status": status}):
        run_summary = _build_pairwise_run_summary(
            request,
            effective_request,
            layout,
            engine_result,
            manifest,
            engine,
            probe,
            query,
            subject,
            preprocess_summaries,
            final_figures,
            status,
            extra_extensions=_summary_extra_extensions(
                context=context,
                pairwise_cache_hit=pairwise_cache_hit,
                cache_key=cache_key,
            ),
        )
        write_run_summary(layout, run_summary)

    set_state(WorkflowState.SUCCEEDED if run_summary.status == "SUCCEEDED" else WorkflowState.FAILED)
    return run_summary


def run_pairwise_mcscan(
    set_state: Callable[[WorkflowState], None],
    request: SyntenyExecutionRequest,
    *,
    context: PlanRunContext | None = None,
) -> RunSummary:
    """运行 pairwise MCscan 并释放任务日志句柄"""

    log_path = build_output_layout(request.outdir).logs / "run.log"
    logger_name = logger_name_for_path(log_path)
    try:
        return _run_pairwise_mcscan(set_state, request, context=context)
    finally:
        close_logging(logger_name)
