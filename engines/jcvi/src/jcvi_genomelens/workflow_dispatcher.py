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

    # 优先按 sub_module_id 解析，让上层子模块请求无需关心底层 workflow 名称。
    # 其次做 workflow 名称归一化，兼容上层别名和历史写法。
    workflow = _resolve_workflow(manifest)
    runner = _WORKFLOW_REGISTRY.get(workflow)
    if runner is None:
        raise ValueError(f"Unsupported workflow: {manifest.workflow}")
    return runner(manifest, outdir)


def _resolve_workflow(manifest: EngineRunManifest) -> str:
    """根据 sub_module_id 或 workflow 字段解析最终 workflow 名称"""

    if manifest.sub_module_id:
        mapped = SUBMODULE_ID_TO_WORKFLOW.get(manifest.sub_module_id)
        if mapped is not None:
            return mapped
    return normalize_workflow(manifest.workflow)


# 子模块 ID 到底层 engine workflow 的映射。
# 一个 engine workflow 可能对应多个子模块（例如 mcscan_pairwise 既可作为独立子模块，
# 也可被拆分为 homology_search + synteny_blocks 两个阶段），因此用 submodule_id 做键。
SUBMODULE_ID_TO_WORKFLOW: dict[str, str] = {
    "jcvi.mcscan_pairwise": "mcscan_pairwise",
    "jcvi.homology_search": "mcscan_pairwise",
    "jcvi.synteny_blocks": "mcscan_pairwise",
    "jcvi.graphics_dotplot": "graphics_dotplot",
    "jcvi.graphics_synteny": "graphics_synteny",
    "jcvi.graphics_karyotype": "graphics_karyotype",
    "jcvi.local_synteny": "local_synteny",
    "jcvi.catalog_ortholog": "catalog_ortholog",
    "jcvi.graphics_histogram": HISTOGRAM_WORKFLOW,
    "jcvi.graphics_heatmap": HEATMAP_WORKFLOW,
    "jcvi.graphics_karyotype_global": GLOBAL_KARYOTYPE_WORKFLOW,
    "jcvi.local_synteny_multi": MULTI_LOCAL_SYNTENY_WORKFLOW,
}

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
