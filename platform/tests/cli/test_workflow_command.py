"""Tests for workflow metadata and v2 analyze CLI entry points."""

from __future__ import annotations

import json

from genomelens.analysis.requests.models import WorkflowRequest
from genomelens.cli.main import main
from genomelens.contracts.summaries import RunSummary, ScoringBlock, UiBlock


def _dummy_summary(**extra) -> RunSummary:
    return RunSummary(
        status="SUCCEEDED",
        schema_version=3,
        workflow="synteny",
        task=dict(extra),
        species=[],
        final_figures=[],
        artifact_index=[],
        logs={},
        ui=UiBlock("SUCCEEDED", 1.0, [], "summary.json", "run.log"),
        scoring=ScoringBlock(),
    )


def test_workflow_list_json(capsys) -> None:
    assert main(["workflow", "list", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert "one_stop_workflows" in payload
    assert "submodules" in payload
    assert "synteny" in {item["workflow_id"] for item in payload["one_stop_workflows"]}
    assert "jcvi.mcscan_pairwise" in {item["module_id"] for item in payload["submodules"]}


def test_workflow_list_filters(capsys) -> None:
    assert main(["workflow", "list", "--kind", "one_stop", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert "one_stop_workflows" in payload
    assert "submodules" not in payload

    assert main(["workflow", "list", "--kind", "sub_module", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert "submodules" in payload
    assert "one_stop_workflows" not in payload


def test_workflow_describe_json(capsys) -> None:
    assert main(["workflow", "describe", "synteny", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["workflow_id"] == "synteny"
    assert payload["kind"] == "one_stop"

    assert main(["workflow", "describe", "jcvi.graphics_histogram", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["module_id"] == "jcvi.graphics_histogram"
    assert payload["kind"] == "sub_module"


def test_workflow_describe_unknown_returns_error(capsys) -> None:
    assert main(["workflow", "describe", "not.found"]) == 2
    assert "not.found" in capsys.readouterr().err


def test_workflow_validate_submodule_ports_json(capsys) -> None:
    code = main(
        [
            "workflow",
            "validate",
            "--submodule",
            "jcvi.graphics_histogram",
            "--ports",
            json.dumps({"numeric_files": ["data.txt"]}),
            "--json",
        ]
    )
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload == {"valid": True, "errors": []}


def test_workflow_validate_submodule_missing_required(capsys) -> None:
    code = main(
        [
            "workflow",
            "validate",
            "--submodule",
            "jcvi.graphics_histogram",
            "--ports",
            json.dumps({}),
            "--json",
        ]
    )
    assert code == 3
    payload = json.loads(capsys.readouterr().out)
    assert payload["valid"] is False
    assert any("numeric_files" in err for err in payload["errors"])


def test_workflow_validate_workflow_request(tmp_path) -> None:
    request_path = tmp_path / "request.json"
    request_path.write_text(
        json.dumps(
            {
                "schema_version": 2,
                "kind": "workflow_request",
                "workflow_id": "graphics_histogram",
                "species": [],
                "reference_index": 0,
                "inputs": {},
                "parameters": {"histogram": {"inputs": ["data.txt"]}},
                "output": {"directory": str(tmp_path / "out")},
                "runtime": {},
            }
        ),
        encoding="utf-8",
    )
    assert main(["workflow", "validate", "--request", str(request_path), "--json"]) == 0


def test_analyze_schema_with_capabilities(capsys) -> None:
    assert main(["analyze", "schema", "--with-capabilities"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert "analysis_request_schema" in payload
    assert "submodules" in payload
    assert "one_stop_workflows" in payload


def test_analyze_schema_default_still_raw_schema(capsys) -> None:
    assert main(["analyze", "schema"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert "properties" in payload


def test_analyze_workflow_unknown_returns_error(capsys) -> None:
    code = main(["analyze", "workflow", "not_found", "in", "out"])
    assert code == 3
    assert "not_found" in capsys.readouterr().err


def test_analyze_submodule_unknown_returns_error(capsys) -> None:
    code = main(["analyze", "submodule", "not.found", "--input-ports", "{}", "--output-dir", "out"])
    assert code == 3
    assert "not.found" in capsys.readouterr().err


def test_analyze_submodule_missing_required_port_returns_error(capsys) -> None:
    code = main(
        [
            "analyze",
            "submodule",
            "jcvi.graphics_histogram",
            "--input-ports",
            json.dumps({}),
            "--output-dir",
            "out",
        ]
    )
    assert code == 3
    assert "histogram" in capsys.readouterr().err


def test_analyze_workflow_synteny_routes_to_workflow_request(monkeypatch, tmp_path) -> None:
    captured: dict[str, WorkflowRequest] = {}

    def fake_dispatch(self, request, signal_bus=None):
        captured["request"] = request
        return _dummy_summary()

    monkeypatch.setattr("genomelens.analysis.dispatcher.AnalysisDispatcher.dispatch", fake_dispatch)

    (tmp_path / "a.bed").write_text("", encoding="utf-8")
    (tmp_path / "a.cds").write_text("", encoding="utf-8")
    (tmp_path / "b.bed").write_text("", encoding="utf-8")
    (tmp_path / "b.cds").write_text("", encoding="utf-8")

    code = main(["analyze", "workflow", "synteny", str(tmp_path), str(tmp_path / "out"), "--force", "--json"])

    assert code == 0
    request = captured["request"]
    assert request.workflow_id == "synteny"
    assert [item.name for item in request.species] == ["a", "b"]


def test_analyze_submodule_heatmap_routes_to_workflow_request(monkeypatch, tmp_path) -> None:
    captured: dict[str, WorkflowRequest] = {}

    def fake_dispatch(self, request, signal_bus=None):
        captured["request"] = request
        return _dummy_summary()

    monkeypatch.setattr("genomelens.analysis.dispatcher.AnalysisDispatcher.dispatch", fake_dispatch)

    matrix = tmp_path / "matrix.csv"
    matrix.write_text("g,s1,s2\na,1,2\n", encoding="utf-8")
    code = main(
        [
            "analyze",
            "submodule",
            "jcvi.graphics_heatmap",
            "--input-ports",
            json.dumps({"matrix_csv": str(matrix)}),
            "--output-dir",
            str(tmp_path / "out"),
            "--force",
            "--json",
        ]
    )

    assert code == 0
    request = captured["request"]
    assert request.workflow_id == "graphics_heatmap"
    assert request.parameters.heatmap.matrix == str(matrix)
    assert request.inputs["ports"]["matrix_csv"] == str(matrix)
