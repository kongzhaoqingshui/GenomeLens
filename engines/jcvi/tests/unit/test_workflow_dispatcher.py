from pathlib import Path

import pytest

import jcvi_genomelens.workflows.dispatcher as dispatcher
from jcvi_genomelens.manifest.models import EngineRunManifest, ToolchainSpec, WorkflowOptions
from jcvi_genomelens.workflows.dispatcher import dispatch


def _manifest(workflow: str) -> EngineRunManifest:
    return EngineRunManifest(workflow=workflow, toolchain=ToolchainSpec(), options=WorkflowOptions())


def test_dispatch_normalizes_workflow_alias(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def fake_run(manifest: EngineRunManifest, outdir: str | Path):
        captured["workflow"] = manifest.workflow
        captured["outdir"] = outdir
        return [], {"ok": True}

    monkeypatch.setitem(dispatcher._WORKFLOW_REGISTRY, "graphics_dotplot", fake_run)

    audits, artifacts = dispatch(_manifest("dotplot"), tmp_path)

    assert audits == []
    assert artifacts == {"ok": True}
    assert captured["outdir"] == tmp_path


def test_dispatch_rejects_unknown_workflow(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Unsupported workflow"):
        dispatch(_manifest("unknown"), tmp_path)
