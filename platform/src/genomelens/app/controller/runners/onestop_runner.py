"""One-stop workflow runner：按 workflow_id 路由到专用 runner"""

# region import
from __future__ import annotations

from dataclasses import replace

from genomelens.analysis.methods.mcscan_request_mapping import to_histogram_request, to_mcscan_request
from genomelens.analysis.requests.models import AnalysisRequest
from genomelens.app.controller.runners.histogram_runner import run_histogram_workflow
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

    根据 `one_stop_workflow_id` 选择已有的优化 runner，并在运行摘要中回写
    workflow_id，方便 GUI/CLI 识别实际触发的是哪条一站式工作流。
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

        def _set_state(state: WorkflowState) -> None:
            signal_bus.emit("state", state=state.value)

        if workflow_id == "multi_species_synteny":
            summary = run_multi_species_mcscan(_set_state, to_mcscan_request(request))
        elif workflow_id == "reference_vs_targets":
            summary = run_reference_vs_targets_mcscan(_set_state, to_mcscan_request(request))
        elif workflow_id == "histogram_plot":
            summary = run_histogram_workflow(_set_state, to_histogram_request(request))
        elif workflow_id in {"pairwise_synteny", "heatmap_plot"}:
            # heatmap_plot 目前与 pairwise 共享基础入口；后续可引入专用 heatmap runner
            summary = run_pairwise_mcscan(_set_state, to_mcscan_request(request))
        else:
            raise InputValidationError(f"未知的一站式工作流：{workflow_id}")

        return replace(summary, task={**summary.task, "one_stop_workflow_id": workflow_id})
