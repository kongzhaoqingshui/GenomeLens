"""已计算局部 blocks 的多物种共线性总图 workflow"""

# region import
from __future__ import annotations

from pathlib import Path

from jcvi.graphics.synteny import main as jcvi_graphics_synteny
from jcvi_genomelens.manifest_models import EngineRunManifest
from jcvi_genomelens.runtime.command_runner import CommandAudit, run_python_step
from jcvi_genomelens.workflows.common import _assert_ok
from jcvi_genomelens.workflows.local_synteny import _figure_options

# endregion


_TRACK_COLORS = ("#2f6f73", "#b85c38", "#5b8c5a", "#8c6bb1", "#c2914a", "#41699e")


def _write_multi_local_layout(path: Path, manifest: EngineRunManifest) -> Path:
    """写出多轨 local synteny layout(布局)"""

    count = len(manifest.tracks)
    top, bottom = 0.82, 0.18
    lines = ["# x, y, rotation, ha, va, color, ratio, label"]
    for index, track in enumerate(manifest.tracks):
        y = (top + bottom) / 2 if count == 1 else top - (top - bottom) * index / (count - 1)
        color = _TRACK_COLORS[index % len(_TRACK_COLORS)]
        va = "top" if index == 0 else "bottom"
        lines.append(f"0.50, {y:.4f}, 0, center, {va}, {color}, 1, {track.name}")

    for index in range(1, count):
        # 多物种局部图以参考物种为中心，连接参考轨道与每个目标轨道。
        lines.append(f"e, 0, {index}, #c8c8c8")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def run(manifest: EngineRunManifest, outdir: str | Path) -> tuple[list[CommandAudit], dict[str, object]]:
    """把 shell 聚合好的多物种局部 blocks 渲染成总图"""

    if manifest.blocks is None or manifest.bed is None:
        raise ValueError("local_synteny_multi requires precomputed blocks and bed")

    root = Path(outdir).expanduser().resolve(strict=False)
    root.mkdir(parents=True, exist_ok=True)

    layout = (
        manifest.options.layout
        if manifest.options.layout
        else _write_multi_local_layout(root / "local_multi.layout", manifest)
    )
    formats = manifest.options.formats or ["png"]
    plot_options = {
        "figsize": manifest.options.figsize,
        "dpi": manifest.options.dpi,
        "glyphstyle": manifest.options.glyphstyle,
        "glyphcolor": manifest.options.glyphcolor,
        "shadestyle": manifest.options.shadestyle,
        "label_targets": manifest.options.label_targets,
        "target_gene_ids": manifest.options.target_gene_ids,
    }

    commands: list[CommandAudit] = []
    figures: list[str] = []
    output_prefix = root / "local_synteny_multi"
    for fmt in formats:
        command = run_python_step(
            "jcvi.graphics.synteny",
            jcvi_graphics_synteny,
            [
                str(manifest.blocks),
                str(manifest.bed),
                str(layout),
                *_figure_options(plot_options, fmt),
                "--outputprefix",
                str(output_prefix),
            ],
            cwd=root,
        )
        commands.append(command)
        _assert_ok(command)
        figure = Path(f"{output_prefix}.{fmt}")
        if not figure.is_file() or figure.stat().st_size == 0:
            raise RuntimeError(f"JCVI multi-species local synteny figure was not created: {figure}")
        figures.append(str(figure))

    return commands, {
        "figures": figures,
        "multi_species_local_figures": figures,
        "multi_species_local_blocks": str(manifest.blocks),
        "multi_species_local_bed": str(manifest.bed),
        "multi_species_local_layout": str(layout),
        "track_count": len(manifest.tracks),
        "target_count": len(manifest.options.target_gene_ids),
        "simplified_fallback": False,
        "backend": "jcvi.graphics.synteny",
    }
