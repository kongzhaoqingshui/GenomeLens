"""Heatmap runner：plot-only JCVI 热图工作流"""

# region import
from __future__ import annotations

import logging
import shutil
from collections.abc import Callable
from typing import cast

from genomelens.analysis.execution.artifact_builder import artifact_record
from genomelens.analysis.execution.summary_builder import (
    build_run_summary,
    scoring_placeholder,
    ui_block,
    write_run_summary,
)
from genomelens.analysis.planning.models import HeatmapExecutionRequest
from genomelens.app.controller.state_machine import WorkflowState
from genomelens.artifacts.archive import archive_figures
from genomelens.contracts.summaries import RunSummary
from genomelens.data.logging.log_setup import run_with_logging
from genomelens.data.logging.task_log import task_scope
from genomelens.data.workspace.output_layout import build_output_layout, create_output_layout
from genomelens.engines.jcvi.adapter import JcviEngineAdapter
from genomelens.engines.jcvi.manifest_builder import JcviManifestBuilder
from genomelens.toolchain.runtime.resource_locator import locate_engine

# endregion


def _build_artifact_index(
    request: HeatmapExecutionRequest,
    *,
    manifest_path: str,
    engine_summary_path: str,
    run_log: str,
    final_figures: list[str],
) -> list[dict[str, object]]:
    """构建 heatmap 结果的 artifact 索引"""

    records: list[dict[str, object]] = []
    for artifact_id, artifact_type, value in [
        ("input_manifest", "manifest", manifest_path),
        ("engine_summary", "summary", engine_summary_path),
        ("run_log", "log", run_log),
        ("matrix", "matrix", str(request.matrix)),
    ]:
        record = artifact_record(artifact_id, artifact_type, value, request.workflow)
        if record:
            records.append(record)

    if request.rowgroups:
        record = artifact_record("rowgroups", "rowgroups", str(request.rowgroups), request.workflow)
        if record:
            records.append(record)

    for index, figure in enumerate(final_figures, start=1):
        record = artifact_record(f"figure_{index}", "figure", figure, request.workflow, preview=True)
        if record:
            records.append(record)

    return records


def _build_run_summary(
    request: HeatmapExecutionRequest,
    *,
    manifest_path: str,
    engine_summary_path: str,
    run_log: str,
    final_figures: list[str],
    probe: dict[str, object],
    status: str,
) -> RunSummary:
    """根据 heatmap 运行结果构建 RunSummary"""

    return build_run_summary(
        status=status,
        workflow="mcscan",
        method="mcscan",
        task={
            "task_id": request.task_id,
            "task_type": "plot_heatmap",
            "workflow": request.workflow,
            "source": "cli",
        },
        species=[],
        final_figures=final_figures,
        artifact_index=_build_artifact_index(
            request,
            manifest_path=manifest_path,
            engine_summary_path=engine_summary_path,
            run_log=run_log,
            final_figures=final_figures,
        ),
        logs={"run_log": run_log},
        ui=ui_block(
            status,
            final_figures,
            summary_path=build_output_layout(request.outdir).run_summary,
            log_path=build_output_layout(request.outdir).logs / "run.log",
        ),
        scoring=scoring_placeholder(),
        extensions={
            "jcvi_backend": "jcvi-genomelens-engine",
            "jcvi_workflow": request.workflow,
            "jcvi_engine_path": str(probe.get("engine_path") or ""),
            "jcvi_distribution": str(probe.get("distribution") or ""),
            "jcvi_engine_version": str(probe.get("engine_version") or ""),
            "jcvi_upstream_version": str(probe.get("jcvi_upstream_version") or ""),
            "jcvi_patchset": str(probe.get("patchset") or ""),
            "jcvi_runtime_mode": str(probe.get("runtime_mode") or ""),
            "jcvi_loaded_extensions": cast(list[str], probe.get("loaded_extensions") or []),
            "jcvi_missing_extensions": cast(list[str], probe.get("missing_extensions") or []),
            "engine_summary_path": engine_summary_path,
            "heatmap_matrix": str(request.matrix),
            "heatmap_cmap": request.cmap,
            "heatmap_groups": request.groups,
            "heatmap_horizontalbar": request.horizontalbar,
        },
    )


def _run_heatmap(
    set_state: Callable[[WorkflowState], None],
    request: HeatmapExecutionRequest,
    logger: logging.Logger,
) -> RunSummary:
    """运行 plot-only heatmap 工作流并写出 run_summary.json"""

    set_state(WorkflowState.VALIDATING_INPUTS)
    if not request.matrix.is_file():
        raise FileNotFoundError(f"矩阵 CSV 不存在：{request.matrix}")

    set_state(WorkflowState.PREPARING_WORKSPACE)
    layout = create_output_layout(request.outdir, force=request.force)

    set_state(WorkflowState.CHECKING_TOOLCHAIN)
    with task_scope(logger, task_id=request.task_id, step="resolve_toolchain"):
        engine = locate_engine(explicit=request.jcvi_engine)
        if not engine.ok:
            raise RuntimeError(engine.message or "jcvi-genomelens executable was not found")

    adapter = JcviEngineAdapter(engine.path)
    with task_scope(logger, task_id=request.task_id, step="probe_engine", context={"engine": engine.path}):
        probe = adapter.probe()
    probe["engine_path"] = engine.path

    set_state(WorkflowState.WRITING_MANIFEST)
    with task_scope(logger, task_id=request.task_id, step="write_manifest", context={"manifest": str(layout.manifest)}):
        manifest = JcviManifestBuilder().build_heatmap_manifest(request)
        adapter.write_manifest(manifest, layout.manifest)
        shutil.copy2(layout.manifest, layout.inputs / "input_manifest.json")

    set_state(WorkflowState.RUNNING_ENGINE)
    with task_scope(logger, task_id=request.task_id, step="run_engine", context={"engine_outdir": str(layout.jcvi)}):
        engine_result = adapter.run_manifest(layout.manifest, layout.jcvi)

    set_state(WorkflowState.FINALIZING)
    with task_scope(logger, task_id=request.task_id, step="archive_figures"):
        figures = [str(item) for item in cast(list[object], engine_result.artifacts.get("figures") or [])]
        final_figures = archive_figures(figures, layout.figures)
        status = "SUCCEEDED" if engine_result.status == "ok" else "FAILED"

    with task_scope(logger, task_id=request.task_id, step="write_summary", context={"status": status}):
        summary = _build_run_summary(
            request,
            manifest_path=str(layout.manifest),
            engine_summary_path=str(engine_result.summary_path),
            run_log=str(layout.logs / "run.log"),
            final_figures=final_figures,
            probe=probe,
            status=status,
        )
        write_run_summary(layout, summary)

    set_state(WorkflowState.SUCCEEDED if summary.status == "SUCCEEDED" else WorkflowState.FAILED)
    return summary


def run_heatmap_workflow(
    set_state: Callable[[WorkflowState], None],
    request: HeatmapExecutionRequest,
) -> RunSummary:
    """运行 heatmap 工作流并释放日志句柄"""

    log_path = build_output_layout(request.outdir).logs / "run.log"
    with run_with_logging(
        log_path,
        level=request.log_level,
        console=False,
        concise=True,
    ) as logger:
        return _run_heatmap(set_state, request, logger)
