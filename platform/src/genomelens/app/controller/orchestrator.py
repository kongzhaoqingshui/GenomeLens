"""v2 工作流规划器/执行器的兼容性外壳（compatibility shell）"""

from __future__ import annotations

import warnings
from dataclasses import replace

from genomelens.analysis.execution.executor import PlanExecutor
from genomelens.analysis.planning.planner import WorkflowPlanner
from genomelens.analysis.requests.models import WorkflowRequest
from genomelens.analysis.workflows.provider import WorkflowProvider
from genomelens.app.events.signal_bus import SignalBus
from genomelens.contracts.summaries import RunSummary
from genomelens.services.scoring import NoOpScoringProvider, ScoringProvider


class WorkflowOrchestrator:
    """通过平台执行计划运行 v2 WorkflowRequest"""

    def __init__(self, scoring_provider: ScoringProvider | None = None) -> None:
        self._scoring_provider = scoring_provider or NoOpScoringProvider()

    def run(
        self,
        request: WorkflowRequest,
        provider: WorkflowProvider,
        signal_bus: SignalBus,
    ) -> RunSummary:
        """运行请求；provider 参数用于兼容旧调用点"""

        _ = provider
        plan = WorkflowPlanner().build(request)
        result = PlanExecutor().execute(plan, signal_bus)
        return self._apply_scoring(result, request)

    def _apply_scoring(self, summary: RunSummary, request: WorkflowRequest) -> RunSummary:
        if summary.status != "SUCCEEDED" or not self._scoring_provider.is_available():
            return summary

        try:
            scoring = self._scoring_provider.score(summary, request)
            return replace(summary, scoring=scoring)
        except Exception as exc:  # noqa: BLE001 - scoring is optional enrichment
            warnings.warn(f"Scoring provider failed and was skipped: {exc}", stacklevel=2)
            return summary
