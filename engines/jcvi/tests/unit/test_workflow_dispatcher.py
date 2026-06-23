"""Tests for workflow dispatch resolution"""

from __future__ import annotations

from jcvi_genomelens.manifest_models import EngineRunManifest, ToolchainSpec, WorkflowOptions
from jcvi_genomelens.workflow_dispatcher import SUBMODULE_ID_TO_WORKFLOW, _resolve_workflow


def _manifest(workflow: str, sub_module_id: str | None = None) -> EngineRunManifest:
    return EngineRunManifest(
        workflow=workflow,
        toolchain=ToolchainSpec(),
        options=WorkflowOptions(),
        sub_module_id=sub_module_id,
    )


def test_resolve_workflow_uses_sub_module_id() -> None:
    manifest = _manifest("mcscan_pairwise", "jcvi.graphics_histogram")
    assert _resolve_workflow(manifest) == "graphics_histogram"


def test_resolve_workflow_falls_back_to_normalized_workflow() -> None:
    manifest = _manifest("dotplot")
    assert _resolve_workflow(manifest) == "graphics_dotplot"


def test_submodule_mapping_covers_known_modules() -> None:
    assert SUBMODULE_ID_TO_WORKFLOW["jcvi.mcscan_pairwise"] == "mcscan_pairwise"
    assert SUBMODULE_ID_TO_WORKFLOW["jcvi.graphics_synteny"] == "graphics_synteny"
    assert SUBMODULE_ID_TO_WORKFLOW["jcvi.local_synteny"] == "local_synteny"
    assert SUBMODULE_ID_TO_WORKFLOW["jcvi.graphics_karyotype_global"] == "graphics_karyotype_global"
