"""Tests for WorkflowOrchestrator task_kind routing."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from genomelens.analysis.requests.models import AnalysisInput, AnalysisOutput, AnalysisRequest
from genomelens.app.controller.orchestrator import WorkflowOrchestrator
from genomelens.app.errors.exceptions import InputValidationError
from genomelens.app.events.signal_bus import SignalBus
from genomelens.core.summary_models import RunSummary, ScoringBlock, UiBlock


def _minimal_request(**overrides) -> AnalysisRequest:
    defaults: dict[str, object] = {
        "method": "mcscan",
        "input": AnalysisInput(mode="auto_directory"),
        "output": AnalysisOutput(directory="out"),
    }
    defaults.update(overrides)
    return AnalysisRequest(**defaults)  # type: ignore[arg-type]


def _dummy_summary(**extra) -> RunSummary:
    return RunSummary(
        status="SUCCEEDED",
        schema_version=2,
        workflow="mcscan",
        task=dict(extra),
        species=[],
        final_figures=[],
        artifact_index=[],
        logs={},
        ui=UiBlock("SUCCEEDED", 1.0, [], "summary.json", "run.log"),
        scoring=ScoringBlock(),
    )


def test_orchestrator_routes_sub_module_histogram(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_to_histogram(request):
        captured["to_histogram"] = request
        return MagicMock()

    def fake_run_histogram(set_state, request):
        captured["called"] = True
        captured["request"] = request
        return _dummy_summary(workflow="graphics_histogram")

    monkeypatch.setattr(
        "genomelens.app.controller.runners.submodule_runner.to_histogram_request",
        fake_to_histogram,
    )
    monkeypatch.setattr(
        "genomelens.app.controller.runners.submodule_runner.run_histogram_workflow",
        fake_run_histogram,
    )

    request = _minimal_request(
        task_kind="sub_module",
        sub_module_id="jcvi.graphics_histogram",
        port_bindings={"numeric_files": ["numbers.txt"]},
    )
    provider = MagicMock()
    summary = WorkflowOrchestrator().run(request, provider, SignalBus())

    assert captured["called"] is True
    assert captured["to_histogram"] is not None
    assert summary.task["sub_module_id"] == "jcvi.graphics_histogram"


def test_orchestrator_routes_one_stop_synteny_pairwise(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_to_mcscan(request):
        captured["to_mcscan"] = request
        return MagicMock()

    def fake_run_pairwise(set_state, request):
        captured["called"] = True
        return _dummy_summary(task_type="pairwise_synteny")

    monkeypatch.setattr(
        "genomelens.app.controller.runners.onestop_runner.to_mcscan_request",
        fake_to_mcscan,
    )
    monkeypatch.setattr(
        "genomelens.app.controller.runners.onestop_runner.run_pairwise_mcscan",
        fake_run_pairwise,
    )

    request = _minimal_request(
        task_kind="one_stop",
        one_stop_workflow_id="synteny",
        input=AnalysisInput(
            mode="auto_directory",
            species=[{"name": "a"}, {"name": "b"}],
        ),
    )
    provider = MagicMock()
    summary = WorkflowOrchestrator().run(request, provider, SignalBus())

    assert captured["called"] is True
    assert captured["to_mcscan"] is not None
    assert summary.task["one_stop_workflow_id"] == "synteny"


def test_orchestrator_routes_one_stop_synteny_reference_vs_targets(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_to_mcscan(request):
        captured["to_mcscan"] = request
        return MagicMock()

    def fake_run_reference_vs_targets(set_state, request):
        captured["called"] = True
        return _dummy_summary(task_type="reference_vs_targets")

    monkeypatch.setattr(
        "genomelens.app.controller.runners.onestop_runner.to_mcscan_request",
        fake_to_mcscan,
    )
    monkeypatch.setattr(
        "genomelens.app.controller.runners.onestop_runner.run_reference_vs_targets_mcscan",
        fake_run_reference_vs_targets,
    )

    request = _minimal_request(
        task_kind="one_stop",
        one_stop_workflow_id="synteny",
        input=AnalysisInput(
            mode="auto_directory",
            species=[{"name": "ref"}, {"name": "tgt"}],
        ),
        method_config={"target_gene_ids": ["g1"]},
    )
    provider = MagicMock()
    summary = WorkflowOrchestrator().run(request, provider, SignalBus())

    assert captured["called"] is True
    assert summary.task["one_stop_workflow_id"] == "synteny"


def test_orchestrator_routes_one_stop_synteny_multi_species(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_to_mcscan(request):
        captured["to_mcscan"] = request
        return MagicMock()

    def fake_run_multi_species(set_state, request):
        captured["called"] = True
        return _dummy_summary(task_type="multi_species_synteny")

    monkeypatch.setattr(
        "genomelens.app.controller.runners.onestop_runner.to_mcscan_request",
        fake_to_mcscan,
    )
    monkeypatch.setattr(
        "genomelens.app.controller.runners.onestop_runner.run_multi_species_mcscan",
        fake_run_multi_species,
    )

    request = _minimal_request(
        task_kind="one_stop",
        one_stop_workflow_id="synteny",
        input=AnalysisInput(
            mode="auto_directory",
            species=[{"name": "a"}, {"name": "b"}, {"name": "c"}],
        ),
    )
    provider = MagicMock()
    summary = WorkflowOrchestrator().run(request, provider, SignalBus())

    assert captured["called"] is True
    assert summary.task["one_stop_workflow_id"] == "synteny"


def test_orchestrator_routes_composition_raises() -> None:
    request = _minimal_request(task_kind="composition")
    provider = MagicMock()
    with pytest.raises(InputValidationError):
        WorkflowOrchestrator().run(request, provider, SignalBus())


def test_orchestrator_legacy_two_species_calls_provider() -> None:
    request = _minimal_request(
        input=AnalysisInput(
            mode="bed_cds",
            species=[
                {"name": "query", "input_mode": "bed_cds", "bed": "q.bed", "cds": "q.cds"},
                {"name": "subject", "input_mode": "bed_cds", "bed": "s.bed", "cds": "s.cds"},
            ],
        ),
    )
    provider = MagicMock()
    provider.supports_native_multi_species.return_value = False
    provider.run.return_value = _dummy_summary()

    summary = WorkflowOrchestrator().run(request, provider, SignalBus())

    provider.run.assert_called_once()
    assert summary.status == "SUCCEEDED"


def test_submodule_runner_validates_missing_required_port() -> None:
    from genomelens.app.controller.runners.submodule_runner import SubModuleRunner

    request = _minimal_request(
        task_kind="sub_module",
        sub_module_id="jcvi.graphics_histogram",
        port_bindings={},
    )
    with pytest.raises(InputValidationError):
        SubModuleRunner().run(request, MagicMock(), SignalBus())


def test_onestop_runner_rejects_unknown_workflow() -> None:
    from genomelens.app.controller.runners.onestop_runner import OneStopWorkflowRunner

    request = _minimal_request(
        task_kind="one_stop",
        one_stop_workflow_id="pairwise_synteny",
    )
    with pytest.raises(InputValidationError):
        OneStopWorkflowRunner().run(request, MagicMock(), SignalBus())


def test_onestop_runner_rejects_too_few_species(tmp_path: Path) -> None:
    from genomelens.app.controller.runners.onestop_runner import OneStopWorkflowRunner

    (tmp_path / "a.bed").write_text("", encoding="utf-8")
    (tmp_path / "a.cds").write_text("", encoding="utf-8")
    request = _minimal_request(
        task_kind="one_stop",
        one_stop_workflow_id="synteny",
        input=AnalysisInput(mode="auto_directory", directory=str(tmp_path), species=[]),
    )
    with pytest.raises(InputValidationError):
        OneStopWorkflowRunner().run(request, MagicMock(), SignalBus())


def test_onestop_runner_rejects_missing_workflow_id() -> None:
    from genomelens.app.controller.runners.onestop_runner import OneStopWorkflowRunner

    request = _minimal_request(task_kind="one_stop")
    with pytest.raises(InputValidationError):
        OneStopWorkflowRunner().run(request, MagicMock(), SignalBus())
