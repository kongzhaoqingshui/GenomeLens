"""Native matplotlib renderer for local synteny figures.

This module provides a self-contained alternative to JCVI ``graphics.synteny``
for local synteny plots.  It directly consumes the same ``blocks`` + ``bed``
files but can render cross-chromosome target windows by splitting the reference
species into chromosome segments instead of compressing everything onto a
single horizontal track.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # noqa: E402
import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.patches import FancyBboxPatch, PathPatch
from matplotlib.path import Path as MplPath

# Default palette matches the existing GenomeLens track colours.
DEFAULT_TRACK_COLORS = ("#2f6f73", "#b85c38", "#5b8c5a", "#8c6bb1", "#c2914a", "#41699e")
HIGHLIGHT_COLOR = "#000000"
BAR_COLOR = "#1f77b4"
TICK_COLOR = "#333333"
LABEL_BG_COLOR = "#fff8dc"
LABEL_TEXT_COLOR = "#333333"
LINK_LW = 0.5
LINK_ALPHA = 0.6
LABEL_MARGIN_RIGHT = 0.94

# Visual layout constants (axes coordinates).
MAX_TRACK_WIDTH = 0.80
MAX_INTRA_GAP_WIDTH = 0.030
INTER_CHROM_GAP_WIDTH = 0.040
MIN_GENE_WIDTH = 0.0012
TRACK_BAR_HEIGHT = 0.010
TRACK_HEIGHT = 0.10
TRACK_GAP = 0.20
BREAK_MARK_WIDTH = 0.005
BREAK_MARK_HEIGHT = 0.018
SPECIES_IMAGE_SIZE = 0.045
LEGEND_Y = 0.04
LEGEND_SQUARE_SIZE = 0.018
LEGEND_FONT_SIZE = 6


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
    """A gene placed in the visual coordinate system of its track."""

    gene: GeneRecord
    x: float
    width: float


@dataclass
class ChromosomeSegment:
    """A contiguous chromosome region inside one track's window."""

    chromosome: str
    genes: list[MappedGene]
    start_bp: float
    end_bp: float
    visual_start: float
    visual_end: float
    has_compressed_gaps: bool = False

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


@dataclass
class RenderBlock:
    """One row of the blocks file, normalised for rendering."""

    query_gene: str
    subject_genes: list[str | None]
    highlighted: bool = False


@dataclass
class LocalSyntenyLayout:
    """Computed layout for a local synteny figure."""

    tracks: list[TrackWindow]
    block_rows: list[RenderBlock]
    target_gene_ids: set[str]
    figsize: tuple[float, float]
    max_track_width: float = MAX_TRACK_WIDTH


def _strip_highlight_prefix(value: str) -> tuple[bool, str]:
    """Return (is_highlighted, accn) splitting the ``r*`` prefix used by JCVI."""

    if "*" in value:
        prefix, body = value.split("*", 1)
        return prefix == "r", body.strip()
    return False, value.strip()


def _read_bed(path: Path) -> dict[str, GeneRecord]:
    """Read a BED file and map accn -> GeneRecord."""

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
    """Parse a blocks file into RenderBlock rows."""

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


# -----------------------------------------------------------------------------
# Scoped accn helpers
# -----------------------------------------------------------------------------


def _is_scoped(accn: str) -> bool:
    return "__" in accn and not accn.endswith("__")


def _scope_of(accn: str) -> tuple[str, str]:
    """Split ``species__gene`` into (species, gene)."""

    if "__" in accn:
        species, _, gene = accn.partition("__")
        return species, gene
    return "", accn


def _display_accn(accn: str) -> str:
    """Return the human-readable part of an accn."""

    return _scope_of(accn)[1]


def _format_bp_range(start_bp: float, end_bp: float) -> str:
    """Format a base-pair range like JCVI does (e.g. 0.00-21.32Mb)."""

    span = end_bp - start_bp
    if span >= 1_000_000:
        return f"{start_bp / 1_000_000:.2f}-{end_bp / 1_000_000:.2f}Mb"
    if span >= 1_000:
        return f"{start_bp / 1_000:.2f}-{end_bp / 1_000:.2f}kb"
    return f"{start_bp:.0f}-{end_bp:.0f}bp"


