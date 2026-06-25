"""Dispatch an engine manifest to a supported workflow"""

from __future__ import annotations

from collections.abc import Callable
from importlib import import_module
from pathlib import Path

from jcvi_genomelens.manifest.models import EngineRunManifest
from jcvi_genomelens.runtime.command_runner import CommandAudit
from jcvi_genomelens.workflows.contract import (
    GLOBAL_KARYOTYPE_WORKFLOW,
    HEATMAP_WORKFLOW,
    HISTOGRAM_WORKFLOW,
    MULTI_LOCAL_SYNTENY_WORKFLOW,
    normalize_workflow,
)


def dispatch(manifest: EngineRunManifest, outdir: str | Path) -> tuple[list[CommandAudit], dict[str, object]]:
    """Dispatch by the normalized v3 workflow field"""

    workflow = normalize_workflow(manifest.workflow)
    runner_ref = _WORKFLOW_REGISTRY.get(workflow)
    if runner_ref is None:
        raise ValueError(f"Unsupported workflow: {manifest.workflow}")
    runner = _load_runner(runner_ref)
    return runner(manifest, outdir)


Runner = Callable[[EngineRunManifest, str | Path], tuple[list[CommandAudit], dict[str, object]]]


RunnerRef = Runner | tuple[str, str]


def _load_runner(runner_ref: RunnerRef) -> Runner:
    if callable(runner_ref):
        return runner_ref
    module_name, function_name = runner_ref
    module = import_module(module_name)
    return getattr(module, function_name)


_WORKFLOW_REGISTRY: dict[str, RunnerRef] = {
    "mcscan_pairwise": ("jcvi_genomelens.workflows.pairwise.mcscan", "run"),
    "graphics_synteny": ("jcvi_genomelens.workflows.graphics.synteny", "run"),
    "graphics_dotplot": ("jcvi_genomelens.workflows.graphics.dotplot", "run"),
    HISTOGRAM_WORKFLOW: ("jcvi_genomelens.workflows.graphics.histogram", "run"),
    "graphics_karyotype": ("jcvi_genomelens.workflows.graphics.karyotype", "run"),
    HEATMAP_WORKFLOW: ("jcvi_genomelens.workflows.graphics.heatmap", "run"),
    "catalog_ortholog": ("jcvi_genomelens.workflows.pairwise.catalog_ortholog", "run"),
    "local_synteny": ("jcvi_genomelens.workflows.local_synteny.single", "run"),
    MULTI_LOCAL_SYNTENY_WORKFLOW: ("jcvi_genomelens.workflows.local_synteny.multi", "run"),
    GLOBAL_KARYOTYPE_WORKFLOW: ("jcvi_genomelens.workflows.graphics.global_karyotype", "run"),
}
