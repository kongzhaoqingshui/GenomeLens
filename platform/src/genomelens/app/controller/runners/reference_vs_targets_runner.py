"""Reference-vs-targets MCscan runner：参考物种对多个目标物种运行局部共线性"""

# region import
from __future__ import annotations

import logging
from collections.abc import Callable

from genomelens.app.controller.runners._shared import (
    build_multi_run_summary,
    prepare_composite_workspace,
    run_composite_pairwise_jobs,
    write_run_summary,
)
from genomelens.app.controller.runners.local_synteny_aggregate import build_multi_species_local_synteny
from genomelens.app.controller.state_machine import WorkflowState
from genomelens.core.jcvi_adapter.adapter_models import McscanRequest
from genomelens.core.summary_models import PairwiseJobSummary, RunSummary
from genomelens.data.logging.log_setup import close_logging, logger_name_for_path
from genomelens.data.logging.task_log import task_scope
from genomelens.data.workspace.output_layout import OutputLayout, build_output_layout

# endregion


def _prepare_reference_workspace(
    set_state: Callable[[WorkflowState], None],
    request: McscanRequest,
) -> tuple[OutputLayout, dict[str, object]]:
    """校验请求、创建工作区并写入顶层 manifest"""

    reference = request.query
    targets = [request.subject, *request.additional_species]
    return prepare_composite_workspace(
        set_state,
        request,
        pairing_strategy="reference_vs_targets",
        logger_message="Starting GenomeLens reference-vs-targets workflow",
        extra_manifest_fields={
            "pair_count": len(targets),
            "reference_name": reference.name,
            "target_names": [t.name for t in targets],
        },
    )


def _run_reference_pairwise_jobs(
    set_state: Callable[[WorkflowState], None],
    request: McscanRequest,
    layout: OutputLayout,
) -> tuple[list[PairwiseJobSummary], list[str]]:
    """以参考物种为中心，分别与每个目标物种运行 pairwise 子任务"""

    reference = request.query
    targets = [request.subject, *request.additional_species]
    return run_composite_pairwise_jobs(
        set_state,
        request,
        layout,
        [(reference, target) for target in targets],
    )


def _run_reference_vs_targets_mcscan(
    set_state: Callable[[WorkflowState], None],
    request: McscanRequest,
) -> RunSummary:
    """以参考物种为中心，分别与每个目标物种运行局部共线性"""

    layout, _manifest = _prepare_reference_workspace(set_state, request)
    pairwise_jobs, final_figures = _run_reference_pairwise_jobs(set_state, request, layout)
    multi_species_local_figures = build_multi_species_local_synteny(request, pairwise_jobs, layout)
    final_figures.extend(multi_species_local_figures)

    reference = request.query
    logger = logging.getLogger(logger_name_for_path(layout.logs / "run.log"))
    with task_scope(logger, task_id=request.task_id, step="write_reference_summary"):
        run_summary = build_multi_run_summary(
            request,
            layout,
            pairwise_jobs,
            final_figures,
            pairing_strategy="reference_vs_targets",
            reference_name=reference.name,
            multi_species_local_figures=multi_species_local_figures,
        )

    write_run_summary(layout, run_summary)
    set_state(WorkflowState.SUCCEEDED if run_summary.status == "SUCCEEDED" else WorkflowState.FAILED)

    return run_summary


def run_reference_vs_targets_mcscan(
    set_state: Callable[[WorkflowState], None],
    request: McscanRequest,
) -> RunSummary:
    """Run reference-vs-targets MCscan and release task log handles."""

    log_path = build_output_layout(request.outdir).logs / "run.log"
    logger_name = logger_name_for_path(log_path)
    try:
        return _run_reference_vs_targets_mcscan(set_state, request)
    finally:
        close_logging(logger_name)
