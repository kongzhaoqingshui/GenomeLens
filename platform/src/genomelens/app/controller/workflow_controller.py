"""shell(外壳) 侧分析的应用工作流控制器"""

# region import
from __future__ import annotations

from genomelens.analysis.requests.models import AnalysisRequest
from genomelens.app.controller.orchestrator import WorkflowOrchestrator
from genomelens.app.controller.state_machine import WorkflowState
from genomelens.app.controller.workflow_provider import WorkflowProvider
from genomelens.app.events.signal_bus import SignalBus
from genomelens.core.summary_models import RunSummary

# endregion


class WorkflowController:
    """WorkflowController(工作流控制器)：编排一次完整的 shell(外壳) 运行"""

    def __init__(self, signal_bus: SignalBus | None = None) -> None:
        self.signal_bus = signal_bus or SignalBus()
        self.state = WorkflowState.PENDING

    def _set_state(self, state: WorkflowState) -> None:
        self.state = state
        # 统一在状态切换点发事件，避免各 runner 自己重复维护 UI/日志通知逻辑
        self.signal_bus.emit("state", state=state.value)

    def run(self, request: AnalysisRequest, provider: WorkflowProvider) -> RunSummary:
        """根据请求与方法提供者编排执行"""

        self._set_state(WorkflowState.PENDING)
        orchestrator = WorkflowOrchestrator()
        result = orchestrator.run(request, provider, self.signal_bus)
        self._set_state(WorkflowState.SUCCEEDED if result.status == "SUCCEEDED" else WorkflowState.FAILED)
        return result
