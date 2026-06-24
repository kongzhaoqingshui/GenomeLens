"""平台内部执行计划与执行请求模型"""

# region import
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from genomelens.contracts.species import AnalysisTaskSpec, GenomeInputSpec

# endregion


StepKind = Literal[
    "pairwise_synteny",
    "global_karyotype",
    "multi_local_synteny",
    "graphics_histogram",
    "graphics_heatmap",
]


@dataclass(frozen=True)
class StepInputRef:
    """StepInputRef(步骤输入引用)：指向前序 step 的产物"""

    # fmt: off
    step_id: str     # 上游 step ID
    artifact_id: str # 上游产物 ID
    # fmt: on

    def to_json(self) -> dict[str, object]:
        """转为 JSON object(JSON 对象)"""

        return {"step_id": self.step_id, "artifact_id": self.artifact_id}


@dataclass(frozen=True)
class StepOutputRef:
    """StepOutputRef(步骤输出引用)：声明 step 预期产物"""

    # fmt: off
    artifact_id: str    # 产物 ID
    artifact_type: str  # 产物类型
    required: bool = False  # 是否为必需产物
    # fmt: on

    def to_json(self) -> dict[str, object]:
        """转为 JSON object(JSON 对象)"""

        return {
            "artifact_id": self.artifact_id,
            "artifact_type": self.artifact_type,
            "required": self.required,
        }


@dataclass(frozen=True)
class PairwiseArtifactInputs:
    """PairwiseArtifactInputs(pairwise 产物输入)：描述可复用的 pairwise core 产物"""

    # fmt: off
    blast_table: Path | None = None  # BLAST/同源比对表
    anchors: Path | None = None      # anchors 文件
    simple: Path | None = None       # simple 文件
    blocks: Path | None = None       # blocks 文件
    merged_bed: Path | None = None   # 合并后的 BED
    layout: Path | None = None       # synteny layout 文件
    # fmt: on

    def to_manifest_json(self) -> dict[str, str]:
        """转为 manifest `inputs.pairwise_artifacts` 对象"""

        data: dict[str, str] = {}
        for key in ("blast_table", "anchors", "simple", "blocks", "merged_bed", "layout"):
            value = getattr(self, key)
            if value is not None:
                data[key] = str(value)
        return data

    @property
    def has_any(self) -> bool:
        """返回是否至少携带一个可复用产物"""

        return any(getattr(self, key) is not None for key in ("blast_table", "anchors", "simple", "blocks"))


@dataclass(frozen=True)
class SyntenyExecutionRequest:
    """SyntenyExecutionRequest：synteny / MCscan 类工作流的内部执行请求"""

    # fmt: off
    reference: GenomeInputSpec  # 参考物种输入
    target: GenomeInputSpec     # 目标/比较物种输入
    outdir: Path                # 工作流输出根目录
    additional_species: list[GenomeInputSpec] = field(default_factory=list)  # 除 reference/target 外的额外物种
    threads: int = 4            # 并行线程数
    min_block_size: int = 5     # 共线性 block 最小基因数
    formats: list[str] = field(default_factory=lambda: ["svg"])  # 输出图件格式列表
    engine_path: str = ""       # 显式指定的 jcvi-genomelens 可执行文件路径
    engine_workflow: str = "graphics_synteny"  # 要调用的 JCVI workflow 名称
    blastn_path: str = ""       # 显式指定的 blastn 路径
    makeblastdb_path: str = ""  # 显式指定的 makeblastdb 路径
    lastal_path: str = ""       # 显式指定的 lastal 路径
    lastdb_path: str = ""       # 显式指定的 lastdb 路径
    layout_path: str = ""       # JCVI layout 文件路径
    seqids_path: str = ""       # JCVI seqids 文件路径
    allow_simplified_fallback: bool = False  # 是否允许简化回退
    force: bool = False         # 是否覆盖已有输出目录
    precomputed_artifacts: PairwiseArtifactInputs | None = None  # 预计算的 pairwise 产物
    input_ports: dict[str, object] = field(default_factory=dict)  # 子模块输入端口快照

    align_soft: str = "blast"   # 同源搜索后端
    dbtype: str = "nucl"        # 序列类型
    cscore: float = 0.7         # 同源比对 cscore 阈值
    dist: int = 20              # 共线性锚点距离阈值
    iter: int = 1               # block 过滤迭代次数

    target_gene_ids: list[str] = field(default_factory=list)  # 目标基因 ID 列表
    up: int = 20                # 目标基因上游窗口
    down: int = 20              # 目标基因下游窗口
    split_targets: bool = False # 是否每个目标基因单独出图
    label_targets: bool = False # 是否在图中标注目标基因名称

    glyphstyle: str = ""        # 基因形状
    glyphcolor: str = ""        # 基因着色策略
    shadestyle: str = ""        # 连线样式
    figsize: str = ""           # 画布尺寸
    dpi: int = 300              # 图件分辨率
    log_level: str = "INFO"     # 日志级别
    verbose: bool = False       # 是否输出更详细日志
    auto_optimization: dict[str, bool] = field(default_factory=dict)  # 自动优化开关
    console_log: bool = False   # 是否同时输出到控制台
    use_native_local_synteny_renderer: bool = False  # 是否使用原生局部共线性渲染器
    # fmt: on

    @property
    def species(self) -> list[GenomeInputSpec]:
        """返回当前任务涉及的物种列表"""

        return [self.reference, self.target, *self.additional_species]

    @property
    def query(self) -> GenomeInputSpec:
        """返回 pairwise workflow 内部使用的 query 物种"""

        return self.reference

    @property
    def subject(self) -> GenomeInputSpec:
        """返回 pairwise workflow 内部使用的 subject 物种"""

        return self.target

    @property
    def jcvi_engine(self) -> str:
        """返回当前 JCVI engine 路径"""

        return self.engine_path

    @property
    def jcvi_workflow(self) -> str:
        """返回当前 JCVI workflow 名称"""

        return self.engine_workflow

    @property
    def jcvi_layout(self) -> str:
        """返回 layout 路径"""

        return self.layout_path

    @property
    def jcvi_seqids(self) -> str:
        """返回 seqids 路径"""

        return self.seqids_path

    @property
    def task_id(self) -> str:
        """返回稳定但可读的任务标识"""

        names = "__".join(species.name for species in self.species)
        return f"{names}__{self.engine_workflow}"

    @property
    def task_spec(self) -> AnalysisTaskSpec:
        """构建平台核心使用的任务规格"""

        return AnalysisTaskSpec(
            task_id=self.task_id,
            task_type="pairwise_synteny" if len(self.species) == 2 else "multi_species_synteny",
            workflow=self.engine_workflow,
            species=self.species,
        )


