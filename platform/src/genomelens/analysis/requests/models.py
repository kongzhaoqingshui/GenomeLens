"""统一 analysis request(分析请求) 数据模型"""

# region import
from __future__ import annotations

from dataclasses import dataclass, field

from genomelens.core.json_utils import (
    _bool,
    _bool_dict,
    _dict,
    _dict_list,
    _float,
    _int,
    _list,
    _nested,
    _optional_int,
    _optional_str,
    _str,
    _str_list,
)

# endregion


@dataclass(frozen=True)
class AnalysisSpeciesInput:
    """AnalysisSpeciesInput(分析物种输入)：单个物种的文件描述"""

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
    def from_json(cls, data: dict[str, object]) -> AnalysisSpeciesInput:
        """从 JSON object(JSON 对象) 读取"""

        return cls(
            name=_str(data.get("name")),
            input_mode=_str(data.get("input_mode")),
            bed=_str(data.get("bed")),
            cds=_str(data.get("cds")),
            gff=_str(data.get("gff")),
            genome=_str(data.get("genome")),
        )


@dataclass(frozen=True)
class AnalysisInput:
    """AnalysisInput(分析输入)：输入模式、目录与物种列表"""

    # fmt: off
    mode: str            # 输入模式（auto_directory/method_specific/bed_cds 等）
    directory: str = ""  # 输入目录或主文件路径
    species: list[AnalysisSpeciesInput] = field(default_factory=list)  # 显式指定的物种列表
    reference_index: int = 0  # 物种列表中参考物种的索引
    # fmt: on

    def to_json(self) -> dict[str, object]:
        data: dict[str, object] = {
            "mode": self.mode,
            "directory": self.directory,
            "species": [item.to_json() for item in self.species],
        }
        # 默认 reference_index 为 0，省略可保持请求体精简并兼容旧版本
        if self.reference_index != 0:
            data["reference_index"] = self.reference_index
        return data

    @classmethod
    def from_json(cls, data: dict[str, object]) -> AnalysisInput:
        species = _dict_list(data.get("species"))

        return cls(
            mode=_str(data.get("mode")),
            directory=_str(data.get("directory")),
            species=[AnalysisSpeciesInput.from_json(item) for item in species],
            reference_index=_int(data.get("reference_index"), default=0),
        )


@dataclass(frozen=True)
class AnalysisOutput:
    """AnalysisOutput(分析输出)：输出目录、覆盖策略和格式"""

    # fmt: off
    directory: str       # 输出目录路径
    force: bool = False  # 是否允许覆盖已有输出目录
    formats: list[str] = field(default_factory=lambda: ["svg"])  # 输出图件格式列表
    # fmt: on

    def to_json(self) -> dict[str, object]:
        return {
            "directory": self.directory,
            "force": self.force,
            "formats": self.formats,
        }

    @classmethod
    def from_json(cls, data: dict[str, object]) -> AnalysisOutput:
        return cls(
            directory=_str(data.get("directory")),
            force=_bool(data.get("force"), default=False),
            formats=_str_list(data.get("formats"), default=["svg"]),
        )


@dataclass(frozen=True)
class AnalysisConfigRef:
    """AnalysisConfigRef(分析配置引用)：主配置与方法配置路径"""

    # fmt: off
    project_config: str = ""  # GenomeLens 项目级配置 JSON 路径
    method_config: str = ""   # 方法专属配置（如 jcvi.config.json）路径
    # fmt: on

    def to_json(self) -> dict[str, object]:
        return {
            "project_config": self.project_config,
            "method_config": self.method_config,
        }

    @classmethod
    def from_json(cls, data: dict[str, object]) -> AnalysisConfigRef:
        return cls(
            project_config=_str(data.get("project_config")),
            method_config=_str(data.get("method_config")),
        )


@dataclass(frozen=True)
class AnalysisOptions:
    """AnalysisOptions(分析选项)：方法无关的通用可调参数

    注意：方法专属参数（如 JCVI 的 workflow/blastn/seqids）不放在这里，而是下沉到
    `AnalysisRequest.method_config`。新方法接入时只定义自己的 method config 类型，
    不应再向本类添加字段。
    """

    # fmt: off
    preset: str = "auto"               # 分析预设策略
    threads: int | None = None         # 并行线程数
    min_block_size: int | None = None  # 最小 block 大小
    log_level: str = "INFO"            # 日志级别
    verbose: bool = False              # 是否启用详细日志
    console_log: bool = False          # 是否同时输出日志到控制台
    # fmt: on

    def to_json(self) -> dict[str, object]:
        return {
            "preset": self.preset,
            "threads": self.threads,
            "min_block_size": self.min_block_size,
            "log_level": self.log_level,
            "verbose": self.verbose,
            "console_log": self.console_log,
        }

    @classmethod
    def from_json(cls, data: dict[str, object]) -> AnalysisOptions:
        return cls(
            preset=_str(data.get("preset"), default="auto"),
            threads=_optional_int(data.get("threads")),
            min_block_size=_optional_int(data.get("min_block_size")),
            log_level=_str(data.get("log_level"), default="INFO"),
            verbose=_bool(data.get("verbose"), default=False),
            console_log=_bool(data.get("console_log"), default=False),
        )


