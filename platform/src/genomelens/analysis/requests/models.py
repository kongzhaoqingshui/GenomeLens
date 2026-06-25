"""统一 workflow request(工作流请求) 数据模型"""

# region import
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Self

from genomelens.utils.json import (
    _bool,
    _bool_dict,
    _dict,
    _float,
    _int,
    _list,
    _nested,
    _optional_int,
    _str,
    _str_list,
)

# endregion


_LEGACY_REQUEST_FIELDS = {
    "method",
    "method_config",
    "task_kind",
    "one_stop_workflow_id",
    "sub_module_id",
    "port_bindings",
    "composition",
}


def _reject_unknown_fields(data: dict[str, object], allowed: set[str], label: str) -> None:
    """拒绝未声明字段，避免请求协议继续膨胀成大参数桶"""

    unknown = sorted(set(data) - allowed)
    if unknown:
        raise ValueError(f"{label} contains unsupported fields: {', '.join(unknown)}")


def _reject_legacy_request_fields(data: dict[str, object]) -> None:
    """拒绝旧版请求字段"""

    found = sorted(_LEGACY_REQUEST_FIELDS & set(data))
    if found:
        raise ValueError(f"WorkflowRequest v2 does not accept legacy fields: {', '.join(found)}")


@dataclass(frozen=True)
class WorkflowSpeciesInput:
    """WorkflowSpeciesInput(工作流物种输入)：单个物种的文件描述"""

    # fmt: off
    name: str         # 物种公开名称
    input_mode: str   # 输入模式（bed_cds 或 gff_genome）
    bed: str = ""     # BED 文件路径（input_mode=bed_cds 时必填）
    cds: str = ""     # CDS FASTA 路径（input_mode=bed_cds 时必填）
    gff: str = ""     # GFF/GTF 路径（input_mode=gff_genome 时必填）
    genome: str = ""  # 基因组 FASTA 路径（input_mode=gff_genome 时必填）
    # fmt: on

    def to_json(self) -> dict[str, object]:
        """转为 JSON object(JSON 对象)"""

        data: dict[str, object] = {
            "name": self.name,
            "input_mode": self.input_mode,
        }
        for key, value in {
            "bed": self.bed,
            "cds": self.cds,
            "gff": self.gff,
            "genome": self.genome,
        }.items():
            if value:
                data[key] = value
        return data

    @classmethod
    def from_json(cls, data: dict[str, object]) -> Self:
        """从 JSON object(JSON 对象) 读取"""

        _reject_unknown_fields(data, {"name", "input_mode", "bed", "cds", "gff", "genome"}, "species[]")
        return cls(
            name=_str(data.get("name")),
            input_mode=_str(data.get("input_mode")),
            bed=_str(data.get("bed")),
            cds=_str(data.get("cds")),
            gff=_str(data.get("gff")),
            genome=_str(data.get("genome")),
        )


@dataclass(frozen=True)
class WorkflowOutput:
    """WorkflowOutput(工作流输出)：输出目录、覆盖策略和格式"""

    # fmt: off
    directory: str       # 输出目录路径
    force: bool = False  # 是否允许覆盖已有输出目录
    formats: list[str] = field(default_factory=lambda: ["svg"])  # 输出图件格式列表
    # fmt: on

    def to_json(self) -> dict[str, object]:
        """转为 JSON object(JSON 对象)"""

        return {
            "directory": self.directory,
            "force": self.force,
            "formats": list(self.formats),
        }

    @classmethod
    def from_json(cls, data: dict[str, object]) -> Self:
        """从 JSON object(JSON 对象) 读取"""

        _reject_unknown_fields(data, {"directory", "force", "formats"}, "output")
        return cls(
            directory=_str(data.get("directory")),
            force=_bool(data.get("force"), default=False),
            formats=_str_list(data.get("formats"), default=["svg"]),
        )


