"""Optional synteny plot input optimization helpers"""

# region import
from __future__ import annotations

import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from jcvi_genomelens.manifest_models import WorkflowOptions

# endregion

EMPTY_BLOCK_VALUES = {"", "."}


@dataclass(frozen=True)
class SyntenyPlotInputs:
    """Resolved JCVI synteny plotting inputs after optional optimization"""

    blocks: Path
    bed: Path
    layout: Path
    figsize: str
    artifacts: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class _LayoutEdge:
    source: int
    target: int
    color: str = ""
    samearc: str = ""


# region blocks trimming
def _split_block_highlight(value: str) -> str:
    if "*" not in value:
        return value
    return value.split("*", 1)[1]


def _read_gene_chromosomes(bed_path: Path) -> dict[str, str]:
    mapping: dict[str, str] = {}
    with bed_path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) < 4:
                continue
            mapping[parts[3].strip()] = parts[0].strip()
    return mapping


def _normal_chromosome(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def trim_cross_chromosome_blocks(blocks_path: Path, bed_path: Path, output_path: Path) -> tuple[Path, int]:
    """Write a blocks file without rows linking genes from different chromosomes"""

    gene_chromosomes = _read_gene_chromosomes(bed_path)
    kept: list[str] = []
    trimmed = 0

    with blocks_path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.rstrip("\n\r")
            if not line or line.startswith("#"):
                kept.append(line)
                continue

            genes = [
                _split_block_highlight(part.strip())
                for part in line.split("\t")
                if part.strip() not in EMPTY_BLOCK_VALUES
            ]
            chromosomes = {
                _normal_chromosome(gene_chromosomes[gene])
                for gene in genes
                if gene in gene_chromosomes and gene_chromosomes[gene]
            }
            if len(chromosomes) > 1:
                trimmed += 1
                continue
            kept.append(line)

    output_path.write_text("\n".join(kept) + ("\n" if kept else ""), encoding="utf-8")
    return output_path, trimmed


# endregion


# region layout rewriting
def _parse_layout_edge(line: str) -> _LayoutEdge | None:
    parts = [part.strip() for part in line.split(",")]
    if len(parts) < 3 or parts[0] != "e":
        return None
    color = parts[3] if len(parts) >= 4 else ""
    samearc = parts[4] if len(parts) >= 5 else ""
    return _LayoutEdge(int(parts[1]), int(parts[2]), color, samearc)


def _format_layout_edge(edge: _LayoutEdge) -> str:
    parts = ["e", str(edge.source), str(edge.target)]
    if edge.color or edge.samearc:
        parts.append(edge.color)
    if edge.samearc:
        parts.append(edge.samearc)
    return ", ".join(parts)


def rewrite_layout_links(layout_path: Path, output_path: Path) -> tuple[Path, int]:
    """Rewrite same-source layout edges into track-to-track chains"""

    passthrough: list[str] = []
    grouped: dict[int, list[_LayoutEdge]] = {}
    single_edges: list[_LayoutEdge] = []

    for raw_line in layout_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or not line.startswith("e"):
            passthrough.append(raw_line)
            continue
        edge = _parse_layout_edge(line)
        if edge is None:
            passthrough.append(raw_line)
            continue
        grouped.setdefault(edge.source, []).append(edge)

    rewritten: list[_LayoutEdge] = []
    changed = 0
    for source, edges in grouped.items():
        if len(edges) == 1:
            single_edges.append(edges[0])
            continue

        ordered = sorted(edges, key=lambda item: item.target)
        current = source
        for edge in ordered:
            if edge.target == current:
                continue
            rewritten.append(_LayoutEdge(current, edge.target, edge.color, edge.samearc))
            current = edge.target
        changed += len(edges)

    output_edges = _dedupe_edges([*single_edges, *rewritten])
    content = [*passthrough, *(_format_layout_edge(edge) for edge in output_edges)]
    output_path.write_text("\n".join(content) + "\n", encoding="utf-8")
    return output_path, changed


def _dedupe_edges(edges: list[_LayoutEdge]) -> list[_LayoutEdge]:
    seen: set[tuple[int, int, str, str]] = set()
    unique: list[_LayoutEdge] = []
    for edge in edges:
        key = (edge.source, edge.target, edge.color, edge.samearc)
        if key in seen:
            continue
        seen.add(key)
        unique.append(edge)
    return unique


# endregion


# region figure sizing
def suggest_figsize(blocks_path: Path, layout_path: Path) -> str:
    """Suggest a stable JCVI figsize from track count and visible block rows"""

    track_count = 0
    for raw_line in layout_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line and not line.startswith("#") and not line.startswith("e"):
            track_count += 1

    block_rows = 0
    with blocks_path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if line and not line.startswith("#"):
                block_rows += 1

    width = min(18.0, max(8.0, 6.0 + block_rows * 0.08))
    height = min(12.0, max(4.0, 2.4 + max(track_count, 2) * 1.25))
    return f"{width:g}x{height:g}"


# endregion


# region public orchestration
def prepare_synteny_plot_inputs(
    *,
    blocks: Path,
    bed: Path,
    layout: Path,
    root: Path,
    stem: str,
    options: WorkflowOptions,
) -> SyntenyPlotInputs:
    """Prepare optional optimized inputs for a JCVI graphics.synteny call"""

    root.mkdir(parents=True, exist_ok=True)
    active_blocks = blocks
    active_layout = layout
    artifacts: dict[str, object] = {}

    if options.trim_cross_chromosome_blocks:
        active_blocks, trimmed = trim_cross_chromosome_blocks(
            active_blocks,
            bed,
            root / f"{stem}.trimmed.blocks",
        )
        artifacts["trimmed_blocks"] = str(active_blocks)
        artifacts["trimmed_cross_chromosome_block_rows"] = trimmed

    if options.rewrite_layout_links:
        active_layout, rewritten = rewrite_layout_links(
            active_layout,
            root / f"{stem}.rewritten.layout",
        )
        artifacts["rewritten_layout"] = str(active_layout)
        artifacts["rewritten_layout_edges"] = rewritten

    figsize = options.figsize
    if options.optimize_figsize and not figsize:
        figsize = suggest_figsize(active_blocks, active_layout)
        artifacts["optimized_figsize"] = figsize

    return SyntenyPlotInputs(
        blocks=active_blocks,
        bed=bed,
        layout=active_layout,
        figsize=figsize,
        artifacts=artifacts,
    )


def copy_plot_inputs(inputs: SyntenyPlotInputs, *, blocks: Path, layout: Path) -> SyntenyPlotInputs:
    """Copy prepared inputs to stable artifact names"""

    artifacts = dict(inputs.artifacts)
    final_blocks = inputs.blocks
    final_layout = inputs.layout
    if inputs.blocks != blocks:
        shutil.copy2(inputs.blocks, blocks)
        final_blocks = blocks
        artifacts["optimized_blocks"] = str(blocks)
    if inputs.layout != layout:
        shutil.copy2(inputs.layout, layout)
        final_layout = layout
        artifacts["optimized_layout"] = str(layout)

    return SyntenyPlotInputs(
        blocks=final_blocks,
        bed=inputs.bed,
        layout=final_layout,
        figsize=inputs.figsize,
        artifacts=artifacts,
    )


# endregion
