"""Tests for `genomelens workflow` and new `genomelens analyze workflow/submodule` CLI."""

from __future__ import annotations

import json

from genomelens.cli.main import main
from genomelens.core.summary_models import RunSummary, ScoringBlock, UiBlock


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


def test_workflow_list_json(capsys) -> None:
    assert main(["workflow", "list", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert "one_stop_workflows" in payload
    assert "submodules" in payload
    workflow_ids = {item["workflow_id"] for item in payload["one_stop_workflows"]}
    assert "pairwise_synteny" in workflow_ids
    module_ids = {item["module_id"] for item in payload["submodules"]}
    assert "jcvi.mcscan_pairwise" in module_ids


def test_workflow_list_one_stop_only(capsys) -> None:
    assert main(["workflow", "list", "--kind", "one_stop", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert "one_stop_workflows" in payload
    assert "submodules" not in payload


def test_workflow_list_sub_module_only(capsys) -> None:
    assert main(["workflow", "list", "--kind", "sub_module", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert "submodules" in payload
    assert "one_stop_workflows" not in payload


def test_workflow_describe_one_stop_json(capsys) -> None:
    assert main(["workflow", "describe", "pairwise_synteny", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["workflow_id"] == "pairwise_synteny"
    assert payload["kind"] == "one_stop"
    assert "equivalent_modules" in payload


def test_workflow_describe_submodule_json(capsys) -> None:
    assert main(["workflow", "describe", "jcvi.graphics_histogram", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["module_id"] == "jcvi.graphics_histogram"
    assert payload["kind"] == "sub_module"
    assert any(port["port_id"] == "numeric_files" for port in payload["inputs"])


def test_workflow_describe_unknown_returns_error(capsys) -> None:
    code = main(["workflow", "describe", "not.found"])
    assert code == 2
    assert "未找到" in capsys.readouterr().err


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
    assert payload["valid"] is True
    assert payload["errors"] == []


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


def test_workflow_validate_analysis_request(tmp_path) -> None:
    request_path = tmp_path / "request.json"
    request_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "kind": "analysis_request",
                "method": "mcscan",
                "task_kind": "sub_module",
                "sub_module_id": "jcvi.graphics_histogram",
                "port_bindings": {"numeric_files": ["data.txt"]},
                "input": {"mode": "method_specific"},
                "output": {"directory": str(tmp_path / "out")},
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
    assert any(spec["workflow_id"] == "pairwise_synteny" for spec in payload["one_stop_workflows"])


def test_analyze_schema_default_still_raw_schema(capsys) -> None:
    assert main(["analyze", "schema"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert "properties" in payload


def test_analyze_workflow_unknown_returns_error(capsys) -> None:
    code = main(["analyze", "workflow", "not_found", "in", "out"])
    assert code == 3
    err = capsys.readouterr().err
    assert "未知的一站式工作流" in err or "not_found" in err


def test_analyze_submodule_unknown_returns_error(capsys) -> None:
    code = main(["analyze", "submodule", "not.found", "--input-ports", "{}", "--output-dir", "out"])
    assert code == 3
    err = capsys.readouterr().err
    assert "未知的子模块" in err or "not.found" in err


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
    err = capsys.readouterr().err
    assert "numeric_files" in err or "histogram" in err


def test_analyze_workflow_histogram_routes_to_one_stop(monkeypatch, tmp_path) -> None:
    captured: dict[str, object] = {}

    def fake_dispatch(self, request, signal_bus=None):
        captured["request"] = request
        return _dummy_summary()

    monkeypatch.setattr("genomelens.analysis.dispatcher.AnalysisDispatcher.dispatch", fake_dispatch)

    numeric = tmp_path / "values.txt"
    numeric.write_text("1\n2\n3\n", encoding="utf-8")
    outdir = tmp_path / "out"

    code = main(
        [
            "analyze",
            "workflow",
            "histogram_plot",
            str(numeric),
            str(outdir),
            "--force",
            "--json",
        ]
    )
    assert code == 0
    request = captured["request"]
    assert request.task_kind == "one_stop"
    assert request.one_stop_workflow_id == "histogram_plot"


def test_analyze_submodule_heatmap_routes_to_sub_module(monkeypatch, tmp_path) -> None:
    captured: dict[str, object] = {}

    def fake_dispatch(self, request, signal_bus=None):
        captured["request"] = request
        return _dummy_summary()

    monkeypatch.setattr("genomelens.analysis.dispatcher.AnalysisDispatcher.dispatch", fake_dispatch)

    matrix = tmp_path / "matrix.csv"
    matrix.write_text("g,s1,s2\na,1,2\n", encoding="utf-8")
    outdir = tmp_path / "out"

    code = main(
        [
            "analyze",
            "submodule",
            "jcvi.graphics_heatmap",
            "--input-ports",
            json.dumps({"matrix_csv": str(matrix)}),
            "--output-dir",
            str(outdir),
            "--force",
            "--json",
        ]
    )
    assert code == 0
    request = captured["request"]
    assert request.task_kind == "sub_module"
    assert request.sub_module_id == "jcvi.graphics_heatmap"
    assert request.port_bindings["matrix_csv"] == str(matrix)
