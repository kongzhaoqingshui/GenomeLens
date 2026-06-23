"""Tests for workflow metadata abstractions: ports, submodules, one-stop workflows."""

from __future__ import annotations

from genomelens.analysis.requests.models import AnalysisRequest, WorkflowComposition
from genomelens.workflow.onestop_registry import OneStopWorkflowRegistry, get_onestop_registry
from genomelens.workflow.port_system import PortBinding, PortDeclaration, PortSystem
from genomelens.workflow.submodule_registry import SubModuleRegistry, get_submodule_registry

# region PortSystem


def test_port_declaration_to_json_omits_empty_fields() -> None:
    port = PortDeclaration(
        port_id="species_pair",
        port_kind="species_pair",
        required=True,
        description="pair of species",
    )
    assert port.to_json() == {
        "port_id": "species_pair",
        "port_kind": "species_pair",
        "required": True,
        "description": "pair of species",
    }


def test_port_declaration_to_json_includes_optional_fields() -> None:
    port = PortDeclaration(
        port_id="blocks",
        port_kind="artifact",
        required=True,
        description="blocks file",
        artifact_type="blocks",
        accepted_formats=[".blocks"],
    )
    assert port.to_json() == {
        "port_id": "blocks",
        "port_kind": "artifact",
        "required": True,
        "description": "blocks file",
        "artifact_type": "blocks",
        "accepted_formats": [".blocks"],
    }


def test_validate_bindings_passes_when_required_ports_present() -> None:
    inputs = [
        PortDeclaration("species_pair", "species_pair", True, "pair"),
        PortDeclaration("anchors", "artifact", False, "anchors"),
    ]
    errors = PortSystem.validate_bindings(inputs, {"species_pair": ["A", "B"]})
    assert errors == []


def test_validate_bindings_reports_missing_required_ports() -> None:
    inputs = [PortDeclaration("species_pair", "species_pair", True, "pair")]
    errors = PortSystem.validate_bindings(inputs, {})
    assert len(errors) == 1
    assert "缺少必填端口" in errors[0]
    assert "species_pair" in errors[0]


def test_validate_bindings_reports_unknown_ports() -> None:
    inputs = [PortDeclaration("species_pair", "species_pair", True, "pair")]
    errors = PortSystem.validate_bindings(inputs, {"species_pair": ["A", "B"], "extra": 1})
    assert len(errors) == 1
    assert "存在未知端口" in errors[0]
    assert "extra" in errors[0]


def test_describe_ports_returns_json_list() -> None:
    ports = [PortDeclaration("figures", "artifact", False, "figures", artifact_type="figures")]
    described = PortSystem.describe_ports(ports)
    assert described == [
        {
            "port_id": "figures",
            "port_kind": "artifact",
            "required": False,
            "description": "figures",
            "artifact_type": "figures",
        }
    ]


# endregion


# region SubModuleRegistry


def test_submodule_registry_contains_mcscan_pairwise() -> None:
    registry = SubModuleRegistry()
    spec = registry.get("jcvi.mcscan_pairwise")
    assert spec is not None
    assert spec.module_id == "jcvi.mcscan_pairwise"
    assert spec.standalone is True
    assert spec.category == "homology_search"
    assert any(p.port_id == "species_pair" for p in spec.inputs)
    assert any(p.port_id == "blocks" for p in spec.outputs)


def test_submodule_registry_list_all_has_expected_modules() -> None:
    registry = SubModuleRegistry()
    ids = {spec.module_id for spec in registry.list_all()}
    expected = {
        "jcvi.mcscan_pairwise",
        "jcvi.graphics_dotplot",
        "jcvi.graphics_synteny",
        "jcvi.graphics_karyotype",
        "jcvi.local_synteny",
        "jcvi.catalog_ortholog",
        "jcvi.graphics_histogram",
        "jcvi.graphics_heatmap",
        "jcvi.graphics_karyotype_global",
        "jcvi.local_synteny_multi",
    }
    assert expected.issubset(ids)


def test_submodule_registry_list_by_category() -> None:
    registry = SubModuleRegistry()
    viz = registry.list_by_category("visualization")
    assert len(viz) >= 4
    assert all(spec.category == "visualization" for spec in viz)


def test_submodule_registry_get_returns_none_for_unknown() -> None:
    assert get_submodule_registry().get("not.found") is None


def test_submodule_spec_to_json_is_serializable() -> None:
    spec = get_submodule_registry().get("jcvi.graphics_histogram")
    assert spec is not None
    data = spec.to_json()
    assert data["module_id"] == "jcvi.graphics_histogram"
    assert "inputs" in data
    assert "outputs" in data
    assert "parameters" in data


# endregion


# region OneStopWorkflowRegistry


def test_onestop_registry_contains_synteny() -> None:
    registry = OneStopWorkflowRegistry()
    spec = registry.get("synteny")
    assert spec is not None
    assert spec.workflow_id == "synteny"
    assert spec.runner == "synteny_router"
    assert "jcvi.mcscan_pairwise" in spec.equivalent_modules
    assert spec.optimization_notes


