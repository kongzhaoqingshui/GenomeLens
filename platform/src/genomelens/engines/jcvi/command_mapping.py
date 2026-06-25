"""稳定的 workflow(工作流) 名称与别名"""

SUPPORTED_WORKFLOWS = {
    "pairwise",
    "graphics_synteny",
    "graphics_dotplot",
    "graphics_heatmap",
    "graphics_histogram",
    "graphics_karyotype",
    "local_synteny",
}
# adapter 层只维护 shell 当前真正承诺支持的稳定 workflow 名称
WORKFLOW_ALIASES = {
    "dotplot": "graphics_dotplot",
    "heatmap": "graphics_heatmap",
    "histogram": "graphics_histogram",
    "karyotype": "graphics_karyotype",
    "local": "local_synteny",
}


def normalize_workflow(name: str) -> str:
    """把兼容 workflow(工作流) 名称规范化"""

    # CLI、配置和请求规范化都走这里，避免别名映射出现多份定义
    return WORKFLOW_ALIASES.get(name, name)


def requires_precomputed_pairwise(name: str) -> bool:
    """渲染类 workflow(工作流) 需要预先算好的 pairwise 共线性基础产物。

    仅 ``pairwise`` 自身是计算入口；其余（synteny/karyotype/dotplot/local_synteny 等）
    都只负责渲染，必须由编排层在请求中注入 ``precomputed_artifacts``。
    """

    return normalize_workflow(name) != "pairwise"
