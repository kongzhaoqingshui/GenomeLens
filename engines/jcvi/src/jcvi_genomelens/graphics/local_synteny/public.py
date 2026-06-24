"""染色体感知的局部共线性图渲染器（renderer）

本渲染器消费 JCVI 风格的 ``blocks`` 与合并后的 BED 文件，但不继承
JCVI ``graphics.synteny`` 中“每条轨道必须是单一连续染色体区间”的假设。
每个轨道按真实染色体拆分为多个 segment（染色体片段），按参考物种的行顺序对齐，
并对长锚点-free 间隙进行压缩，从而使跨染色体的局部窗口仍可阅读。
"""

# ruff: noqa: E402

from __future__ import annotations

import re
from pathlib import Path
from statistics import median

import matplotlib

matplotlib.use("Agg")  # noqa: E402
matplotlib.rcParams["svg.fonttype"] = "none"
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.axes import Axes  # noqa: E402
from matplotlib.collections import LineCollection  # noqa: E402
from matplotlib.patches import FancyBboxPatch, PathPatch  # noqa: E402
from matplotlib.path import Path as MplPath  # noqa: E402

from jcvi_genomelens.graphics.local_synteny.models import (
    AnchorLink,
    ChromosomeSegment,
    GeneRecord,
    LocalSyntenyLayout,
    LocalSyntenyScene,
    MappedGene,
    PositionedGene,
    RenderBlock,
    TargetLegendEntry,
    TrackIntervalGenes,
    TrackWindow,
)
from jcvi_genomelens.graphics.local_synteny.style import (
    _CHROMOSOME_COLOR_PALETTE,
    ANCHOR_TICK_BASE_LW,
    ANCHOR_TICK_MIN_LW,
    AXIS_LEFT,
    AXIS_RIGHT,
    BACKGROUND_LINK_COLOR,
    BACKGROUND_TICK_BASE_LW,
    BACKGROUND_TICK_MIN_LW,
    BREAK_MARK_HEIGHT,
    BREAK_MARK_WIDTH,
    COMPRESS_GAP_BP,
    CONTENT_X_PADDING,
    CONTEXT_FLANK_GENES,
    DEFAULT_TRACK_COLORS,
    DRAW_CHROMOSOME_LEGEND,
    GENE_FORWARD_COLOR,
    GENE_REVERSE_COLOR,
    GENE_TICK_HALF_HEIGHT,
    HIGHLIGHT_COLOR,
    HIGHLIGHT_LINK_COLOR,
    HIGHLIGHT_LINK_COLORS,
    INTER_SEGMENT_GAP,
    LABEL_BOX_HEIGHT,
    LANE_GAP,
    LEGEND_FONT_SIZE,
    LEGEND_SQUARE_SIZE,
    LEGEND_Y,
    LINK_ALPHA,
    MAX_INTRA_GAP_WIDTH,
    MAX_LEGEND_ENTRIES,
    MAX_SEGMENT_WIDTH,
    MAX_TRACK_WIDTH,
    MIN_GENE_WIDTH,
    MIN_RIBBON_GENE_WIDTH,
    MIN_SEGMENT_WIDTH,
    RANGE_LABEL_HEIGHT,
    RIBBON_WIDTH_SCALE,
    SHORT_SEGMENT_CONTEXT_ANCHORS,
    SHORT_SEGMENT_CONTEXT_BP,
    SPECIAL_TRUNCATED_COLOR,
    SPECIES_LABEL_GAP,
    TRACK_BAR_COLORS,
    TRACK_BAR_HEIGHT,
    TRACK_GAP,
)


# region 场景构建与布局求解
class LocalSyntenySceneBuilder:
    """Build a chromosome-aware scene from JCVI-style input files."""

    def build(
        self,
        blocks_path: Path,
        bed_path: Path,
        track_names: list[str],
        target_gene_ids: list[str],
    ) -> LocalSyntenyScene:
        """从 blocks 与 BED 构建局部共线性场景"""

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
        """求解染色体片段位置、压缩间隙、lane 与相邻连线"""

        del dpi
        track_items = _collect_track_gene_rows(scene.genes, scene.block_rows, len(scene.track_names))
        track_spans = [_total_track_span(items) for items in track_items]
        max_track_span = max(track_spans, default=1.0)
        track_widths = [_track_visual_width_for_span(span, max_track_span) for span in track_spans]

        tracks: list[TrackWindow] = []
        if scene.track_names:
            reference_color = DEFAULT_TRACK_COLORS[0]
            reference_track, row_x = _build_reference_track(
                scene.track_names[0],
                0,
                reference_color,
                track_items[0],
                scene.genes,
                max_visual_width=track_widths[0],
            )
            tracks.append(reference_track)
        else:
            row_x = {}

        for index, name in enumerate(scene.track_names[1:], start=1):
            color = DEFAULT_TRACK_COLORS[index % len(DEFAULT_TRACK_COLORS)]
            track = _build_target_track(
                name,
                index,
                color,
                track_items[index],
                row_x,
                scene.genes,
                max_visual_width=track_widths[index],
            )
            tracks.append(track)

        for track in tracks:
            _center_track_window(track)

        width, height = _derive_figsize(len(tracks), len(scene.block_rows), figsize, tracks)
        return LocalSyntenyLayout(
            tracks=tracks,
            block_rows=scene.block_rows,
            links=_build_links(scene.block_rows, len(scene.track_names)),
            target_gene_ids=scene.target_gene_ids,
            target_legend_entries=_build_target_legend_entries(scene.block_rows, scene.target_gene_ids),
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
        dpi: int = 900,
        fmt: str = "svg",
    ) -> Path:
        """将求解后的布局渲染为紧凑的出版级图件"""

        fig, ax = plt.subplots(figsize=layout.figsize)
        ax.axis("off")

        self._assign_track_y(layout)
        species_label_x = _species_label_anchor_x(layout.tracks, layout.target_gene_ids)
        track_positions = [
            _draw_track(
                ax,
                track,
                layout.target_gene_ids,
                label_targets,
                species_label_x=species_label_x,
            )
            for track in layout.tracks
        ]
        self._draw_links(ax, layout, track_positions)
        ys = [_segment_y(track, segment) for track in layout.tracks for segment in track.segments]
        legend_y = min(ys) - 0.105 if ys else LEGEND_Y
        _draw_target_legend(ax, layout.target_legend_entries, y_base=legend_y)

        if DRAW_CHROMOSOME_LEGEND:
            chromosomes = sorted({segment.chromosome for track in layout.tracks for segment in track.segments})
            color_map = _build_chromosome_color_map(chromosomes)
            _draw_chromosome_legend(ax, chromosomes, color_map)
        ax.set_xlim(*_centered_x_limits(layout, species_label_x))
        if ys:
            bottom = min(legend_y - 0.04 if layout.target_legend_entries else min(ys) - 0.14, min(ys) - 0.14)
            ax.set_ylim(max(0.0, bottom), min(1.0, max(ys) + 0.10))
        else:
            ax.set_ylim(0.0, 1.0)
        fig.subplots_adjust(left=0.10, right=0.98, top=0.96, bottom=0.14)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output_path, format=fmt, dpi=_effective_dpi(dpi, fmt), bbox_inches="tight", pad_inches=0.08)
        plt.close(fig)
        return output_path

    def _assign_track_y(self, layout: LocalSyntenyLayout) -> None:
        """为每条轨道分配垂直 y 位置"""

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
        track_positions: list[dict[str, PositionedGene]],
    ) -> None:
        """绘制相邻轨道间的共线性连线"""

        drawable_links: list[tuple[AnchorLink, PositionedGene, PositionedGene]] = []
        for link in layout.links:
            if link.left_track >= len(track_positions) or link.right_track >= len(track_positions):
                continue
            left = track_positions[link.left_track].get(link.left_gene)
            right = track_positions[link.right_track].get(link.right_gene)
            if left is None or right is None:
                continue
            drawable_links.append((link, left, right))

        target_colors = _target_color_by_gene(layout)
        for link, left, right in drawable_links:
            color = BACKGROUND_LINK_COLOR
            alpha = LINK_ALPHA
            zorder = 1
            if layout.block_rows[link.row_index].highlighted:
                color = target_colors.get(layout.block_rows[link.row_index].query_gene, HIGHLIGHT_LINK_COLOR)
                alpha = 1.0
                zorder = 2
            elif link.left_gene in layout.target_gene_ids or link.right_gene in layout.target_gene_ids:
                color = target_colors.get(link.left_gene) or target_colors.get(link.right_gene) or "#6b7280"
                alpha = 1.0
                zorder = 2
            _draw_ribbon_link(
                ax,
                left,
                right,
                color=color,
                alpha=alpha,
                zorder=zorder,
            )