def test_onestop_registry_list_all_has_expected_workflows() -> None:
    registry = OneStopWorkflowRegistry()
    ids = {spec.workflow_id for spec in registry.list_all()}
    assert ids == {"synteny"}


def test_onestop_registry_get_returns_none_for_unknown() -> None:
    assert get_onestop_registry().get("unknown") is None


def test_onestop_spec_to_json_is_serializable() -> None:
    spec = get_onestop_registry().get("synteny")
    assert spec is not None
    data = spec.to_json()
    assert data["workflow_id"] == "synteny"
    assert data["runner"] == "synteny_router"
    assert "equivalent_modules" in data
    assert "optimization_notes" in data


# endregion


# region AnalysisRequest extensions


def _minimal_analysis_request_data() -> dict[str, object]:
    return {
        "schema_version": 1,
        "kind": "analysis_request",
        "method": "mcscan",
        "input": {"mode": "auto_directory"},
        "output": {"directory": "out"},
    }


def test_analysis_request_defaults_to_task_kind_analysis() -> None:
    request = AnalysisRequest.from_json(_minimal_analysis_request_data())
    assert request.task_kind == "analysis"
    assert request.one_stop_workflow_id is None
    assert request.sub_module_id is None
    assert request.port_bindings == {}
    assert request.composition is None


def test_analysis_request_round_trip_with_submodule_fields() -> None:
    request = AnalysisRequest.from_json(
        {
            **_minimal_analysis_request_data(),
            "task_kind": "sub_module",
            "sub_module_id": "jcvi.graphics_histogram",
            "port_bindings": {"numeric_files": ["data.txt"]},
        }
    )
    assert request.task_kind == "sub_module"
    assert request.sub_module_id == "jcvi.graphics_histogram"
    assert request.port_bindings == {"numeric_files": ["data.txt"]}

    json_data = request.to_json()
    assert json_data["task_kind"] == "sub_module"
    assert json_data["sub_module_id"] == "jcvi.graphics_histogram"
    assert json_data["port_bindings"] == {"numeric_files": ["data.txt"]}


def test_analysis_request_round_trip_with_one_stop_fields() -> None:
    request = AnalysisRequest.from_json(
        {
            **_minimal_analysis_request_data(),
            "task_kind": "one_stop",
            "one_stop_workflow_id": "synteny",
        }
    )
    assert request.task_kind == "one_stop"
    assert request.one_stop_workflow_id == "synteny"

    json_data = request.to_json()
    assert json_data["task_kind"] == "one_stop"
    assert json_data["one_stop_workflow_id"] == "synteny"


def test_analysis_request_round_trip_with_composition() -> None:
    request = AnalysisRequest.from_json(
        {
            **_minimal_analysis_request_data(),
            "task_kind": "composition",
            "composition": {
                "nodes": [{"module_id": "jcvi.mcscan_pairwise"}],
                "edges": [{"from": "a", "to": "b"}],
            },
        }
    )
    assert request.task_kind == "composition"
    assert request.composition is not None
    assert request.composition.nodes == [{"module_id": "jcvi.mcscan_pairwise"}]
    assert request.composition.edges == [{"from": "a", "to": "b"}]

    json_data = request.to_json()
    assert json_data["task_kind"] == "composition"
    assert json_data["composition"]["nodes"] == [{"module_id": "jcvi.mcscan_pairwise"}]


def test_port_binding_round_trip() -> None:
    binding = PortBinding.from_json({"port_id": "blocks", "value": "path/to/blocks"})
    assert binding.port_id == "blocks"
    assert binding.value == "path/to/blocks"
    assert binding.to_json() == {"port_id": "blocks", "value": "path/to/blocks"}


def test_workflow_composition_ignores_non_dict_items() -> None:
    composition = WorkflowComposition.from_json(
        {
            "nodes": [{"module_id": "a"}, "ignored", 123],
            "edges": [{"from": "a", "to": "b"}],
        }
    )
    assert composition.nodes == [{"module_id": "a"}]
    assert composition.edges == [{"from": "a", "to": "b"}]


# endregion


# region Method registry integration


def test_list_submodules_includes_mcscan_modules() -> None:
    from genomelens.analysis.methods.registry import list_submodules

    ids = {spec.module_id for spec in list_submodules()}
    assert "jcvi.mcscan_pairwise" in ids
    assert "jcvi.graphics_dotplot" in ids


def test_list_one_stop_workflows_includes_expected() -> None:
    from genomelens.analysis.methods.registry import list_one_stop_workflows

    ids = {spec.workflow_id for spec in list_one_stop_workflows()}
    assert "synteny" in ids


# endregion


def test_registry_singletons_return_same_instance() -> None:
    assert get_submodule_registry() is get_submodule_registry()
    assert get_onestop_registry() is get_onestop_registry()
