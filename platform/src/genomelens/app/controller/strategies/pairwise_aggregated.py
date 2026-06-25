"""Compatibility strategy backed by the v2 plan executor"""

from __future__ import annotations

from genomelens.analysis.execution.executor import PlanExecutor
from genomelens.analysis.planning.planner import WorkflowPlanner
from genomelens.analysis.requests.models import WorkflowRequest
from genomelens.analysis.workflows.provider import WorkflowProvider
from genomelens.app.events.signal_bus import SignalBus
from genomelens.contracts.summaries import RunSummary


class PairwiseAggregatedMultiSpecies:
    """Execute multi-species workflows through the unified v2 plan"""

    def execute(
        self,
        request: WorkflowRequest,
        provider: WorkflowProvider,
        signal_bus: SignalBus,
    ) -> RunSummary:
        _ = provider
        return PlanExecutor().execute(WorkflowPlanner().build(request), signal_bus)