# endregion


# region 输入解析与工具函数
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


def _safe_prefix(value: str) -> str:
    """Return the scoped-ID prefix used by multi-species local BED files."""

    text = re.sub(r"[^0-9A-Za-z_.-]+", "_", value.strip())
    return text or "species"


def _track_prefix(track_name: str) -> str:
    """Return the expected scoped-ID prefix for a track name."""

    return _safe_prefix(track_name)


def _display_accn(accn: str) -> str:
    """Return the human-readable part of an accn."""

    return _scope_of(accn)[1]


def _format_bp_range(start_bp: float, end_bp: float) -> str:
    """Format a base-pair range like JCVI does."""

    span = abs(end_bp - start_bp)
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


def _track_chromosome_genes(
    genes: dict[str, GeneRecord],
    *,
    track_name: str,
    chromosome: str,
) -> list[GeneRecord]:
    """Return all BED genes for a track/chromosome, preferring scoped IDs."""

    prefix = _track_prefix(track_name)
    scoped_matches = [
        gene for gene in genes.values() if _scope_of(gene.accn)[0] == prefix and gene.chromosome == chromosome
    ]
    candidates = scoped_matches
    if not candidates:
        candidates = [gene for gene in genes.values() if gene.chromosome == chromosome]
    return sorted(candidates, key=lambda gene: (gene.start, gene.end, gene.accn))


def _should_expand_context(anchors: list[tuple[GeneRecord, int]], start_bp: float, end_bp: float) -> bool:
    """Return True for very small local segments that need flanking context."""

    return len(anchors) <= SHORT_SEGMENT_CONTEXT_ANCHORS or (end_bp - start_bp) <= SHORT_SEGMENT_CONTEXT_BP


def _genes_in_track_interval(
    genes: dict[str, GeneRecord],
    *,
    track_name: str,
    chromosome: str,
    start_bp: float,
    end_bp: float,
    anchors: list[tuple[GeneRecord, int]],
) -> TrackIntervalGenes:
    """Return all BED genes from one track interval, preserving anchor rows and context."""

    anchor_rows = {gene.accn: row_index for gene, row_index in anchors}
    chromosome_genes = _track_chromosome_genes(genes, track_name=track_name, chromosome=chromosome)
    if not chromosome_genes:
        return TrackIntervalGenes(list(anchors), start_bp, end_bp)

    selected = [gene for gene in chromosome_genes if gene.end >= start_bp and gene.start <= end_bp]
    if _should_expand_context(anchors, start_bp, end_bp):
        anchor_accns = {gene.accn for gene, _row_index in anchors}
        anchor_indices = [index for index, gene in enumerate(chromosome_genes) if gene.accn in anchor_accns]
        if anchor_indices:
            left = max(0, min(anchor_indices) - CONTEXT_FLANK_GENES)
            right = min(len(chromosome_genes) - 1, max(anchor_indices) + CONTEXT_FLANK_GENES)
            selected = chromosome_genes[left : right + 1]

    merged = {gene.accn: (gene, anchor_rows.get(gene.accn, -1)) for gene in selected}
    for gene, row_index in anchors:
        merged[gene.accn] = (gene, row_index)
    ordered = sorted(merged.values(), key=lambda item: (item[0].start, item[0].end, item[0].accn))
    selected_accns = {gene.accn for gene, _row_index in ordered}
    selected_indices = [index for index, gene in enumerate(chromosome_genes) if gene.accn in selected_accns]
    left_truncated = bool(selected_indices and min(selected_indices) > 0)
    right_truncated = bool(selected_indices and max(selected_indices) < len(chromosome_genes) - 1)
    interval_start = min((gene.start for gene, _row_index in ordered), default=start_bp)
    interval_end = max((gene.end for gene, _row_index in ordered), default=end_bp)
    return TrackIntervalGenes(
        items=ordered,
        start_bp=float(interval_start),
        end_bp=float(interval_end),
        left_truncated=left_truncated,
        right_truncated=right_truncated,
    )


def _total_track_span(items: list[tuple[GeneRecord, int]]) -> float:
    """Return total BED span across chromosome segments in one track."""

    total = 0.0
    for _chromosome, group in _chromosome_ordered_groups(_dedupe_gene_rows(items)):
        total += max(1.0, float(max(gene.end for gene, _ in group) - min(gene.start for gene, _ in group)))
    return max(1.0, total)


