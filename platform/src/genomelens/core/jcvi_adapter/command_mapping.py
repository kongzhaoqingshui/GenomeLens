"""稳定的 workflow(工作流) 名称与别名"""

SUPPORTED_WORKFLOWS = {
    "mcscan_pairwise",
    "graphics_synteny",
    "graphics_dotplot",
    "graphics_heatmap",
    "graphics_histogram",
    "graphics_karyotype",
    "catalog_ortholog",
    "local_synteny",
}
# adapter 层只维护 shell 当前真正承诺支持的稳定 workflow 名称。
WORKFLOW_ALIASES = {
    "dotplot": "graphics_dotplot",
    "heatmap": "graphics_heatmap",
    "histogram": "graphics_histogram",
    "karyotype": "graphics_karyotype",
    "local": "local_synteny",
}


def normalize_workflow(name: str) -> str:
    """把兼容 workflow(工作流) 名称规范化"""

    # CLI、配置和请求规范化都走这里，避免别名映射出现多份定义。
    return WORKFLOW_ALIASES.get(name, name)
