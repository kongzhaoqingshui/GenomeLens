"""可编排子模块注册表

维护 GenomeLens 平台所有可独立运行或可被组合的子模块元数据，包括输入/输出端口、
参数声明和引擎 workflow 映射。
"""

# region import
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from genomelens.analysis.workflows.input_bindings import PortDeclaration, PortSystem

# endregion


SubModuleKind = Literal["lightweight", "aggregate"]


@dataclass(frozen=True)
class ParameterDeclaration:
    """参数声明：子模块或工作流的可调参数"""

    # fmt: off
    param_id: str           # 参数唯一标识
    param_type: str         # 参数类型（string/integer/number/boolean/array）
    required: bool          # 是否必填
    default: object = None  # 默认值
    description: str = ""   # 参数用途描述
    # fmt: on

    def to_json(self) -> dict[str, object]:
        data: dict[str, object] = {
            "param_id": self.param_id,
            "param_type": self.param_type,
            "required": self.required,
            "description": self.description,
        }
        if self.default is not None:
            data["default"] = self.default
        return data


@dataclass(frozen=True)
class SubModuleSpec:
    """子模块规范：单个可编排子模块的完整元数据"""

    # fmt: off
    module_id: str        # 子模块唯一标识（如 jcvi.graphics_dotplot）
    name: str             # 面向用户展示的子模块名称
    description: str      # 子模块功能描述
    category: str         # 子模块分类（visualization/homology_search/synteny_analysis）
    module_kind: SubModuleKind  # 子模块编排类型（lightweight/aggregate）
    engine_workflow: str  # 映射到底层引擎的 workflow 名称
    standalone: bool      # 是否可独立运行
    inputs: list[PortDeclaration] = field(default_factory=list)           # 输入端口声明
    outputs: list[PortDeclaration] = field(default_factory=list)          # 输出端口声明
    parameters: list[ParameterDeclaration] = field(default_factory=list)  # 可调参数声明
    # fmt: on

    def to_json(self) -> dict[str, object]:
        return {
            "module_id": self.module_id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "module_kind": self.module_kind,
            "engine_workflow": self.engine_workflow,
            "standalone": self.standalone,
            "inputs": PortSystem.describe_ports(self.inputs),
            "outputs": PortSystem.describe_ports(self.outputs),
            "parameters": [p.to_json() for p in self.parameters],
        }


