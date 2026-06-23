"""Tests for `genomelens workflow` CLI."""

from __future__ import annotations

import json

from genomelens.cli.main import main


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
