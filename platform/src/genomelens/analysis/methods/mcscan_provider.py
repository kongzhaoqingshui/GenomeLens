"""MCscan 工作流提供者"""

# region import
from __future__ import annotations

from genomelens.analysis.execution_models import HistogramExecutionRequest, McscanExecutionRequest
from genomelens.analysis.methods.execution_request_mapping import (
    to_heatmap_request,
    to_histogram_request,
    to_mcscan_request,
)
from genomelens.analysis.requests.models import AnalysisRequest
from genomelens.app.controller.state_machine import WorkflowState
from genomelens.app.controller.workflow_provider import WorkflowProvider
from genomelens.app.events.signal_bus import SignalBus
from genomelens.core.summary_models import RunSummary

# endregion


class McscanWorkflowProvider(WorkflowProvider):
    """McscanWorkflowProvider：MCscan/JCVI 方法的 WorkflowProvider 实现

    当前只支持 pairwise 执行；多物种场景由 `PairwiseAggregatedMultiSpecies`
    策略拆成多个 pairwise 子任务后调用本 provider。
    """

    @property
    def name(self) -> str:
        """返回方法名称"""

        return "mcscan"

    def supports_native_multi_species(self) -> bool:
        """当前 MCscan 引擎本身不提供原生多物种能力"""

        return False

    def run(self, request: AnalysisRequest, signal_bus: SignalBus) -> RunSummary:
        """运行一次 MCscan 分析任务（预期为 2 个物种的 pairwise 请求）"""

        from genomelens.app.controller.runners.heatmap_runner import run_heatmap_workflow
        from genomelens.app.controller.runners.histogram_runner import run_histogram_workflow
        from genomelens.app.controller.runners.pairwise_runner import run_pairwise_mcscan

        def _set_state(state: WorkflowState) -> None:
            signal_bus.emit("state", state=state.value)

        workflow = str(request.method_config.get("workflow") or "")
        if workflow == "graphics_histogram":
            histogram_request = to_histogram_request(request)
            return run_histogram_workflow(_set_state, histogram_request)
        if workflow == "graphics_heatmap":
            heatmap_request = to_heatmap_request(request)
            return run_heatmap_workflow(_set_state, heatmap_request)

        mcscan_request = to_mcscan_request(request)
        return run_pairwise_mcscan(_set_state, mcscan_request)


def _to_mcscan_request(request: AnalysisRequest) -> McscanExecutionRequest:
    """把 AnalysisRequest 转成 McscanExecutionRequest（provider 内部使用的便利函数）"""

    return to_mcscan_request(request)


def _to_histogram_request(request: AnalysisRequest) -> HistogramExecutionRequest:
    """把 AnalysisRequest 转成 HistogramExecutionRequest（provider 内部使用的便利函数）"""

    return to_histogram_request(request)
