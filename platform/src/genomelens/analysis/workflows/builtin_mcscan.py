"""MCscan 工作流提供者"""

# region import
from __future__ import annotations

from genomelens.analysis.execution.executor import PlanExecutor
from genomelens.analysis.execution.workflow_mapping import to_mcscan_request
from genomelens.analysis.planning.models import SyntenyExecutionRequest
from genomelens.analysis.planning.planner import WorkflowPlanner
from genomelens.analysis.requests.models import WorkflowRequest
from genomelens.analysis.workflows.onestop import get_onestop_registry
from genomelens.analysis.workflows.provider import WorkflowProvider
from genomelens.analysis.workflows.registry import ArtifactDeclaration, WorkflowPlugin
from genomelens.analysis.workflows.submodules import get_submodule_registry
from genomelens.app.events.signal_bus import SignalBus
from genomelens.contracts.summaries import RunSummary

# endregion


class McscanPlugin(WorkflowPlugin):
    """McscanPlugin(MCscan workflow 插件)：把 MCscan/JCVI 接入平台注册表"""

    @property
    def name(self) -> str:
        """返回 workflow 插件唯一标识名"""

        return "mcscan"

    @property
    def description(self) -> str:
        """返回供 CLI/GUI 展示的一行描述"""

        return "JCVI 共线性分析与绘图"

    @property
    def stable(self) -> bool:
        """MCscan 是平台当前的主要稳定 workflow"""

        return True

    def validate_request(self, request: WorkflowRequest) -> None:
        """通过构造 ExecutionPlan 来校验输入是否满足 MCscan 要求"""

        WorkflowPlanner().build(request)

    def get_provider(self) -> WorkflowProvider:
        """返回 MCscan 工作流提供者"""

        return McscanWorkflowProvider()

    def list_artifacts(self) -> list[ArtifactDeclaration]:
        """返回 MCscan workflow 可能产出的主要产物"""

        return [
            ArtifactDeclaration("blast_table", "table", "BLAST 同源比对表", required=True),
            ArtifactDeclaration("anchors", "table", "共线性锚点文件", required=True),
            ArtifactDeclaration("simple", "table", "简化共线性边文件", required=False),
            ArtifactDeclaration("blocks", "table", "共线性 block 文件", required=False),
            ArtifactDeclaration("figures", "image", "共线性图件", required=False),
            ArtifactDeclaration("global_karyotype", "image", "全局核型总图", required=False),
        ]

    def list_submodules(self) -> list:
        """返回 MCscan workflow 暴露的 JCVI 子模块规范"""

        return get_submodule_registry().list_all()

    def list_one_stop_workflows(self) -> list:
        """返回 MCscan workflow 暴露的一站式工作流规范"""

        return get_onestop_registry().list_all()


class McscanWorkflowProvider(WorkflowProvider):
    """McscanWorkflowProvider：MCscan/JCVI 方法的 WorkflowProvider 实现

    provider 只负责把 WorkflowRequest 交给 WorkflowPlanner/PlanExecutor；
    配对策略和多物种编排不再分散在 provider 内部。
    """

    @property
    def name(self) -> str:
        """返回方法名称"""

        return "mcscan"

    def supports_native_multi_species(self) -> bool:
        """当前 MCscan 引擎本身不提供原生多物种能力"""

        return False

    def run(self, request: WorkflowRequest, signal_bus: SignalBus) -> RunSummary:
        """运行一次 MCscan/JCVI 工作流请求"""

        plan = WorkflowPlanner().build(request)
        return PlanExecutor().execute(plan, signal_bus)


def _to_mcscan_request(request: WorkflowRequest) -> SyntenyExecutionRequest:
    """把 WorkflowRequest 转成 SyntenyExecutionRequest（provider 内部使用的便利函数）"""

    return to_mcscan_request(request)
