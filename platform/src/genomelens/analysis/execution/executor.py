"""PlanExecutor(执行计划运行器)：按 DAG 执行平台步骤"""

# region import
from __future__ import annotations

import json
import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

from genomelens.analysis.execution.artifact_builder import copy_pairwise_figures
from genomelens.analysis.execution.handlers.heatmap import run_heatmap_workflow
from genomelens.analysis.execution.handlers.histogram import run_histogram_workflow
from genomelens.analysis.execution.handlers.multi_local import build_multi_species_local_synteny
from genomelens.analysis.execution.handlers.pairwise import run_pairwise_mcscan
from genomelens.analysis.execution.summary_builder import (
    build_multi_run_summary,
    species_summary,
    write_run_summary,
)
from genomelens.analysis.planning.models import ExecutionPlan, ExecutionStep, SyntenyExecutionRequest
from genomelens.app.controller.state_machine import WorkflowState
from genomelens.app.errors.exceptions import InputValidationError
from genomelens.app.events.signal_bus import SignalBus
from genomelens.contracts.summaries import ChildRunRecord, RunSummary
from genomelens.data.logging.log_setup import close_logging, logger_name_for_path, setup_logging
from genomelens.data.logging.task_log import task_scope
from genomelens.data.workspace.output_layout import build_output_layout, create_output_layout
from genomelens.engines.jcvi.adapter import JcviEngineAdapter
from genomelens.engines.jcvi.manifest_builder import JcviManifestBuilder
from genomelens.toolchain.runtime.resource_locator import locate_engine

# endregion


