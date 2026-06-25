"""TaskDispatcher：统一分发 WorkflowRequest 与 SubmoduleRequest"""

# region import
from __future__ import annotations

from genomelens.analysis.dispatchers.submodule_dispatcher import SubmoduleDispatcher
from genomelens.analysis.dispatchers.workflow_dispatcher import WorkflowDispatcher
from genomelens.analysis.requests.models import WorkflowRequest
from genomelens.analysis.requests.submodule_models import SubmoduleRequest
from genomelens.app.events.signal_bus import SignalBus
from genomelens.contracts.summaries import RunSummary

# endregion


class TaskDispatcher:
    """TaskDispatcher：按请求类型委托给对应调度器"""

    def dispatch(
        self,
        request: WorkflowRequest | SubmoduleRequest,
        signal_bus: SignalBus | None = None,
    ) -> RunSummary:
        """分发并运行一个任务请求"""

        if isinstance(request, WorkflowRequest):
            return WorkflowDispatcher().dispatch(request, signal_bus)
        if isinstance(request, SubmoduleRequest):
            return SubmoduleDispatcher().dispatch(request, signal_bus)
        msg = f"unsupported request type: {type(request).__name__}"
        raise TypeError(msg)


__all__ = ["TaskDispatcher"]