@dataclass(frozen=True)
class WorkflowRuntime:
    """WorkflowRuntime(运行时配置)：工作流无关的执行选项"""

    # fmt: off
    project_config: str = ""       # GenomeLens 项目级配置 JSON 路径
    engine_config: str = ""        # 引擎配置路径（当前为 jcvi.config.json）
    jcvi_engine: str = ""          # 显式指定 jcvi-genomelens 引擎
    blastn: str = ""               # 显式指定 blastn
    makeblastdb: str = ""          # 显式指定 makeblastdb
    lastal: str = ""               # 显式指定 lastal
    lastdb: str = ""               # 显式指定 lastdb
    threads: int | None = None     # 并行线程数
    min_block_size: int | None = None  # 最小 block 大小
    log_level: str = "INFO"        # 日志级别
    verbose: bool = False          # 是否启用详细日志
    console_log: bool = False      # 是否同时输出日志到控制台
    # fmt: on

    def to_json(self) -> dict[str, object]:
        """转为 JSON object(JSON 对象)"""

        return {
            "project_config": self.project_config,
            "engine_config": self.engine_config,
            "jcvi_engine": self.jcvi_engine,
            "blastn": self.blastn,
            "makeblastdb": self.makeblastdb,
            "lastal": self.lastal,
            "lastdb": self.lastdb,
            "threads": self.threads,
            "min_block_size": self.min_block_size,
            "log_level": self.log_level,
            "verbose": self.verbose,
            "console_log": self.console_log,
        }

    @classmethod
    def from_json(cls, data: dict[str, object]) -> Self:
        """从 JSON object(JSON 对象) 读取"""

        _reject_unknown_fields(
            data,
            {
                "project_config",
                "engine_config",
                "jcvi_engine",
                "blastn",
                "makeblastdb",
                "lastal",
                "lastdb",
                "threads",
                "min_block_size",
                "log_level",
                "verbose",
                "console_log",
            },
            "runtime",
        )
        return cls(
            project_config=_str(data.get("project_config")),
            engine_config=_str(data.get("engine_config")),
            jcvi_engine=_str(data.get("jcvi_engine")),
            blastn=_str(data.get("blastn")),
            makeblastdb=_str(data.get("makeblastdb")),
            lastal=_str(data.get("lastal")),
            lastdb=_str(data.get("lastdb")),
            threads=_optional_int(data.get("threads")),
            min_block_size=_optional_int(data.get("min_block_size")),
            log_level=_str(data.get("log_level"), default="INFO"),
            verbose=_bool(data.get("verbose"), default=False),
            console_log=_bool(data.get("console_log"), default=False),
        )


@dataclass(frozen=True)
class SyntenyParameters:
    """SyntenyParameters(共线性参数)：同源搜索与 block 扫描参数"""

    # fmt: off
    align_soft: str = "blast"  # 同源搜索后端
    dbtype: str = "nucl"       # 序列类型
    cscore: float = 0.7        # 同源比对 cscore 阈值
    dist: int = 20             # 共线性锚点距离阈值
    iter: int = 1              # block 过滤迭代次数
    min_block_size: int = 5    # 最小 block 大小
    allow_simplified_fallback: bool = False  # 是否允许简化回退
    # fmt: on

    def to_json(self) -> dict[str, object]:
        """转为 JSON object(JSON 对象)"""

        return {
            "align_soft": self.align_soft,
            "dbtype": self.dbtype,
            "cscore": self.cscore,
            "dist": self.dist,
            "iter": self.iter,
            "min_block_size": self.min_block_size,
            "allow_simplified_fallback": self.allow_simplified_fallback,
        }

    @classmethod
    def from_json(cls, data: dict[str, object]) -> Self:
        """从 JSON object(JSON 对象) 读取"""

        _reject_unknown_fields(
            data,
            {"align_soft", "dbtype", "cscore", "dist", "iter", "min_block_size", "allow_simplified_fallback"},
            "parameters.synteny",
        )
        return cls(
            align_soft=_str(data.get("align_soft"), default="blast"),
            dbtype=_str(data.get("dbtype"), default="nucl"),
            cscore=_float(data.get("cscore"), default=0.7),
            dist=_int(data.get("dist"), default=20),
            iter=_int(data.get("iter"), default=1),
            min_block_size=_int(data.get("min_block_size"), default=5),
            allow_simplified_fallback=_bool(data.get("allow_simplified_fallback"), default=False),
        )


