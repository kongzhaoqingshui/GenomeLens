"""一站式工作流注册表

维护 GenomeLens 平台所有一站式工作流（One-Stop Workflow）的元数据。一站式工作流
面向常见分析场景，保留专用、可优化的执行路径，而不是子模块的简单拼接。
"""

# region import
from __future__ import annotations

from dataclasses import dataclass, field

from genomelens.workflow.port_system import PortSystem
from genomelens.workflow.submodule_registry import ParameterDeclaration

# endregion


@dataclass(frozen=True)
class OneStopWorkflowSpec:
    """一站式工作流规范"""

    # fmt: off
    workflow_id: str  # 一站式工作流唯一标识
    name: str         # 面向用户展示的工作流名称
    description: str  # 工作流功能描述
    category: str     # 工作流分类
    runner: str       # 专用 runner 名称
    engine_workflow: str | None    # 映射的底层引擎 workflow（plot-only 可能为 None）
    equivalent_modules: list[str]  # 等价子模块组合（仅用于文档/GUI 展示）
    optimization_notes: str        # 该工作流的优化说明
    inputs: list = field(default_factory=list)   # 输入端口声明
    outputs: list = field(default_factory=list)  # 输出端口声明
    parameters: list[ParameterDeclaration] = field(default_factory=list)  # 可调参数声明
    # fmt: on

    def to_json(self) -> dict[str, object]:
        return {
            "workflow_id": self.workflow_id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "runner": self.runner,
            "engine_workflow": self.engine_workflow,
            "equivalent_modules": list(self.equivalent_modules),
            "optimization_notes": self.optimization_notes,
            "inputs": PortSystem.describe_ports(self.inputs),
            "outputs": PortSystem.describe_ports(self.outputs),
            "parameters": [p.to_json() for p in self.parameters],
        }


class OneStopWorkflowRegistry:
    """一站式工作流注册表"""

    def __init__(self) -> None:
        self._workflows: dict[str, OneStopWorkflowSpec] = {}
        self._register_builtin_workflows()

    def register(self, spec: OneStopWorkflowSpec) -> None:
        """注册一个一站式工作流"""

        self._workflows[spec.workflow_id] = spec

    def get(self, workflow_id: str) -> OneStopWorkflowSpec | None:
        """按 ID 获取一站式工作流规范"""

        return self._workflows.get(workflow_id)

    def list_all(self) -> list[OneStopWorkflowSpec]:
        """返回全部一站式工作流规范"""

        return list(self._workflows.values())

    def list_by_category(self, category: str) -> list[OneStopWorkflowSpec]:
        """按分类返回一站式工作流规范"""

        return [spec for spec in self._workflows.values() if spec.category == category]

    def _register_builtin_workflows(self) -> None:
        """注册平台内置一站式工作流"""

        self.register(self._build_synteny())

    def _build_synteny(self) -> OneStopWorkflowSpec:
        """构建单一集成共线性分析工作流"""

        return OneStopWorkflowSpec(
            workflow_id="synteny",
            name="Synteny Analysis",
            description=(
                "单一集成共线性分析流：根据物种数、参考物种与目标基因自动选择 "
                "pairwise / 多物种 / reference-vs-targets 执行路径"
            ),
            category="synteny_analysis",
            runner="synteny_router",
            engine_workflow=None,
            equivalent_modules=[
                "jcvi.mcscan_pairwise",
                "jcvi.graphics_synteny",
                "jcvi.graphics_dotplot",
                "jcvi.graphics_karyotype_global",
                "jcvi.local_synteny_multi",
            ],
            optimization_notes=(
                "根据输入自动路由：2 物种走 pairwise；≥3 物种走 all-vs-all 多物种聚合；"
                "提供目标基因时走 reference-vs-targets 局部共线性。"
            ),
            parameters=[
                ParameterDeclaration("reference", "string", False, "", "参考物种名称或 1-based 索引"),
                ParameterDeclaration("target_gene_ids", "array", False, [], "目标基因 ID 列表"),
                ParameterDeclaration("up", "integer", False, 20, "上游取基因数"),
                ParameterDeclaration("down", "integer", False, 20, "下游取基因数"),
                ParameterDeclaration("split_targets", "boolean", False, False, "每个目标基因单独出图"),
                ParameterDeclaration("label_targets", "boolean", False, False, "标注目标基因"),
                ParameterDeclaration(
                    "use_native_local_synteny_renderer", "boolean", False, False, "使用原生局部共线性渲染器"
                ),
                ParameterDeclaration("align_soft", "string", False, "blast", "比对后端"),
                ParameterDeclaration("cscore", "number", False, 0.7, "同源匹配过滤强度"),
                ParameterDeclaration("dist", "integer", False, 20, "共线性锚点间最大基因距离"),
                ParameterDeclaration("min_block_size", "integer", False, 1, "最小 block 大小"),
                ParameterDeclaration("threads", "integer", False, None, "线程数"),
                ParameterDeclaration("formats", "array", False, ["svg"], "输出格式"),
            ],
        )


# 模块级单例
_ONE_STOP_REGISTRY: OneStopWorkflowRegistry | None = None


def get_onestop_registry() -> OneStopWorkflowRegistry:
    """返回全局一站式工作流注册表实例"""

    global _ONE_STOP_REGISTRY
    if _ONE_STOP_REGISTRY is None:
        _ONE_STOP_REGISTRY = OneStopWorkflowRegistry()
    assert _ONE_STOP_REGISTRY is not None
    return _ONE_STOP_REGISTRY
