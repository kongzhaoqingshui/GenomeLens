from unittest.mock import MagicMock

from genomelens.analysis.requests.models import WorkflowOutput, WorkflowRequest, WorkflowSpeciesInput
from genomelens.app.controller.orchestrator import WorkflowOrchestrator
from genomelens.app.events.signal_bus import SignalBus
from genomelens.contracts.summaries import RunSummary, ScoringBlock, UiBlock


def _request() -> WorkflowRequest:
    return WorkflowRequest(
        workflow_id="synteny",
        species=[
            WorkflowSpeciesInput(name="A", input_mode="bed_cds", bed="A.bed", cds="A.cds"),
            WorkflowSpeciesInput(name="B", input_mode="bed_cds", bed="B.bed", cds="B.cds"),
        ],
        output=WorkflowOutput(directory="out"),
    )


def _summary() -> RunSummary:
    return RunSummary(
        status="SUCCEEDED",
        schema_version=3,
        workflow="synteny",
        task={},
        species=[],
        final_figures=[],
        artifact_index=[],
        logs={},
        ui=UiBlock("SUCCEEDED", 1.0, [], "summary.json", "run.log"),
        scoring=ScoringBlock(),
    )


def test_orchestrator_uses_unified_plan_executor(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class FakePlanner:
        def build(self, request: WorkflowRequest) -> object:
            captured["request"] = request
            return "plan"

    class FakeExecutor:
        def execute(self, plan: object, signal_bus: SignalBus) -> RunSummary:
            captured["plan"] = plan
            captured["signal_bus"] = signal_bus
            return _summary()

    monkeypatch.setattr("genomelens.app.controller.orchestrator.WorkflowPlanner", FakePlanner)
    monkeypatch.setattr("genomelens.app.controller.orchestrator.PlanExecutor", FakeExecutor)

    signal_bus = SignalBus()
    provider = MagicMock()
    summary = WorkflowOrchestrator().run(_request(), provider, signal_bus)

    assert summary.status == "SUCCEEDED"
    assert captured["plan"] == "plan"
    assert captured["signal_bus"] is signal_bus
    provider.run.assert_not_called()


def test_orchestrator_applies_optional_scoring(monkeypatch) -> None:
    class FakePlanner:
        def build(self, request: WorkflowRequest) -> object:
            return "plan"

    class FakeExecutor:
        def execute(self, plan: object, signal_bus: SignalBus) -> RunSummary:
            return _summary()

    class FakeScoring:
        def is_available(self) -> bool:
            return True

        def score(self, summary: RunSummary, request: WorkflowRequest) -> ScoringBlock:
            return ScoringBlock(status="READY", scores=[{"score": 1.0}])

    monkeypatch.setattr("genomelens.app.controller.orchestrator.WorkflowPlanner", FakePlanner)
    monkeypatch.setattr("genomelens.app.controller.orchestrator.PlanExecutor", FakeExecutor)

    summary = WorkflowOrchestrator(scoring_provider=FakeScoring()).run(_request(), MagicMock(), SignalBus())

    assert summary.scoring.status == "READY"
    assert summary.scoring.scores == [{"score": 1.0}]
