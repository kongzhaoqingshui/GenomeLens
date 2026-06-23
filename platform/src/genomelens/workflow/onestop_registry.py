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

    workflow_id: str
    name: str
    description: str
    category: str
    runner: str
    engine_workflow: str | None
    equivalent_modules: list[str]
    optimization_notes: str
    inputs: list = field(default_factory=list)
    outputs: list = field(default_factory=list)
    parameters: list[ParameterDeclaration] = field(default_factory=list)

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

        self.register(self._build_pairwise_synteny())
        self.register(self._build_multi_species_synteny())
        self.register(self._build_reference_vs_targets())
        self.register(self._build_histogram_plot())
        self.register(self._build_heatmap_plot())

    def _build_pairwise_synteny(self) -> OneStopWorkflowSpec:
        return OneStopWorkflowSpec(
            workflow_id="pairwise_synteny",
            name="Pairwise Synteny Analysis",
            description="两个物种的共线性分析一站式流程：预处理、比对、MCscan、出图",
            category="synteny_analysis",
            runner="pairwise_runner",
            engine_workflow="graphics_synteny",
            equivalent_modules=["jcvi.mcscan_pairwise", "jcvi.graphics_synteny"],
            optimization_notes=(
                "一站式路径内部预计算 layout、合并 BED、并行生成 dotplot 与 synteny，"
                "避免子模块拼接时的中间文件重复读写。"
            ),
            parameters=[
                ParameterDeclaration("align_soft", "string", False, "blast", "比对后端"),
                ParameterDeclaration("cscore", "number", False, 0.7, "同源匹配过滤强度"),
                ParameterDeclaration("dist", "integer", False, 20, "共线性锚点间最大基因距离"),
                ParameterDeclaration("min_block_size", "integer", False, 1, "最小 block 大小"),
                ParameterDeclaration("threads", "integer", False, None, "线程数"),
                ParameterDeclaration("formats", "array", False, ["svg"], "输出格式"),
            ],
        )

    def _build_multi_species_synteny(self) -> OneStopWorkflowSpec:
        return OneStopWorkflowSpec(
            workflow_id="multi_species_synteny",
            name="Multi-Species Synteny",
            description="三个及以上物种的 all-vs-all 共线性分析与全局核型总图",
            category="synteny_analysis",
            runner="multi_species_runner",
            engine_workflow="graphics_karyotype_global",
            equivalent_modules=["jcvi.mcscan_pairwise", "jcvi.graphics_karyotype_global"],
            optimization_notes=(
                "一站式路径自动拆分为 all-vs-all pairwise 子任务并行执行，"
                "并将成功的共线性边聚合为全局核型总图；未来可加入布局自动优化。"
            ),
            parameters=[
                ParameterDeclaration("align_soft", "string", False, "blast", "比对后端"),
                ParameterDeclaration("cscore", "number", False, 0.7, "同源匹配过滤强度"),
                ParameterDeclaration("dist", "integer", False, 20, "共线性锚点间最大基因距离"),
                ParameterDeclaration("min_block_size", "integer", False, 1, "最小 block 大小"),
                ParameterDeclaration("threads", "integer", False, None, "线程数"),
                ParameterDeclaration("formats", "array", False, ["svg"], "输出格式"),
            ],
        )

    def _build_reference_vs_targets(self) -> OneStopWorkflowSpec:
        return OneStopWorkflowSpec(
            workflow_id="reference_vs_targets",
            name="Reference vs Targets",
            description="以参考物种为中心，与多个目标物种进行 pairwise 分析并聚合局部共线性",
            category="synteny_analysis",
            runner="reference_vs_targets_runner",
            engine_workflow="local_synteny_multi",
            equivalent_modules=["jcvi.mcscan_pairwise", "jcvi.local_synteny_multi"],
            optimization_notes=(
                "一站式路径针对 reference-vs-targets 场景做 pairwise 并行与局部共线性聚合，"
                "共享中间 BED/CDS 与 blocks，避免每个目标重复预处理。"
            ),
            parameters=[
                ParameterDeclaration("reference", "string", False, "", "参考物种名称或索引"),
                ParameterDeclaration("target_gene_ids", "array", False, [], "目标基因 ID 列表"),
                ParameterDeclaration("up", "integer", False, 20, "上游取基因数"),
                ParameterDeclaration("down", "integer", False, 20, "下游取基因数"),
                ParameterDeclaration("split_targets", "boolean", False, False, "每个目标基因单独出图"),
                ParameterDeclaration("label_targets", "boolean", False, False, "标注目标基因"),
                ParameterDeclaration("use_native_local_synteny_renderer", "boolean", False, False, "使用原生渲染器"),
            ],
        )

    def _build_histogram_plot(self) -> OneStopWorkflowSpec:
        return OneStopWorkflowSpec(
            workflow_id="histogram_plot",
            name="Histogram Plot",
            description="数值分布直方图一站式绘制",
            category="visualization",
            runner="histogram_runner",
            engine_workflow="graphics_histogram",
            equivalent_modules=["jcvi.graphics_histogram"],
            optimization_notes="纯 matplotlib 渲染，不依赖 JCVI 引擎，执行路径轻量。",
            parameters=[
                ParameterDeclaration("histogram_columns", "array", False, [0], "读取列号"),
                ParameterDeclaration("histogram_bins", "integer", False, 20, "bin 数"),
                ParameterDeclaration("histogram_title", "string", False, "", "图标题"),
                ParameterDeclaration("histogram_base", "integer", False, 0, "对数坐标底数"),
            ],
        )

    def _build_heatmap_plot(self) -> OneStopWorkflowSpec:
        return OneStopWorkflowSpec(
            workflow_id="heatmap_plot",
            name="Heatmap Plot",
            description="矩阵 CSV 热图一站式绘制",
            category="visualization",
            runner="plot_heatmap_command",
            engine_workflow="graphics_heatmap",
            equivalent_modules=["jcvi.graphics_heatmap"],
            optimization_notes="直接消费矩阵 CSV，复用 JCVI heatmap 渲染能力。",
            parameters=[
                ParameterDeclaration("groups", "boolean", False, False, "首行作为列分组"),
                ParameterDeclaration("rowgroups", "string", False, "", "行分组文件路径"),
                ParameterDeclaration("horizontalbar", "boolean", False, False, "水平色条"),
                ParameterDeclaration("cmap", "string", False, "jet", "matplotlib colormap"),
            ],
        )


# 模块级单例
_ONE_STOP_REGISTRY: OneStopWorkflowRegistry | None = None


def get_onestop_registry() -> OneStopWorkflowRegistry:
    """返回全局一站式工作流注册表实例"""

    global _ONE_STOP_REGISTRY
    if _ONE_STOP_REGISTRY is None:
        _ONE_STOP_REGISTRY = OneStopWorkflowRegistry()
    return _ONE_STOP_REGISTRY