@dataclass(frozen=True)
class McscanMethodConfig:
    """McscanMethodConfig(mcscan 方法配置)：mcscan/JCVI 方法专属的内联载荷

    这是 `AnalysisRequest.method_config` 在 method=mcscan 时的具体形态。其他方法
    （syri / pangenome 等）接入时各自定义对应的 method config 类型，互不污染。
    """

    # fmt: off
    workflow: str = "graphics_synteny"  # 要调用的 JCVI workflow 名称
    jcvi_engine: str = ""  # 显式指定的引擎可执行文件路径
    blastn: str = ""       # 显式指定的 blastn 路径
    makeblastdb: str = ""  # 显式指定的 makeblastdb 路径
    jcvi_layout: str = ""  # JCVI layout 文件路径（synteny/karyotype/heatmap 行分组）
    jcvi_seqids: str = ""  # JCVI seqids 文件路径
    allow_simplified_fallback: bool = False  # 是否允许简化回退（生产环境应关闭）
    # 同源搜索与共线性参数
    align_soft: str = "blast"  # 同源搜索后端
    dbtype: str = "nucl"       # 序列类型
    cscore: float = 0.7        # 同源比对 cscore 阈值
    dist: int = 20             # 共线性锚点距离阈值
    iter: int = 1              # block 过滤迭代次数
    # 目标基因局部共线性参数
    target_gene_ids: list[str] = field(default_factory=list)  # 目标基因 ID 列表
    up: int = 20    # 目标基因上游窗口大小
    down: int = 20  # 目标基因下游窗口大小
    split_targets: bool = False  # 每个目标基因是否单独出图
    label_targets: bool = False  # 是否标注目标基因名称
    # 图件样式参数
    glyphstyle: str = ""  # 基因形状
    glyphcolor: str = ""  # 基因着色策略
    shadestyle: str = ""  # 连线样式
    figsize: str = ""     # 画布尺寸
    dpi: int = 300        # 图件分辨率
    # 热图 workflow 参数
    cmap: str = ""               # 颜色映射
    groups: bool = False         # 是否对列分组聚类
    horizontalbar: bool = False  # 是否绘制顶部水平颜色条
    # GenomeLens 自动优化开关（嵌套，便于区分原生 JCVI 参数）
    auto_optimization: dict[str, bool] = field(default_factory=dict)  # 自动优化开关集合
    use_native_local_synteny_renderer: bool = False  # 是否使用原生 matplotlib 局部渲染器
    # 直方图 workflow 参数
    histogram_inputs: list[str] = field(default_factory=list)          # 直方图输入文件路径列表
    histogram_columns: list[int] = field(default_factory=lambda: [0])  # 要绘制的列索引
    histogram_skip: int = 0              # 直方图要跳过的行数
    histogram_bins: int = 20             # 分箱数量
    histogram_vmin: float | None = 0.0   # 最小值截断
    histogram_vmax: float | None = None  # 最大值截断
    histogram_xlabel: str = "value"      # X 轴标签
    histogram_title: str = ""            # 图标题
    histogram_base: int = 0              # 对数底数（0 为线性）
    histogram_facet: bool = False        # 是否按文件分面
    histogram_fill: str = "white"        # 柱状填充色
    # 热图 workflow 参数
    matrix: str = ""  # 热图矩阵 CSV 路径
    # fmt: on

    def to_json(self) -> dict[str, object]:
        return {
            "workflow": self.workflow,
            "jcvi_engine": self.jcvi_engine,
            "blastn": self.blastn,
            "makeblastdb": self.makeblastdb,
            "jcvi_layout": self.jcvi_layout,
            "jcvi_seqids": self.jcvi_seqids,
            "allow_simplified_fallback": self.allow_simplified_fallback,
            "align_soft": self.align_soft,
            "dbtype": self.dbtype,
            "cscore": self.cscore,
            "dist": self.dist,
            "iter": self.iter,
            "target_gene_ids": list(self.target_gene_ids),
            "up": self.up,
            "down": self.down,
            "split_targets": self.split_targets,
            "label_targets": self.label_targets,
            "glyphstyle": self.glyphstyle,
            "glyphcolor": self.glyphcolor,
            "shadestyle": self.shadestyle,
            "figsize": self.figsize,
            "dpi": self.dpi,
            "cmap": self.cmap,
            "groups": self.groups,
            "horizontalbar": self.horizontalbar,
            "auto_optimization": dict(self.auto_optimization),
            "use_native_local_synteny_renderer": self.use_native_local_synteny_renderer,
            "histogram_inputs": list(self.histogram_inputs),
            "histogram_columns": list(self.histogram_columns),
            "histogram_skip": self.histogram_skip,
            "histogram_bins": self.histogram_bins,
            "histogram_vmin": self.histogram_vmin,
            "histogram_vmax": self.histogram_vmax,
            "histogram_xlabel": self.histogram_xlabel,
            "histogram_title": self.histogram_title,
            "histogram_base": self.histogram_base,
            "histogram_facet": self.histogram_facet,
            "histogram_fill": self.histogram_fill,
            "matrix": self.matrix,
        }

    @classmethod
    def from_json(cls, data: dict[str, object]) -> McscanMethodConfig:
        raw_histogram_columns = data.get("histogram_columns")
        return cls(
            workflow=_str(data.get("workflow"), default="graphics_synteny"),
            jcvi_engine=_str(data.get("jcvi_engine")),
            blastn=_str(data.get("blastn")),
            makeblastdb=_str(data.get("makeblastdb")),
            jcvi_layout=_str(data.get("jcvi_layout")),
            jcvi_seqids=_str(data.get("jcvi_seqids")),
            allow_simplified_fallback=_bool(data.get("allow_simplified_fallback"), default=False),
            align_soft=_str(data.get("align_soft"), default="blast"),
            dbtype=_str(data.get("dbtype"), default="nucl"),
            cscore=_float(data.get("cscore"), default=0.7),
            dist=_int(data.get("dist"), default=20),
            iter=_int(data.get("iter"), default=1),
            target_gene_ids=_str_list(data.get("target_gene_ids")),
            up=_int(data.get("up"), default=20),
            down=_int(data.get("down"), default=20),
            split_targets=_bool(data.get("split_targets"), default=False),
            label_targets=_bool(data.get("label_targets"), default=False),
            glyphstyle=_str(data.get("glyphstyle")),
            glyphcolor=_str(data.get("glyphcolor")),
            shadestyle=_str(data.get("shadestyle")),
            figsize=_str(data.get("figsize")),
            dpi=_int(data.get("dpi"), default=300),
            cmap=_str(data.get("cmap")),
            groups=_bool(data.get("groups"), default=False),
            horizontalbar=_bool(data.get("horizontalbar"), default=False),
            auto_optimization=_bool_dict(data.get("auto_optimization")),
            use_native_local_synteny_renderer=_bool(data.get("use_native_local_synteny_renderer"), default=False),
            histogram_inputs=_str_list(data.get("histogram_inputs")),
            histogram_columns=[_int(item, default=0) for item in raw_histogram_columns]
            if isinstance(raw_histogram_columns, list) and raw_histogram_columns
            else [0],
            histogram_skip=_int(data.get("histogram_skip"), default=0),
            histogram_bins=_int(data.get("histogram_bins"), default=20),
            histogram_vmin=_float(data.get("histogram_vmin"), default=0.0),
            histogram_vmax=_float(data.get("histogram_vmax"), default=0.0)
            if data.get("histogram_vmax") is not None
            else None,
            histogram_xlabel=_str(data.get("histogram_xlabel"), default="value"),
            histogram_title=_str(data.get("histogram_title")),
            histogram_base=_int(data.get("histogram_base"), default=0),
            histogram_facet=_bool(data.get("histogram_facet"), default=False),
            histogram_fill=_str(data.get("histogram_fill"), default="white"),
            matrix=_str(data.get("matrix")),
        )