def _track_visual_width_for_span(span: float, max_span: float) -> float:
    """Scale a track's total visual width against the longest local window."""

    if max_span <= 0:
        return MAX_TRACK_WIDTH
    return max(MIN_SEGMENT_WIDTH, MAX_TRACK_WIDTH * max(1.0, span) / max_span)


def _center_track_window(track: TrackWindow) -> None:
    """Center one track's solved visual span on the shared canvas axis."""

    if not track.segments:
        return
    left = min(segment.visual_start for segment in track.segments)
    right = max(segment.visual_end for segment in track.segments)
    desired_center = (AXIS_LEFT + AXIS_RIGHT) / 2.0
    _shift = desired_center - (left + right) / 2.0
    for segment in track.segments:
        _shift_segment(segment, _shift)


def _build_target_legend_entries(
    block_rows: list[RenderBlock],
    target_gene_ids: set[str],
) -> list[TargetLegendEntry]:
    """Build stable target legend entries from highlighted rows and explicit target genes."""

    ordered: list[str] = []
    for row in block_rows:
        if row.highlighted and row.query_gene not in ordered:
            ordered.append(row.query_gene)
    for gene_id in sorted(target_gene_ids):
        if gene_id not in ordered:
            ordered.append(gene_id)
    entries = [
        TargetLegendEntry(gene_id=gene_id, color=HIGHLIGHT_LINK_COLORS[index % len(HIGHLIGHT_LINK_COLORS)])
        for index, gene_id in enumerate(ordered[:MAX_LEGEND_ENTRIES])
    ]
    if len(ordered) > MAX_LEGEND_ENTRIES and entries:
        last = entries[-1]
        entries[-1] = TargetLegendEntry(last.gene_id, last.color, hidden_count=len(ordered) - MAX_LEGEND_ENTRIES)
    return entries


def _target_color_by_gene(layout: LocalSyntenyLayout) -> dict[str, str]:
    """Return legend colour by full gene ID."""

    return {entry.gene_id: entry.color for entry in layout.target_legend_entries}


def _estimate_segment_width(genes: list[GeneRecord]) -> float:
    """Estimate a compact segment width before gap-compressed mapping."""

    if not genes:
        return MIN_SEGMENT_WIDTH
    raw_span = max(g.end for g in genes) - min(g.start for g in genes)
    gene_component = max(MIN_SEGMENT_WIDTH, min(0.24, len(genes) * 0.022))
    span_component = min(MAX_SEGMENT_WIDTH, max(MIN_SEGMENT_WIDTH, raw_span / 5_000_000 * 0.18))
    return min(MAX_SEGMENT_WIDTH, max(gene_component, span_component))


def _allocate_segment_widths_by_span(spans: list[float], available_width: float) -> list[float]:
    """Allocate same-row chromosome widths proportionally to real BED spans."""

    if not spans:
        return []
    if available_width <= 0:
        return [MIN_SEGMENT_WIDTH for _ in spans]

    min_width = min(MIN_SEGMENT_WIDTH, available_width / len(spans))
    if min_width * len(spans) >= available_width:
        return [available_width / len(spans) for _ in spans]

    widths = [0.0 for _ in spans]
    remaining = set(range(len(spans)))
    remaining_width = available_width
    while remaining:
        total_span = sum(max(1.0, spans[index]) for index in remaining)
        below_min: list[int] = []
        proposed: dict[int, float] = {}
        for index in remaining:
            width = remaining_width * max(1.0, spans[index]) / total_span
            proposed[index] = width
            if width < min_width:
                below_min.append(index)
        if not below_min:
            for index, width in proposed.items():
                widths[index] = width
            break
        for index in below_min:
            widths[index] = min_width
            remaining.remove(index)
            remaining_width -= min_width
        if remaining_width <= 0:
            for index in remaining:
                widths[index] = min_width
            break

    return widths


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

    _cap_mapped_segment_width(mapped, gap_markers, start_x=start_x, max_width=target_width)
    return mapped, gap_markers, compressed


def _flip_strand(strand: str) -> str:
    """Flip a BED strand for a visually reversed segment."""

    if strand == "-":
        return "+"
    if strand == "+":
        return "-"
    return strand


def _should_reverse_segment(group: list[tuple[GeneRecord, int]], row_x: dict[int, float]) -> bool:
    """Infer whether a target segment should be drawn in reverse orientation."""

    pairs = sorted((row_x[row_index], gene.start) for gene, row_index in group if row_index in row_x)
    if len(pairs) < 2:
        return False
    left_x, left_bp = pairs[0]
    right_x, right_bp = pairs[-1]
    if abs(right_x - left_x) < 1e-9:
        return False
    return right_bp < left_bp


def _reverse_mapped_segment(
    mapped: list[MappedGene],
    gap_markers: list[float],
    *,
    start_x: float,
    width: float,
) -> None:
    """Mirror mapped genes inside a segment and flip their displayed strand."""

    for item in mapped:
        offset = item.x - start_x
        item.x = start_x + width - offset
        item.visual_strand = _flip_strand(item.gene.strand)
    for index, marker in enumerate(gap_markers):
        gap_markers[index] = start_x + width - (marker - start_x)


def _set_segment_orientation(segment: ChromosomeSegment, *, reversed_orientation: bool) -> None:
    """Mirror a solved segment when enforcing same-track visual orientation."""

    if segment.reversed == reversed_orientation:
        return
    start_x = segment.visual_start
    width = segment.visual_end - segment.visual_start
    for item in segment.genes:
        item.x = start_x + width - (item.x - start_x)
        item.visual_strand = _flip_strand(item.gene.strand) if reversed_orientation else None
    segment.gap_markers = [start_x + width - (marker - start_x) for marker in segment.gap_markers]
    segment.start_bp, segment.end_bp = segment.end_bp, segment.start_bp
    segment.reversed = reversed_orientation


def _unify_track_segment_orientations(segments: list[ChromosomeSegment]) -> None:
    """Keep all chromosome segments in one track oriented like the leftmost segment."""

    if len(segments) <= 1:
        return
    leftmost = min(segments, key=lambda segment: segment.visual_start)
    for segment in segments:
        _set_segment_orientation(segment, reversed_orientation=leftmost.reversed)


