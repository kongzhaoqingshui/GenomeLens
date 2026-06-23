"""平台内部执行请求模型

这些 dataclass 是 `AnalysisRequest` 进入执行层后的类型化形态，面向 runners 和
provider，不直接暴露给 CLI/GUI/JSON。它们按 workflow 类型拆分，避免把 synteny、
histogram、heatmap 的生命周期与字段混在一个大配置对象里。
"""

# region import
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from genomelens.core.models import AnalysisTaskSpec, GenomeInputSpec

# endregion


@dataclass(frozen=True)
class McscanExecutionRequest:
    """McscanExecutionRequest：synteny / MCscan 类工作流的内部执行请求"""

    # fmt: off
    query: GenomeInputSpec    # 参考/查询物种输入
    subject: GenomeInputSpec  # 目标/比较物种输入
    outdir: Path  # 工作流输出根目录
    additional_species: list[GenomeInputSpec] = field(default_factory=list)  # 除 query/subject 外的额外物种
    threads: int = 4          # 并行线程数
    min_block_size: int = 5   # 共线性 block 最小基因数
    formats: list[str] = field(default_factory=lambda: ["svg"])  # 输出图件格式列表
    jcvi_engine: str = ""     # 显式指定的 jcvi-genomelens 可执行文件路径
    jcvi_workflow: str = "graphics_synteny"  # 要调用的 JCVI workflow 名称
    blastn_path: str = ""       # 显式指定的 blastn 路径
    makeblastdb_path: str = ""  # 显式指定的 makeblastdb 路径
    lastal_path: str = ""       # 显式指定的 lastal 路径
    lastdb_path: str = ""       # 显式指定的 lastdb 路径
    jcvi_layout: str = ""       # JCVI layout 文件路径（synteny/karyotype 使用）
    jcvi_seqids: str = ""       # JCVI seqids 文件路径
    allow_simplified_fallback: bool = False  # 是否允许简化回退（生产环境应关闭）
    force: bool = False  # 是否覆盖已有输出目录

    # 同源搜索与共线性参数
    align_soft: str = "blast"  # 同源搜索后端（blast/last/diamond_blastp）
    dbtype: str = "nucl"       # 序列类型（nucl/prot）
    cscore: float = 0.7   # 同源比对的 cscore 阈值
    dist: int = 20             # 共线性锚点距离阈值
    iter: int = 1              # block 过滤迭代次数

    # 目标基因局部共线性参数
    target_gene_ids: list[str] = field(default_factory=list)  # 目标基因 ID 列表
    up: int = 20    # 目标基因上游窗口大小
    down: int = 20  # 目标基因下游窗口大小
    split_targets: bool = False  # 是否每个目标基因单独出图
    label_targets: bool = False  # 是否在图中标注目标基因名称

    # 图件样式参数
    glyphstyle: str = ""     # 基因形状（box/arrow）
    glyphcolor: str = ""     # 基因着色策略（orientation/orthogroup）
    shadestyle: str = ""     # 连线样式（curve/line）
    figsize: str = ""        # 画布尺寸（如 10x5）
    dpi: int = 300           # 图件分辨率
    log_level: str = "INFO"  # 日志级别
    verbose: bool = False    # 是否输出更详细的日志
    auto_optimization: dict[str, bool] = field(default_factory=dict)  # GenomeLens 自动优化开关
    console_log: bool = False  # 是否同时输出到控制台
    use_native_local_synteny_renderer: bool = False  # 是否使用原生 matplotlib 局部共线性渲染
    # fmt: on

    @property
    def species(self) -> list[GenomeInputSpec]:
        """返回当前任务涉及的物种列表"""

        return [self.query, self.subject, *self.additional_species]

    @property
    def task_id(self) -> str:
        """返回稳定但可读的任务标识"""

        names = "__".join(species.name for species in self.species)
        return f"{names}__{self.jcvi_workflow}"

    @property
    def task_spec(self) -> AnalysisTaskSpec:
        """构建平台核心使用的任务规格"""

        return AnalysisTaskSpec(
            task_id=self.task_id,
            task_type="pairwise_synteny" if len(self.species) == 2 else "multi_species_synteny",
            workflow=self.jcvi_workflow,
            species=self.species,
        )


@dataclass(frozen=True)
class HeatmapExecutionRequest:
    """HeatmapExecutionRequest：独立热图绘制的内部执行请求"""

    # fmt: off
    matrix: Path  # 热图矩阵 CSV 文件路径
    outdir: Path  # 输出目录
    formats: list[str] = field(default_factory=lambda: ["svg"])  # 输出图件格式
    jcvi_engine: str = ""          # 显式指定的引擎路径
    figsize: str = ""              # 画布尺寸
    dpi: int = 300                 # 图件分辨率
    cmap: str = ""                 # 颜色映射名称
    groups: bool = False           # 是否按列分组聚类
    rowgroups: Path | None = None  # 行分组文件路径
    horizontalbar: bool = False    # 是否在顶部绘制水平颜色条
    force: bool = False            # 是否覆盖已有输出目录
    log_level: str = "INFO"        # 日志级别
    # fmt: on

    @property
    def workflow(self) -> str:
        """返回公开 workflow 名称"""

        return "graphics_heatmap"

    @property
    def task_id(self) -> str:
        """返回稳定但可读的任务标识"""

        return f"{self.matrix.stem}__{self.workflow}"

    @property
    def task_spec(self) -> AnalysisTaskSpec:
        """构建平台核心使用的任务规格"""

        return AnalysisTaskSpec(
            task_id=self.task_id,
            task_type="plot_heatmap",
            workflow=self.workflow,
            species=[],
        )


@dataclass(frozen=True)
class HistogramExecutionRequest:
    """HistogramExecutionRequest：plot-only 直方图的内部执行请求"""

    # fmt: off
    inputs: list[Path]  # 直方图输入文件路径列表
    outdir: Path        # 输出目录
    columns: list[int] = field(default_factory=lambda: [0])      # 要绘制的列索引
    formats: list[str] = field(default_factory=lambda: ["svg"])  # 输出图件格式
    jcvi_engine: str = ""                # 显式指定的引擎路径
    force: bool = False                  # 是否覆盖已有输出目录
    histogram_skip: int = 0              # 直方图要跳过的行数
    histogram_bins: int = 20             # 分箱数量
    histogram_vmin: float | None = 0.0   # 最小值截断
    histogram_vmax: float | None = None  # 最大值截断
    histogram_xlabel: str = "value"      # X 轴标签
    histogram_title: str = ""            # 图标题
    histogram_base: int = 0              # 对数底数（0 为线性，2/10 为对数）
    histogram_facet: bool = False        # 是否按文件分面
    histogram_fill: str = "white"        # 柱状填充色
    dpi: int = 300             # 图件分辨率
    log_level: str = "INFO"    # 日志级别
    verbose: bool = False      # 是否输出详细日志
    console_log: bool = False  # 是否同时输出到控制台
    # fmt: on

    @property
    def workflow(self) -> str:
        """返回稳定的 workflow 名称"""

        return "graphics_histogram"

    @property
    def task_id(self) -> str:
        """返回可读且稳定的任务标识"""

        stems = "__".join(path.stem for path in self.inputs)
        suffix = "cols_" + "_".join(str(item) for item in self.columns)
        return f"{stems}__{suffix}__{self.workflow}"

    @property
    def task_spec(self) -> AnalysisTaskSpec:
        """构建平台核心使用的任务规格"""

        return AnalysisTaskSpec(
            task_id=self.task_id,
            task_type="plot_histogram",
            workflow=self.workflow,
            species=[],
        )
