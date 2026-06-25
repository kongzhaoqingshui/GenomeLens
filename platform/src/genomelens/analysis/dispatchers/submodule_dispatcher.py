"""SubmoduleDispatcher：把 SubmoduleRequest 展开为执行计划或直接运行"""

# region import
from __future__ import annotations

import json
import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

from genomelens.analysis.execution.artifact_builder import artifact_record
from genomelens.analysis.execution.executor import PlanExecutor
from genomelens.analysis.execution.submodule_mapping import (
    to_heatmap_request,
    to_histogram_request,
    to_synteny_like_request,
)
from genomelens.analysis.execution.summary_builder import (
    build_run_summary,
    scoring_placeholder,
    ui_block,
    write_run_summary,
)
from genomelens.analysis.planning.models import (
    ExecutionPlan,
    ExecutionStep,
    StepKind,
    StepOutputRef,
)
from genomelens.analysis.requests.submodule_models import SubmoduleRequest
from genomelens.analysis.requests.task_loader import write_task_request
from genomelens.analysis.workflows.input_bindings import PortSystem
from genomelens.analysis.workflows.submodules import SubModuleSpec, get_submodule_registry
from genomelens.app.controller.state_machine import WorkflowState
from genomelens.app.errors.exceptions import InputValidationError
from genomelens.app.events.signal_bus import SignalBus
from genomelens.artifacts.archive import archive_figures
from genomelens.contracts.summaries import RunSummary
from genomelens.data.logging.log_setup import run_with_logging
from genomelens.data.logging.task_log import task_scope
from genomelens.data.workspace.output_layout import build_output_layout, create_output_layout
from genomelens.engines.jcvi.adapter import JcviEngineAdapter
from genomelens.engines.jcvi.manifest_builder import JcviManifestBuilder
from genomelens.toolchain.runtime.resource_locator import locate_engine

# endregion