def _cap_mapped_segment_width(
    mapped: list[MappedGene],
    gap_markers: list[float],
    *,
    start_x: float,
    max_width: float,
) -> None:
    """Keep compressed gap glyphs from expanding a segment beyond its real-width allocation."""

    if not mapped:
        return
    left = min(item.x - item.width / 2.0 for item in mapped)
    right = max(item.x + item.width / 2.0 for item in mapped)
    span = right - left
    if span <= max_width:
        shift = start_x - left
        for item in mapped:
            item.x += shift
        for index, marker in enumerate(gap_markers):
            gap_markers[index] = marker + shift
        return

    factor = max_width / max(1e-9, span)
    for item in mapped:
        item.x = start_x + (item.x - left) * factor
        item.width = max(MIN_GENE_WIDTH, item.width * factor)
    for index, marker in enumerate(gap_markers):
        gap_markers[index] = start_x + (marker - left) * factor


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
    genes: dict[str, GeneRecord],
    *,
    max_visual_width: float = MAX_TRACK_WIDTH,
) -> tuple[TrackWindow, dict[int, float]]:
    """Build the reference track on true BED coordinates."""

    segments: list[ChromosomeSegment] = []
    all_mapped: list[MappedGene] = []
    row_x: dict[int, float] = {}
    groups = _chromosome_ordered_groups(_dedupe_gene_rows(items))
    spans = [max(1, max(gene.end for gene, _ in group) - min(gene.start for gene, _ in group)) for _, group in groups]
    available_width = max(MIN_SEGMENT_WIDTH, max_visual_width - INTER_SEGMENT_GAP * max(0, len(groups) - 1))
    total_span = max(1, sum(spans))
    x = AXIS_LEFT

    for (chromosome, group), span in zip(groups, spans, strict=False):
        start_bp = min(gene.start for gene, _ in group)
        end_bp = max(gene.end for gene, _ in group)
        interval = _genes_in_track_interval(
            genes,
            track_name=name,
            chromosome=chromosome,
            start_bp=start_bp,
            end_bp=end_bp,
            anchors=group,
        )
        visual_width = max(MIN_SEGMENT_WIDTH, available_width * span / total_span)
        if x + visual_width > AXIS_RIGHT:
            visual_width = max(MIN_SEGMENT_WIDTH, AXIS_RIGHT - x)
        mapped, start_bp, end_bp = _map_reference_segment_genes(
            interval.items,
            visual_start=x,
            visual_width=visual_width,
        )
        all_mapped.extend(mapped)
        for mapped_gene in mapped:
            if mapped_gene.row_index >= 0:
                row_x[mapped_gene.row_index] = mapped_gene.x
        segments.append(
            ChromosomeSegment(
                chromosome=chromosome,
                genes=mapped,
                start_bp=start_bp,
                end_bp=end_bp,
                visual_start=x,
                visual_end=x + visual_width,
                left_truncated=interval.left_truncated,
                right_truncated=interval.right_truncated,
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
            visual_width=max_visual_width,
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
    genes: dict[str, GeneRecord],
    *,
    max_visual_width: float = MAX_TRACK_WIDTH,
) -> TrackWindow:
    """Build a non-reference track and align segments to reference anchors."""

    segments: list[ChromosomeSegment] = []
    all_mapped: list[MappedGene] = []
    segment_specs: list[tuple[str, list[tuple[GeneRecord, int]], TrackIntervalGenes, float, float, float]] = []
    for chromosome, group in _chromosome_ordered_groups(_dedupe_gene_rows(items)):
        start_bp = min(gene.start for gene, _ in group)
        end_bp = max(gene.end for gene, _ in group)
        interval = _genes_in_track_interval(
            genes,
            track_name=name,
            chromosome=chromosome,
            start_bp=start_bp,
            end_bp=end_bp,
            anchors=group,
        )
        if not interval.items:
            continue
        segment_specs.append(
            (
                chromosome,
                group,
                interval,
                interval.start_bp,
                interval.end_bp,
                max(1.0, interval.end_bp - interval.start_bp),
            )
        )

    available_width = max(MIN_SEGMENT_WIDTH, max_visual_width - INTER_SEGMENT_GAP * max(0, len(segment_specs) - 1))
    target_widths = _allocate_segment_widths_by_span(
        [span for *_prefix, span in segment_specs],
        max(MIN_SEGMENT_WIDTH, available_width),
    )

    for (chromosome, group, interval, start_bp, end_bp, _span), target_width in zip(
        segment_specs,
        target_widths,
        strict=False,
    ):
        mapped, gap_markers, compressed = _map_segment_genes(interval.items, start_x=0.0, target_width=target_width)
        if not mapped:
            continue
        reversed_segment = _should_reverse_segment(group, row_x)
        if reversed_segment:
            _reverse_mapped_segment(mapped, gap_markers, start_x=0.0, width=target_width)
        anchor_mapped = [item for item in mapped if item.row_index in row_x]
        if not anchor_mapped:
            continue
        desired = median(row_x[item.row_index] for item in anchor_mapped)
        current = median(item.x for item in anchor_mapped)
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
        display_start_bp = end_bp if reversed_segment else start_bp
        display_end_bp = start_bp if reversed_segment else end_bp
        segments.append(
            ChromosomeSegment(
                chromosome=chromosome,
                genes=mapped,
                start_bp=display_start_bp,
                end_bp=display_end_bp,
                visual_start=min(item.x - item.width / 2.0 for item in mapped),
                visual_end=max(item.x + item.width / 2.0 for item in mapped),
                has_compressed_gaps=compressed,
                gap_markers=shifted_markers,
                left_truncated=interval.left_truncated,
                right_truncated=interval.right_truncated,
                reversed=reversed_segment,
            )
        )

    _assign_segment_lanes(segments)
    _pack_segments_same_row(segments)
    _unify_track_segment_orientations(segments)
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
        visual_width=max_visual_width,
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


# endregion


# region 布局与渲染工具函数
def _compute_layout(
    blocks_path: Path,
    bed_path: Path,
    track_names: list[str],
    target_gene_ids: list[str],
    figsize: str = "",
    dpi: int = 900,
) -> LocalSyntenyLayout:
    """从 blocks + BED 构建染色体感知的局部共线性场景"""

    scene = LocalSyntenySceneBuilder().build(blocks_path, bed_path, track_names, target_gene_ids)
    return LocalSyntenyLayoutSolver().solve(scene, figsize=figsize, dpi=dpi)


def _effective_dpi(dpi: int, fmt: str) -> int:
    """光栅格式返回至少 2x DPI，矢量格式不受影响"""

    if fmt.lower() in {"png", "jpg", "jpeg", "tif", "tiff", "webp"}:
        return max(900, dpi)
    return max(1, dpi)


def _layout_visual_audit(layout: LocalSyntenyLayout) -> dict[str, object]:
    """返回紧凑的几何事实，用于视觉回归检查"""

    track_records: list[dict[str, object]] = []
    for track in layout.tracks:
        if track.segments:
            left = min(segment.visual_start for segment in track.segments)
            right = max(segment.visual_end for segment in track.segments)
        else:
            left = right = 0.0
        track_records.append(
            {
                "name": track.name,
                "center": round((left + right) / 2.0, 6),
                "width": round(right - left, 6),
                "segments": [
                    {
                        "chromosome": segment.chromosome,
                        "width": round(segment.visual_end - segment.visual_start, 6),
                        "left_truncated": segment.left_truncated,
                        "right_truncated": segment.right_truncated,
                        "reversed": segment.reversed,
                    }
                    for segment in track.segments
                ],
            }
        )
    return {
        "tracks": track_records,
        "ribbon_count": len(layout.links),
        "legend_entries": [entry.gene_id for entry in layout.target_legend_entries],
    }


def _derive_figsize(
    track_count: int,
    block_rows: int,
    figsize: str,
    tracks: list[TrackWindow] | None = None,
) -> tuple[float, float]:
    """返回合理的画布尺寸(英寸)"""

    if figsize:
        parts = figsize.lower().split("x")
        if len(parts) == 2:
            try:
                return float(parts[0]), float(parts[1])
            except ValueError:
                pass
    lane_total = sum(track.lane_count for track in tracks or [])
    height = max(4.5, 1.65 + track_count * 0.78 + lane_total * 0.24)
    width = max(10.0, min(18.0, 8.0 + block_rows * 0.045))
    return width, height


# endregion


# region 绘图原语
def _draw_break_marker(ax: Axes, x: float, y: float, color: str = "#777777") -> None:
    """在压缩染色体条上绘制小双斜线断裂标记"""

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


def _draw_segment_truncation_markers(ax: Axes, segment: ChromosomeSegment, y: float) -> None:
    """当上下文扩展片段仍被裁剪时绘制紧凑断裂标记"""

    if segment.left_truncated:
        _draw_terminal_break_marker(ax, segment.visual_start - 0.0040, y, side="left")
    if segment.right_truncated:
        _draw_terminal_break_marker(ax, segment.visual_end + 0.0018, y, side="right")


def _draw_terminal_break_marker(ax: Axes, x: float, y: float, *, side: str) -> None:
    """绘制集成式末端截断标记"""

    del side
    color = "#728088"
    direction = 1
    for offset in (0.0, 0.0022 * direction):
        ax.plot(
            [x + offset - 0.0010 * direction, x + offset + 0.0010 * direction],
            [y - 0.0054, y + 0.0054],
            color=color,
            lw=0.42,
            alpha=0.76,
            zorder=8,
            solid_capstyle="round",
            clip_on=False,
        )


def _track_bar_color(index: int) -> str:
    """返回柔和的按轨道条颜色"""

    return TRACK_BAR_COLORS[index % len(TRACK_BAR_COLORS)]


def _track_bar_edge_color(index: int) -> str:
    """返回柔和的按轨道条边缘颜色"""

    return DEFAULT_TRACK_COLORS[index % len(DEFAULT_TRACK_COLORS)]


def _is_special_truncated_segment(segment: ChromosomeSegment) -> bool:
    """判断短上下文扩展片段是否失去真实比例可读性"""

    if not (segment.left_truncated or segment.right_truncated):
        return False
    visual_width = segment.visual_end - segment.visual_start
    return visual_width <= MIN_SEGMENT_WIDTH * 1.35


def _draw_gene_tick_collection(
    ax: Axes,
    ticks: list[list[tuple[float, float]]],
    color: str,
    *,
    alpha: float,
    linewidth: float | list[float],
) -> None:
    """高效绘制大量背景基因刻度"""

    if not ticks:
        return
    ax.add_collection(
        LineCollection(
            ticks,
            colors=color,
            linewidths=linewidth,
            alpha=alpha,
            zorder=4,
            clip_on=False,
        )
    )


def _typical_gene_length(mapped_genes: list[MappedGene]) -> float:
    """返回稳健的常见基因长度，用于局部线宽缩放"""

    lengths = [max(1, mapped.gene.length_bp) for mapped in mapped_genes]
    if not lengths:
        return 1.0
    bucket_counts: dict[int, int] = {}
    for length in lengths:
        bucket = max(1, int(round(length / 100.0)) * 100)
        bucket_counts[bucket] = bucket_counts.get(bucket, 0) + 1
    common_bucket = max(bucket_counts.items(), key=lambda item: (item[1], -item[0]))[0]
    return float(common_bucket)


def _scaled_gene_tick_linewidth(mapped: MappedGene, typical_length: float, *, baseline: float, minimum: float) -> float:
    """按基因长度缩放刻度线宽，同时保留可见下限"""

    multiplier = max(0.01, mapped.gene.length_bp / max(1.0, typical_length))
    return max(minimum, baseline * multiplier)


def _abbreviate_track_name(name: str) -> str:
    """生成紧凑的物种标签"""

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
    """估计染色体标签框的轴宽度"""

    return max(0.038, len(text) * 0.0078 + 0.012)


def _estimate_range_label_width(text: str) -> float:
    """估计紧凑范围标签的轴宽度"""

    return max(0.046, len(text) * 0.0054 + 0.010)


def _estimate_species_label_width(text: str) -> float:
    """估计粗体物种标签的轴宽度"""

    return max(0.050, len(text) * 0.0068 + 0.012)


def _estimate_legend_label_width(text: str) -> float:
    """估计底部目标图例标签的轴宽度"""

    return max(0.035, len(text) * 0.0050 + 0.008)


def _draw_label_box(
    ax: Axes,
    text: str,
    x: float,
    y: float,
    fontsize: int = 7,
    color: str = "#4b5963",
) -> None:
    """绘制带微妙白色衬垫的紧凑染色体标签"""

    box_width = _estimate_label_box_width(text)
    ax.text(
        x + box_width / 2.0,
        y,
        text,
        fontsize=fontsize,
        fontweight="semibold",
        ha="center",
        va="center",
        color=color,
        zorder=9,
        clip_on=False,
        bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.62, "pad": 0.42},
    )