# -----------------------------------------------------------------------------
# Coordinate mapping with gap compression
# -----------------------------------------------------------------------------


def _build_track_window(
    name: str,
    index: int,
    color: str,
    genes: list[GeneRecord],
    scale: float,
) -> TrackWindow:
    """Build a TrackWindow with gap-compressed proportional coordinates.

    ``scale`` is a global visual-unit-per-bp factor.  Large intra-chromosomal
    gaps and all inter-chromosomal gaps are compressed so that the figure does
    not waste space on synteny-free regions.
    """

    # Preserve order of first appearance when multiple chromosomes are present.
    chrom_order: list[str] = []
    seen_chrom: set[str] = set()
    for gene in genes:
        if gene.chromosome not in seen_chrom:
            seen_chrom.add(gene.chromosome)
            chrom_order.append(gene.chromosome)

    by_chrom: dict[str, list[GeneRecord]] = {}
    for gene in genes:
        by_chrom.setdefault(gene.chromosome, []).append(gene)

    segments: list[ChromosomeSegment] = []
    all_mapped: list[MappedGene] = []
    x = 0.0

    for chrom in chrom_order:
        chrom_genes = sorted(by_chrom[chrom], key=lambda g: g.start)
        seg_start_bp = chrom_genes[0].start
        seg_end_bp = chrom_genes[-1].end
        seg_visual_start = x
        mapped_genes: list[MappedGene] = []
        has_compressed_gaps = False

        for i, gene in enumerate(chrom_genes):
            if i > 0:
                prev = chrom_genes[i - 1]
                gap_bp = gene.start - prev.end
                raw_gap = gap_bp * scale
                if raw_gap > MAX_INTRA_GAP_WIDTH or gap_bp > 1_000_000:
                    x += MAX_INTRA_GAP_WIDTH
                    has_compressed_gaps = True
                else:
                    x += raw_gap
            gene_width = max(MIN_GENE_WIDTH, gene.length_bp * scale)
            gene_x = x + gene_width / 2.0
            x += gene_width
            mapped = MappedGene(gene=gene, x=gene_x, width=gene_width)
            mapped_genes.append(mapped)
            all_mapped.append(mapped)

        seg_visual_end = x
        segments.append(
            ChromosomeSegment(
                chromosome=chrom,
                genes=mapped_genes,
                start_bp=seg_start_bp,
                end_bp=seg_end_bp,
                visual_start=seg_visual_start,
                visual_end=seg_visual_end,
                has_compressed_gaps=has_compressed_gaps,
            )
        )
        x += INTER_CHROM_GAP_WIDTH

    visual_width = max(0.0, x - INTER_CHROM_GAP_WIDTH)

    # Build a JCVI-style range label.  For a single chromosome show
    # "chrom 0.00-21.32Mb"; for multiple chromosomes list each range.
    if len(segments) == 1:
        seg = segments[0]
        range_label = f"{seg.chromosome} {_format_bp_range(seg.start_bp, seg.end_bp)}"
    else:
        range_label = " | ".join(f"{seg.chromosome} {_format_bp_range(seg.start_bp, seg.end_bp)}" for seg in segments)

    return TrackWindow(
        name=name,
        index=index,
        color=color,
        segments=segments,
        all_genes=all_mapped,
        visual_width=visual_width,
        range_label=range_label,
    )