@dataclass(frozen=True)
class HeatmapExecutionRequest:
    """HeatmapExecutionRequest：独立热图绘制的内部执行请求"""

    # fmt: off
    matrix: Path  # 热图矩阵 CSV 文件路径
    outdir: Path  # 输出目录
    formats: list[str] = field(default_factory=lambda: ["svg"])  # 输出图件格式
    engine_path: str = ""          # 显式指定的引擎路径
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
    def jcvi_engine(self) -> str:
        """返回当前 JCVI engine 路径"""

        return self.engine_path

    @property
    def task_id(self) -> str:
        """返回稳定但可读的任务标识"""

        return f"{self.matrix.stem}__{self.workflow}"

    @property
    def task_spec(self) -> AnalysisTaskSpec:
        """构建平台核心使用的任务规格"""

        return AnalysisTaskSpec(task_id=self.task_id, task_type="plot_heatmap", workflow=self.workflow, species=[])


@dataclass(frozen=True)
class HistogramExecutionRequest:
    """HistogramExecutionRequest：plot-only 直方图的内部执行请求"""

    # fmt: off
    inputs: list[Path]  # 直方图输入文件路径列表
    outdir: Path        # 输出目录
    columns: list[int] = field(default_factory=lambda: [0])      # 要绘制的列索引
    formats: list[str] = field(default_factory=lambda: ["svg"])  # 输出图件格式
    engine_path: str = ""                # 显式指定的引擎路径
    force: bool = False                  # 是否覆盖已有输出目录
    histogram_skip: int = 0              # 要跳过的行数
    histogram_bins: int = 20             # 分箱数量
    histogram_vmin: float | None = 0.0   # 最小值截断
    histogram_vmax: float | None = None  # 最大值截断
    histogram_xlabel: str = "value"      # X 轴标签
    histogram_title: str = ""            # 图标题
    histogram_base: int = 0              # 对数底数
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
    def jcvi_engine(self) -> str:
        """返回当前 JCVI engine 路径"""

        return self.engine_path

    @property
    def task_id(self) -> str:
        """返回可读且稳定的任务标识"""

        stems = "__".join(path.stem for path in self.inputs)
        suffix = "cols_" + "_".join(str(item) for item in self.columns)
        return f"{stems}__{suffix}__{self.workflow}"

    @property
    def task_spec(self) -> AnalysisTaskSpec:
        """构建平台核心使用的任务规格"""

        return AnalysisTaskSpec(task_id=self.task_id, task_type="plot_histogram", workflow=self.workflow, species=[])


@dataclass(frozen=True)
class ExecutionStep:
    """ExecutionStep(执行步骤)：执行计划中的一个 DAG 节点"""

    # fmt: off
    step_id: str       # 步骤唯一标识
    kind: StepKind     # 步骤类型
    payload: object    # 类型化执行请求或聚合参数
    depends_on: list[str] = field(default_factory=list)        # 上游 step ID 列表
    inputs: list[StepInputRef] = field(default_factory=list)    # 上游产物引用
    outputs: list[StepOutputRef] = field(default_factory=list)  # 预期输出声明
    # fmt: on


@dataclass(frozen=True)
class ExecutionPlan:
    """ExecutionPlan(执行计划)：由 WorkflowRequest 展开的平台执行 DAG"""

    # fmt: off
    plan_id: str           # 计划 ID
    workflow_id: str       # 公开 workflow ID
    outdir: Path           # 顶层输出目录
    force: bool = False    # 是否覆盖输出目录
    steps: list[ExecutionStep] = field(default_factory=list)  # 执行步骤列表
    reference_name: str | None = None  # reference-vs-targets 参考物种名
    target_names: list[str] = field(default_factory=list)     # reference-vs-targets 目标物种名
    # fmt: on