class SubmoduleDispatcher:
    """SubmoduleDispatcher：负责子模块请求到执行层的调度"""

    def dispatch(self, request: SubmoduleRequest, signal_bus: SignalBus | None = None) -> RunSummary:
        """运行一个 SubmoduleRequest"""

        registry = get_submodule_registry()
        spec = registry.get(request.module_id)
        if spec is None:
            raise InputValidationError(f"未知的子模块：{request.module_id}")

        errors = PortSystem.validate_bindings(spec.inputs, request.inputs)
        if errors:
            raise InputValidationError("; ".join(errors))

        set_state = self._set_state(signal_bus or SignalBus())
        summary = self._dispatch_by_kind(request, spec, set_state)
        if isinstance(summary, dict):
            summary = RunSummary.from_json(summary)

        self._write_request_snapshot(request, summary)
        return summary

    def _dispatch_by_kind(
        self,
        request: SubmoduleRequest,
        spec: SubModuleSpec,
        set_state: Callable[[WorkflowState], None],
    ) -> RunSummary:
        """根据子模块类型选择执行路径"""

        if spec.engine_workflow == "graphics_histogram":
            return self._run_lightweight(request, to_histogram_request(request), "graphics_histogram")
        if spec.engine_workflow == "graphics_heatmap":
            return self._run_lightweight(request, to_heatmap_request(request), "graphics_heatmap")
        if spec.module_kind == "lightweight":
            payload = to_synteny_like_request(request, spec.engine_workflow)
            return self._run_lightweight(request, payload, "pairwise_synteny")
        if spec.module_id == "jcvi.graphics_karyotype_global":
            return self._run_global_karyotype(request, set_state)
        if spec.module_id == "jcvi.local_synteny_multi":
            return self._run_multi_local_synteny(request, set_state)
        raise InputValidationError(f"暂不支持的子模块：{request.module_id}")

    @staticmethod
    def _run_lightweight(request: SubmoduleRequest, payload: object, step_kind: StepKind) -> RunSummary:
        """通过单步 ExecutionPlan 复用 PlanExecutor 执行轻量子模块"""

        plan = ExecutionPlan(
            plan_id=request.module_id,
            workflow_id=request.module_id,
            outdir=Path(request.output.directory).expanduser().resolve(strict=False),
            force=request.output.force,
            steps=[
                ExecutionStep(
                    step_id=request.module_id,
                    kind=step_kind,
                    payload=payload,
                    outputs=[StepOutputRef("figures", "figure")],
                )
            ],
        )
        return PlanExecutor().execute(plan, SignalBus())

    def _run_global_karyotype(
        self,
        request: SubmoduleRequest,
        set_state: Callable[[WorkflowState], None],
    ) -> RunSummary:
        """直接运行 aggregate 全局核型子模块"""

        log_path = build_output_layout(request.output.directory).logs / "run.log"
        with run_with_logging(log_path, level="INFO", console=False, concise=True) as logger:
            return self._run_global_karyotype_inner(request, set_state, logger)

    def _run_global_karyotype_inner(
        self,
        request: SubmoduleRequest,
        set_state: Callable[[WorkflowState], None],
        logger: Any,
    ) -> RunSummary:
        set_state(WorkflowState.VALIDATING_INPUTS)
        ports = request.inputs
        parameters = request.parameters
        tracks = self._parse_tracks(ports.get("tracks"))
        edges = self._parse_edges(ports.get("edges"))
        if len(tracks) < 2 or not edges:
            raise InputValidationError("global_karyotype 至少需要两个 track 和至少一条 edge")

        set_state(WorkflowState.PREPARING_WORKSPACE)
        layout = create_output_layout(request.output.directory, force=request.output.force)

        set_state(WorkflowState.CHECKING_TOOLCHAIN)
        engine = locate_engine(explicit=request.runtime.jcvi_engine)
        if not engine.ok:
            raise RuntimeError(engine.message or "jcvi-genomelens executable was not found")

        adapter = JcviEngineAdapter(engine.path)
        with task_scope(logger, task_id=request.module_id, step="probe_engine"):
            probe = adapter.probe()
        probe["engine_path"] = engine.path

        set_state(WorkflowState.WRITING_MANIFEST)
        manifest = JcviManifestBuilder().build_global_karyotype_manifest(
            tracks=tracks,
            edges=edges,
            blastn_path=request.runtime.blastn,
            makeblastdb_path=request.runtime.makeblastdb,
            formats=request.output.formats,
            figsize=str(parameters.get("figsize") or ""),
            dpi=int(cast(int, parameters.get("dpi")) or 300),
            auto_optimization={
                "optimize_figsize": bool(parameters.get("optimize_figsize")),
                "rewrite_layout_links": bool(parameters.get("rewrite_layout_links")),
                "optimize_karyotype_labels": bool(parameters.get("optimize_karyotype_labels")),
            },
            log_level=str(request.runtime.log_level or "INFO").upper(),
        )
        adapter.write_manifest(manifest, layout.manifest)
        shutil.copy2(layout.manifest, layout.inputs / "input_manifest.json")

        set_state(WorkflowState.RUNNING_ENGINE)
        with task_scope(logger, task_id=request.module_id, step="run_engine"):
            engine_result = adapter.run_manifest(layout.manifest, layout.jcvi)

        set_state(WorkflowState.FINALIZING)
        figures = [str(item) for item in cast(list[object], engine_result.artifacts.get("figures")) or []]
        final_figures = archive_figures(figures, layout.figures)
        status = "SUCCEEDED" if engine_result.status == "ok" else "FAILED"

        summary = build_run_summary(
            status=status,
            workflow="mcscan",
            method="mcscan",
            task={"task_id": request.module_id, "task_type": "global_synteny", "workflow": "graphics_karyotype_global"},
            species=[{"name": track["name"], "role": "track", "input_mode": "bed_cds"} for track in tracks],
            final_figures=final_figures,
            artifact_index=self._aggregate_artifact_index(layout, final_figures, []),
            logs={"run_log": str(layout.logs / "run.log")},
            ui=ui_block(
                status,
                final_figures,
                summary_path=layout.run_summary,
                log_path=layout.logs / "run.log",
            ),
            scoring=scoring_placeholder(),
            extensions={
                "jcvi_backend": "jcvi-genomelens-engine",
                "jcvi_workflow": "graphics_karyotype_global",
                "jcvi_engine_path": str(probe.get("engine_path") or ""),
                "engine_summary_path": str(engine_result.summary_path),
            },
        )
        write_run_summary(layout, summary)
        set_state(WorkflowState.SUCCEEDED if status == "SUCCEEDED" else WorkflowState.FAILED)
        return summary

    def _run_multi_local_synteny(
        self,
        request: SubmoduleRequest,
        set_state: Callable[[WorkflowState], None],
    ) -> RunSummary:
        """直接运行 aggregate 多物种局部共线性子模块"""

        log_path = build_output_layout(request.output.directory).logs / "run.log"
        with run_with_logging(log_path, level="INFO", console=False, concise=True) as logger:
            return self._run_multi_local_synteny_inner(request, set_state, logger)

    def _run_multi_local_synteny_inner(
        self,
        request: SubmoduleRequest,
        set_state: Callable[[WorkflowState], None],
        logger: Any,
    ) -> RunSummary:
        set_state(WorkflowState.VALIDATING_INPUTS)
        ports = request.inputs
        parameters = request.parameters
        tracks = self._parse_tracks(ports.get("tracks"))
        blocks = self._path(ports.get("blocks"))
        bed = self._path(ports.get("bed"))
        target_genes = self._parse_target_genes(ports.get("target_genes") or parameters.get("target_genes"))
        if len(tracks) < 2 or blocks is None or bed is None or not target_genes:
            raise InputValidationError("local_synteny_multi 需要 tracks、blocks、bed 和 target_genes")

        set_state(WorkflowState.PREPARING_WORKSPACE)
        layout = create_output_layout(request.output.directory, force=request.output.force)

        set_state(WorkflowState.CHECKING_TOOLCHAIN)
        engine = locate_engine(explicit=request.runtime.jcvi_engine)
        if not engine.ok:
            raise RuntimeError(engine.message or "jcvi-genomelens executable was not found")

        adapter = JcviEngineAdapter(engine.path)
        with task_scope(logger, task_id=request.module_id, step="probe_engine"):
            probe = adapter.probe()
        probe["engine_path"] = engine.path

        set_state(WorkflowState.WRITING_MANIFEST)
        manifest = JcviManifestBuilder().build_multi_local_synteny_manifest(
            tracks=tracks,
            blocks=blocks,
            bed=bed,
            formats=request.output.formats,
            target_gene_ids=target_genes,
            label_targets=bool(parameters.get("label_targets")),
            glyphstyle=str(parameters.get("glyphstyle") or ""),
            glyphcolor=str(parameters.get("glyphcolor") or ""),
            shadestyle=str(parameters.get("shadestyle") or ""),
            figsize=str(parameters.get("figsize") or ""),
            dpi=int(cast(int, parameters.get("dpi")) or 300),
            auto_optimization={
                "optimize_figsize": bool(parameters.get("optimize_figsize")),
                "rewrite_layout_links": bool(parameters.get("rewrite_layout_links")),
                "optimize_karyotype_labels": bool(parameters.get("optimize_karyotype_labels")),
            },
            use_native_local_synteny_renderer=bool(parameters.get("use_native_local_synteny_renderer")),
        )
        adapter.write_manifest(manifest, layout.manifest)
        shutil.copy2(layout.manifest, layout.inputs / "input_manifest.json")

        set_state(WorkflowState.RUNNING_ENGINE)
        with task_scope(logger, task_id=request.module_id, step="run_engine"):
            engine_result = adapter.run_manifest(layout.manifest, layout.jcvi)

        set_state(WorkflowState.FINALIZING)
        figures = [str(item) for item in cast(list[object], engine_result.artifacts.get("figures")) or []]
        final_figures = archive_figures(figures, layout.figures)
        status = "SUCCEEDED" if engine_result.status == "ok" else "FAILED"

        summary = build_run_summary(
            status=status,
            workflow="mcscan",
            method="mcscan",
            task={
                "task_id": request.module_id,
                "task_type": "multi_species_local_synteny",
                "workflow": "local_synteny_multi",
            },
            species=[{"name": track["name"], "role": "track", "input_mode": "bed_cds"} for track in tracks],
            final_figures=final_figures,
            artifact_index=self._aggregate_artifact_index(layout, final_figures, []),
            logs={"run_log": str(layout.logs / "run.log")},
            ui=ui_block(
                status,
                final_figures,
                summary_path=layout.run_summary,
                log_path=layout.logs / "run.log",
            ),
            scoring=scoring_placeholder(),
            extensions={
                "jcvi_backend": "jcvi-genomelens-engine",
                "jcvi_workflow": "local_synteny_multi",
                "jcvi_engine_path": str(probe.get("engine_path") or ""),
                "engine_summary_path": str(engine_result.summary_path),
            },
        )
        write_run_summary(layout, summary)
        set_state(WorkflowState.SUCCEEDED if status == "SUCCEEDED" else WorkflowState.FAILED)
        return summary

    @staticmethod
    def _parse_tracks(value: object) -> list[dict[str, str]]:
        """解析 tracks 端口"""

        if not isinstance(value, list):
            raise InputValidationError("tracks 必须是对象列表")
        tracks: list[dict[str, str]] = []
        for item in value:
            if not isinstance(item, dict):
                raise InputValidationError("tracks 每一项必须是包含 name 与 bed 的字典")
            name = str(item.get("name") or "").strip()
            bed = str(item.get("bed") or "").strip()
            if not name or not bed:
                raise InputValidationError("track 必须包含 name 与 bed")
            tracks.append({"name": name, "bed": bed})
        return tracks

    @staticmethod
    def _parse_edges(value: object) -> list[dict[str, object]]:
        """解析 edges 端口"""

        if not isinstance(value, list):
            raise InputValidationError("edges 必须是对象列表")
        edges: list[dict[str, object]] = []
        for item in value:
            if not isinstance(item, dict):
                raise InputValidationError("edges 每一项必须是字典")
            i = item.get("i")
            j = item.get("j")
            simple = str(item.get("simple") or "").strip()
            if i is None or j is None or not simple:
                raise InputValidationError("edge 必须包含 i、j、simple")
            edges.append({"i": int(i), "j": int(j), "simple": simple})
        return edges

    @staticmethod
    def _parse_target_genes(value: object) -> list[str]:
        """解析目标基因列表"""

        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str) and value.strip():
            return [value.strip()]
        return []

    @staticmethod
    def _path(value: object) -> Path | None:
        """把字符串解析为 Path"""

        if not isinstance(value, str) or not value.strip():
            return None
        return Path(value).expanduser().resolve(strict=False)

    @staticmethod
    def _aggregate_artifact_index(
        layout: Any,
        final_figures: list[str],
        extra: list[dict[str, object]],
    ) -> list[dict[str, object]]:
        """为 aggregate 子模块构造 artifact 索引"""

        records: list[dict[str, object]] = [
            item
            for item in [
                artifact_record("input_manifest", "manifest", layout.manifest, "aggregate"),
                artifact_record("run_log", "log", layout.logs / "run.log", "aggregate"),
            ]
            if item
        ]
        records.extend(extra)
        for index, figure in enumerate(final_figures, start=1):
            record = artifact_record(f"figure_{index}", "figure", figure, "aggregate", preview=True)
            if record:
                records.append(record)
        return records

    def _write_request_snapshot(self, request: SubmoduleRequest, summary: RunSummary) -> None:
        """写出子模块请求快照并回填 run_summary"""

        outdir = Path(request.output.directory).expanduser().resolve(strict=False)
        request_path = write_task_request(request, outdir / "inputs" / "submodule_request.json")
        data = summary.to_json()
        data["analysis_request_path"] = str(request_path)

        run_summary_path = outdir / "report" / "run_summary.json"
        if run_summary_path.is_file():
            run_summary_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    @staticmethod
    def _set_state(signal_bus: SignalBus) -> Callable[[WorkflowState], None]:
        """构造状态发射函数"""

        def set_state(state: WorkflowState) -> None:
            signal_bus.emit("state", state=state.value)

        return set_state


__all__ = ["SubmoduleDispatcher"]
