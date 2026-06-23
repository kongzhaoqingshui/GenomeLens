"""把 manifest(清单) 分发到受支持的 workflows(工作流)"""

# region import
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from jcvi_genomelens.manifest_models import EngineRunManifest
from jcvi_genomelens.runtime.command_runner import CommandAudit
from jcvi_genomelens.workflow_contract import (
    GLOBAL_KARYOTYPE_WORKFLOW,
    HEATMAP_WORKFLOW,
    HISTOGRAM_WORKFLOW,
    MULTI_LOCAL_SYNTENY_WORKFLOW,
    normalize_workflow,
)
from jcvi_genomelens.workflows import (
    catalog_ortholog,
    graphics_dotplot,
    graphics_heatmap,
    graphics_histogram,
    graphics_karyotype,
    graphics_karyotype_global,
    graphics_synteny,
    local_synteny,
    local_synteny_multi,
    mcscan_pairwise,
)

# endregion


def dispatch(manifest: EngineRunManifest, outdir: str | Path) -> tuple[list[CommandAudit], dict[str, object]]:
    """分发 manifest(清单) 中的 workflow(工作流) 名称"""

    # 入口先做 workflow 名称归一化，兼容上层别名和历史写法。
    workflow = normalize_workflow(manifest.workflow)
    runner = _WORKFLOW_REGISTRY.get(workflow)
    if runner is None:
        raise ValueError(f"Unsupported workflow: {manifest.workflow}")
    return runner(manifest, outdir)


_WORKFLOW_REGISTRY: dict[
    str,
    Callable[[EngineRunManifest, str | Path], tuple[list[CommandAudit], dict[str, object]]],
] = {
    "mcscan_pairwise": mcscan_pairwise.run,
    "graphics_synteny": graphics_synteny.run,
    "graphics_dotplot": graphics_dotplot.run,
    HISTOGRAM_WORKFLOW: graphics_histogram.run,
    "graphics_karyotype": graphics_karyotype.run,
    HEATMAP_WORKFLOW: graphics_heatmap.run,
    "catalog_ortholog": catalog_ortholog.run,
    "local_synteny": local_synteny.run,
    MULTI_LOCAL_SYNTENY_WORKFLOW: local_synteny_multi.run,
    GLOBAL_KARYOTYPE_WORKFLOW: graphics_karyotype_global.run,
}
