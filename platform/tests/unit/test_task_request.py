from pathlib import Path

import pytest

from genomelens.analysis.requests.loader import load_analysis_request
from genomelens.analysis.requests.models import (
    SyntenyParameters,
    WorkflowOutput,
    WorkflowParameters,
    WorkflowRequest,
    WorkflowRuntime,
    WorkflowSpeciesInput,
    workflow_template_request,
)
from genomelens.analysis.requests.schema import WORKFLOW_REQUEST_JSON_SCHEMA
from genomelens.analysis.requests.submodule_models import (
    SubmoduleRequest,
    submodule_template_request,
)
from genomelens.analysis.requests.submodule_schema import SUBMODULE_REQUEST_JSON_SCHEMA
from genomelens.analysis.requests.task_loader import load_task_request, write_task_request


def test_workflow_request_default_schema_version_is_three() -> None:
    request = workflow_template_request()

    assert request.schema_version == 3
    assert request.kind == "workflow_request"
    assert request.workflow_id == "synteny"


def test_workflow_request_rejects_non_synteny_workflow_id() -> None:
    with pytest.raises(ValueError, match="workflow_id"):
        WorkflowRequest.from_json(
            {
                "schema_version": 3,
                "kind": "workflow_request",
                "workflow_id": "graphics_histogram",
                "output": {"directory": "out"},
            }
        )


def test_workflow_request_rejects_local_synteny_workflow_id() -> None:
    with pytest.raises(ValueError, match="workflow_id"):
        WorkflowRequest.from_json(
            {
                "schema_version": 3,
                "kind": "workflow_request",
                "workflow_id": "local_synteny",
                "output": {"directory": "out"},
            }
        )


def test_synteny_parameters_include_min_block_size() -> None:
    params = SyntenyParameters()

    assert params.min_block_size == 5
    assert params.to_json()["min_block_size"] == 5


def test_synteny_parameters_roundtrip_min_block_size() -> None:
    params = SyntenyParameters.from_json({"min_block_size": 12})

    assert params.min_block_size == 12


def test_workflow_request_roundtrip(tmp_path: Path) -> None:
    request = WorkflowRequest(
        workflow_id="synteny",
        species=[
            WorkflowSpeciesInput(name="A", input_mode="bed_cds", bed="A.bed", cds="A.cds"),
            WorkflowSpeciesInput(name="B", input_mode="bed_cds", bed="B.bed", cds="B.cds"),
        ],
        parameters=WorkflowParameters(synteny=SyntenyParameters(min_block_size=7)),
        output=WorkflowOutput(directory="out"),
        runtime=WorkflowRuntime(threads=4),
    )
    path = tmp_path / "request.json"
    write_task_request(request, path)

    loaded = load_task_request(path)

    assert isinstance(loaded, WorkflowRequest)
    assert loaded.schema_version == 3
    assert loaded.workflow_id == "synteny"
    assert loaded.parameters.synteny.min_block_size == 7
    assert loaded.runtime.threads == 4


def test_submodule_request_roundtrip(tmp_path: Path) -> None:
    request = SubmoduleRequest(
        module_id="jcvi.graphics_histogram",
        inputs={"numeric_files": ["values.txt"]},
        parameters={"histogram_columns": [0], "histogram_bins": 20},
        output=WorkflowOutput(directory="out", formats=["png"]),
        runtime=WorkflowRuntime(threads=2),
    )
    path = tmp_path / "submodule.json"
    write_task_request(request, path)

    loaded = load_task_request(path)

    assert isinstance(loaded, SubmoduleRequest)
    assert loaded.schema_version == 3
    assert loaded.kind == "submodule_request"
    assert loaded.module_id == "jcvi.graphics_histogram"
    assert loaded.inputs["numeric_files"] == ["values.txt"]
    assert loaded.output.formats == ["png"]


def test_task_loader_rejects_unknown_kind() -> None:
    path = Path(__file__).with_name("unknown_kind_request.json")
    path.write_text(
        '{"schema_version": 3, "kind": "legacy_request", "output": {"directory": "out"}}',
        encoding="utf-8",
    )
    try:
        with pytest.raises(Exception, match="kind"):
            load_task_request(path)
    finally:
        path.unlink(missing_ok=True)


def test_submodule_template_request_has_module_id() -> None:
    request = submodule_template_request("jcvi.graphics_heatmap")

    assert request.module_id == "jcvi.graphics_heatmap"
    assert request.kind == "submodule_request"


def test_workflow_schema_narrows_workflow_id_to_synteny() -> None:
    enum = WORKFLOW_REQUEST_JSON_SCHEMA["properties"]["workflow_id"]["enum"]

    assert enum == ["synteny"]


def test_workflow_schema_has_min_block_size_under_synteny() -> None:
    props = WORKFLOW_REQUEST_JSON_SCHEMA["$defs"]["synteny_parameters"]["properties"]

    assert "min_block_size" in props
    assert props["min_block_size"]["default"] == 5


def test_submodule_schema_has_module_id_and_free_inputs() -> None:
    props = SUBMODULE_REQUEST_JSON_SCHEMA["properties"]

    assert props["module_id"]["type"] == "string"
    assert props["inputs"]["type"] == "object"
    assert props["parameters"]["type"] == "object"


def test_load_analysis_request_still_works_for_workflow_request(tmp_path: Path) -> None:
    request = workflow_template_request()
    path = tmp_path / "request.json"
    write_task_request(request, path)

    loaded = load_analysis_request(path)

    assert loaded.workflow_id == "synteny"
    assert loaded.schema_version == 3