def _label_rect(x: float, y: float, width: float) -> tuple[float, float, float, float]:
    """返回标签矩形 ``(left, right, bottom, top)``"""

    return (x, x + width, y - LABEL_BOX_HEIGHT / 2.0, y + LABEL_BOX_HEIGHT / 2.0)


def _centered_rect(x: float, y: float, width: float, height: float) -> tuple[float, float, float, float]:
    """返回中心锚定矩形"""

    return (x - width / 2.0, x + width / 2.0, y - height / 2.0, y + height / 2.0)


def _rects_overlap(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> bool:
    """判断两个轴坐标矩形是否重叠"""

    return not (a[1] <= b[0] or b[1] <= a[0] or a[3] <= b[2] or b[3] <= a[2])


def _clamp(value: float, lower: float, upper: float) -> float:
    """将浮点数限制在闭区间内"""

    return min(max(value, lower), upper)


def _label_overlaps_segment_bar(
    rect: tuple[float, float, float, float],
    segment: ChromosomeSegment,
    y: float,
) -> bool:
    """检测标签框是否覆盖染色体条"""

    bar_rect = (
        segment.visual_start - 0.004,
        segment.visual_end + 0.004,
        y - TRACK_BAR_HEIGHT * 0.9,
        y + TRACK_BAR_HEIGHT * 0.9,
    )
    return _rects_overlap(rect, bar_rect)


def _label_overlaps_track_bar(rect: tuple[float, float, float, float], track: TrackWindow) -> bool:
    """检测标签框是否覆盖轨道内的任何染色体条"""

    return any(_label_overlaps_segment_bar(rect, segment, _segment_y(track, segment)) for segment in track.segments)


def _draw_range_label(
    ax: Axes,
    text: str,
    track: TrackWindow,
    segment: ChromosomeSegment,
    y: float,
    occupied: list[tuple[float, float, float, float]],
) -> None:
    """在最近的非重叠位置绘制范围标签"""

    width = _estimate_range_label_width(text)
    center = (segment.visual_start + segment.visual_end) / 2.0
    candidates = [
        (center, y - 0.034),
        (center, y - 0.064),
        (segment.visual_start - width / 2.0 - 0.010, y - 0.026),
        (segment.visual_end + width / 2.0 + 0.010, y - 0.026),
        (center, y + 0.034),
        (center, y + 0.064),
    ]
    label_x = _clamp(center, -0.22 + width / 2.0, AXIS_RIGHT - width / 2.0)
    label_y = y - 0.034
    label_rect = _centered_rect(label_x, label_y, width, RANGE_LABEL_HEIGHT)
    for raw_x, raw_y in candidates:
        x = _clamp(raw_x, -0.22 + width / 2.0, AXIS_RIGHT - width / 2.0)
        rect = _centered_rect(x, raw_y, width, RANGE_LABEL_HEIGHT)
        if _label_overlaps_track_bar(rect, track):
            continue
        if any(_rects_overlap(rect, other) for other in occupied):
            continue
        label_x = x
        label_y = raw_y
        label_rect = rect
        break
    occupied.append(label_rect)
    ax.text(
        label_x,
        label_y,
        text,
        fontsize=5.4,
        ha="center",
        va="center",
        color="#64748b",
        alpha=0.90,
        zorder=7,
        clip_on=False,
        bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.68, "pad": 0.35},
    )