class SubModuleRegistry:
    """子模块注册表：统一管理子模块元数据"""

    def __init__(self) -> None:
        self._modules: dict[str, SubModuleSpec] = {}
        self._register_builtin_jcvi_modules()

    def register(self, spec: SubModuleSpec) -> None:
        """注册一个子模块规范"""

        self._modules[spec.module_id] = spec

    def get(self, module_id: str) -> SubModuleSpec | None:
        """按 ID 获取子模块规范"""

        return self._modules.get(module_id)

    def list_all(self) -> list[SubModuleSpec]:
        """返回全部子模块规范"""

        return list(self._modules.values())

    def list_by_category(self, category: str) -> list[SubModuleSpec]:
        """按分类返回子模块规范"""

        return [spec for spec in self._modules.values() if spec.category == category]

    def list_by_kind(self, module_kind: SubModuleKind) -> list[SubModuleSpec]:
        """按编排类型返回子模块规范"""

        return [spec for spec in self._modules.values() if spec.module_kind == module_kind]

    def _register_builtin_jcvi_modules(self) -> None:
        """注册 JCVI 引擎内置子模块"""

        self.register(self._build_pairwise_module())
        self.register(self._build_graphics_dotplot_module())
        self.register(self._build_graphics_synteny_module())
        self.register(self._build_graphics_karyotype_module())
        self.register(self._build_local_synteny_module())
        self.register(self._build_graphics_histogram_module())
        self.register(self._build_graphics_heatmap_module())
        self.register(self._build_graphics_karyotype_global_module())
        self.register(self._build_local_synteny_multi_module())

    @staticmethod
    def _species_pair_port(required: bool = True) -> PortDeclaration:
        return PortDeclaration(
            port_id="species_pair",
            port_kind="species_pair",
            required=required,
            description="两个物种的 BED/CDS 或 GFF/FASTA 输入对",
        )

    @staticmethod
    def _figures_port() -> PortDeclaration:
        return PortDeclaration(
            port_id="figures",
            port_kind="artifact",
            required=False,
            description="生成的图件文件列表",
            artifact_type="figures",
            accepted_formats=[".svg", ".pdf", ".png"],
        )

    def _build_pairwise_module(self) -> SubModuleSpec:
        return SubModuleSpec(
            module_id="jcvi.pairwise",
            name="Pairwise Synteny",
            description=(
                "对两个物种执行 BLAST/LAST/Diamond 比对、锚点扫描与 block 计算；"
                "emit_ortholog=true 时附带产出双向 ortholog 目录"
            ),
            category="homology_search",
            module_kind="lightweight",
            engine_workflow="pairwise",
            standalone=True,
            inputs=[
                self._species_pair_port(),
                PortDeclaration(
                    port_id="toolchain",
                    port_kind="config",
                    required=False,
                    description="比对工具链路径（blastn/makeblastdb/lastal/lastdb）",
                ),
            ],
            outputs=[
                PortDeclaration(
                    port_id="blast_table",
                    port_kind="artifact",
                    required=False,
                    description="BLAST 同源比对表",
                    artifact_type="blast_table",
                    accepted_formats=[".blast"],
                ),
                PortDeclaration(
                    port_id="anchors",
                    port_kind="artifact",
                    required=False,
                    description="共线性锚点文件",
                    artifact_type="anchors",
                    accepted_formats=[".anchors"],
                ),
                PortDeclaration(
                    port_id="simple",
                    port_kind="artifact",
                    required=False,
                    description="简化共线性边文件",
                    artifact_type="simple",
                    accepted_formats=[".simple"],
                ),
                PortDeclaration(
                    port_id="blocks",
                    port_kind="artifact",
                    required=False,
                    description="共线性 block 文件",
                    artifact_type="blocks",
                    accepted_formats=[".blocks"],
                ),
                PortDeclaration(
                    port_id="ortholog",
                    port_kind="artifact",
                    required=False,
                    description="双向同源基因表（emit_ortholog=true 时产出）",
                    artifact_type="ortholog",
                    accepted_formats=[".ortholog"],
                ),
            ],
            parameters=[
                ParameterDeclaration("align_soft", "string", False, "blast", "比对后端"),
                ParameterDeclaration("dbtype", "string", False, "nucl", "序列类型"),
                ParameterDeclaration("emit_ortholog", "boolean", False, False, "是否额外产出双向 ortholog 目录"),
                ParameterDeclaration("cscore", "number", False, 0.7, "同源匹配过滤强度"),
                ParameterDeclaration("dist", "integer", False, 20, "共线性锚点间最大基因距离"),
                ParameterDeclaration("iter", "integer", False, 1, "Block 过滤迭代次数"),
                ParameterDeclaration("min_block_size", "integer", False, 1, "最小 block 大小"),
                ParameterDeclaration("threads", "integer", False, None, "线程数"),
            ],
        )

    def _build_graphics_dotplot_module(self) -> SubModuleSpec:
        return SubModuleSpec(
            module_id="jcvi.graphics_dotplot",
            name="Dotplot",
            description="基于锚点绘制两个物种的共线性点图",
            category="visualization",
            module_kind="lightweight",
            engine_workflow="graphics_dotplot",
            standalone=True,
            inputs=[
                self._species_pair_port(),
                PortDeclaration(
                    port_id="anchors",
                    port_kind="artifact",
                    required=True,
                    description="共线性锚点文件",
                    artifact_type="anchors",
                    accepted_formats=[".anchors"],
                ),
            ],
            outputs=[self._figures_port()],
            parameters=[
                ParameterDeclaration("figsize", "string", False, "", "画布尺寸"),
                ParameterDeclaration("dpi", "integer", False, 300, "分辨率"),
                ParameterDeclaration("formats", "array", False, ["svg"], "输出格式"),
            ],
        )

    def _build_graphics_synteny_module(self) -> SubModuleSpec:
        return SubModuleSpec(
            module_id="jcvi.graphics_synteny",
            name="Synteny Figure",
            description="基于 blocks 与 layout 绘制多物种共线性对齐图",
            category="visualization",
            module_kind="lightweight",
            engine_workflow="graphics_synteny",
            standalone=True,
            inputs=[
                self._species_pair_port(),
                PortDeclaration(
                    port_id="blocks",
                    port_kind="artifact",
                    required=True,
                    description="共线性 block 文件",
                    artifact_type="blocks",
                    accepted_formats=[".blocks"],
                ),
                PortDeclaration(
                    port_id="layout",
                    port_kind="artifact",
                    required=False,
                    description="JCVI layout 文件",
                    artifact_type="layout",
                    accepted_formats=[".layout"],
                ),
            ],
            outputs=[self._figures_port()],
            parameters=[
                ParameterDeclaration("glyphstyle", "string", False, "", "基因形状"),
                ParameterDeclaration("glyphcolor", "string", False, "", "基因着色"),
                ParameterDeclaration("shadestyle", "string", False, "", "连线样式"),
                ParameterDeclaration("figsize", "string", False, "", "画布尺寸"),
                ParameterDeclaration("dpi", "integer", False, 300, "分辨率"),
                ParameterDeclaration("formats", "array", False, ["svg"], "输出格式"),
            ],
        )

    def _build_graphics_karyotype_module(self) -> SubModuleSpec:
        return SubModuleSpec(
            module_id="jcvi.graphics_karyotype",
            name="Karyotype",
            description="绘制物种内或两物种核型共线性图",
            category="visualization",
            module_kind="lightweight",
            engine_workflow="graphics_karyotype",
            standalone=True,
            inputs=[
                self._species_pair_port(),
                PortDeclaration(
                    port_id="blocks",
                    port_kind="artifact",
                    required=True,
                    description="共线性 block 文件",
                    artifact_type="blocks",
                    accepted_formats=[".blocks"],
                ),
                PortDeclaration(
                    port_id="simple",
                    port_kind="artifact",
                    required=False,
                    description="简化共线性边文件",
                    artifact_type="simple",
                    accepted_formats=[".simple"],
                ),
                PortDeclaration(
                    port_id="layout",
                    port_kind="artifact",
                    required=False,
                    description="核型图 layout 文件",
                    artifact_type="layout",
                    accepted_formats=[".layout"],
                ),
                PortDeclaration(
                    port_id="karyotype_seqids",
                    port_kind="artifact",
                    required=False,
                    description="核型图 seqids 文件",
                    artifact_type="seqids",
                    accepted_formats=[".seqids"],
                ),
            ],
            outputs=[
                self._figures_port(),
                PortDeclaration(
                    port_id="karyotype_seqids",
                    port_kind="artifact",
                    required=False,
                    description="核型图 seqids 文件",
                    artifact_type="seqids",
                    accepted_formats=[".seqids"],
                ),
                PortDeclaration(
                    port_id="karyotype_layout",
                    port_kind="artifact",
                    required=False,
                    description="核型图 layout 文件",
                    artifact_type="layout",
                    accepted_formats=[".layout"],
                ),
            ],
            parameters=[
                ParameterDeclaration("figsize", "string", False, "", "画布尺寸"),
                ParameterDeclaration("dpi", "integer", False, 300, "分辨率"),
                ParameterDeclaration("formats", "array", False, ["svg"], "输出格式"),
            ],
        )

    def _build_local_synteny_module(self) -> SubModuleSpec:
        return SubModuleSpec(
            module_id="jcvi.local_synteny",
            name="Local Synteny",
            description="以目标基因为中心绘制局部共线性图",
            category="synteny_analysis",
            module_kind="lightweight",
            engine_workflow="local_synteny",
            standalone=True,
            inputs=[
                self._species_pair_port(),
                PortDeclaration(
                    port_id="blocks",
                    port_kind="artifact",
                    required=True,
                    description="共线性 block 文件",
                    artifact_type="blocks",
                    accepted_formats=[".blocks"],
                ),
                PortDeclaration(
                    port_id="target_genes",
                    port_kind="value",
                    required=True,
                    description="目标基因 ID 列表",
                ),
            ],
            outputs=[self._figures_port()],
            parameters=[
                ParameterDeclaration("up", "integer", False, 20, "目标基因上游取基因数"),
                ParameterDeclaration("down", "integer", False, 20, "目标基因下游取基因数"),
                ParameterDeclaration("split_targets", "boolean", False, False, "每个目标基因单独出图"),
                ParameterDeclaration("label_targets", "boolean", False, False, "标注目标基因名称"),
                ParameterDeclaration(
                    "use_native_local_synteny_renderer", "boolean", False, False, "使用原生 matplotlib 渲染器"
                ),
            ],
        )

    def _build_graphics_histogram_module(self) -> SubModuleSpec:
        return SubModuleSpec(
            module_id="jcvi.graphics_histogram",
            name="Histogram",
            description="绘制数值分布直方图",
            category="visualization",
            module_kind="lightweight",
            engine_workflow="graphics_histogram",
            standalone=True,
            inputs=[
                PortDeclaration(
                    port_id="numeric_files",
                    port_kind="artifact",
                    required=True,
                    description="输入数值文件列表",
                    artifact_type="numeric_file",
                    accepted_formats=[".txt", ".tsv", ".csv"],
                ),
            ],
            outputs=[self._figures_port()],
            parameters=[
                ParameterDeclaration("histogram_columns", "array", False, [0], "读取列号"),
                ParameterDeclaration("histogram_bins", "integer", False, 20, "bin 数"),
                ParameterDeclaration("histogram_vmin", "number", False, 0.0, "最小值下界"),
                ParameterDeclaration("histogram_vmax", "number", False, None, "最大值上界"),
                ParameterDeclaration("histogram_xlabel", "string", False, "value", "X 轴标签"),
                ParameterDeclaration("histogram_title", "string", False, "", "图标题"),
                ParameterDeclaration("histogram_base", "integer", False, 0, "对数坐标底数"),
                ParameterDeclaration("histogram_facet", "boolean", False, False, "分面展示"),
                ParameterDeclaration("histogram_fill", "string", False, "white", "柱体填充色"),
            ],
        )

    def _build_graphics_heatmap_module(self) -> SubModuleSpec:
        return SubModuleSpec(
            module_id="jcvi.graphics_heatmap",
            name="Heatmap",
            description="将矩阵 CSV 渲染为热图",
            category="visualization",
            module_kind="lightweight",
            engine_workflow="graphics_heatmap",
            standalone=True,
            inputs=[
                PortDeclaration(
                    port_id="matrix_csv",
                    port_kind="artifact",
                    required=True,
                    description="矩阵 CSV 文件",
                    artifact_type="matrix",
                    accepted_formats=[".csv"],
                ),
            ],
            outputs=[self._figures_port()],
            parameters=[
                ParameterDeclaration("groups", "boolean", False, False, "首行作为列分组"),
                ParameterDeclaration("rowgroups", "string", False, "", "行分组文件路径"),
                ParameterDeclaration("horizontalbar", "boolean", False, False, "水平色条"),
                ParameterDeclaration("cmap", "string", False, "jet", "matplotlib colormap"),
                ParameterDeclaration("figsize", "string", False, "", "画布尺寸"),
                ParameterDeclaration("dpi", "integer", False, 300, "分辨率"),
                ParameterDeclaration("formats", "array", False, ["svg"], "输出格式"),
            ],
        )

    def _build_graphics_karyotype_global_module(self) -> SubModuleSpec:
        return SubModuleSpec(
            module_id="jcvi.graphics_karyotype_global",
            name="Global Karyotype",
            description="基于 tracks 与 edges 聚合全局核型总图",
            category="visualization",
            module_kind="aggregate",
            engine_workflow="graphics_karyotype_global",
            standalone=True,
            inputs=[
                PortDeclaration(
                    port_id="tracks",
                    port_kind="value",
                    required=True,
                    description="轨道列表（每个 track 包含 name 与 bed 路径）",
                ),
                PortDeclaration(
                    port_id="edges",
                    port_kind="value",
                    required=True,
                    description="共线性边列表（每个 edge 包含 i/j/simple 路径）",
                ),
            ],
            outputs=[self._figures_port()],
            parameters=[
                ParameterDeclaration("figsize", "string", False, "", "画布尺寸"),
                ParameterDeclaration("dpi", "integer", False, 300, "分辨率"),
                ParameterDeclaration("formats", "array", False, ["svg"], "输出格式"),
            ],
        )

    def _build_local_synteny_multi_module(self) -> SubModuleSpec:
        return SubModuleSpec(
            module_id="jcvi.local_synteny_multi",
            name="Multi-Species Local Synteny",
            description="在多个物种间以目标基因为中心绘制局部共线性总图",
            category="synteny_analysis",
            module_kind="aggregate",
            engine_workflow="local_synteny_multi",
            standalone=True,
            inputs=[
                PortDeclaration(
                    port_id="tracks",
                    port_kind="value",
                    required=True,
                    description="多物种轨道列表",
                ),
                PortDeclaration(
                    port_id="blocks",
                    port_kind="artifact",
                    required=True,
                    description="共线性 block 文件",
                    artifact_type="blocks",
                    accepted_formats=[".blocks"],
                ),
                PortDeclaration(
                    port_id="bed",
                    port_kind="artifact",
                    required=True,
                    description="合并后的 BED 文件",
                    artifact_type="bed",
                    accepted_formats=[".bed"],
                ),
                PortDeclaration(
                    port_id="target_genes",
                    port_kind="value",
                    required=True,
                    description="目标基因 ID 列表",
                ),
            ],
            outputs=[self._figures_port()],
            parameters=[
                ParameterDeclaration("up", "integer", False, 20, "上游取基因数"),
                ParameterDeclaration("down", "integer", False, 20, "下游取基因数"),
                ParameterDeclaration("split_targets", "boolean", False, False, "每个目标基因单独出图"),
                ParameterDeclaration("label_targets", "boolean", False, False, "标注目标基因"),
                ParameterDeclaration("use_native_local_synteny_renderer", "boolean", False, False, "使用原生渲染器"),
            ],
        )


# 模块级单例，供 CLI/GUI/插件统一使用
_SUBMODULE_REGISTRY: SubModuleRegistry | None = None


def get_submodule_registry() -> SubModuleRegistry:
    """返回全局子模块注册表实例"""

    global _SUBMODULE_REGISTRY
    if _SUBMODULE_REGISTRY is None:
        _SUBMODULE_REGISTRY = SubModuleRegistry()
    assert _SUBMODULE_REGISTRY is not None
    return _SUBMODULE_REGISTRY