def _compute_layout(
    blocks_path: Path,
    bed_path: Path,
    track_names: list[str],
    target_gene_ids: list[str],
    figsize: str = "",
    dpi: int = 300,
) -> LocalSyntenyLayout:
    """Build a layout from blocks + bed files."""

    genes = _read_bed(bed_path)
    block_rows = _read_blocks(blocks_path, len(track_names))

    # Collect genes per track.
    track_genes: list[list[GeneRecord]] = [[] for _ in track_names]
    for row in block_rows:
        ref_gene = genes.get(row.query_gene)
        if ref_gene is not None:
            track_genes[0].append(ref_gene)
        for subject_index, subject_accn in enumerate(row.subject_genes):
            if subject_accn is None:
                continue
            gene = genes.get(subject_accn)
            if gene is not None:
                track_genes[subject_index + 1].append(gene)

    # Determine a common scale from the largest raw genomic span.
    max_raw_span = 1.0
    for track_gene_list in track_genes:
        if not track_gene_list:
            continue
        chroms: dict[str, list[GeneRecord]] = {}
        for gene in track_gene_list:
            chroms.setdefault(gene.chromosome, []).append(gene)
        for chrom_gene_list in chroms.values():
            chrom_gene_list.sort(key=lambda g: g.start)
            span = chrom_gene_list[-1].end - chrom_gene_list[0].start
            max_raw_span = max(max_raw_span, span)
        # Also consider span across all chromosomes (with inter-chrom gaps).
        all_sorted = sorted(track_gene_list, key=lambda g: (g.chromosome, g.start))
        full_span = all_sorted[-1].end - all_sorted[0].start
        max_raw_span = max(max_raw_span, full_span)

    scale = MAX_TRACK_WIDTH / max_raw_span

    tracks = [
        _build_track_window(
            name=name,
            index=index,
            color=DEFAULT_TRACK_COLORS[index % len(DEFAULT_TRACK_COLORS)],
            genes=track_genes[index],
            scale=scale,
        )
        for index, name in enumerate(track_names)
    ]

    # Center each track horizontally within the common MAX_TRACK_WIDTH.
    for track in tracks:
        track.x_offset = (MAX_TRACK_WIDTH - track.visual_width) / 2.0

    # Auto-derive figure size if not provided.
    width, height = _derive_figsize(len(tracks), len(block_rows), figsize)

    return LocalSyntenyLayout(
        tracks=tracks,
        block_rows=block_rows,
        target_gene_ids=set(target_gene_ids),
        figsize=(width, height),
    )


def _derive_figsize(
    track_count: int,
    block_rows: int,
    figsize: str,
) -> tuple[float, float]:
    """Return a sensible (width, height) in inches."""

    if figsize:
        parts = figsize.split("x")
        if len(parts) == 2:
            try:
                return float(parts[0]), float(parts[1])
            except ValueError:
                pass

    # Compact publication-style canvas; width is fixed, height grows with tracks.
    width = 10.0
    height = max(4.0, 1.0 + track_count * 2.0)
    return width, height


# -----------------------------------------------------------------------------
# Drawing helpers
# -----------------------------------------------------------------------------


def _draw_break_marker(ax: Axes, x: float, y: float, color: str = "#999999") -> None:
    """Draw a small double-slash break marker on the chromosome bar."""

    dx = BREAK_MARK_WIDTH / 2.0
    dy = BREAK_MARK_HEIGHT / 2.0
    offset = dx * 0.7
    # Two parallel diagonal slashes (//).
    for ox in (-offset, offset):
        ax.plot(
            [x - dx + ox, x + dx + ox],
            [y - dy, y + dy],
            color=color,
            lw=0.8,
            zorder=5,
            solid_capstyle="round",
        )


def _abbreviate_track_name(name: str) -> str:
    """Produce a short species abbreviation for in-figure labels.

    Rules:
    * If the name is already short, return it unchanged.
    * Otherwise take the first alphabetic token and the first letter of each
      subsequent alphabetic token, preserving a trailing numeric suffix.
    """

    cleaned = name.strip().replace("_", " ").replace("-", " ").replace(".", " ")
    tokens = [t for t in cleaned.split() if t]
    if len(name) <= 12 or len(tokens) <= 1:
        return name
    abbr = tokens[0]
    for token in tokens[1:]:
        if token[0].isalpha():
            abbr += token[0]
    # If the last token is purely numeric, append it (e.g. "Chr1" -> "C1").
    if tokens[-1] and tokens[-1][0].isdigit():
        abbr = abbr.rstrip("0123456789") + tokens[-1]
    return abbr if len(abbr) <= 12 else abbr[:12]


def _estimate_label_box_width(text: str) -> float:
    """Return the axes-width of a rounded chromosome label box."""

    padding = 0.005
    return max(0.04, len(text) * 0.008 + padding * 2)