@dataclass(frozen=True)
class LocalSyntenyParameters:
    """LocalSyntenyParameters(局部共线性参数)：目标基因与窗口设置"""

    # fmt: off
    target_gene_ids: list[str] = field(default_factory=list)  # 目标基因 ID 列表
    up: int = 20                      # 目标基因上游窗口
    down: int = 20                    # 目标基因下游窗口
    split_targets: bool = False       # 是否每个目标基因单独出图
    label_targets: bool = False       # 是否在图中标注目标基因
    use_native_renderer: bool = False # 是否使用 GenomeLens 原生局部渲染器
    # fmt: on

    def to_json(self) -> dict[str, object]:
        """转为 JSON object(JSON 对象)"""

        return {
            "target_gene_ids": list(self.target_gene_ids),
            "up": self.up,
            "down": self.down,
            "split_targets": self.split_targets,
            "label_targets": self.label_targets,
            "use_native_renderer": self.use_native_renderer,
        }

    @classmethod
    def from_json(cls, data: dict[str, object]) -> Self:
        """从 JSON object(JSON 对象) 读取"""

        _reject_unknown_fields(
            data,
            {"target_gene_ids", "up", "down", "split_targets", "label_targets", "use_native_renderer"},
            "parameters.local_synteny",
        )
        return cls(
            target_gene_ids=_str_list(data.get("target_gene_ids")),
            up=_int(data.get("up"), default=20),
            down=_int(data.get("down"), default=20),
            split_targets=_bool(data.get("split_targets"), default=False),
            label_targets=_bool(data.get("label_targets"), default=False),
            use_native_renderer=_bool(data.get("use_native_renderer"), default=False),
        )


@dataclass(frozen=True)
class PlotParameters:
    """PlotParameters(图件参数)：通用绘图样式"""

    # fmt: off
    glyphstyle: str = ""     # 基因形状
    glyphcolor: str = ""     # 基因着色策略
    shadestyle: str = ""     # 连线样式
    figsize: str = ""        # 画布尺寸
    dpi: int = 300           # 图件分辨率
    auto_optimization: dict[str, bool] = field(default_factory=dict)  # 自动优化开关
    # fmt: on

    def to_json(self) -> dict[str, object]:
        """转为 JSON object(JSON 对象)"""

        return {
            "glyphstyle": self.glyphstyle,
            "glyphcolor": self.glyphcolor,
            "shadestyle": self.shadestyle,
            "figsize": self.figsize,
            "dpi": self.dpi,
            "auto_optimization": dict(self.auto_optimization),
        }

    @classmethod
    def from_json(cls, data: dict[str, object]) -> Self:
        """从 JSON object(JSON 对象) 读取"""

        _reject_unknown_fields(
            data,
            {"glyphstyle", "glyphcolor", "shadestyle", "figsize", "dpi", "auto_optimization"},
            "parameters.plot",
        )
        return cls(
            glyphstyle=_str(data.get("glyphstyle")),
            glyphcolor=_str(data.get("glyphcolor")),
            shadestyle=_str(data.get("shadestyle")),
            figsize=_str(data.get("figsize")),
            dpi=_int(data.get("dpi"), default=300),
            auto_optimization=_bool_dict(data.get("auto_optimization")),
        )


@dataclass(frozen=True)
class HistogramParameters:
    """HistogramParameters(直方图参数)：plot-only histogram 输入与样式"""

    # fmt: off
    inputs: list[str] = field(default_factory=list)          # 直方图输入文件路径列表
    columns: list[int] = field(default_factory=lambda: [0])  # 要绘制的列索引
    skip: int = 0                 # 跳过行数
    bins: int = 20                # 分箱数量
    vmin: float | None = 0.0      # 最小值截断
    vmax: float | None = None     # 最大值截断
    xlabel: str = "value"         # X 轴标签
    title: str = ""               # 图标题
    base: int = 0                 # 对数底数
    facet: bool = False           # 是否按文件分面
    fill: str = "white"           # 柱状填充色
    # fmt: on

    def to_json(self) -> dict[str, object]:
        """转为 JSON object(JSON 对象)"""

        return {
            "inputs": list(self.inputs),
            "columns": list(self.columns),
            "skip": self.skip,
            "bins": self.bins,
            "vmin": self.vmin,
            "vmax": self.vmax,
            "xlabel": self.xlabel,
            "title": self.title,
            "base": self.base,
            "facet": self.facet,
            "fill": self.fill,
        }

    @classmethod
    def from_json(cls, data: dict[str, object]) -> Self:
        """从 JSON object(JSON 对象) 读取"""

        _reject_unknown_fields(
            data,
            {"inputs", "columns", "skip", "bins", "vmin", "vmax", "xlabel", "title", "base", "facet", "fill"},
            "parameters.histogram",
        )
        raw_columns = data.get("columns")
        return cls(
            inputs=_str_list(data.get("inputs")),
            columns=[_int(item, default=0) for item in raw_columns]
            if isinstance(raw_columns, list) and raw_columns
            else [0],
            skip=_int(data.get("skip"), default=0),
            bins=_int(data.get("bins"), default=20),
            vmin=_float(data.get("vmin"), default=0.0) if data.get("vmin") is not None else None,
            vmax=_float(data.get("vmax"), default=0.0) if data.get("vmax") is not None else None,
            xlabel=_str(data.get("xlabel"), default="value"),
            title=_str(data.get("title")),
            base=_int(data.get("base"), default=0),
            facet=_bool(data.get("facet"), default=False),
            fill=_str(data.get("fill"), default="white"),
        )


