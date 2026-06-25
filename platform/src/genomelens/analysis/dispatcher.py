"""WorkflowRequest dispatcher(工作流请求调度器)

保留 AnalysisDispatcher 作为公开入口的薄 facade，内部委托给 TaskDispatcher。
"""

# region import
from __future__ import annotations

from genomelens.analysis.dispatchers.task_dispatcher import TaskDispatcher
from genomelens.analysis.requests.models import WorkflowRequest
from genomelens.app.events.signal_bus import SignalBus
from genomelens.contracts.summaries import RunSummary

# endregion


class AnalysisDispatcher:
    """统一调度公开分析请求"""

    def dispatch(self, request: WorkflowRequest, signal_bus: SignalBus | None = None) -> RunSummary:
        """运行一个 WorkflowRequest（兼容旧调用点）"""

        return TaskDispatcher().dispatch(request, signal_bus)


__all__ = ["AnalysisDispatcher"]