def _draw_chromosome_label_box(
    ax: Axes,
    text: str,
    box_left: float,
    y: float,
    fontsize: int = 7,
) -> float:
    """Draw a chromosome label in a rounded box; return the box width."""

    box_width = _estimate_label_box_width(text)
    box_height = 0.026
    box_bottom = y - box_height / 2.0

    box = FancyBboxPatch(
        (box_left, box_bottom),
        box_width,
        box_height,
        boxstyle="round,pad=0,rounding_size=0.003",
        facecolor=LABEL_BG_COLOR,
        edgecolor="#cccccc",
        lw=0.5,
        zorder=5,
        clip_on=False,
    )
    ax.add_patch(box)
    ax.text(
        box_left + box_width / 2.0,
        y,
        text,
        fontsize=fontsize,
        ha="center",
        va="center",
        color=LABEL_TEXT_COLOR,
        zorder=6,
        clip_on=False,
    )
    return box_width


def _draw_species_image_placeholder(ax: Axes, track: TrackWindow) -> None:
    """Draw a small rounded placeholder for a species image on the right."""

    size = SPECIES_IMAGE_SIZE
    x = LABEL_MARGIN_RIGHT + 0.02
    y = track.y
    box = FancyBboxPatch(
        (x, y - size / 2.0),
        size,
        size,
        boxstyle="round,pad=0,rounding_size=0.006",
        facecolor="#f5f5f5",
        edgecolor="#cccccc",
        lw=0.5,
        zorder=5,
        clip_on=False,
    )
    ax.add_patch(box)
    ax.text(
        x + size / 2.0,
        y,
        _abbreviate_track_name(track.name)[:4].rstrip("."),
        fontsize=5,
        ha="center",
        va="center",
        color="#666666",
        zorder=6,
        clip_on=False,
    )


def _draw_star(ax: Axes, x: float, y: float, color: str = HIGHLIGHT_COLOR, size: float = 0.018) -> None:
    """Draw a 5-point star marker at the target gene position."""

    # Matplotlib marker '*' is good enough; scale it by axes size.
    ax.plot(
        x,
        y,
        marker="*",
        markersize=size * 1000,  # rough scaling for axes coordinates
        markeredgecolor=color,
        markerfacecolor=color,
        zorder=7,
        clip_on=False,
    )


def _draw_track(
    ax: Axes,
    track: TrackWindow,
    target_gene_ids: set[str],
    label_targets: bool,
) -> dict[str, tuple[float, float]]:
    """Draw one track's chromosome bars, gene ticks and labels.

    Returns a mapping from gene accn to (x, y) centre coordinate in axes
    coordinates (i.e. already includes the track's x_offset).
    """

    y = track.y
    gene_positions: dict[str, tuple[float, float]] = {}

    for segment in track.segments:
        seg_left = track.x_offset + segment.visual_start
        seg_right = track.x_offset + segment.visual_end

        # Chromosome backbone as a rounded bar (pill shape).
        bar = FancyBboxPatch(
            (seg_left, y - TRACK_BAR_HEIGHT / 2.0),
            seg_right - seg_left,
            TRACK_BAR_HEIGHT,
            boxstyle=f"round,pad=0,rounding_size={TRACK_BAR_HEIGHT / 2.0}",
            facecolor=BAR_COLOR,
            edgecolor="none",
            zorder=3,
            clip_on=False,
        )
        ax.add_patch(bar)

        # Break marker at compressed intra-chromosomal gaps.
        if segment.has_compressed_gaps:
            prev_x = None
            for mapped in segment.genes:
                if prev_x is not None:
                    gap_width = mapped.x - mapped.width / 2 - prev_x
                    if gap_width >= MAX_INTRA_GAP_WIDTH * 0.95:
                        _draw_break_marker(ax, (prev_x + mapped.x - mapped.width / 2) / 2.0, y)
                prev_x = mapped.x + mapped.width / 2

        # Gene ticks.
        tick_top = y + 0.018
        tick_bottom = y - 0.018
        for mapped in segment.genes:
            x = track.x_offset + mapped.x
            ax.plot(
                [x, x],
                [tick_bottom, tick_top],
                color=TICK_COLOR,
                lw=0.5,
                alpha=0.7,
                zorder=4,
            )
            gene_positions[mapped.gene.accn] = (x, y)

            if mapped.gene.accn in target_gene_ids:
                _draw_star(ax, x, y)
                if label_targets:
                    ax.text(
                        x,
                        y + 0.045,
                        _display_accn(mapped.gene.accn),
                        fontsize=5,
                        ha="center",
                        va="bottom",
                        color=HIGHLIGHT_COLOR,
                        rotation=45,
                        rotation_mode="anchor",
                        clip_on=False,
                    )

        # Chromosome label.
        _draw_chromosome_label(ax, segment.chromosome, seg_left, y)

        # Small range label above the chromosome bar.
        range_text = _format_bp_range(segment.start_bp, segment.end_bp)
        ax.text(
            (seg_left + seg_right) / 2.0,
            y + 0.028,
            range_text,
            fontsize=6,
            ha="center",
            va="bottom",
            color="#666666",
            zorder=4,
            clip_on=False,
        )

    # Species image placeholder on the right side of the track.
    _draw_species_image_placeholder(ax, track)

    return gene_positions