@dataclass(frozen=True)
class PortBinding:
    """PortBinding(端口绑定)：运行时子模块端口的具体值

    在 AnalysisRequest 中通常以 `port_bindings: dict[str, object]` 平铺存储，
    键为 port_id，值为运行时值。本 dataclass 用于代码层显式转换。
    """

    # fmt: off
    port_id: str   # 子模块端口唯一标识
    value: object  # 运行时绑定的端口值
    # fmt: on

    def to_json(self) -> dict[str, object]:
        return {"port_id": self.port_id, "value": self.value}

    @classmethod
    def from_json(cls, data: dict[str, object]) -> PortBinding:
        return cls(port_id=_str(data.get("port_id")), value=data.get("value"))


@dataclass(frozen=True)
class WorkflowComposition:
    """WorkflowComposition(工作流组合)：多个子模块按 DAG 连接

    当前为面向未来 GUI 可视化编排的预留结构。节点表示子模块实例，边表示
    端口之间的数据流动。
    """

    # fmt: off
    nodes: list[dict[str, object]] = field(default_factory=list)  # 子模块实例节点列表
    edges: list[dict[str, object]] = field(default_factory=list)  # 端口连接边列表
    # fmt: on

    def to_json(self) -> dict[str, object]:
        return {
            "nodes": list(self.nodes),
            "edges": list(self.edges),
        }

    @classmethod
    def from_json(cls, data: dict[str, object]) -> WorkflowComposition:
        return cls(
            nodes=[dict(item) for item in _list(data.get("nodes")) if isinstance(item, dict)],
            edges=[dict(item) for item in _list(data.get("edges")) if isinstance(item, dict)],
        )


