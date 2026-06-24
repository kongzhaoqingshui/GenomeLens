from __future__ import annotations

import pytest

from genomelens.analysis.requests.models import WorkflowRequest
from genomelens.analysis.workflows.input_bindings import PortBinding, PortDeclaration, PortSystem
from genomelens.analysis.workflows.onestop import OneStopWorkflowRegistry, get_onestop_registry
from genomelens.analysis.workflows.registry import list_one_stop_workflows, list_submodules
from genomelens.analysis.workflows.submodules import SubModuleRegistry, get_submodule_registry


def test_port_declaration_to_json_omits_empty_fields() -> None:
    port = PortDeclaration("species_pair", "species_pair", True, "pair of species")
    assert port.to_json() == {
        "port_id": "species_pair",
        "port_kind": "species_pair",
        "required": True,
        "description": "pair of species",
    }


def test_port_declaration_to_json_includes_optional_fields() -> None:
    port = PortDeclaration(
        "blocks",
        "artifact",
        True,
        "blocks file",
        artifact_type="blocks",
        accepted_formats=[".blocks"],
    )
    assert port.to_json()["accepted_formats"] == [".blocks"]


def test_validate_bindings_passes_when_required_ports_present() -> None:
    inputs = [PortDeclaration("species_pair", "species_pair", True, "pair")]
    assert PortSystem.validate_bindings(inputs, {"species_pair": ["A", "B"]}) == []


def test_validate_bindings_reports_missing_required_ports() -> None:
    inputs = [PortDeclaration("species_pair", "species_pair", True, "pair")]
    errors = PortSystem.validate_bindings(inputs, {})
    assert len(errors) == 1
    assert "species_pair" in errors[0]


def test_validate_bindings_reports_unknown_ports() -> None:
    inputs = [PortDeclaration("species_pair", "species_pair", True, "pair")]
    errors = PortSystem.validate_bindings(inputs, {"species_pair": ["A", "B"], "extra": 1})
    assert len(errors) == 1
    assert "extra" in errors[0]


def test_describe_ports_returns_json_list() -> None:
    ports = [PortDeclaration("figures", "artifact", False, "figures", artifact_type="figures")]
    assert PortSystem.describe_ports(ports)[0]["artifact_type"] == "figures"


def test_submodule_registry_contains_mcscan_pairwise() -> None:
    spec = SubModuleRegistry().get("jcvi.mcscan_pairwise")
    assert spec is not None
    assert spec.module_id == "jcvi.mcscan_pairwise"
    assert spec.module_kind == "lightweight"
    assert spec.standalone is True
    assert any(port.port_id == "species_pair" for port in spec.inputs)


def test_submodule_spec_to_json_includes_module_kind() -> None:
    spec = SubModuleRegistry().get("jcvi.graphics_karyotype_global")
    assert spec is not None
    assert spec.to_json()["module_kind"] == "aggregate"


def test_submodule_registry_list_all_has_expected_modules() -> None:
    ids = {spec.module_id for spec in SubModuleRegistry().list_all()}
    assert {"jcvi.mcscan_pairwise", "jcvi.graphics_histogram", "jcvi.local_synteny_multi"}.issubset(ids)


def test_submodule_registry_get_returns_none_for_unknown() -> None:
    assert get_submodule_registry().get("not.found") is None


def test_submodule_registry_can_filter_by_kind() -> None:
    registry = SubModuleRegistry()

    lightweight_ids = {spec.module_id for spec in registry.list_by_kind("lightweight")}
    aggregate_ids = {spec.module_id for spec in registry.list_by_kind("aggregate")}

    assert {
        "jcvi.mcscan_pairwise",
        "jcvi.catalog_ortholog",
        "jcvi.graphics_dotplot",
        "jcvi.graphics_synteny",
        "jcvi.graphics_karyotype",
        "jcvi.local_synteny",
        "jcvi.graphics_histogram",
        "jcvi.graphics_heatmap",
    } == lightweight_ids
    assert aggregate_ids == {
        "jcvi.graphics_karyotype_global",
        "jcvi.local_synteny_multi",
    }


def test_onestop_registry_contains_synteny() -> None:
    spec = OneStopWorkflowRegistry().get("synteny")
    assert spec is not None
    assert spec.workflow_id == "synteny"
    assert spec.runner == "synteny_router"


def test_onestop_registry_list_all_has_expected_workflows() -> None:
    ids = {spec.workflow_id for spec in OneStopWorkflowRegistry().list_all()}
    assert ids == {"synteny"}


def test_workflow_request_v2_rejects_removed_compatibility_fields() -> None:
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
                "output": {"directory": "out"},
                "runtime": {},
                "composition": {},
            }
        )


def test_port_binding_round_trip() -> None:
    binding = PortBinding.from_json({"port_id": "blocks", "value": "path/to/blocks"})
    assert binding.port_id == "blocks"
    assert binding.value == "path/to/blocks"
    assert binding.to_json() == {"port_id": "blocks", "value": "path/to/blocks"}


def test_list_submodules_includes_mcscan_modules() -> None:
    ids = {spec.module_id for spec in list_submodules()}
    assert "jcvi.mcscan_pairwise" in ids
    assert "jcvi.graphics_dotplot" in ids


def test_list_one_stop_workflows_includes_expected() -> None:
    ids = {spec.workflow_id for spec in list_one_stop_workflows()}
    assert "synteny" in ids


def test_registry_singletons_return_same_instance() -> None:
    assert get_submodule_registry() is get_submodule_registry()
    assert get_onestop_registry() is get_onestop_registry()
