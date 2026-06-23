"""One-stop workflow runner：按 workflow_id 路由到专用 runner"""

# region import
from __future__ import annotations

from dataclasses import replace

from genomelens.analysis.methods.execution_request_mapping import to_mcscan_request
from genomelens.analysis.requests.models import AnalysisRequest
from genomelens.app.controller.runners.multi_species_runner import run_multi_species_mcscan
from genomelens.app.controller.runners.pairwise_runner import run_pairwise_mcscan
from genomelens.app.controller.runners.reference_vs_targets_runner import run_reference_vs_targets_mcscan
from genomelens.app.controller.state_machine import WorkflowState
from genomelens.app.controller.workflow_provider import WorkflowProvider
from genomelens.app.errors.exceptions import InputValidationError
from genomelens.app.events.signal_bus import SignalBus
from genomelens.core.summary_models import RunSummary

# endregion


class OneStopWorkflowRunner:
    """OneStopWorkflowRunner：一站式工作流专用执行路径

    目前只有单一集成工作流 ``synteny``；根据请求特征在内部选择 pairwise /
    multi-species / reference-vs-targets 执行路径，并在运行摘要中回写 workflow_id。
    """

    def run(
        self,
        request: AnalysisRequest,
        _provider: WorkflowProvider,
        signal_bus: SignalBus,
    ) -> RunSummary:
        """执行一站式工作流请求"""

        workflow_id = request.one_stop_workflow_id
        if not workflow_id:
            raise InputValidationError("task_kind=one_stop 时必须提供 one_stop_workflow_id")

        if workflow_id != "synteny":
            raise InputValidationError(f"未知的一站式工作流：{workflow_id}")

        def _set_state(state: WorkflowState) -> None:
            signal_bus.emit("state", state=state.value)

        mcscan_request = to_mcscan_request(request)
        species_count = len(request.input.species)
        method_config = request.method_config
        target_gene_ids = method_config.get("target_gene_ids") or []

        if target_gene_ids:
            summary = run_reference_vs_targets_mcscan(_set_state, mcscan_request)
        elif species_count == 2:
            summary = run_pairwise_mcscan(_set_state, mcscan_request)
        elif species_count >= 3:
            summary = run_multi_species_mcscan(_set_state, mcscan_request)
        else:
            raise InputValidationError("synteny 工作流至少需要 2 个物种")

        return replace(summary, task={**summary.task, "one_stop_workflow_id": workflow_id})