def _target_star_rects(track: TrackWindow, target_gene_ids: set[str]) -> list[tuple[float, float, float, float]]:
    """返回目标标记占用的矩形区域

    目标星形标记已被底部颜色图例取代，因此标签不再需要预留标记空间
    """

    del track, target_gene_ids
    return []


def _label_positions_for_segments(
    track: TrackWindow,
    target_gene_ids: set[str],
) -> dict[int, tuple[float, float]]:
    """计算不覆盖条形的非重叠标签位置"""

    occupied: list[tuple[float, float, float, float]] = _target_star_rects(track, target_gene_ids)
    positions: dict[int, tuple[float, float]] = {}
    ordered_segments = sorted(enumerate(track.segments), key=lambda item: item[1].visual_start)
    for ordered_index, (original_index, segment) in enumerate(ordered_segments):
        y = _segment_y(track, segment)
        width = _estimate_label_box_width(segment.chromosome)
        center = (segment.visual_start + segment.visual_end) / 2.0
        candidates = _chromosome_label_candidates(track, segment, ordered_index, center, width, y)
        fallback = candidates[-1]
        for raw_x, raw_y in candidates:
            x = _clamp(raw_x, -0.22, AXIS_RIGHT - width)
            rect = _label_rect(x, raw_y, width)
            if _label_overlaps_track_bar(rect, track):
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


def _track_visual_extent(track: TrackWindow, target_gene_ids: set[str]) -> tuple[float, float]:
    """返回轨道的可见水平范围，包括侧边标签"""

    left_edges = [segment.visual_start for segment in track.segments]
    right_edges = [segment.visual_end for segment in track.segments]
    for segment_index, (label_x, _label_y) in _label_positions_for_segments(track, target_gene_ids).items():
        width = _estimate_label_box_width(track.segments[segment_index].chromosome)
        left_edges.append(label_x)
        right_edges.append(label_x + width)
    return min(left_edges), max(right_edges)


def _species_label_anchor_x(tracks: list[TrackWindow], target_gene_ids: set[str]) -> float:
    """将物种标签右对齐到最宽可见轨道范围的左侧"""

    if not tracks:
        return AXIS_LEFT - SPECIES_LABEL_GAP
    left, _right = max(
        (_track_visual_extent(track, target_gene_ids) for track in tracks),
        key=lambda extent: extent[1] - extent[0],
    )
    return left - SPECIES_LABEL_GAP


def _target_legend_extent(entries: list[TargetLegendEntry]) -> tuple[float, float] | None:
    """返回底部目标图例占用的水平范围"""

    if not entries:
        return None
    columns = min(6, len(entries))
    col_width = min(0.145, MAX_TRACK_WIDTH / max(1, columns))
    left_edges: list[float] = []
    right_edges: list[float] = []
    for index, entry in enumerate(entries):
        col = index % columns
        x = AXIS_LEFT + col * col_width
        label = _display_accn(entry.gene_id)
        if entry.hidden_count:
            label = f"{label} +{entry.hidden_count}"
        left_edges.append(x)
        right_edges.append(x + 0.036 + _estimate_legend_label_width(label))
    return min(left_edges), max(right_edges)