def _draw_curve_link(
    ax: Axes,
    p1: tuple[float, float],
    p2: tuple[float, float],
    color: str,
    lw: float = LINK_LW,
    alpha: float = LINK_ALPHA,
) -> None:
    """Draw a thin curved link between two gene positions."""

    x1, y1 = p1
    x2, y2 = p2
    mid_y = (y1 + y2) / 2.0

    verts = [(x1, y1), (x1, mid_y), (x2, mid_y), (x2, y2)]
    codes = [MplPath.MOVETO, MplPath.CURVE4, MplPath.CURVE4, MplPath.CURVE4]
    path = MplPath(verts, codes)
    ax.add_patch(PathPatch(path, fill=False, edgecolor=color, lw=lw, alpha=alpha, zorder=1))


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


def _chromosome_color(chromosome: str, color_map: dict[str, str] | None = None) -> str:
    """Return a stable colour for a chromosome name.

    If ``color_map`` is supplied, the chromosome is looked up there so that
    colours are unique across the current figure.  Otherwise the name is hashed.
    """

    if color_map is not None:
        return color_map.get(chromosome, "#999999")
    idx = hash(chromosome) % len(_CHROMOSOME_COLOR_PALETTE)
    return _CHROMOSOME_COLOR_PALETTE[idx]


def _build_chromosome_color_map(chromosomes: list[str]) -> dict[str, str]:
    """Assign a unique palette colour to each chromosome in the figure."""

    return {chrom: _CHROMOSOME_COLOR_PALETTE[i % len(_CHROMOSOME_COLOR_PALETTE)] for i, chrom in enumerate(chromosomes)}


def _draw_chromosome_legend(ax: Axes, chromosomes: list[str], color_map: dict[str, str]) -> None:
    """Draw a horizontal chromosome colour legend below the tracks."""

    if not chromosomes:
        return
    entry_width = 0.12
    total_width = len(chromosomes) * entry_width
    start_x = (1.0 - total_width) / 2.0
    y = LEGEND_Y
    for index, chrom in enumerate(chromosomes):
        x = start_x + index * entry_width
        box = FancyBboxPatch(
            (x, y - LEGEND_SQUARE_SIZE / 2.0),
            LEGEND_SQUARE_SIZE,
            LEGEND_SQUARE_SIZE,
            boxstyle="round,pad=0,rounding_size=0.002",
            facecolor=_chromosome_color(chrom, color_map),
            edgecolor="#cccccc",
            lw=0.4,
            zorder=5,
            clip_on=False,
        )
        ax.add_patch(box)
        ax.text(
            x + LEGEND_SQUARE_SIZE + 0.004,
            y,
            chrom,
            fontsize=LEGEND_FONT_SIZE,
            ha="left",
            va="center",
            color="#333333",
            zorder=6,
            clip_on=False,
        )