@dataclass(frozen=True)
class HeatmapParameters:
    """HeatmapParameters(热图参数)：plot-only heatmap 输入与样式"""

    # fmt: off
    matrix: str = ""             # 热图矩阵 CSV 路径
    rowgroups: str = ""          # 行分组文件路径
    cmap: str = ""               # 颜色映射
    groups: bool = False         # 是否对列分组聚类
    horizontalbar: bool = False  # 是否绘制顶部水平颜色条
    # fmt: on

    def to_json(self) -> dict[str, object]:
        """转为 JSON object(JSON 对象)"""

        return {
            "matrix": self.matrix,
            "rowgroups": self.rowgroups,
            "cmap": self.cmap,
            "groups": self.groups,
            "horizontalbar": self.horizontalbar,
        }

    @classmethod
    def from_json(cls, data: dict[str, object]) -> Self:
        """从 JSON object(JSON 对象) 读取"""

        _reject_unknown_fields(data, {"matrix", "rowgroups", "cmap", "groups", "horizontalbar"}, "parameters.heatmap")
        return cls(
            matrix=_str(data.get("matrix")),
            rowgroups=_str(data.get("rowgroups")),
            cmap=_str(data.get("cmap")),
            groups=_bool(data.get("groups"), default=False),
            horizontalbar=_bool(data.get("horizontalbar"), default=False),
        )


@dataclass(frozen=True)
class WorkflowParameters:
    """WorkflowParameters(工作流参数)：按领域拆分后的参数集合"""

    # fmt: off
    synteny: SyntenyParameters = field(default_factory=SyntenyParameters)
    local_synteny: LocalSyntenyParameters = field(default_factory=LocalSyntenyParameters)
    plot: PlotParameters = field(default_factory=PlotParameters)
    histogram: HistogramParameters = field(default_factory=HistogramParameters)
    heatmap: HeatmapParameters = field(default_factory=HeatmapParameters)
    extras: dict[str, object] = field(default_factory=dict)  # 预留给后续 workflow 的命名空间参数
    # fmt: on

    def to_json(self) -> dict[str, object]:
        """转为 JSON object(JSON 对象)"""

        data: dict[str, object] = {
            "synteny": self.synteny.to_json(),
            "local_synteny": self.local_synteny.to_json(),
            "plot": self.plot.to_json(),
            "histogram": self.histogram.to_json(),
            "heatmap": self.heatmap.to_json(),
        }
        if self.extras:
            data["extras"] = dict(self.extras)
        return data

    @classmethod
    def from_json(cls, data: dict[str, object]) -> Self:
        """从 JSON object(JSON 对象) 读取"""

        _reject_unknown_fields(
            data, {"synteny", "local_synteny", "plot", "histogram", "heatmap", "extras"}, "parameters"
        )
        return cls(
            synteny=SyntenyParameters.from_json(_dict(data.get("synteny"))),
            local_synteny=LocalSyntenyParameters.from_json(_dict(data.get("local_synteny"))),
            plot=PlotParameters.from_json(_dict(data.get("plot"))),
            histogram=HistogramParameters.from_json(_dict(data.get("histogram"))),
            heatmap=HeatmapParameters.from_json(_dict(data.get("heatmap"))),
            extras=_dict(data.get("extras")),
        )