def _layout_visual_extent(layout: LocalSyntenyLayout, species_label_x: float) -> tuple[float, float]:
    """返回所有可见局部共线性内容的水平范围"""

    left_edges: list[float] = []
    right_edges: list[float] = []
    for track in layout.tracks:
        track_left, track_right = _track_visual_extent(track, layout.target_gene_ids)
        left_edges.append(track_left)
        right_edges.append(track_right)
        species_label = _abbreviate_track_name(track.name)
        left_edges.append(species_label_x - _estimate_species_label_width(species_label))
        right_edges.append(species_label_x)

    legend_extent = _target_legend_extent(layout.target_legend_entries)
    if legend_extent is not None:
        left_edges.append(legend_extent[0])
        right_edges.append(legend_extent[1])

    if not left_edges:
        return AXIS_LEFT, AXIS_RIGHT
    return min(left_edges), max(right_edges)


def _centered_x_limits(layout: LocalSyntenyLayout, species_label_x: float) -> tuple[float, float]:
    """围绕可见内容范围计算平衡的 x 轴限制"""

    left, right = _layout_visual_extent(layout, species_label_x)
    return left - CONTENT_X_PADDING, right + CONTENT_X_PADDING


def _chromosome_label_candidates(
    track: TrackWindow,
    segment: ChromosomeSegment,
    ordered_index: int,
    center: float,
    width: float,
    y: float,
) -> list[tuple[float, float]]:
    """返回遵循局部共线性风格规则的染色体标签候选位置"""

    has_long_name = len(segment.chromosome) > 8
    if len(track.segments) == 2 and not has_long_name:
        if ordered_index == 0:
            margin = 0.022 if segment.left_truncated else 0.008
            primary = (segment.visual_start - width - margin, y)
        else:
            margin = 0.022 if segment.right_truncated else 0.008
            primary = (segment.visual_end + margin, y)
        return [
            primary,
            (primary[0], y + 0.034),
            (center - width / 2.0, y + 0.034),
            (center - width / 2.0, y - 0.038),
        ]

    return [
        (center - width / 2.0, y + 0.034),
        (segment.visual_start - width * 0.30, y + 0.034),
        (segment.visual_end - width * 0.70, y + 0.034),
        (segment.visual_start - width - 0.008, y),
        (segment.visual_end + 0.008, y),
    ]


def _draw_star(ax: Axes, x: float, y: float, color: str = HIGHLIGHT_LINK_COLOR) -> None:
    """绘制目标基因标记"""

    ax.plot(
        x,
        y,
        marker="*",
        markersize=13,
        markeredgecolor=HIGHLIGHT_COLOR,
        markerfacecolor=color,
        markeredgewidth=0.55,
        zorder=11,
        clip_on=False,
    )


def _draw_target_gene_label(ax: Axes, text: str, x: float, y: float, segment: ChromosomeSegment) -> None:
    """在星形标记附近绘制目标基因标签，避免覆盖条形"""

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
    """返回片段 lane 的 y 坐标"""

    if track.lane_count <= 1:
        return track.y
    center_offset = (track.lane_count - 1) * LANE_GAP / 2.0
    return track.y + center_offset - segment.lane * LANE_GAP


def _draw_track(
    ax: Axes,
    track: TrackWindow,
    target_gene_ids: set[str],
    label_targets: bool,
    *,
    species_label_x: float,
) -> dict[str, PositionedGene]:
    """绘制单个轨道并返回基因中心位置"""

    gene_positions: dict[str, PositionedGene] = {}
    label_positions = _label_positions_for_segments(track, target_gene_ids)
    occupied_text_rects = _target_star_rects(track, target_gene_ids)
    for segment_index, (label_x, label_y) in label_positions.items():
        segment = track.segments[segment_index]
        occupied_text_rects.append(_label_rect(label_x, label_y, _estimate_label_box_width(segment.chromosome)))

    ax.text(
        species_label_x,
        track.y,
        _abbreviate_track_name(track.name),
        fontsize=8,
        fontweight="bold",
        ha="right",
        va="center",
        color=track.color,
        zorder=9,
        clip_on=False,
    )

    for segment_index, segment in enumerate(track.segments):
        y = _segment_y(track, segment)
        is_special_truncated = _is_special_truncated_segment(segment)
        bar = FancyBboxPatch(
            (segment.visual_start, y - TRACK_BAR_HEIGHT / 2.0),
            max(MIN_SEGMENT_WIDTH / 2.0, segment.visual_end - segment.visual_start),
            TRACK_BAR_HEIGHT,
            boxstyle=f"round,pad=0,rounding_size={TRACK_BAR_HEIGHT / 2.0}",
            facecolor=_track_bar_color(track.index),
            edgecolor=SPECIAL_TRUNCATED_COLOR if is_special_truncated else _track_bar_edge_color(track.index),
            lw=0.58 if is_special_truncated else 0.4,
            zorder=3,
            clip_on=False,
        )
        ax.add_patch(bar)

        _draw_segment_truncation_markers(ax, segment, y)
        for marker in segment.gap_markers:
            _draw_break_marker(ax, marker, y)

        tick_top = y + GENE_TICK_HALF_HEIGHT
        tick_bottom = y - GENE_TICK_HALF_HEIGHT
        typical_length = _typical_gene_length(segment.genes)
        background_forward = [
            [(mapped.x, tick_bottom), (mapped.x, tick_top)]
            for mapped in segment.genes
            if mapped.row_index < 0 and mapped.display_strand != "-"
        ]
        background_forward_widths = [
            _scaled_gene_tick_linewidth(
                mapped,
                typical_length,
                baseline=BACKGROUND_TICK_BASE_LW,
                minimum=BACKGROUND_TICK_MIN_LW,
            )
            for mapped in segment.genes
            if mapped.row_index < 0 and mapped.display_strand != "-"
        ]
        background_reverse = [
            [(mapped.x, tick_bottom), (mapped.x, tick_top)]
            for mapped in segment.genes
            if mapped.row_index < 0 and mapped.display_strand == "-"
        ]
        background_reverse_widths = [
            _scaled_gene_tick_linewidth(
                mapped,
                typical_length,
                baseline=BACKGROUND_TICK_BASE_LW,
                minimum=BACKGROUND_TICK_MIN_LW,
            )
            for mapped in segment.genes
            if mapped.row_index < 0 and mapped.display_strand == "-"
        ]
        _draw_gene_tick_collection(
            ax,
            background_forward,
            GENE_FORWARD_COLOR,
            alpha=0.88,
            linewidth=background_forward_widths,
        )
        _draw_gene_tick_collection(
            ax,
            background_reverse,
            GENE_REVERSE_COLOR,
            alpha=0.88,
            linewidth=background_reverse_widths,
        )
        for mapped in segment.genes:
            is_anchor = mapped.row_index >= 0
            if not is_anchor:
                continue
            gene_color = GENE_REVERSE_COLOR if mapped.display_strand == "-" else GENE_FORWARD_COLOR
            linewidth = _scaled_gene_tick_linewidth(
                mapped,
                typical_length,
                baseline=ANCHOR_TICK_BASE_LW,
                minimum=ANCHOR_TICK_MIN_LW,
            )
            ax.plot(
                [mapped.x, mapped.x],
                [tick_bottom, tick_top],
                color=gene_color,
                lw=linewidth,
                alpha=0.96,
                zorder=6,
                solid_capstyle="butt",
            )
            gene_positions[mapped.gene.accn] = PositionedGene(
                mapped=mapped,
                y=y,
            )
            if mapped.gene.accn in target_gene_ids and label_targets:
                _draw_target_gene_label(ax, _display_accn(mapped.gene.accn), mapped.x, y, segment)

        label_x, label_y = label_positions.get(segment_index, (-0.18, y))
        label_color = SPECIAL_TRUNCATED_COLOR if is_special_truncated else "#4b5963"
        _draw_label_box(ax, segment.chromosome, label_x, label_y, color=label_color)
        _draw_range_label(
            ax,
            _format_bp_range(segment.start_bp, segment.end_bp),
            track,
            segment,
            y,
            occupied_text_rects,
        )

    return gene_positions


