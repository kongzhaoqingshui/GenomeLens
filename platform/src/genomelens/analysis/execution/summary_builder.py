"""执行层 RunSummary 构造辅助函数"""

# region import
from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from genomelens.analysis.execution.artifact_builder import artifact_record
from genomelens.analysis.planning.models import SyntenyExecutionRequest
from genomelens.app.errors import messages
from genomelens.contracts.extensions.mcscan import McscanSummaryExtension
from genomelens.contracts.summaries import ChildRunRecord, RunSummary, ScoringBlock, UiBlock

# endregion


if TYPE_CHECKING:
    from genomelens.data.workspace.output_layout import OutputLayout


# region 请求元数据辅助函数
def species_summary(request: SyntenyExecutionRequest) -> list[dict[str, object]]:
    """把 request.species 转成 summary 列表"""

    # 摘要角色沿用 reference / target / additional，便于 CLI 和 GUI 稳定展示
    return [
        {
            "name": species.name,
            "role": "reference" if index == 0 else "target" if index == 1 else "additional",
            "input_mode": species.mode,
        }
        for index, species in enumerate(request.species)
    ]


def scoring_placeholder() -> ScoringBlock:
    """统一的 scoring(评分) 占位块

    注意：这是未来 ML Scoring Layer 接入前的占位。后续把评分结果纳入统一
    artifact/summary schema 时，应从这里开始收口，而不是再在各工作流里手写。
    """

    return ScoringBlock(message=messages.SCORING_NOT_RUN)


def ui_block(
    status: str,
    final_figures: list[str],
    *,
    summary_path: Path,
    log_path: Path,
) -> UiBlock:
    """统一的 ui(界面) 块。GUI/工作台读取的渲染契约，两类工作流共用同一构造"""

    return UiBlock(
        state=status,
        progress=1.0 if status == "SUCCEEDED" else 0.0,
        primary_figures=list(final_figures),
        summary_path=str(summary_path),
        log_path=str(log_path),
    )


def build_run_summary(
    *,
    status: str,
    workflow: str,
    method: str,
    task: dict[str, object],
    species: list[dict[str, object]],
    final_figures: list[str],
    artifact_index: list[dict[str, object]],
    logs: dict[str, str],
    ui: UiBlock,
    scoring: ScoringBlock,
    extensions: dict[str, object],
    child_runs: list[ChildRunRecord] | None = None,
) -> RunSummary:
    """统一构造 RunSummary，消除各 runner 和 CLI 命令中的重复拼装"""

    return RunSummary(
        status=status,
        schema_version=3,
        workflow=workflow,
        method=method,
        task=task,
        species=species,
        final_figures=final_figures,
        artifact_index=artifact_index,
        logs=logs,
        ui=ui,
        scoring=scoring,
        extensions=extensions,
        child_runs=child_runs or [],
    )


def pair_id(species_a_name: str, species_b_name: str) -> str:
    """两个物种名称组成 pair id"""

    return f"{species_a_name}__{species_b_name}"


def write_run_summary(layout: OutputLayout, summary: RunSummary) -> None:
    """把 run_summary 写入磁盘"""

    layout.run_summary.write_text(json.dumps(summary.to_json(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_multi_run_summary(
    request: SyntenyExecutionRequest,
    layout: OutputLayout,
    pairwise_jobs: list[ChildRunRecord],
    final_figures: list[str],
    *,
    pairing_strategy: str,
    global_figures: list[str] | None = None,
    reference_name: str | None = None,
    native_multi_species: bool = False,
    native_layout: dict[str, object] | None = None,
    multi_species_local_figures: list[str] | None = None,
    task_type_override: str | None = None,
    species_a_name: str | None = None,
    species_b_name: str | None = None,
    extra_extensions: dict[str, object] | None = None,
) -> RunSummary:
    """为 multi-species 或 reference-vs-targets 构造顶层 RunSummary"""

    # 顶层多物种状态以所有子任务是否成功为准；局部失败仍保留已产出的子任务图件
    status = "SUCCEEDED" if all(item.status == "SUCCEEDED" for item in pairwise_jobs) else "FAILED"

    artifact_index = [
        item
        for item in [
            artifact_record("input_manifest", "manifest", layout.manifest, request.jcvi_workflow),
            artifact_record("run_log", "log", layout.logs / "run.log", request.jcvi_workflow),
        ]
        if item
    ]

    # 多物种顶层只归档聚合后的图件，不重复塞入每个子任务的全部中间产物
    for index, figure in enumerate(final_figures, start=1):
        record = artifact_record(f"figure_{index}", "figure", figure, request.jcvi_workflow, preview=True)
        if record:
            artifact_index.append(record)

    task = request.task_spec.to_manifest_json()
    if task_type_override:
        task = {**task, "task_type": task_type_override}

    extension = McscanSummaryExtension(
        jcvi_backend="jcvi-genomelens-engine",
        jcvi_workflow=request.jcvi_workflow,
        species_count=len(request.species),
        pairing_strategy=pairing_strategy,
        child_run_count=len(pairwise_jobs),
        global_figures=global_figures or [],
        multi_species_local_figures=multi_species_local_figures or [],
        reference_name=reference_name,
        native_multi_species=native_multi_species,
        native_layout=native_layout,
        species_a_name=species_a_name,
        species_b_name=species_b_name,
    )
    extensions = extension.to_dict()
    if extra_extensions:
        extensions.update(extra_extensions)

    return build_run_summary(
        status=status,
        workflow="mcscan",
        method="mcscan",
        task=task,
        species=species_summary(request),
        final_figures=final_figures,
        artifact_index=artifact_index,
        logs={"run_log": str(layout.logs / "run.log")},
        ui=ui_block(
            status,
            final_figures,
            summary_path=layout.run_summary,
            log_path=layout.logs / "run.log",
        ),
        scoring=scoring_placeholder(),
        extensions=extensions,
        child_runs=pairwise_jobs,
    )


# endregion
