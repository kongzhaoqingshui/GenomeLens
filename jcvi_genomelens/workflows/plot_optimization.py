"""synteny(共线性图) 输入优化辅助函数"""

# region import
from __future__ import annotations

import math
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from jcvi_genomelens.manifest_models import WorkflowOptions

# endregion

EMPTY_BLOCK_VALUES = {"", "."}


@dataclass(frozen=True)
class SyntenyPlotInputs:
    """SyntenyPlotInputs(synteny 出图输入)：可选优化后的 JCVI 入参"""

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


# region blocks 裁切相关函数
def _strip_highlight_prefix(value: str) -> str:
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


def _count_block_rows(blocks_path: Path) -> int:
    count = 0
    with blocks_path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if line and not line.startswith("#"):
                count += 1
    return count


def _read_bed_gene_ids(bed_path: Path) -> set[str]:
    gene_ids: set[str] = set()
    with bed_path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) < 4:
                continue
            gene_ids.add(parts[3].strip())
    return gene_ids


def _read_layout_shape(layout_path: Path) -> tuple[int, list[_LayoutEdge]]:
    track_count = 0
    edges: list[_LayoutEdge] = []
    for raw_line in layout_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("e"):
            edge = _parse_layout_edge(line)
            if edge is not None:
                edges.append(edge)
            continue
        track_count += 1
    return track_count, edges


def _can_render_trimmed_blocks(blocks_path: Path, bed_path: Path, layout_path: Path) -> bool:
    gene_ids = _read_bed_gene_ids(bed_path)
    track_count, edges = _read_layout_shape(layout_path)
    if track_count == 0:
        return False

    columns_with_genes = [False] * track_count
    edge_pairs = {(edge.source, edge.target): False for edge in edges}
    block_rows = 0

    with blocks_path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue

            atoms = [part.strip() or "." for part in line.split("\t")]
            if len(atoms) < track_count:
                atoms.extend(["."] * (track_count - len(atoms)))
            elif len(atoms) > track_count:
                atoms = atoms[:track_count]

            block_rows += 1
            for index, atom in enumerate(atoms):
                gene_id = _strip_highlight_prefix(atom)
                if gene_id not in EMPTY_BLOCK_VALUES and gene_id in gene_ids:
                    columns_with_genes[index] = True

            for source, target in edge_pairs:
                source_gene = _strip_highlight_prefix(atoms[source])
                target_gene = _strip_highlight_prefix(atoms[target])
                if (
                    source_gene not in EMPTY_BLOCK_VALUES
                    and target_gene not in EMPTY_BLOCK_VALUES
                    and source_gene in gene_ids
                    and target_gene in gene_ids
                ):
                    edge_pairs[(source, target)] = True

    return block_rows > 0 and all(columns_with_genes) and all(edge_pairs.values())


def trim_cross_chromosome_blocks(blocks_path: Path, bed_path: Path, output_path: Path) -> tuple[Path, int]:
    """写出移除跨染色体基因行后的 blocks，并返回被裁掉的行数"""

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
                _strip_highlight_prefix(part.strip())
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


# region layout 重写相关函数
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
    """把同一源轨道发散出去的 layout 连线重写成链式连接"""

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


# region 图件尺寸推导
def _jcvi_figsize_dimension(value: float) -> int:
    """把尺寸向上取整到 vendored JCVI 能接受的整数 figsize"""

    return max(1, math.ceil(value))


def suggest_figsize(blocks_path: Path, layout_path: Path) -> str:
    """根据轨道数和可见 block 行数推导稳定的 JCVI figsize"""

    track_count = 0
    for raw_line in layout_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line and not line.startswith("#") and not line.startswith("e"):
            track_count += 1

    block_rows = _count_block_rows(blocks_path)

    width = _jcvi_figsize_dimension(min(18.0, max(8.0, 6.0 + block_rows * 0.08)))
    height = _jcvi_figsize_dimension(min(12.0, max(4.0, 2.4 + max(track_count, 2) * 1.25)))
    return f"{width}x{height}"


def suggest_karyotype_figsize(track_labels: list[str], edge_count: int) -> str:
    """根据轨道标签长度和边数量推导 karyotype figsize"""

    track_count = max(len(track_labels), 2)
    longest_label = max((len(label) for label in track_labels), default=0)

    width = _jcvi_figsize_dimension(min(22.0, max(10.0, 7.0 + edge_count * 0.5 + longest_label * 0.18)))
    height = _jcvi_figsize_dimension(min(16.0, max(6.0, 2.8 + track_count * 1.8)))
    return f"{width}x{height}"


# endregion


# region 对外编排函数
def prepare_synteny_plot_inputs(
    *,
    blocks: Path,
    bed: Path,
    layout: Path,
    root: Path,
    stem: str,
    options: WorkflowOptions,
) -> SyntenyPlotInputs:
    """为一次 JCVI `graphics.synteny` 调用准备可选优化后的输入"""

    root.mkdir(parents=True, exist_ok=True)
    active_blocks = blocks
    active_layout = layout
    artifacts: dict[str, object] = {}

    if options.trim_cross_chromosome_blocks:
        trimmed_blocks, trimmed = trim_cross_chromosome_blocks(
            active_blocks,
            bed,
            root / f"{stem}.trimmed.blocks",
        )
        artifacts["trimmed_blocks"] = str(trimmed_blocks)
        artifacts["trimmed_cross_chromosome_block_rows"] = trimmed
        if not _can_render_trimmed_blocks(trimmed_blocks, bed, layout):
            # 更保守的策略：裁切结果对 JCVI 不再可渲染时，回退到原始 blocks
            artifacts["trimmed_blocks_fallback"] = "original_blocks"
        else:
            active_blocks = trimmed_blocks

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
    """把准备好的优化输入复制到稳定的产物文件名"""

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