def _gene_interval_points(positioned: PositionedGene) -> tuple[tuple[float, float], tuple[float, float]]:
    """返回单个映射基因的可见左右端点"""

    width = max(MIN_RIBBON_GENE_WIDTH, positioned.mapped.width * RIBBON_WIDTH_SCALE)
    x1 = positioned.mapped.x - width / 2.0
    x2 = positioned.mapped.x + width / 2.0
    return (x1, positioned.y), (x2, positioned.y)


def _ribbon_endpoint_pairs(
    left: PositionedGene,
    right: PositionedGene,
) -> tuple[tuple[float, float], tuple[float, float], tuple[float, float], tuple[float, float]]:
    """返回 ribbon 端点对，倒位时反转右侧端点"""

    left_a, left_b = _gene_interval_points(left)
    right_a, right_b = _gene_interval_points(right)
    if left.mapped.display_strand != right.mapped.display_strand:
        right_a, right_b = right_b, right_a
    return left_a, left_b, right_a, right_b


def _draw_ribbon_link(
    ax: Axes,
    left: PositionedGene,
    right: PositionedGene,
    *,
    color: str,
    alpha: float,
    zorder: int,
) -> None:
    """使用基因区间端点绘制 JCVI 风格共线性 ribbon"""

    left_a, left_b, right_a, right_b = _ribbon_endpoint_pairs(left, right)
    verts, codes = _jcvi_shade_curve_path(left_a, left_b, right_a, right_b)
    ax.add_patch(
        PathPatch(
            MplPath(verts, codes),
            facecolor=color,
            edgecolor=color,
            lw=0,
            alpha=alpha,
            zorder=zorder,
            clip_on=False,
        )
    )


def _jcvi_shade_curve_path(
    left_a: tuple[float, float],
    left_b: tuple[float, float],
    right_a: tuple[float, float],
    right_b: tuple[float, float],
) -> tuple[list[tuple[float, float]], list[int]]:
    """返回与 ``jcvi.graphics.synteny.Shade`` 相同的曲线路径形状"""

    mid_y1 = (left_a[1] + right_a[1]) / 2.0
    mid_y2 = (left_b[1] + right_b[1]) / 2.0
    verts = [
        left_a,
        (left_a[0], mid_y1),
        (right_a[0], mid_y1),
        right_a,
        right_b,
        (right_b[0], mid_y2),
        (left_b[0], mid_y2),
        left_b,
        left_a,
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
    return verts, [int(code) for code in codes]


def _draw_target_legend(ax: Axes, entries: list[TargetLegendEntry], *, y_base: float = LEGEND_Y) -> None:
    """绘制底部图例，将高亮颜色映射到目标基因"""

    if not entries:
        return
    columns = min(6, len(entries))
    row_gap = 0.034
    x0 = AXIS_LEFT
    col_width = min(0.145, MAX_TRACK_WIDTH / max(1, columns))
    for index, entry in enumerate(entries):
        row = index // columns
        col = index % columns
        x = x0 + col * col_width
        y = y_base - row * row_gap
        ax.plot([x, x + 0.030], [y, y], color=entry.color, lw=2.4, solid_capstyle="round", zorder=12, clip_on=False)
        label = _display_accn(entry.gene_id)
        if entry.hidden_count:
            label = f"{label} +{entry.hidden_count}"
        ax.text(
            x + 0.036,
            y,
            label,
            fontsize=LEGEND_FONT_SIZE,
            ha="left",
            va="center",
            color="#374151",
            zorder=12,
            clip_on=False,
        )


def _percentile(values: list[float], fraction: float) -> float:
    """返回非空浮点列表的简单百分位数"""

    if not values:
        return 0.0
    ordered = sorted(values)
    index = int(round((len(ordered) - 1) * fraction))
    return ordered[index]


def _build_chromosome_color_map(chromosomes: list[str]) -> dict[str, str]:
    """在图内分配稳定的染色体颜色"""

    return {
        chromosome: _CHROMOSOME_COLOR_PALETTE[index % len(_CHROMOSOME_COLOR_PALETTE)]
        for index, chromosome in enumerate(chromosomes)
    }


def _draw_chromosome_legend(ax: Axes, chromosomes: list[str], color_map: dict[str, str]) -> None:
    """绘制紧凑的染色体颜色图例"""

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
    """从第一个非注释 block 行推断通用轨道名称"""

    with blocks_path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if line and not line.startswith("#"):
                return [f"Track {index + 1}" for index in range(len(line.split("\t")))]
    return ["Reference", "Subject"]


# endregion


# region 公共入口
def render_local_synteny(
    blocks_path: str | Path,
    bed_path: str | Path,
    output_path: str | Path,
    *,
    track_names: list[str] | None = None,
    target_gene_ids: list[str] | None = None,
    label_targets: bool = False,
    figsize: str = "",
    dpi: int = 900,
    fmt: str = "svg",
) -> Path:
    """渲染染色体感知的局部共线性图"""

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


# endregion