class PlanExecutor:
    """PlanExecutor：执行 WorkflowPlanner 生成的 ExecutionPlan"""

    def execute(self, plan: ExecutionPlan, signal_bus: SignalBus) -> RunSummary:
        """执行计划并返回 RunSummary"""

        if len(plan.steps) == 1:
            return self._execute_single(plan.steps[0], signal_bus)
        return self._execute_composite(plan, signal_bus)

    def _execute_single(self, step: ExecutionStep, signal_bus: SignalBus) -> RunSummary:
        """执行单步计划"""

        set_state = self._set_state(signal_bus)
        if step.kind == "pairwise_synteny":
            return run_pairwise_mcscan(set_state, cast(SyntenyExecutionRequest, step.payload))
        if step.kind == "graphics_histogram":
            return run_histogram_workflow(set_state, step.payload)  # type: ignore[arg-type]
        if step.kind == "graphics_heatmap":
            return run_heatmap_workflow(set_state, step.payload)  # type: ignore[arg-type]
        raise InputValidationError(f"unsupported single execution step: {step.kind}")

    def _execute_composite(self, plan: ExecutionPlan, signal_bus: SignalBus) -> RunSummary:
        """执行复合计划"""

        log_path = build_output_layout(plan.outdir).logs / "run.log"
        logger_name = logger_name_for_path(log_path)
        try:
            return self._execute_composite_inner(plan, signal_bus)
        finally:
            close_logging(logger_name)

    def _execute_composite_inner(self, plan: ExecutionPlan, signal_bus: SignalBus) -> RunSummary:
        """执行复合计划主体"""

        set_state = self._set_state(signal_bus)
        set_state(WorkflowState.PREPARING_WORKSPACE)
        layout = create_output_layout(plan.outdir, force=plan.force)
        logger = setup_logging(
            layout.logs / "run.log",
            level="INFO",
            logger_name=logger_name_for_path(layout.logs / "run.log"),
            console=False,
            concise=True,
        )
        pairwise_jobs: list[ChildRunRecord] = []
        final_figures: list[str] = []
        successful_pair_summaries: dict[str, RunSummary] = {}

        manifest = {
            "schema_version": 3,
            "workflow_id": plan.workflow_id,
            "plan_id": plan.plan_id,
            "steps": [
                {
                    "step_id": step.step_id,
                    "kind": step.kind,
                    "depends_on": list(step.depends_on),
                    "inputs": [item.to_json() for item in step.inputs],
                    "outputs": [item.to_json() for item in step.outputs],
                }
                for step in plan.steps
            ],
        }
        layout.manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        shutil.copy2(layout.manifest, layout.inputs / "input_manifest.json")

        pair_steps = [step for step in plan.steps if step.kind == "pairwise_synteny"]
        for index, step in enumerate(pair_steps, start=1):
            request = cast(SyntenyExecutionRequest, step.payload)
            signal_bus.emit(
                "pair_started",
                pair_id=step.step_id,
                index=index,
                total=len(pair_steps),
                query=request.reference.name,
                subject=request.target.name,
                outdir=str(request.outdir),
            )
            try:
                with task_scope(logger, task_id=step.step_id, step="run_pairwise_job"):
                    pair_summary = run_pairwise_mcscan(set_state, request)
            except Exception as exc:  # noqa: BLE001 - 复合任务需要记录单个子任务失败
                pairwise_jobs.append(
                    ChildRunRecord(
                        pair_id=step.step_id,
                        species_a_name=request.reference.name,
                        species_b_name=request.target.name,
                        status="FAILED",
                        outdir=str(request.outdir),
                        run_summary_path=str(request.outdir / "report" / "run_summary.json"),
                        error={"type": exc.__class__.__name__, "message": str(exc)},
                    )
                )
                continue

            successful_pair_summaries[step.step_id] = pair_summary
            copied = copy_pairwise_figures(step.step_id, list(pair_summary.final_figures), layout.figures)
            final_figures.extend(copied)
            pairwise_jobs.append(
                ChildRunRecord(
                    pair_id=step.step_id,
                    species_a_name=request.reference.name,
                    species_b_name=request.target.name,
                    status=pair_summary.status,
                    outdir=str(request.outdir),
                    run_summary_path=str(request.outdir / "report" / "run_summary.json"),
                    engine_summary_path=str(pair_summary.extensions.get("engine_summary_path", "")),
                    blast_table=str(pair_summary.extensions.get("blast_table", "")),
                    anchors_path=str(pair_summary.extensions.get("anchors_path", "")),
                    simple_path=str(pair_summary.extensions.get("simple_path", "")),
                    blocks_path=str(pair_summary.extensions.get("blocks_path", "")),
                    query_bed=str(pair_summary.extensions.get("query_bed", "")),
                    subject_bed=str(pair_summary.extensions.get("subject_bed", "")),
                    final_figures=copied,
                )
            )

        set_state(WorkflowState.FINALIZING)
        global_figures: list[str] = []
        multi_local_figures: list[str] = []
        aggregate_request = self._aggregate_request(plan)
        for step in plan.steps:
            if step.kind == "global_karyotype":
                with task_scope(logger, task_id=step.step_id, step="build_global_karyotype"):
                    global_figures = self._build_global_karyotype(aggregate_request, pairwise_jobs, layout)
                final_figures.extend(global_figures)
            elif step.kind == "multi_local_synteny":
                with task_scope(logger, task_id=step.step_id, step="build_multi_local_synteny"):
                    multi_local_figures = build_multi_species_local_synteny(aggregate_request, pairwise_jobs, layout)
                final_figures.extend(multi_local_figures)

        summary = build_multi_run_summary(
            aggregate_request,
            layout,
            pairwise_jobs,
            final_figures,
            pairing_strategy="reference_vs_targets" if plan.reference_name else "all_vs_all_pairwise",
            global_figures=global_figures,
            reference_name=plan.reference_name,
            multi_species_local_figures=multi_local_figures,
            task_type_override="reference_vs_targets" if plan.reference_name else None,
        )
        write_run_summary(layout, summary)
        set_state(WorkflowState.SUCCEEDED if summary.status == "SUCCEEDED" else WorkflowState.FAILED)
        return summary

    @staticmethod
    def _aggregate_request(plan: ExecutionPlan) -> SyntenyExecutionRequest:
        """从计划中取一个聚合步骤携带的顶层请求"""

        for step in plan.steps:
            if isinstance(step.payload, dict) and "request" in step.payload:
                return cast(SyntenyExecutionRequest, step.payload["request"])
        for step in plan.steps:
            if step.kind == "pairwise_synteny":
                return cast(SyntenyExecutionRequest, step.payload)
        raise InputValidationError("execution plan has no synteny request payload")

    @staticmethod
    def _set_state(signal_bus: SignalBus) -> Callable[[WorkflowState], None]:
        """构造状态发射函数"""

        def set_state(state: WorkflowState) -> None:
            signal_bus.emit("state", state=state.value)

        return set_state

    @staticmethod
    def _build_global_karyotype(
        request: SyntenyExecutionRequest,
        pairwise_jobs: list[ChildRunRecord],
        layout,
    ) -> list[str]:
        """把成功 pairwise 的 simple 边聚合成一张全局核型总图"""

        species_order = [item.name for item in request.species]
        track_index = {name: index for index, name in enumerate(species_order)}
        track_beds: dict[str, str] = {}
        edges: list[dict[str, object]] = []

        for job in pairwise_jobs:
            if job.status != "SUCCEEDED":
                continue
            if not (job.simple_path and job.query_bed and job.subject_bed and Path(job.simple_path).is_file()):
                continue
            if job.species_a_name not in track_index or job.species_b_name not in track_index:
                continue
            track_beds.setdefault(job.species_a_name, job.query_bed)
            track_beds.setdefault(job.species_b_name, job.subject_bed)
            edges.append(
                {
                    "i": track_index[job.species_a_name],
                    "j": track_index[job.species_b_name],
                    "simple": job.simple_path,
                }
            )

        usable_tracks = [name for name in species_order if name in track_beds]
        if len(usable_tracks) < 2 or not edges:
            return []

        compact_index = {name: index for index, name in enumerate(usable_tracks)}
        tracks = [{"name": name, "bed": track_beds[name]} for name in usable_tracks]
        remapped_edges = [
            {
                "i": compact_index[species_order[int(cast(int, edge["i"]))]],
                "j": compact_index[species_order[int(cast(int, edge["j"]))]],
                "simple": edge["simple"],
            }
            for edge in edges
            if species_order[int(cast(int, edge["i"]))] in compact_index
            and species_order[int(cast(int, edge["j"]))] in compact_index
        ]
        if not remapped_edges:
            return []

        try:
            engine = locate_engine(explicit=request.engine_path)
            if not engine.ok:
                return []

            adapter = JcviEngineAdapter(engine.path)
            global_dir = layout.intermediate / "global_karyotype"
            global_dir.mkdir(parents=True, exist_ok=True)
            manifest = JcviManifestBuilder().build_global_karyotype_manifest(
                tracks=tracks,
                edges=remapped_edges,
                blastn_path=request.blastn_path,
                makeblastdb_path=request.makeblastdb_path,
                formats=request.formats,
                figsize=request.figsize,
                dpi=request.dpi,
                auto_optimization=request.auto_optimization,
                log_level=request.log_level,
                task={"workflow": "graphics_karyotype_global", "task_type": "global_synteny"},
                species=species_summary(request),
            )
            manifest_path = global_dir / "global_manifest.json"
            adapter.write_manifest(manifest, manifest_path)
            result = adapter.run_manifest(manifest_path, global_dir)
            raw_figures = result.artifacts.get("global_karyotype_figures") or result.artifacts.get("figures") or []
            figures = cast(list[Any], raw_figures)
            return copy_pairwise_figures("global", [str(item) for item in figures], layout.figures)
        except Exception:  # noqa: BLE001 - 总图是增量产物，失败不影响 pairwise 结果
            return []