@dataclass(frozen=True)
class WorkflowRequest:
    """WorkflowRequest(工作流请求)：CLI、GUI、插件和 Agent 共用的新公开入口"""

    # fmt: off
    workflow_id: str  # 工作流 ID，V3 仅保留 synteny
    species: list[WorkflowSpeciesInput] = field(default_factory=list)  # 参与分析的物种列表
    reference_index: int = 0  # 参考物种在 species[] 中的索引
    inputs: dict[str, object] = field(default_factory=dict)  # 子模块输入端口占位
    parameters: WorkflowParameters = field(default_factory=WorkflowParameters)  # 类型化参数集合
    output: WorkflowOutput = field(default_factory=lambda: WorkflowOutput(directory="workspace/output"))
    runtime: WorkflowRuntime = field(default_factory=WorkflowRuntime)
    schema_version: int = 3
    kind: str = "workflow_request"
    # fmt: on

    def to_json(self) -> dict[str, object]:
        """转为 JSON object(JSON 对象)"""

        return {
            "schema_version": self.schema_version,
            "kind": self.kind,
            "workflow_id": self.workflow_id,
            "species": [item.to_json() for item in self.species],
            "reference_index": self.reference_index,
            "inputs": dict(self.inputs),
            "parameters": self.parameters.to_json(),
            "output": self.output.to_json(),
            "runtime": self.runtime.to_json(),
        }

    @classmethod
    def from_json(cls, data: dict[str, object]) -> WorkflowRequest:
        """从 JSON object(JSON 对象) 读取"""

        _reject_legacy_request_fields(data)
        _reject_unknown_fields(
            data,
            {
                "schema_version",
                "kind",
                "workflow_id",
                "species",
                "reference_index",
                "inputs",
                "parameters",
                "output",
                "runtime",
            },
            "WorkflowRequest",
        )
        species = [_nested(WorkflowSpeciesInput, item) for item in _list(data.get("species"))]
        workflow_id = _str(data.get("workflow_id"))
        if workflow_id != "synteny":
            raise ValueError(
                f"WorkflowRequest V3 workflow_id 只能是 'synteny'，收到：{workflow_id!r}"
            )
        return cls(
            schema_version=_int(data.get("schema_version"), default=3),
            kind=_str(data.get("kind"), default="workflow_request"),
            workflow_id=workflow_id,
            species=species,
            reference_index=_int(data.get("reference_index"), default=0),
            inputs=_dict(data.get("inputs")),
            parameters=WorkflowParameters.from_json(_dict(data.get("parameters"))),
            output=_nested(WorkflowOutput, data.get("output")),
            runtime=_nested(WorkflowRuntime, data.get("runtime")),
        )

    @property
    def target_gene_ids(self) -> list[str]:
        """返回目标基因 ID 列表"""

        return list(self.parameters.local_synteny.target_gene_ids)

    @property
    def is_local_synteny(self) -> bool:
        """返回当前请求是否需要目标基因局部共线性路径"""

        return bool(self.parameters.local_synteny.target_gene_ids)

    @property
    def is_plot_only(self) -> bool:
        """返回当前请求是否为纯图件工作流（V3 已取消，始终为 False）"""

        return False


def workflow_template_request() -> WorkflowRequest:
    """生成新版 WorkflowRequest 模板"""

    return WorkflowRequest(
        workflow_id="synteny",
        species=[
            WorkflowSpeciesInput(
                name="species_a",
                input_mode="bed_cds",
                bed="workspace/species_a.bed",
                cds="workspace/species_a.cds",
            ),
            WorkflowSpeciesInput(
                name="species_b",
                input_mode="bed_cds",
                bed="workspace/species_b.bed",
                cds="workspace/species_b.cds",
            ),
        ],
        output=WorkflowOutput(directory="workspace/output", formats=["svg"]),
    )


__all__ = [
    "HeatmapParameters",
    "HistogramParameters",
    "LocalSyntenyParameters",
    "PlotParameters",
    "SyntenyParameters",
    "WorkflowOutput",
    "WorkflowParameters",
    "WorkflowRequest",
    "WorkflowRuntime",
    "WorkflowSpeciesInput",
    "workflow_template_request",
]