@dataclass(frozen=True)
class AnalysisRequest:
    """AnalysisRequest(分析请求)：CLI、GUI、插件和 Agent 共用的稳定入口

    1.X 架构新增 `task_kind` 字段以区分三种使用模式：
    - "analysis"：旧模式/兼容模式，由 `method` + `method_config` 驱动。
    - "one_stop"：一站式工作流，由 `one_stop_workflow_id` 驱动。
    - "sub_module"：可编排子模块，由 `sub_module_id` + `port_bindings` 驱动。
    - "composition"：子模块组合（未来 GUI 编排），由 `composition` 驱动。
    """

    # fmt: off
    method: str             # 分析方法名（如 mcscan）
    input: AnalysisInput    # 输入配置
    output: AnalysisOutput  # 输出配置
    config: AnalysisConfigRef = field(default_factory=AnalysisConfigRef)  # 配置引用
    options: AnalysisOptions = field(default_factory=AnalysisOptions)     # 通用分析选项
    method_config: dict[str, object] = field(default_factory=dict)        # 方法专属配置载荷
    schema_version: int = 1         # 请求 JSON schema 版本
    kind: str = "analysis_request"  # 请求类型常量
    task_kind: str = "analysis"     # 任务模式（analysis/one_stop/sub_module/composition）
    one_stop_workflow_id: str | None = None  # one_stop 模式下的一站式工作流 ID
    sub_module_id: str | None = None         # sub_module 模式下的子模块 ID
    port_bindings: dict[str, object] = field(default_factory=dict)  # 子模块端口绑定
    composition: WorkflowComposition | None = None  # 可视化编排组合（预留）
    # fmt: on

    def to_json(self) -> dict[str, object]:
        data: dict[str, object] = {
            "schema_version": self.schema_version,
            "kind": self.kind,
            "method": self.method,
            "input": self.input.to_json(),
            "output": self.output.to_json(),
            "config": self.config.to_json(),
            "options": self.options.to_json(),
            "method_config": dict(self.method_config),
        }
        # 1.X 扩展字段仅在非默认值时写出，保持旧请求体精简
        if self.task_kind != "analysis":
            data["task_kind"] = self.task_kind
        if self.one_stop_workflow_id is not None:
            data["one_stop_workflow_id"] = self.one_stop_workflow_id
        if self.sub_module_id is not None:
            data["sub_module_id"] = self.sub_module_id
        if self.port_bindings:
            data["port_bindings"] = dict(self.port_bindings)
        if self.composition is not None:
            data["composition"] = self.composition.to_json()
        return data

    @classmethod
    def from_json(cls, data: dict[str, object]) -> AnalysisRequest:
        composition_raw = data.get("composition")
        composition = None
        if isinstance(composition_raw, dict):
            composition = WorkflowComposition.from_json(composition_raw)

        return cls(
            schema_version=_int(data.get("schema_version"), default=1),
            kind=_str(data.get("kind"), default="analysis_request"),
            method=_str(data.get("method")),
            input=_nested(AnalysisInput, data.get("input")),
            output=_nested(AnalysisOutput, data.get("output")),
            config=_nested(AnalysisConfigRef, data.get("config")),
            options=_nested(AnalysisOptions, data.get("options")),
            method_config=_dict(data.get("method_config")),
            task_kind=_str(data.get("task_kind"), default="analysis"),
            one_stop_workflow_id=_optional_str(data.get("one_stop_workflow_id")),
            sub_module_id=_optional_str(data.get("sub_module_id")),
            port_bindings=_dict(data.get("port_bindings")),
            composition=composition,
        )
