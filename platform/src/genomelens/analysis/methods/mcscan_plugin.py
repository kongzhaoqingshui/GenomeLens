"""MCscan 方法插件"""

# region import
from __future__ import annotations

from genomelens.analysis.methods.mcscan_provider import McscanWorkflowProvider
from genomelens.analysis.methods.mcscan_request_mapping import (
    to_heatmap_request,
    to_histogram_request,
    to_mcscan_request,
)
from genomelens.analysis.methods.registry import ArtifactDeclaration, MethodPlugin
from genomelens.analysis.requests.models import AnalysisRequest, McscanMethodConfig
from genomelens.app.controller.workflow_provider import WorkflowProvider
from genomelens.core.validators import validate_histogram_request
from genomelens.workflow.onestop_registry import get_onestop_registry
from genomelens.workflow.submodule_registry import get_submodule_registry

# endregion


class McscanPlugin(MethodPlugin):
    """McscanPlugin(MCscan 方法插件)：把 MCscan/JCVI 接入平台注册表"""

    @property
    def name(self) -> str:
        """返回方法唯一标识名"""

        return "mcscan"

    @property
    def description(self) -> str:
        """返回供 CLI/GUI 展示的一行描述"""

        return "JCVI 共线性分析与绘图"

    @property
    def stable(self) -> bool:
        """MCscan 是平台当前的主要稳定方法"""

        return True

    def validate_request(self, request: AnalysisRequest) -> None:
        """通过构造 McscanRequest 来校验输入是否满足 MCscan 要求"""

        workflow = McscanMethodConfig.from_json(request.method_config).workflow
        if workflow == "graphics_histogram":
            validate_histogram_request(to_histogram_request(request))
            return
        if workflow == "graphics_heatmap":
            to_heatmap_request(request)
            return
        to_mcscan_request(request)

    def get_provider(self) -> WorkflowProvider:
        """返回 MCscan 工作流提供者"""

        return McscanWorkflowProvider()

    def list_artifacts(self) -> list[ArtifactDeclaration]:
        """返回 MCscan 方法可能产出的主要产物"""

        return [
            ArtifactDeclaration("blast_table", "table", "BLAST 同源比对表", required=True),
            ArtifactDeclaration("anchors", "table", "共线性锚点文件", required=True),
            ArtifactDeclaration("simple", "table", "简化共线性边文件", required=False),
            ArtifactDeclaration("blocks", "table", "共线性 block 文件", required=False),
            ArtifactDeclaration("figures", "image", "共线性图件", required=False),
            ArtifactDeclaration("global_karyotype", "image", "全局核型总图", required=False),
        ]

    def list_submodules(self) -> list:
        """返回 MCscan 方法暴露的 JCVI 子模块规范"""

        return get_submodule_registry().list_all()

    def list_one_stop_workflows(self) -> list:
        """返回 MCscan 方法暴露的一站式工作流规范"""

        return get_onestop_registry().list_all()
