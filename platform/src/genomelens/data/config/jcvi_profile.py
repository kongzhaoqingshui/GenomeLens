"""JCVI engine profile 数据模型：纯默认参数模板"""

# region import
from __future__ import annotations

from dataclasses import asdict, dataclass, field

from genomelens.utils.json import _bool, _dict, _float, _int, _str, _str_list

# endregion


@dataclass
class SyntenyProfileDefaults:
    """SyntenyProfileDefaults(共线性默认参数)"""

    # fmt: off
    align_soft: str = "blast"  # 默认同源搜索后端
    dbtype: str = "nucl"       # 默认序列类型
    cscore: float = 0.7        # 默认 cscore 阈值
    dist: int = 20             # 默认锚点距离
    iter: int = 1              # 默认 block 过滤迭代次数
    min_block_size: int = 5    # 默认最小 block 基因数
    # fmt: on


@dataclass
class LocalSyntenyProfileDefaults:
    """LocalSyntenyProfileDefaults(局部共线性默认参数)

    注意：profile 不再包含任务身份或目标基因列表，只提供默认窗口与渲染选项。
    """

    # fmt: off
    up: int = 20    # 默认上游窗口大小
    down: int = 20  # 默认下游窗口大小
    split_targets: bool = False  # 每个目标基因是否单独出图
    label_targets: bool = False  # 是否标注目标基因名称
    use_native_local_synteny_renderer: bool = False  # 是否使用原生 matplotlib 渲染器
    # fmt: on


@dataclass
class AutoOptimizationDefaults:
    """AutoOptimizationDefaults(出图自动优化开关)"""

    # fmt: off
    optimize_figsize: bool = False           # 自动推导 synteny 图件尺寸
    rewrite_layout_links: bool = False       # 改写跨轨道 layout 连线为邻接轨道链
    optimize_karyotype_labels: bool = False  # 自动优化核型图轨道标签位置
    # fmt: on


@dataclass
class PlotProfileDefaults:
    """PlotProfileDefaults(通用绘图默认参数)"""

    # fmt: off
    glyphstyle: str = ""     # 基因形状
    glyphcolor: str = ""     # 基因着色策略
    shadestyle: str = ""     # 连线样式
    figsize: str = ""        # 画布尺寸
    dpi: int = 300           # 图件分辨率
    auto_optimization: AutoOptimizationDefaults = field(default_factory=AutoOptimizationDefaults)
    # fmt: on


@dataclass
class HistogramProfileDefaults:
    """HistogramProfileDefaults(直方图默认参数)"""

    # fmt: off
    inputs: list[str] = field(default_factory=list)
    columns: list[int] = field(default_factory=lambda: [0])
    skip: int = 0
    bins: int = 20
    vmin: float | None = 0.0
    vmax: float | None = None
    xlabel: str = "value"
    title: str = ""
    base: int = 0
    facet: bool = False
    fill: str = "white"
    # fmt: on


@dataclass
class HeatmapProfileDefaults:
    """HeatmapProfileDefaults(热图默认参数)"""

    # fmt: off
    matrix: str = ""
    rowgroups: str = ""
    cmap: str = ""
    groups: bool = False
    horizontalbar: bool = False
    # fmt: on