# -----------------------------------------------------------------------------
# Public entry point
# -----------------------------------------------------------------------------


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
    """Render a local synteny figure directly with matplotlib.

    Parameters
    ----------
    blocks_path
        Path to the JCVI-style blocks file.
    bed_path
        Path to the merged BED file containing all genes.
    output_path
        Destination file path (extension should match ``fmt``).
    track_names
        Human-readable names for each column of ``blocks``.  If omitted, generic
        names are generated.
    target_gene_ids
        Genes to highlight in the reference track.
    label_targets
        Whether to draw text labels next to highlighted target genes.
    figsize
        Optional canvas size as ``"WxH"`` in inches.  Auto-derived if empty.
    dpi
        Rasterisation resolution for non-vector backends.
    fmt
        Output format: ``svg``, ``png``, ``pdf``, ``eps``, etc.

    Returns
    -------
    Path
        The written figure path.
    """

    blocks_path = Path(blocks_path).expanduser().resolve(strict=False)
    bed_path = Path(bed_path).expanduser().resolve(strict=False)
    output_path = Path(output_path).expanduser().resolve(strict=False)

    # Infer track names from the first blocks row if not provided.
    if track_names is None:
        with blocks_path.open("r", encoding="utf-8") as handle:
            for raw_line in handle:
                line = raw_line.strip()
                if line and not line.startswith("#"):
                    count = len(line.split("\t"))
                    track_names = [f"Track {i + 1}" for i in range(count)]
                    break
        if track_names is None:
            track_names = ["Reference", "Subject"]

    target_gene_ids = target_gene_ids or []
    layout = _compute_layout(
        blocks_path,
        bed_path,
        track_names,
        target_gene_ids,
        figsize=figsize,
        dpi=dpi,
    )

    fig, ax = plt.subplots(figsize=layout.figsize)
    ax.set_aspect("auto")
    ax.axis("off")

    # Vertically center the block of tracks.
    track_count = len(layout.tracks)
    total_height = track_count * TRACK_HEIGHT + (track_count - 1) * TRACK_GAP
    y_center = 0.5
    y_start = y_center + total_height / 2.0 - TRACK_HEIGHT / 2.0
    for index, track in enumerate(layout.tracks):
        track.y = y_start - index * (TRACK_HEIGHT + TRACK_GAP)

    # Draw tracks and collect gene positions.
    track_positions: list[dict[str, tuple[float, float]]] = []
    for track in layout.tracks:
        positions = _draw_track(ax, track, layout.target_gene_ids, label_targets)
        track_positions.append(positions)

    # Build quick gene -> MappedGene lookups for link colouring and widths.
    gene_maps = [{m.gene.accn: m for m in track.all_genes} for track in layout.tracks]

    # Build a deterministic chromosome -> colour map so every chromosome in this
    # figure gets a unique, reproducible colour.
    all_chromosomes = sorted({segment.chromosome for track in layout.tracks for segment in track.segments})
    chrom_color_map = _build_chromosome_color_map(all_chromosomes)

    # Draw links between adjacent tracks (chain style: 0-1, 1-2, ...).
    # Each link segment is coloured by the chromosome of the gene on the
    # lower/right-hand track, matching publication-style chromosome-coded links.
    for track_index in range(len(layout.tracks) - 1):
        left_positions = track_positions[track_index]
        right_positions = track_positions[track_index + 1]
        right_map = gene_maps[track_index + 1]

        for row in layout.block_rows:
            left_accn = (
                row.query_gene
                if track_index == 0
                else (row.subject_genes[track_index - 1] if track_index - 1 < len(row.subject_genes) else None)
            )
            right_accn = row.subject_genes[track_index] if track_index < len(row.subject_genes) else None
            if left_accn is None or right_accn is None:
                continue
            if left_accn not in left_positions or right_accn not in right_positions:
                continue
            right_mapped = right_map.get(right_accn)
            if right_mapped is None:
                link_color = "#999999"
            else:
                link_color = _chromosome_color(right_mapped.gene.chromosome, chrom_color_map)
            _draw_curve_link(
                ax,
                left_positions[left_accn],
                right_positions[right_accn],
                color=link_color,
            )

    # Chromosome colour legend.
    _draw_chromosome_legend(ax, all_chromosomes, chrom_color_map)

    ax.set_xlim(-0.25, 1.0)
    ax.set_ylim(0.0, 1.0)
    fig.subplots_adjust(left=0.16, right=LABEL_MARGIN_RIGHT + 0.06, top=0.96, bottom=0.10)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, format=fmt, dpi=dpi, bbox_inches=None, pad_inches=0.05)
    plt.close(fig)
    return output_path
