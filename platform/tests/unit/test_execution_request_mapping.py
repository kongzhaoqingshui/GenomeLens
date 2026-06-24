from pathlib import Path

import pytest

from genomelens.analysis.execution.request_mapping import to_histogram_request, to_mcscan_request
from genomelens.analysis.planning.models import SyntenyExecutionRequest
from genomelens.analysis.planning.planner import WorkflowPlanner
from genomelens.analysis.requests.models import WorkflowRequest, WorkflowSpeciesInput
from genomelens.app.errors.exceptions import InputValidationError
from genomelens.contracts.species import PreparedGenomeInputSpec
from genomelens.engines.jcvi.manifest_builder import JcviManifestBuilder


def _species(name: str) -> WorkflowSpeciesInput:
    return WorkflowSpeciesInput(name=name, input_mode="bed_cds", bed=f"/tmp/{name}.bed", cds=f"/tmp/{name}.cds")


def _request(species: list[WorkflowSpeciesInput], **overrides: object) -> WorkflowRequest:
    data: dict[str, object] = {
        "schema_version": 2,
        "kind": "workflow_request",
        "workflow_id": "synteny",
        "species": [item.to_json() for item in species],
        "reference_index": 0,
        "inputs": {},
        "parameters": {},
        "output": {"directory": "/tmp/out", "force": True, "formats": ["svg"]},
        "runtime": {},
    }
    data.update(overrides)
    return WorkflowRequest.from_json(data)


def test_workflow_request_rejects_legacy_fields() -> None:
    with pytest.raises(ValueError, match="legacy fields"):
        WorkflowRequest.from_json(
            {
                "schema_version": 2,
                "kind": "workflow_request",
                "workflow_id": "synteny",
                "species": [],
                "reference_index": 0,
                "inputs": {},
                "parameters": {},
                "output": {"directory": "/tmp/out"},
                "runtime": {},
                "method_config": {},
            }
        )


def test_to_mcscan_request_uses_species_array_and_reference_index() -> None:
    request = _request([_species("query"), _species("subject")], reference_index=1)

    mapped = to_mcscan_request(request)

    assert mapped.reference.name == "subject"
    assert mapped.target.name == "query"
    assert mapped.outdir == Path("/tmp/out").expanduser().resolve(strict=False)
    assert mapped.force is True
    assert mapped.engine_workflow == "graphics_synteny"


def test_to_mcscan_request_requires_at_least_two_species() -> None:
    request = _request([_species("query")])

    with pytest.raises(InputValidationError, match="mcscan 至少需要两个物种"):
        to_mcscan_request(request)


def test_workflow_planner_two_species_has_single_pairwise_step() -> None:
    plan = WorkflowPlanner().build(_request([_species("A"), _species("B")]))

    assert [step.kind for step in plan.steps] == ["pairwise_synteny"]
    assert plan.steps[0].step_id == "A__B"


def test_workflow_planner_honors_pairwise_engine_workflow_extra() -> None:
    request = _request(
        [_species("A"), _species("B")],
        parameters={"extras": {"engine_workflow": "graphics_dotplot"}},
    )

    plan = WorkflowPlanner().build(request)

    payload = plan.steps[0].payload
    assert isinstance(payload, SyntenyExecutionRequest)
    assert payload.engine_workflow == "graphics_dotplot"


def test_workflow_planner_catalog_ortholog_does_not_require_figures() -> None:
    request = _request(
        [_species("A"), _species("B")],
        parameters={"extras": {"engine_workflow": "catalog_ortholog"}},
    )

    plan = WorkflowPlanner().build(request)

    output_ids = {item.artifact_id for item in plan.steps[0].outputs}
    required_ids = {item.artifact_id for item in plan.steps[0].outputs if item.required}
    assert "figures" not in output_ids
    assert "figures" not in required_ids


def test_workflow_planner_multi_species_global_karyotype() -> None:
    plan = WorkflowPlanner().build(_request([_species("A"), _species("B"), _species("C")]))

    assert [step.kind for step in plan.steps] == [
        "pairwise_synteny",
        "pairwise_synteny",
        "pairwise_synteny",
        "global_karyotype",
    ]
    assert plan.steps[-1].depends_on == ["A__B", "A__C", "B__C"]


def test_workflow_planner_target_genes_reference_vs_targets() -> None:
    request = _request(
        [_species("A"), _species("B"), _species("C")],
        parameters={"local_synteny": {"target_gene_ids": ["g1"]}},
    )

    plan = WorkflowPlanner().build(request)

    assert [step.kind for step in plan.steps] == ["pairwise_synteny", "pairwise_synteny", "multi_local_synteny"]
    assert {step.step_id for step in plan.steps[:2]} == {"A__B", "A__C"}
    assert plan.steps[-1].depends_on == ["A__B", "A__C"]


def test_histogram_request_uses_grouped_parameters(tmp_path: Path) -> None:
    numbers = tmp_path / "numbers.txt"
    numbers.write_text("1\n2\n3\n", encoding="utf-8")
    request = WorkflowRequest.from_json(
        {
            "schema_version": 2,
            "kind": "workflow_request",
            "workflow_id": "graphics_histogram",
            "species": [],
            "reference_index": 0,
            "inputs": {},
            "parameters": {"histogram": {"inputs": [str(numbers)], "columns": [0, 1], "bins": 12}},
            "output": {"directory": str(tmp_path / "out"), "formats": ["png"]},
            "runtime": {"log_level": "WARNING"},
        }
    )

    histogram = to_histogram_request(request)

    assert histogram.inputs == [numbers.resolve(strict=False)]
    assert histogram.columns == [0, 1]
    assert histogram.histogram_bins == 12
    assert histogram.formats == ["png"]


def test_manifest_builder_pairwise_schema_v3_has_no_top_level_query_subject() -> None:
    request = to_mcscan_request(_request([_species("A"), _species("B")]))
    manifest = JcviManifestBuilder().build_pairwise_manifest(
        request,
        query=PreparedGenomeInputSpec(Path("/tmp/A.bed"), Path("/tmp/A.cds")),
        subject=PreparedGenomeInputSpec(Path("/tmp/B.bed"), Path("/tmp/B.cds")),
        blastn_path="",
        makeblastdb_path="",
    )

    assert manifest["schema_version"] == 3
    assert "query" not in manifest
    assert "subject" not in manifest
    assert manifest["inputs"]["species"][0]["name"] == "A"  # type: ignore[index]