@dataclass
class JcviProfileModel:
    """JcviProfileModel(JCVI 引擎默认值模板)

    V3 升级为纯默认参数模板，不承载任务身份、参考物种、目标基因或输入路径。
    """

    # fmt: off
    schema_version: int = 3
    synteny: SyntenyProfileDefaults = field(default_factory=SyntenyProfileDefaults)
    local_synteny: LocalSyntenyProfileDefaults = field(default_factory=LocalSyntenyProfileDefaults)
    plot: PlotProfileDefaults = field(default_factory=PlotProfileDefaults)
    histogram: HistogramProfileDefaults = field(default_factory=HistogramProfileDefaults)
    heatmap: HeatmapProfileDefaults = field(default_factory=HeatmapProfileDefaults)
    # fmt: on

    def to_json_dict(self) -> dict[str, object]:
        """序列化为 engine profile 配置文件"""

        return {
            "schema_version": self.schema_version,
            "synteny": {
                "align_soft": self.synteny.align_soft,
                "dbtype": self.synteny.dbtype,
                "cscore": self.synteny.cscore,
                "dist": self.synteny.dist,
                "iter": self.synteny.iter,
                "min_block_size": self.synteny.min_block_size,
            },
            "local_synteny": {
                "up": self.local_synteny.up,
                "down": self.local_synteny.down,
                "split_targets": self.local_synteny.split_targets,
                "label_targets": self.local_synteny.label_targets,
                "use_native_local_synteny_renderer": self.local_synteny.use_native_local_synteny_renderer,
            },
            "plot": {
                "glyphstyle": self.plot.glyphstyle,
                "glyphcolor": self.plot.glyphcolor,
                "shadestyle": self.plot.shadestyle,
                "figsize": self.plot.figsize,
                "dpi": self.plot.dpi,
                "auto_optimization": {
                    "optimize_figsize": self.plot.auto_optimization.optimize_figsize,
                    "rewrite_layout_links": self.plot.auto_optimization.rewrite_layout_links,
                    "optimize_karyotype_labels": self.plot.auto_optimization.optimize_karyotype_labels,
                },
            },
            "histogram": {
                "inputs": list(self.histogram.inputs),
                "columns": list(self.histogram.columns),
                "skip": self.histogram.skip,
                "bins": self.histogram.bins,
                "vmin": self.histogram.vmin,
                "vmax": self.histogram.vmax,
                "xlabel": self.histogram.xlabel,
                "title": self.histogram.title,
                "base": self.histogram.base,
                "facet": self.histogram.facet,
                "fill": self.histogram.fill,
            },
            "heatmap": {
                "matrix": self.heatmap.matrix,
                "rowgroups": self.heatmap.rowgroups,
                "cmap": self.heatmap.cmap,
                "groups": self.heatmap.groups,
                "horizontalbar": self.heatmap.horizontalbar,
            },
        }

    @classmethod
    def from_json_dict(cls, data: dict[str, object]) -> JcviProfileModel:
        """从 engine profile JSON 反序列化"""

        synteny_raw = _dict(data.get("synteny"))
        synteny = SyntenyProfileDefaults(
            align_soft=_str(synteny_raw.get("align_soft"), default="blast"),
            dbtype=_str(synteny_raw.get("dbtype"), default="nucl"),
            cscore=_float(synteny_raw.get("cscore"), default=0.7),
            dist=_int(synteny_raw.get("dist"), default=20),
            iter=_int(synteny_raw.get("iter"), default=1),
            min_block_size=_int(synteny_raw.get("min_block_size"), default=5),
        )

        local_raw = _dict(data.get("local_synteny"))
        local_synteny = LocalSyntenyProfileDefaults(
            up=_int(local_raw.get("up"), default=20),
            down=_int(local_raw.get("down"), default=20),
            split_targets=_bool(local_raw.get("split_targets"), default=False),
            label_targets=_bool(local_raw.get("label_targets"), default=False),
            use_native_local_synteny_renderer=_bool(local_raw.get("use_native_local_synteny_renderer"), default=False),
        )

        plot_raw = _dict(data.get("plot"))
        auto_opt_raw = _dict(plot_raw.get("auto_optimization"))
        auto_optimization = AutoOptimizationDefaults(
            optimize_figsize=_bool(auto_opt_raw.get("optimize_figsize"), default=False),
            rewrite_layout_links=_bool(auto_opt_raw.get("rewrite_layout_links"), default=False),
            optimize_karyotype_labels=_bool(auto_opt_raw.get("optimize_karyotype_labels"), default=False),
        )
        plot = PlotProfileDefaults(
            glyphstyle=_str(plot_raw.get("glyphstyle")),
            glyphcolor=_str(plot_raw.get("glyphcolor")),
            shadestyle=_str(plot_raw.get("shadestyle")),
            figsize=_str(plot_raw.get("figsize")),
            dpi=_int(plot_raw.get("dpi"), default=300),
            auto_optimization=auto_optimization,
        )

        histogram_raw = _dict(data.get("histogram"))
        columns_raw = histogram_raw.get("columns")
        histogram = HistogramProfileDefaults(
            inputs=_str_list(histogram_raw.get("inputs")),
            columns=[_int(item, default=0) for item in columns_raw]
            if isinstance(columns_raw, list) and columns_raw
            else [0],
            skip=_int(histogram_raw.get("skip"), default=0),
            bins=_int(histogram_raw.get("bins"), default=20),
            vmin=_float(histogram_raw.get("vmin"), default=0.0) if histogram_raw.get("vmin") is not None else None,
            vmax=_float(histogram_raw.get("vmax"), default=0.0) if histogram_raw.get("vmax") is not None else None,
            xlabel=_str(histogram_raw.get("xlabel"), default="value"),
            title=_str(histogram_raw.get("title")),
            base=_int(histogram_raw.get("base"), default=0),
            facet=_bool(histogram_raw.get("facet"), default=False),
            fill=_str(histogram_raw.get("fill"), default="white"),
        )

        heatmap_raw = _dict(data.get("heatmap"))
        heatmap = HeatmapProfileDefaults(
            matrix=_str(heatmap_raw.get("matrix")),
            rowgroups=_str(heatmap_raw.get("rowgroups")),
            cmap=_str(heatmap_raw.get("cmap")),
            groups=_bool(heatmap_raw.get("groups"), default=False),
            horizontalbar=_bool(heatmap_raw.get("horizontalbar"), default=False),
        )

        return cls(
            schema_version=_int(data.get("schema_version"), default=3),
            synteny=synteny,
            local_synteny=local_synteny,
            plot=plot,
            histogram=histogram,
            heatmap=heatmap,
        )

    def as_nested_dict(self) -> dict[str, object]:
        """返回供内部调试使用的嵌套 dict(字典)"""

        return asdict(self)


__all__ = [
    "AutoOptimizationDefaults",
    "HeatmapProfileDefaults",
    "HistogramProfileDefaults",
    "JcviProfileModel",
    "LocalSyntenyProfileDefaults",
    "PlotProfileDefaults",
    "SyntenyProfileDefaults",
]
