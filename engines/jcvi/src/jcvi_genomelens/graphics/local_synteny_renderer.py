"""Chromosome-aware renderer for local synteny figures.

The renderer consumes JCVI-style ``blocks`` plus a merged BED file, but does
not inherit the JCVI ``graphics.synteny`` assumption that every track is a
single continuous chromosome interval.  Each track is split into chromosome
segments, aligned to the reference row order, and long anchor-free gaps are
compressed so cross-chromosome local windows remain readable.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from statistics import median

import matplotlib

matplotlib.use("Agg")  # noqa: E402
matplotlib.rcParams["svg.fonttype"] = "none"
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.axes import Axes  # noqa: E402
from matplotlib.patches import FancyBboxPatch, PathPatch, Rectangle  # noqa: E402
from matplotlib.path import Path as MplPath  # noqa: E402

DEFAULT_TRACK_COLORS = ("#2f6f73", "#b85c38", "#5b8c5a", "#8c6bb1", "#c2914a", "#41699e")
_CHROMOSOME_COLOR_PALETTE = (
    "#c44e52",
    "#4c72b0",
    "#55a868",
    "#8172b3",
    "#ccb974",
    "#64b5cd",
    "#da8bc0",
    "#8c8c8c",
    "#bcbd22",
    "#17becf",
)

HIGHLIGHT_COLOR = "#000000"
BAR_COLOR = "#49a6b2"
TICK_COLOR = "#2f3a45"
GENE_FORWARD_COLOR = "#5f9f81"
GENE_REVERSE_COLOR = "#5f789e"
LABEL_BG_COLOR = "#fff8dc"
LABEL_TEXT_COLOR = "#30363d"
BACKGROUND_LINK_COLOR = "#b9b9b9"
LABEL_BOX_HEIGHT = 0.028

AXIS_LEFT = 0.08
AXIS_RIGHT = 0.88
MAX_TRACK_WIDTH = AXIS_RIGHT - AXIS_LEFT
MAX_SEGMENT_WIDTH = 0.58
MIN_SEGMENT_WIDTH = 0.045
MIN_GENE_WIDTH = 0.0015
MIN_VISIBLE_GENE_WIDTH = 0.0022
MAX_INTRA_GAP_WIDTH = 0.035
COMPRESS_GAP_BP = 500_000
INTER_SEGMENT_GAP = 0.018
SEGMENT_COLLISION_GAP = 0.012
LANE_GAP = 0.055
TRACK_GAP = 0.20
TRACK_BAR_HEIGHT = 0.010
BREAK_MARK_WIDTH = 0.006
BREAK_MARK_HEIGHT = 0.020
LINK_LW = 0.65
LINK_ALPHA = 0.68
LEGEND_Y = 0.045
LEGEND_SQUARE_SIZE = 0.016
LEGEND_FONT_SIZE = 6
DRAW_CHROMOSOME_LEGEND = False


@dataclass(frozen=True)
class GeneRecord:
    """A single gene parsed from a BED file."""

    accn: str
    chromosome: str
    start: int
    end: int
    strand: str

    @property
    def length_bp(self) -> int:
        return max(1, self.end - self.start)


@dataclass
class MappedGene:
    """A gene placed in visual coordinates inside a chromosome segment."""

    gene: GeneRecord
    x: float
    width: float
    row_index: int = -1


@dataclass
class ChromosomeSegment:
    """One chromosome interval rendered inside a track."""

    chromosome: str
    genes: list[MappedGene]
    start_bp: float
    end_bp: float
    visual_start: float
    visual_end: float
    has_compressed_gaps: bool = False
    gap_markers: list[float] = field(default_factory=list)
    lane: int = 0

    @property
    def span_bp(self) -> float:
        return max(1.0, self.end_bp - self.start_bp)


@dataclass
class TrackWindow:
    """All visual information needed to draw one species/track."""

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
    """One row of the blocks file, normalised for rendering."""

    query_gene: str
    subject_genes: list[str | None]
    highlighted: bool = False


@dataclass(frozen=True)
class AnchorLink:
    """A drawable connection between adjacent tracks."""

    row_index: int
    left_track: int
    right_track: int
    left_gene: str
    right_gene: str


@dataclass
class LocalSyntenyScene:
    """Parsed local synteny data before visual placement."""

    genes: dict[str, GeneRecord]
    block_rows: list[RenderBlock]
    track_names: list[str]
    target_gene_ids: set[str]


@dataclass
class LocalSyntenyLayout:
    """Computed chromosome-aware local synteny scene."""

    tracks: list[TrackWindow]
    block_rows: list[RenderBlock]
    links: list[AnchorLink]
    target_gene_ids: set[str]
    figsize: tuple[float, float]
    max_track_width: float = MAX_TRACK_WIDTH


class LocalSyntenySceneBuilder:
    """Build a chromosome-aware scene from JCVI-style input files."""

    def build(
        self,
        blocks_path: Path,
        bed_path: Path,
        track_names: list[str],
        target_gene_ids: list[str],
    ) -> LocalSyntenyScene:
        genes = _read_bed(bed_path)
        block_rows = _read_blocks(blocks_path, len(track_names))
        highlighted = {row.query_gene for row in block_rows if row.highlighted}
        return LocalSyntenyScene(
            genes=genes,
            block_rows=block_rows,
            track_names=track_names,
            target_gene_ids=set(target_gene_ids) | highlighted,
        )


class LocalSyntenyLayoutSolver:
    """Place chromosome segments, compressed gaps, lanes, and adjacent links."""

    def solve(self, scene: LocalSyntenyScene, *, figsize: str = "", dpi: int = 300) -> LocalSyntenyLayout:
        del dpi
        track_items = _collect_track_gene_rows(scene.genes, scene.block_rows, len(scene.track_names))

        tracks: list[TrackWindow] = []
        if scene.track_names:
            reference_color = DEFAULT_TRACK_COLORS[0]
            reference_track, row_x = _build_reference_track(
                scene.track_names[0],
                0,
                reference_color,
                track_items[0],
            )
            tracks.append(reference_track)
        else:
            row_x = {}

        for index, name in enumerate(scene.track_names[1:], start=1):
            color = DEFAULT_TRACK_COLORS[index % len(DEFAULT_TRACK_COLORS)]
            track = _build_target_track(name, index, color, track_items[index], row_x)
            tracks.append(track)

        width, height = _derive_figsize(len(tracks), len(scene.block_rows), figsize, tracks)
        return LocalSyntenyLayout(
            tracks=tracks,
            block_rows=scene.block_rows,
            links=_build_links(scene.block_rows, len(scene.track_names)),
            target_gene_ids=scene.target_gene_ids,
            figsize=(width, height),
        )


class MatplotlibLocalSyntenyRenderer:
    """Render a solved local synteny layout as a compact publication-style figure."""

    def render(
        self,
        layout: LocalSyntenyLayout,
        output_path: Path,
        *,
        label_targets: bool = False,
        dpi: int = 300,
        fmt: str = "svg",
    ) -> Path:
        fig, ax = plt.subplots(figsize=layout.figsize)
        ax.axis("off")

        self._assign_track_y(layout)
        track_positions = [_draw_track(ax, track, layout.target_gene_ids, label_targets) for track in layout.tracks]
        self._draw_links(ax, layout, track_positions)

        if DRAW_CHROMOSOME_LEGEND:
            chromosomes = sorted({segment.chromosome for track in layout.tracks for segment in track.segments})
            color_map = _build_chromosome_color_map(chromosomes)
            _draw_chromosome_legend(ax, chromosomes, color_map)
        ax.set_xlim(-0.25, 1.02)
        ys = [_segment_y(track, segment) for track in layout.tracks for segment in track.segments]
        if ys:
            ax.set_ylim(max(0.0, min(ys) - 0.14), min(1.0, max(ys) + 0.10))
        else:
            ax.set_ylim(0.0, 1.0)
        fig.subplots_adjust(left=0.10, right=0.98, top=0.96, bottom=0.08)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output_path, format=fmt, dpi=dpi, bbox_inches="tight", pad_inches=0.08)
        plt.close(fig)
        return output_path

    def _assign_track_y(self, layout: LocalSyntenyLayout) -> None:
        usable_height = 0.78
        lane_units = sum(max(1, track.lane_count) for track in layout.tracks)
        unit_gap = usable_height / max(1, lane_units + len(layout.tracks) - 1)
        y = 0.90
        for track in layout.tracks:
            track.y = y - (track.lane_count - 1) * LANE_GAP / 2.0
            y -= unit_gap * max(1, track.lane_count) + TRACK_GAP * 0.32

    def _draw_links(
        self,
        ax: Axes,
        layout: LocalSyntenyLayout,
        track_positions: list[dict[str, tuple[float, float]]],
    ) -> None:
        drawable_links: list[tuple[AnchorLink, tuple[float, float], tuple[float, float]]] = []
        for link in layout.links:
            if link.left_track >= len(track_positions) or link.right_track >= len(track_positions):
                continue
            left = track_positions[link.left_track].get(link.left_gene)
            right = track_positions[link.right_track].get(link.right_gene)
            if left is None or right is None:
                continue
            drawable_links.append((link, left, right))

        links_by_pair: dict[tuple[int, int], list[tuple[tuple[float, float], tuple[float, float]]]] = defaultdict(list)
        for link, left, right in drawable_links:
            links_by_pair[(link.left_track, link.right_track)].append((left, right))
        for pair_links in links_by_pair.values():
            _draw_pair_cloud(ax, pair_links)

        for _link, left, right in drawable_links:
            _draw_curve_link(ax, left, right, color="#9ca3af", lw=3.8, alpha=0.045, zorder=0)
        for link, left, right in drawable_links:
            color = BACKGROUND_LINK_COLOR
            alpha = LINK_ALPHA
            lw = LINK_LW
            if link.left_gene in layout.target_gene_ids or link.right_gene in layout.target_gene_ids:
                color = "#6b7280"
                alpha = 0.72
                lw = 0.85
            _draw_curve_link(ax, left, right, color=color, lw=lw, alpha=alpha, zorder=1)


def _strip_highlight_prefix(value: str) -> tuple[bool, str]:
    """Return ``(is_highlighted, accn)`` after stripping a JCVI ``r*`` prefix."""

    if "*" in value:
        prefix, body = value.split("*", 1)
        return prefix == "r", body.strip()
    return False, value.strip()


def _read_bed(path: Path) -> dict[str, GeneRecord]:
    """Read a BED file and map ``accn -> GeneRecord``."""

    genes: dict[str, GeneRecord] = {}
    with path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) < 4:
                continue
            accn = parts[3].strip()
            genes[accn] = GeneRecord(
                accn=accn,
                chromosome=parts[0].strip(),
                start=int(parts[1]),
                end=int(parts[2]),
                strand=parts[5].strip() if len(parts) > 5 else "+",
            )
    return genes


def _read_blocks(path: Path, track_count: int) -> list[RenderBlock]:
    """Parse a JCVI-style blocks file."""

    rows: list[RenderBlock] = []
    with path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            parts = [p.strip() for p in line.split("\t")]
            if len(parts) < 2:
                continue
            highlighted, query = _strip_highlight_prefix(parts[0])
            subjects: list[str | None] = []
            for index in range(1, track_count):
                value = parts[index] if index < len(parts) else "."
                if value in {"", "."}:
                    subjects.append(None)
                else:
                    _, accn = _strip_highlight_prefix(value)
                    subjects.append(accn)
            rows.append(RenderBlock(query_gene=query, subject_genes=subjects, highlighted=highlighted))
    return rows


def _scope_of(accn: str) -> tuple[str, str]:
    """Split ``species__gene`` into ``(species, gene)``."""

    if "__" in accn:
        species, _, gene = accn.partition("__")
        return species, gene
    return "", accn


def _display_accn(accn: str) -> str:
    """Return the human-readable part of an accn."""

    return _scope_of(accn)[1]


def _format_bp_range(start_bp: float, end_bp: float) -> str:
    """Format a base-pair range like JCVI does."""

    span = end_bp - start_bp
    if span >= 1_000_000:
        return f"{start_bp / 1_000_000:.2f}-{end_bp / 1_000_000:.2f}Mb"
    if span >= 1_000:
        return f"{start_bp / 1_000:.2f}-{end_bp / 1_000:.2f}kb"
    return f"{start_bp:.0f}-{end_bp:.0f}bp"


def _chromosome_ordered_groups(items: list[tuple[GeneRecord, int]]) -> list[tuple[str, list[tuple[GeneRecord, int]]]]:
    """Group genes by chromosome while preserving first block-row appearance."""

    order: list[str] = []
    grouped: dict[str, list[tuple[GeneRecord, int]]] = {}
    for gene, row_index in items:
        if gene.chromosome not in grouped:
            grouped[gene.chromosome] = []
            order.append(gene.chromosome)
        grouped[gene.chromosome].append((gene, row_index))
    return [(chromosome, grouped[chromosome]) for chromosome in order]


def _dedupe_gene_rows(items: list[tuple[GeneRecord, int]]) -> list[tuple[GeneRecord, int]]:
    """Keep the first visual occurrence of each gene for segment placement."""

    seen: set[str] = set()
    unique: list[tuple[GeneRecord, int]] = []
    for gene, row_index in items:
        if gene.accn in seen:
            continue
        seen.add(gene.accn)
        unique.append((gene, row_index))
    return unique


def _estimate_segment_width(genes: list[GeneRecord]) -> float:
    """Estimate a compact segment width before gap-compressed mapping."""

    if not genes:
        return MIN_SEGMENT_WIDTH
    raw_span = max(g.end for g in genes) - min(g.start for g in genes)
    gene_component = max(MIN_SEGMENT_WIDTH, min(0.24, len(genes) * 0.022))
    span_component = min(MAX_SEGMENT_WIDTH, max(MIN_SEGMENT_WIDTH, raw_span / 5_000_000 * 0.18))
    return min(MAX_SEGMENT_WIDTH, max(gene_component, span_component))


def _map_segment_genes(
    items: list[tuple[GeneRecord, int]],
    *,
    start_x: float,
    target_width: float,
) -> tuple[list[MappedGene], list[float], bool]:
    """Map one chromosome segment with compressed intra-chromosomal gaps."""

    ordered = sorted(items, key=lambda item: (item[0].start, item[0].end, item[0].accn))
    genes = [gene for gene, _ in ordered]
    if not genes:
        return [], [], False

    raw_span = max(1, max(g.end for g in genes) - min(g.start for g in genes))
    scale = target_width / raw_span
    x = start_x
    mapped: list[MappedGene] = []
    gap_markers: list[float] = []
    compressed = False

    for index, (gene, row_index) in enumerate(ordered):
        if index > 0:
            prev = ordered[index - 1][0]
            gap_bp = max(0, gene.start - prev.end)
            raw_gap = gap_bp * scale
            if raw_gap > MAX_INTRA_GAP_WIDTH or gap_bp > COMPRESS_GAP_BP:
                marker_x = x + MAX_INTRA_GAP_WIDTH / 2.0
                x += MAX_INTRA_GAP_WIDTH
                gap_markers.append(marker_x)
                compressed = True
            else:
                x += raw_gap
        width = max(MIN_GENE_WIDTH, gene.length_bp * scale)
        mapped.append(MappedGene(gene=gene, x=x + width / 2.0, width=width, row_index=row_index))
        x += width

    return mapped, gap_markers, compressed


def _map_reference_segment_genes(
    items: list[tuple[GeneRecord, int]],
    *,
    visual_start: float,
    visual_width: float,
) -> tuple[list[MappedGene], float, float]:
    """Map reference genes by true BED coordinates without row-order spacing."""

    ordered = sorted(items, key=lambda item: (item[0].start, item[0].end, item[0].accn))
    start_bp = min(gene.start for gene, _ in ordered)
    end_bp = max(gene.end for gene, _ in ordered)
    scale = visual_width / max(1.0, end_bp - start_bp)
    mapped = [
        MappedGene(
            gene=gene,
            x=visual_start + ((gene.start + gene.end) / 2.0 - start_bp) * scale,
            width=max(MIN_GENE_WIDTH, gene.length_bp * scale),
            row_index=row_index,
        )
        for gene, row_index in ordered
    ]
    return mapped, float(start_bp), float(end_bp)


def _build_track_window(
    name: str,
    index: int,
    color: str,
    genes: list[GeneRecord],
    scale: float,
) -> TrackWindow:
    """Build a standalone gap-compressed track window.

    This helper is retained for existing tests and for simple proportional
    mapping.  The production renderer uses the reference-aware builder below.
    """

    items = [(gene, row_index) for row_index, gene in enumerate(genes)]
    segments: list[ChromosomeSegment] = []
    all_mapped: list[MappedGene] = []
    x = 0.0
    for chromosome, group in _chromosome_ordered_groups(items):
        ordered = sorted(group, key=lambda item: item[0].start)
        mapped: list[MappedGene] = []
        gap_markers: list[float] = []
        compressed = False
        seg_start = x
        for item_index, (gene, row_index) in enumerate(ordered):
            if item_index > 0:
                prev = ordered[item_index - 1][0]
                gap_bp = max(0, gene.start - prev.end)
                raw_gap = gap_bp * scale
                if raw_gap > MAX_INTRA_GAP_WIDTH or gap_bp > COMPRESS_GAP_BP:
                    marker_x = x + MAX_INTRA_GAP_WIDTH / 2.0
                    x += MAX_INTRA_GAP_WIDTH
                    gap_markers.append(marker_x)
                    compressed = True
                else:
                    x += raw_gap
            width = max(MIN_GENE_WIDTH, gene.length_bp * scale)
            mapped_gene = MappedGene(gene=gene, x=x + width / 2.0, width=width, row_index=row_index)
            mapped.append(mapped_gene)
            all_mapped.append(mapped_gene)
            x += width
        segments.append(
            ChromosomeSegment(
                chromosome=chromosome,
                genes=mapped,
                start_bp=min(gene.start for gene, _ in ordered),
                end_bp=max(gene.end for gene, _ in ordered),
                visual_start=seg_start,
                visual_end=x,
                has_compressed_gaps=compressed,
                gap_markers=gap_markers,
            )
        )
        x += INTER_SEGMENT_GAP

    visual_width = max(0.0, x - INTER_SEGMENT_GAP)
    range_label = " | ".join(
        f"{segment.chromosome} {_format_bp_range(segment.start_bp, segment.end_bp)}" for segment in segments
    )
    return TrackWindow(name, index, color, segments, all_mapped, visual_width, range_label=range_label)


def _build_reference_track(
    name: str,
    index: int,
    color: str,
    items: list[tuple[GeneRecord, int]],
) -> tuple[TrackWindow, dict[int, float]]:
    """Build the reference track on true BED coordinates."""

    segments: list[ChromosomeSegment] = []
    all_mapped: list[MappedGene] = []
    row_x: dict[int, float] = {}
    groups = _chromosome_ordered_groups(_dedupe_gene_rows(items))
    spans = [max(1, max(gene.end for gene, _ in group) - min(gene.start for gene, _ in group)) for _, group in groups]
    available_width = MAX_TRACK_WIDTH - INTER_SEGMENT_GAP * max(0, len(groups) - 1)
    total_span = max(1, sum(spans))
    x = AXIS_LEFT

    for (chromosome, group), span in zip(groups, spans, strict=False):
        visual_width = max(MIN_SEGMENT_WIDTH, available_width * span / total_span)
        if x + visual_width > AXIS_RIGHT:
            visual_width = max(MIN_SEGMENT_WIDTH, AXIS_RIGHT - x)
        mapped, start_bp, end_bp = _map_reference_segment_genes(
            group,
            visual_start=x,
            visual_width=visual_width,
        )
        all_mapped.extend(mapped)
        for mapped_gene in mapped:
            row_x[mapped_gene.row_index] = mapped_gene.x
        segments.append(
            ChromosomeSegment(
                chromosome=chromosome,
                genes=mapped,
                start_bp=start_bp,
                end_bp=end_bp,
                visual_start=x,
                visual_end=x + visual_width,
            )
        )
        x += visual_width + INTER_SEGMENT_GAP

    range_label = " | ".join(
        f"{segment.chromosome} {_format_bp_range(segment.start_bp, segment.end_bp)}" for segment in segments
    )
    return (
        TrackWindow(
            name=name,
            index=index,
            color=color,
            segments=segments,
            all_genes=all_mapped,
            visual_width=MAX_TRACK_WIDTH,
            range_label=range_label,
        ),
        row_x,
    )


def _build_target_track(
    name: str,
    index: int,
    color: str,
    items: list[tuple[GeneRecord, int]],
    row_x: dict[int, float],
) -> TrackWindow:
    """Build a non-reference track and align segments to reference anchors."""

    segments: list[ChromosomeSegment] = []
    all_mapped: list[MappedGene] = []
    for chromosome, group in _chromosome_ordered_groups(_dedupe_gene_rows(items)):
        genes = [gene for gene, _ in group]
        target_width = _estimate_segment_width(genes)
        mapped, gap_markers, compressed = _map_segment_genes(group, start_x=0.0, target_width=target_width)
        if not mapped:
            continue
        desired = median(row_x[item.row_index] for item in mapped if item.row_index in row_x)
        current = median(item.x for item in mapped)
        shift = desired - current
        left = min(item.x - item.width / 2.0 for item in mapped)
        right = max(item.x + item.width / 2.0 for item in mapped)
        shifted_left = left + shift
        shifted_right = right + shift
        if shifted_left < AXIS_LEFT:
            shift += AXIS_LEFT - shifted_left
            shifted_right = right + shift
        if shifted_right > AXIS_RIGHT:
            shift -= shifted_right - AXIS_RIGHT
        for mapped_gene in mapped:
            mapped_gene.x += shift
            all_mapped.append(mapped_gene)
        shifted_markers = [marker + shift for marker in gap_markers]
        segments.append(
            ChromosomeSegment(
                chromosome=chromosome,
                genes=mapped,
                start_bp=min(gene.start for gene, _ in group),
                end_bp=max(gene.end for gene, _ in group),
                visual_start=min(item.x - item.width / 2.0 for item in mapped),
                visual_end=max(item.x + item.width / 2.0 for item in mapped),
                has_compressed_gaps=compressed,
                gap_markers=shifted_markers,
            )
        )

    _assign_segment_lanes(segments)
    _pack_segments_same_row(segments)
    range_label = " | ".join(
        f"{segment.chromosome} {_format_bp_range(segment.start_bp, segment.end_bp)}" for segment in segments
    )
    lane_count = max((segment.lane for segment in segments), default=0) + 1
    return TrackWindow(
        name=name,
        index=index,
        color=color,
        segments=segments,
        all_genes=all_mapped,
        visual_width=MAX_TRACK_WIDTH,
        range_label=range_label,
        lane_count=max(1, lane_count),
    )


def _assign_segment_lanes(segments: list[ChromosomeSegment]) -> None:
    """Keep chromosome segments on the same species row."""

    for segment in segments:
        segment.lane = 0


def _shift_segment(segment: ChromosomeSegment, delta: float) -> None:
    """Shift a solved chromosome segment horizontally."""

    if delta == 0:
        return
    for mapped in segment.genes:
        mapped.x += delta
    segment.gap_markers = [marker + delta for marker in segment.gap_markers]
    segment.visual_start += delta
    segment.visual_end += delta


def _rescale_segment(segment: ChromosomeSegment, *, new_start: float, new_width: float) -> None:
    """Rescale a segment into a new horizontal span."""

    old_start = segment.visual_start
    old_width = max(1e-9, segment.visual_end - segment.visual_start)
    factor = new_width / old_width
    for mapped in segment.genes:
        mapped.x = new_start + (mapped.x - old_start) * factor
        mapped.width = max(MIN_GENE_WIDTH, mapped.width * factor)
    segment.gap_markers = [new_start + (marker - old_start) * factor for marker in segment.gap_markers]
    segment.visual_start = new_start
    segment.visual_end = new_start + new_width


def _pack_segments_same_row(segments: list[ChromosomeSegment]) -> None:
    """Pack same-track chromosome segments on one row without overlaps."""

    if not segments:
        return

    widths = [segment.visual_end - segment.visual_start for segment in segments]
    gap = INTER_SEGMENT_GAP
    total_width = sum(widths) + gap * max(0, len(segments) - 1)
    if total_width > MAX_TRACK_WIDTH:
        available_for_segments = max(MIN_SEGMENT_WIDTH, MAX_TRACK_WIDTH - gap * max(0, len(segments) - 1))
        scale = available_for_segments / max(1e-9, sum(widths))
        x = AXIS_LEFT
        for segment, width in zip(segments, widths, strict=False):
            new_width = max(MIN_SEGMENT_WIDTH * 0.35, width * scale)
            _rescale_segment(segment, new_start=x, new_width=new_width)
            x = segment.visual_end + gap
        return

    previous_end: float | None = None
    for segment in segments:
        if previous_end is None:
            if segment.visual_start < AXIS_LEFT:
                _shift_segment(segment, AXIS_LEFT - segment.visual_start)
        else:
            minimum_start = previous_end + INTER_SEGMENT_GAP
            if segment.visual_start < minimum_start:
                _shift_segment(segment, minimum_start - segment.visual_start)
        previous_end = segment.visual_end

    if segments and segments[-1].visual_end > AXIS_RIGHT:
        overflow = segments[-1].visual_end - AXIS_RIGHT
        movable_left = min(segment.visual_start for segment in segments) - AXIS_LEFT
        _shift = -min(overflow, max(0.0, movable_left))
        for segment in segments:
            _shift_segment(segment, _shift)


def _collect_track_gene_rows(
    genes: dict[str, GeneRecord],
    block_rows: list[RenderBlock],
    track_count: int,
) -> list[list[tuple[GeneRecord, int]]]:
    """Collect genes per track from parsed blocks."""

    track_items: list[list[tuple[GeneRecord, int]]] = [[] for _ in range(track_count)]
    for row_index, row in enumerate(block_rows):
        query = genes.get(row.query_gene)
        if query is not None:
            track_items[0].append((query, row_index))
        for subject_index, accn in enumerate(row.subject_genes):
            if accn is None:
                continue
            gene = genes.get(accn)
            if gene is not None and subject_index + 1 < track_count:
                track_items[subject_index + 1].append((gene, row_index))
    return track_items


def _build_links(block_rows: list[RenderBlock], track_count: int) -> list[AnchorLink]:
    """Build adjacent-track links from block rows."""

    links: list[AnchorLink] = []
    for row_index, row in enumerate(block_rows):
        genes_by_track: list[str | None] = [row.query_gene, *row.subject_genes]
        if len(genes_by_track) < track_count:
            genes_by_track.extend([None] * (track_count - len(genes_by_track)))
        for left_track in range(track_count - 1):
            left = genes_by_track[left_track]
            right = genes_by_track[left_track + 1]
            if left and right:
                links.append(AnchorLink(row_index, left_track, left_track + 1, left, right))
    return links


def _compute_layout(
    blocks_path: Path,
    bed_path: Path,
    track_names: list[str],
    target_gene_ids: list[str],
    figsize: str = "",
    dpi: int = 300,
) -> LocalSyntenyLayout:
    """Build the chromosome-aware scene from blocks + BED."""

    scene = LocalSyntenySceneBuilder().build(blocks_path, bed_path, track_names, target_gene_ids)
    return LocalSyntenyLayoutSolver().solve(scene, figsize=figsize, dpi=dpi)


def _derive_figsize(
    track_count: int,
    block_rows: int,
    figsize: str,
    tracks: list[TrackWindow] | None = None,
) -> tuple[float, float]:
    """Return a sensible figure size in inches."""

    if figsize:
        parts = figsize.lower().split("x")
        if len(parts) == 2:
            try:
                return float(parts[0]), float(parts[1])
            except ValueError:
                pass
    lane_total = sum(track.lane_count for track in tracks or [])
    height = max(4.2, 1.35 + track_count * 0.78 + lane_total * 0.24)
    width = max(10.0, min(18.0, 8.0 + block_rows * 0.045))
    return width, height


def _draw_break_marker(ax: Axes, x: float, y: float, color: str = "#777777") -> None:
    """Draw a small double-slash break marker on a compressed chromosome bar."""

    dx = BREAK_MARK_WIDTH / 2.0
    dy = BREAK_MARK_HEIGHT / 2.0
    for offset in (-dx * 0.65, dx * 0.65):
        ax.plot(
            [x - dx + offset, x + dx + offset],
            [y - dy, y + dy],
            color=color,
            lw=0.9,
            zorder=7,
            solid_capstyle="round",
        )


def _abbreviate_track_name(name: str) -> str:
    """Produce a compact species label."""

    raw = name.strip()
    species_part = raw.split("-", 1)[0]
    species_tokens = [token for token in species_part.replace("_", " ").split() if token]
    if len(species_tokens) >= 2 and species_tokens[0][0].isalpha():
        label = f"{species_tokens[0][0]}. {species_tokens[1]}"
        if len(label) <= 16:
            return label
    cleaned = raw.replace("_", " ").replace("-", " ").replace(".", " ")
    tokens = [token for token in cleaned.split() if token]
    if len(name) <= 14 or len(tokens) <= 1:
        return name
    abbr = tokens[0]
    for token in tokens[1:]:
        if token[0].isalpha():
            abbr += token[0]
    return abbr[:14]


def _estimate_label_box_width(text: str) -> float:
    """Estimate axes-width of a chromosome label box."""

    return max(0.038, len(text) * 0.0078 + 0.012)


def _draw_label_box(ax: Axes, text: str, x: float, y: float, fontsize: int = 7) -> None:
    """Draw a rounded label box."""

    box_width = _estimate_label_box_width(text)
    box = FancyBboxPatch(
        (x, y - LABEL_BOX_HEIGHT / 2.0),
        box_width,
        LABEL_BOX_HEIGHT,
        boxstyle="round,pad=0,rounding_size=0.004",
        facecolor=LABEL_BG_COLOR,
        edgecolor="#d0d0d0",
        lw=0.5,
        zorder=8,
        clip_on=False,
    )
    ax.add_patch(box)
    ax.text(
        x + box_width / 2.0,
        y,
        text,
        fontsize=fontsize,
        ha="center",
        va="center",
        color=LABEL_TEXT_COLOR,
        zorder=9,
        clip_on=False,
    )


def _label_rect(x: float, y: float, width: float) -> tuple[float, float, float, float]:
    """Return a label rectangle as ``(left, right, bottom, top)``."""

    return (x, x + width, y - LABEL_BOX_HEIGHT / 2.0, y + LABEL_BOX_HEIGHT / 2.0)


def _rects_overlap(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> bool:
    """Return True when two axes-coordinate rectangles overlap."""

    return not (a[1] <= b[0] or b[1] <= a[0] or a[3] <= b[2] or b[3] <= a[2])


def _clamp(value: float, lower: float, upper: float) -> float:
    """Clamp a float into a closed interval."""

    return min(max(value, lower), upper)


def _label_overlaps_segment_bar(
    rect: tuple[float, float, float, float],
    segment: ChromosomeSegment,
    y: float,
) -> bool:
    """Detect whether a label box covers the chromosome bar."""

    bar_rect = (
        segment.visual_start - 0.004,
        segment.visual_end + 0.004,
        y - TRACK_BAR_HEIGHT * 0.9,
        y + TRACK_BAR_HEIGHT * 0.9,
    )
    return _rects_overlap(rect, bar_rect)


def _target_star_rects(track: TrackWindow, target_gene_ids: set[str]) -> list[tuple[float, float, float, float]]:
    """Return rough occupied rectangles for target-star markers."""

    rects: list[tuple[float, float, float, float]] = []
    for segment in track.segments:
        y = _segment_y(track, segment)
        for mapped in segment.genes:
            if mapped.gene.accn in target_gene_ids:
                rects.append((mapped.x - 0.018, mapped.x + 0.018, y - 0.030, y + 0.030))
    return rects


def _label_positions_for_segments(
    track: TrackWindow,
    target_gene_ids: set[str],
) -> dict[int, tuple[float, float]]:
    """Compute non-overlapping label positions that do not cover bars."""

    occupied: list[tuple[float, float, float, float]] = _target_star_rects(track, target_gene_ids)
    positions: dict[int, tuple[float, float]] = {}
    for original_index, segment in sorted(enumerate(track.segments), key=lambda item: item[1].visual_start):
        y = _segment_y(track, segment)
        width = _estimate_label_box_width(segment.chromosome)
        center = (segment.visual_start + segment.visual_end) / 2.0
        candidates = [
            (segment.visual_start - width - 0.008, y),
            (segment.visual_start - width - 0.008, y + 0.052),
            (segment.visual_start - width - 0.008, y - 0.052),
            (segment.visual_start - width * 0.45, y + 0.043),
            (segment.visual_start - width * 0.45, y - 0.043),
            (center - width / 2.0, y + 0.043),
            (center - width / 2.0, y - 0.043),
        ]
        fallback = candidates[-1]
        for raw_x, raw_y in candidates:
            x = _clamp(raw_x, -0.22, AXIS_RIGHT - width)
            rect = _label_rect(x, raw_y, width)
            if _label_overlaps_segment_bar(rect, segment, y):
                continue
            if any(_rects_overlap(rect, other) for other in occupied):
                continue
            positions[original_index] = (x, raw_y)
            occupied.append(rect)
            break
        else:
            x = _clamp(fallback[0], -0.22, AXIS_RIGHT - width)
            positions[original_index] = (x, fallback[1])
            occupied.append(_label_rect(x, fallback[1], width))
    return positions


def _draw_star(ax: Axes, x: float, y: float, color: str = HIGHLIGHT_COLOR) -> None:
    """Draw a target gene marker."""

    ax.plot(
        x,
        y,
        marker="*",
        markersize=13,
        markeredgecolor=color,
        markerfacecolor=color,
        zorder=11,
        clip_on=False,
    )


def _draw_target_gene_label(ax: Axes, text: str, x: float, y: float, segment: ChromosomeSegment) -> None:
    """Draw a target gene label near a star without covering the bar."""

    width = max(0.075, min(0.30, len(text) * 0.0080 + 0.024))
    candidates = [
        (x + 0.012, y + 0.055),
        (x + 0.012, y - 0.055),
        (x - width - 0.012, y + 0.055),
        (x - width - 0.012, y - 0.055),
    ]
    label_x, label_y = candidates[0]
    for raw_x, raw_y in candidates:
        candidate_x = _clamp(raw_x, -0.22, AXIS_RIGHT - width)
        rect = _label_rect(candidate_x, raw_y, width)
        if not _label_overlaps_segment_bar(rect, segment, y):
            label_x, label_y = candidate_x, raw_y
            break

    box = FancyBboxPatch(
        (label_x, label_y - LABEL_BOX_HEIGHT / 2.0),
        width,
        LABEL_BOX_HEIGHT,
        boxstyle="round,pad=0,rounding_size=0.004",
        facecolor="#ffffff",
        edgecolor="#c8c8c8",
        lw=0.45,
        alpha=0.92,
        zorder=12,
        clip_on=False,
    )
    ax.add_patch(box)
    ax.text(
        label_x + width / 2.0,
        label_y,
        text,
        fontsize=5.8,
        ha="center",
        va="center",
        color=HIGHLIGHT_COLOR,
        zorder=13,
        clip_on=False,
    )


def _segment_y(track: TrackWindow, segment: ChromosomeSegment) -> float:
    """Return y coordinate for a segment lane."""

    if track.lane_count <= 1:
        return track.y
    center_offset = (track.lane_count - 1) * LANE_GAP / 2.0
    return track.y + center_offset - segment.lane * LANE_GAP


def _draw_track(
    ax: Axes,
    track: TrackWindow,
    target_gene_ids: set[str],
    label_targets: bool,
) -> dict[str, tuple[float, float]]:
    """Draw one track and return gene centre positions."""

    gene_positions: dict[str, tuple[float, float]] = {}
    label_positions = _label_positions_for_segments(track, target_gene_ids)

    ax.text(
        -0.235,
        track.y,
        _abbreviate_track_name(track.name),
        fontsize=8,
        ha="left",
        va="center",
        color=track.color,
        zorder=9,
        clip_on=False,
    )

    for segment_index, segment in enumerate(track.segments):
        y = _segment_y(track, segment)
        bar = FancyBboxPatch(
            (segment.visual_start, y - TRACK_BAR_HEIGHT / 2.0),
            max(MIN_SEGMENT_WIDTH / 2.0, segment.visual_end - segment.visual_start),
            TRACK_BAR_HEIGHT,
            boxstyle=f"round,pad=0,rounding_size={TRACK_BAR_HEIGHT / 2.0}",
            facecolor=BAR_COLOR,
            edgecolor="#2d6970",
            lw=0.4,
            zorder=3,
            clip_on=False,
        )
        ax.add_patch(bar)

        for marker in segment.gap_markers:
            _draw_break_marker(ax, marker, y)
            ax.text(marker, y + 0.026, "...", fontsize=6, ha="center", va="bottom", color="#777777", zorder=8)

        tick_top = y + 0.021
        tick_bottom = y - 0.021
        for mapped in segment.genes:
            gene_width = max(MIN_VISIBLE_GENE_WIDTH, mapped.width)
            gene_left = mapped.x - gene_width / 2.0
            gene_color = GENE_REVERSE_COLOR if mapped.gene.strand == "-" else GENE_FORWARD_COLOR
            ax.add_patch(
                Rectangle(
                    (gene_left, y - TRACK_BAR_HEIGHT * 0.48),
                    gene_width,
                    TRACK_BAR_HEIGHT * 0.96,
                    facecolor=gene_color,
                    edgecolor="none",
                    alpha=0.78,
                    zorder=5,
                    clip_on=False,
                )
            )
            ax.plot(
                [mapped.x, mapped.x],
                [tick_bottom, tick_top],
                color=TICK_COLOR,
                lw=0.42,
                alpha=0.58,
                zorder=6,
            )
            gene_positions[mapped.gene.accn] = (mapped.x, y)
            if mapped.gene.accn in target_gene_ids:
                _draw_star(ax, mapped.x, y)
                if label_targets:
                    _draw_target_gene_label(ax, _display_accn(mapped.gene.accn), mapped.x, y, segment)

        label_x, label_y = label_positions.get(segment_index, (-0.18, y))
        _draw_label_box(ax, segment.chromosome, label_x, label_y)
        ax.text(
            (segment.visual_start + segment.visual_end) / 2.0,
            y + 0.030,
            _format_bp_range(segment.start_bp, segment.end_bp),
            fontsize=6,
            ha="center",
            va="bottom",
            color="#64748b",
            zorder=6,
            clip_on=False,
        )

    return gene_positions


def _draw_curve_link(
    ax: Axes,
    p1: tuple[float, float],
    p2: tuple[float, float],
    color: str = BACKGROUND_LINK_COLOR,
    lw: float = LINK_LW,
    alpha: float = LINK_ALPHA,
    zorder: int = 1,
) -> None:
    """Draw a thin curved synteny link."""

    x1, y1 = p1
    x2, y2 = p2
    mid_y = (y1 + y2) / 2.0
    verts = [(x1, y1), (x1, mid_y), (x2, mid_y), (x2, y2)]
    codes = [MplPath.MOVETO, MplPath.CURVE4, MplPath.CURVE4, MplPath.CURVE4]
    ax.add_patch(PathPatch(MplPath(verts, codes), fill=False, edgecolor=color, lw=lw, alpha=alpha, zorder=zorder))


def _draw_pair_cloud(
    ax: Axes,
    links: list[tuple[tuple[float, float], tuple[float, float]]],
) -> None:
    """Draw a soft filled synteny cloud between one adjacent track pair."""

    if len(links) < 3:
        return
    left_points = [left for left, _right in links]
    right_points = [right for _left, right in links]
    top_y = median(point[1] for point in left_points)
    bottom_y = median(point[1] for point in right_points)
    top_left, top_right = (
        _percentile([point[0] for point in left_points], 0.10),
        _percentile([point[0] for point in left_points], 0.90),
    )
    bottom_left, bottom_right = (
        _percentile([point[0] for point in right_points], 0.10),
        _percentile([point[0] for point in right_points], 0.90),
    )
    mid_y = (top_y + bottom_y) / 2.0
    verts = [
        (top_left, top_y),
        (top_left, mid_y),
        (bottom_left, mid_y),
        (bottom_left, bottom_y),
        (bottom_right, bottom_y),
        (bottom_right, mid_y),
        (top_right, mid_y),
        (top_right, top_y),
        (top_left, top_y),
    ]
    codes = [
        MplPath.MOVETO,
        MplPath.CURVE4,
        MplPath.CURVE4,
        MplPath.CURVE4,
        MplPath.LINETO,
        MplPath.CURVE4,
        MplPath.CURVE4,
        MplPath.CURVE4,
        MplPath.CLOSEPOLY,
    ]
    ax.add_patch(
        PathPatch(
            MplPath(verts, codes),
            facecolor="#b8b8b8",
            edgecolor="none",
            alpha=0.085,
            zorder=-1,
        )
    )


def _percentile(values: list[float], fraction: float) -> float:
    """Return a simple percentile for a non-empty float list."""

    if not values:
        return 0.0
    ordered = sorted(values)
    index = int(round((len(ordered) - 1) * fraction))
    return ordered[index]


def _build_chromosome_color_map(chromosomes: list[str]) -> dict[str, str]:
    """Assign stable colours within a figure."""

    return {
        chromosome: _CHROMOSOME_COLOR_PALETTE[index % len(_CHROMOSOME_COLOR_PALETTE)]
        for index, chromosome in enumerate(chromosomes)
    }


def _draw_chromosome_legend(ax: Axes, chromosomes: list[str], color_map: dict[str, str]) -> None:
    """Draw a compact chromosome colour legend."""

    if not chromosomes:
        return
    entry_width = min(0.13, 0.88 / max(1, len(chromosomes)))
    total_width = entry_width * len(chromosomes)
    start_x = max(AXIS_LEFT, (1.0 - total_width) / 2.0)
    for index, chromosome in enumerate(chromosomes):
        x = start_x + index * entry_width
        box = FancyBboxPatch(
            (x, LEGEND_Y - LEGEND_SQUARE_SIZE / 2.0),
            LEGEND_SQUARE_SIZE,
            LEGEND_SQUARE_SIZE,
            boxstyle="round,pad=0,rounding_size=0.002",
            facecolor=color_map.get(chromosome, "#999999"),
            edgecolor="#cccccc",
            lw=0.35,
            zorder=10,
            clip_on=False,
        )
        ax.add_patch(box)
        ax.text(
            x + LEGEND_SQUARE_SIZE + 0.004,
            LEGEND_Y,
            chromosome,
            fontsize=LEGEND_FONT_SIZE,
            ha="left",
            va="center",
            color="#333333",
            zorder=11,
            clip_on=False,
        )


def _infer_track_names(blocks_path: Path) -> list[str]:
    """Infer generic track names from the first non-comment block row."""

    with blocks_path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if line and not line.startswith("#"):
                return [f"Track {index + 1}" for index in range(len(line.split("\t")))]
    return ["Reference", "Subject"]


def render_local_synteny(
    blocks_path: str | Path,
    bed_path: str | Path,
    output_path: str | Path,
    *,
    track_names: list[str] | None = None,
    target_gene_ids: list[str] | None = None,
    label_targets: bool = False,
    figsize: str = "",
    dpi: int = 300,
    fmt: str = "svg",
) -> Path:
    """Render a chromosome-aware local synteny figure."""

    blocks_path = Path(blocks_path).expanduser().resolve(strict=False)
    bed_path = Path(bed_path).expanduser().resolve(strict=False)
    output_path = Path(output_path).expanduser().resolve(strict=False)

    if track_names is None:
        track_names = _infer_track_names(blocks_path)

    scene = LocalSyntenySceneBuilder().build(blocks_path, bed_path, track_names, target_gene_ids or [])
    layout = LocalSyntenyLayoutSolver().solve(scene, figsize=figsize, dpi=dpi)
    return MatplotlibLocalSyntenyRenderer().render(
        layout,
        output_path,
        label_targets=label_targets,
        dpi=dpi,
        fmt=fmt,
    )
