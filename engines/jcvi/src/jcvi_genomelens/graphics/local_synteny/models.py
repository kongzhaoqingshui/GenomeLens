"""Data models for the chromosome-aware local synteny renderer."""

from __future__ import annotations

from dataclasses import dataclass, field

from jcvi_genomelens.graphics.local_synteny.style import MAX_TRACK_WIDTH


# region 数据模型
@dataclass(frozen=True)
class GeneRecord:
    """GeneRecord(基因记录)：从 BED 文件解析的单个基因"""

    accn: str
    chromosome: str
    start: int
    end: int
    strand: str

    @property
    def length_bp(self) -> int:
        """返回基因长度(bp)"""

        return max(1, self.end - self.start)


@dataclass
class MappedGene:
    """MappedGene(映射基因)：在染色体片段内已放置到视觉坐标的基因"""

    gene: GeneRecord
    x: float
    width: float
    row_index: int = -1
    visual_strand: str | None = None

    @property
    def display_strand(self) -> str:
        """返回经视觉片段反转后的链方向"""

        return self.visual_strand or self.gene.strand


@dataclass
class ChromosomeSegment:
    """ChromosomeSegment(染色体片段)：轨道内渲染的一个染色体区间"""

    chromosome: str
    genes: list[MappedGene]
    start_bp: float
    end_bp: float
    visual_start: float
    visual_end: float
    has_compressed_gaps: bool = False
    gap_markers: list[float] = field(default_factory=list)
    lane: int = 0
    left_truncated: bool = False
    right_truncated: bool = False
    reversed: bool = False

    @property
    def span_bp(self) -> float:
        """返回区间跨度(bp)"""

        return max(1.0, abs(self.end_bp - self.start_bp))


@dataclass
class TrackWindow:
    """TrackWindow(轨道窗口)：绘制一个物种/轨道所需的全部视觉信息"""

    name: str
    index: int
    color: str
    segments: list[ChromosomeSegment]
    all_genes: list[MappedGene]
    visual_width: float
    y: float = 0.0
    x_offset: float = 0.0
    range_label: str = ""
    lane_count: int = 1


@dataclass
class RenderBlock:
    """RenderBlock(渲染行)：规范化后的 blocks 文件单行"""

    query_gene: str
    subject_genes: list[str | None]
    highlighted: bool = False


@dataclass(frozen=True)
class AnchorLink:
    """AnchorLink(锚点连线)：相邻轨道间可绘制的连接"""

    row_index: int
    left_track: int
    right_track: int
    left_gene: str
    right_gene: str


@dataclass(frozen=True)
class TargetLegendEntry:
    """TargetLegendEntry(目标图例项)：底部图例中展示的高亮目标基因"""

    gene_id: str
    color: str
    hidden_count: int = 0


@dataclass(frozen=True)
class PositionedGene:
    """PositionedGene(定位基因)：MappedGene 加上渲染后的 y 坐标"""

    mapped: MappedGene
    y: float


@dataclass(frozen=True)
class TrackIntervalGenes:
    """TrackIntervalGenes(轨道区间基因)：为单个渲染染色体区间筛选的 BED 基因"""

    items: list[tuple[GeneRecord, int]]
    start_bp: float
    end_bp: float
    left_truncated: bool = False
    right_truncated: bool = False


@dataclass
class LocalSyntenyScene:
    """LocalSyntenyScene(局部共线性场景)：视觉放置前解析好的局部共线性数据"""

    genes: dict[str, GeneRecord]
    block_rows: list[RenderBlock]
    track_names: list[str]
    target_gene_ids: set[str]


@dataclass
class LocalSyntenyLayout:
    """LocalSyntenyLayout(局部共线性布局)：计算完成的染色体感知局部共线性场景"""

    tracks: list[TrackWindow]
    block_rows: list[RenderBlock]
    links: list[AnchorLink]
    target_gene_ids: set[str]
    target_legend_entries: list[TargetLegendEntry]
    figsize: tuple[float, float]
    max_track_width: float = MAX_TRACK_WIDTH


# endregion
