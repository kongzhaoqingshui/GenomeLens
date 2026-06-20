"""Real JCVI graphics.karyotype global multi-species workflow."""

from __future__ import annotations

from pathlib import Path

from jcvi_genomelens.manifest_models import EngineEdge, EngineRunManifest, EngineTrack
from jcvi_genomelens.runtime.command_runner import CommandAudit, run_python_step
from jcvi_genomelens.workflows.common import _assert_ok
from jcvi_genomelens.workflows.karyotype_support import format_track_row, select_karyotype_renderer
from jcvi_genomelens.workflows.plot_optimization import suggest_karyotype_figsize

_TRACK_COLORS = ("#2f6f73", "#b85c38", "#5b8c5a", "#8c6bb1", "#c2914a", "#41699e")


def _seqids_from_bed(path: Path) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip() or line.startswith("#"):
                continue
            seqid = line.split("\t", 1)[0].strip()
            if seqid and seqid not in seen:
                seen.add(seqid)
                ordered.append(seqid)
    if not ordered:
        raise RuntimeError(f"No seqids found in BED: {path}")
    return ordered


def _write_global_seqids(path: Path, tracks: list[EngineTrack]) -> Path:
    lines = [",".join(_seqids_from_bed(track.bed)) for track in tracks]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _display_tracks_and_edges(
    manifest: EngineRunManifest,
    *,
    allow_rewrite: bool,
) -> tuple[list[EngineTrack], list[EngineEdge], int, list[str]]:
    """Conservatively reorder tracks and remap edges for display only."""

    tracks = list(manifest.tracks)
    edges = list(manifest.edges)
    track_order = [track.name for track in tracks]
    if not allow_rewrite or not manifest.options.rewrite_layout_links or len(tracks) < 3 or len(edges) < 2:
        return tracks, edges, 0, track_order

    degrees = [0] * len(tracks)
    for edge in edges:
        degrees[edge.i] += 1
        degrees[edge.j] += 1

    hub_index = max(range(len(tracks)), key=lambda index: (degrees[index], -index))
    other_indexes = [index for index in range(len(tracks)) if index != hub_index]
    split = max(1, len(other_indexes) // 2)
    order = [*other_indexes[:split], hub_index, *other_indexes[split:]]
    if order == list(range(len(tracks))):
        return tracks, edges, 0, track_order

    remapped_tracks = [tracks[index] for index in order]
    index_map = {old: new for new, old in enumerate(order)}
    remapped_edges = [
        EngineEdge(i=i, j=j, simple=edge.simple)
        for edge in edges
        for i, j in [sorted((index_map[edge.i], index_map[edge.j]))]
    ]
    return remapped_tracks, remapped_edges, len(edges), [track.name for track in remapped_tracks]


def _write_global_layout(
    path: Path,
    tracks: list[EngineTrack],
    edges: list[EngineEdge],
    *,
    fix_label_overlap: bool,
) -> Path:
    header = (
        "# y, xstart, xend, rotation, color, label, va, bed, label_va"
        if fix_label_overlap
        else "# y, xstart, xend, rotation, color, label, va, bed"
    )
    lines = [header]
    count = len(tracks)
    top, bottom = 0.85, 0.15
    for index, track in enumerate(tracks):
        y = (top + bottom) / 2 if count == 1 else top - (top - bottom) * index / (count - 1)
        color = _TRACK_COLORS[index % len(_TRACK_COLORS)]
        is_upper = index <= (count - 1) // 2
        va = "bottom" if fix_label_overlap and is_upper else "top"
        lines.append(format_track_row(y, color, track.name, va, track.bed, fix_label_overlap=fix_label_overlap))
    lines.append("# edges")
    for edge in edges:
        lines.append(f"e, {edge.i}, {edge.j}, {edge.simple}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def run(manifest: EngineRunManifest, outdir: str | Path) -> tuple[list[CommandAudit], dict[str, object]]:
    """Render the aggregated multi-species karyotype figure."""

    root = Path(outdir).expanduser().resolve(strict=False)
    root.mkdir(parents=True, exist_ok=True)
    karyotype_main, renderer_variant = select_karyotype_renderer(manifest.options.fix_karyotype_label_overlap)
    display_tracks, display_edges, rewritten_edges, track_order = _display_tracks_and_edges(
        manifest,
        allow_rewrite=manifest.options.layout is None and manifest.options.seqids is None,
    )

    seqids = (
        manifest.options.seqids
        if manifest.options.seqids
        else _write_global_seqids(root / "karyotype_global.seqids", display_tracks)
    )
    layout = (
        manifest.options.layout
        if manifest.options.layout
        else _write_global_layout(
            root / "karyotype_global.layout",
            display_tracks,
            display_edges,
            fix_label_overlap=manifest.options.fix_karyotype_label_overlap,
        )
    )
    figsize = manifest.options.figsize
    artifacts: dict[str, object] = {
        "rewritten_layout_edges": rewritten_edges,
        "rewritten_track_order": track_order,
        "karyotype_renderer_variant": renderer_variant,
        "karyotype_label_overlap_fix": manifest.options.fix_karyotype_label_overlap,
    }
    if manifest.options.optimize_figsize and not figsize:
        figsize = suggest_karyotype_figsize(track_order, len(display_edges))
        artifacts["optimized_figsize"] = figsize

    commands: list[CommandAudit] = []
    figures: list[str] = []
    formats = manifest.options.formats or ["png"]
    for fmt in formats:
        figure = root / f"karyotype_global.{fmt}"
        argv = [str(seqids), str(layout), "--format", fmt, "--notex"]
        if figsize:
            argv.extend(["--figsize", figsize])
        if manifest.options.dpi > 0:
            argv.extend(["--dpi", str(manifest.options.dpi)])
        argv.extend(["-o", str(figure)])
        command = run_python_step("jcvi.graphics.karyotype", karyotype_main, argv, cwd=root)
        commands.append(command)
        _assert_ok(command)
        if not figure.is_file() or figure.stat().st_size == 0:
            raise RuntimeError(f"JCVI global karyotype figure was not created: {figure}")
        figures.append(str(figure))

    artifacts.update(
        {
            "figures": figures,
            "global_karyotype_figures": figures,
            "global_karyotype_seqids": str(seqids),
            "global_karyotype_layout": str(layout),
            "track_count": len(display_tracks),
            "edge_count": len(display_edges),
            "simplified_fallback": False,
            "backend": "jcvi.graphics.karyotype",
        }
    )
    return commands, artifacts
