"""已计算局部 blocks 的多物种共线性总图 workflow"""

# region import
from __future__ import annotations

from pathlib import Path

from jcvi_genomelens.graphics.local_synteny import render_local_synteny
from jcvi_genomelens.manifest.models import EngineRunManifest
from jcvi_genomelens.runtime.command_runner import CommandAudit, run_python_step
from jcvi_genomelens.workflows.common import _assert_ok, build_figure_options, close_matplotlib_figures
from jcvi_genomelens.workflows.graphics.plot_optimization import copy_plot_inputs, prepare_synteny_plot_inputs
from jcvi_genomelens.workflows.local_synteny.single import _layout_label_fields

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
        default_va = "top" if index == 0 else "bottom"
        ha, va, display_label, fontsize = _layout_label_fields(track.name, default_va)
        lines.append(f"0.50, {y:.4f}, 0, {ha}, {va}, {color}, 1, {display_label}, {fontsize}")

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

    use_native = manifest.options.use_native_local_synteny_renderer

    if manifest.options.layout is None and not use_native:
        layout = _write_multi_local_layout(root / "local_multi.layout", manifest)
        plot_inputs = copy_plot_inputs(
            prepare_synteny_plot_inputs(
                blocks=manifest.blocks,
                bed=manifest.bed,
                layout=layout,
                root=root,
                stem="local_multi",
                options=manifest.options,
            ),
            blocks=manifest.blocks,
            layout=layout,
        )
    elif manifest.options.layout is not None and not use_native:
        plot_inputs = prepare_synteny_plot_inputs(
            blocks=manifest.blocks,
            bed=manifest.bed,
            layout=manifest.options.layout,
            root=root,
            stem="local_multi",
            options=manifest.options,
        )
    else:
        # Native renderer does not need a JCVI layout for drawing, but the
        # figsize optimization helper still expects one to count tracks.
        layout = _write_multi_local_layout(root / "local_multi.layout", manifest)
        plot_inputs = prepare_synteny_plot_inputs(
            blocks=manifest.blocks,
            bed=manifest.bed,
            layout=layout,
            root=root,
            stem="local_multi",
            options=manifest.options,
        )

    formats = manifest.options.formats or ["svg"]
    plot_options = {
        "figsize": plot_inputs.figsize,
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
        figure = Path(f"{output_prefix}.{fmt}")

        if use_native:
            track_names = [track.name for track in manifest.tracks]
            argv = [
                str(plot_inputs.blocks),
                str(plot_inputs.bed),
                str(figure),
                "--track-names",
                *track_names,
                "--target-gene-ids",
                *manifest.options.target_gene_ids,
            ]
            if plot_inputs.figsize:
                argv.extend(["--figsize", plot_inputs.figsize])
            close_matplotlib_figures()
            try:
                render_local_synteny(
                    blocks_path=plot_inputs.blocks,
                    bed_path=plot_inputs.bed,
                    output_path=figure,
                    track_names=track_names,
                    target_gene_ids=list(manifest.options.target_gene_ids),
                    label_targets=bool(plot_options.get("label_targets")),
                    figsize=plot_inputs.figsize,
                    dpi=manifest.options.dpi,
                    fmt=fmt,
                )
            finally:
                close_matplotlib_figures()
            command = CommandAudit(
                name="local_synteny_renderer",
                argv=argv,
                returncode=0,
                cwd=str(root),
            )
        else:
            from jcvi.graphics.synteny import main as jcvi_graphics_synteny

            figure_args = build_figure_options(manifest.options, fmt, plot_inputs.figsize)
            if manifest.options.label_targets and manifest.options.target_gene_ids:
                figure_args.extend(["--genelabels", ",".join(manifest.options.target_gene_ids)])
            close_matplotlib_figures()
            try:
                command = run_python_step(
                    "jcvi.graphics.synteny",
                    jcvi_graphics_synteny,
                    [
                        str(plot_inputs.blocks),
                        str(plot_inputs.bed),
                        str(plot_inputs.layout),
                        *figure_args,
                        "--outputprefix",
                        str(output_prefix),
                    ],
                    cwd=root,
                )
            finally:
                close_matplotlib_figures()

        commands.append(command)
        _assert_ok(command)
        if not figure.is_file() or figure.stat().st_size == 0:
            raise RuntimeError(f"Multi-species local synteny figure was not created: {figure}")
        figures.append(str(figure))

    artifacts = {
        "figures": figures,
        "multi_species_local_figures": figures,
        "multi_species_local_blocks": str(plot_inputs.blocks),
        "multi_species_local_bed": str(plot_inputs.bed),
        "multi_species_local_layout": str(plot_inputs.layout),
        "track_count": len(manifest.tracks),
        "target_count": len(manifest.options.target_gene_ids),
        "simplified_fallback": False,
        "backend": "local_synteny_renderer" if use_native else "jcvi.graphics.synteny",
    }
    artifacts.update(plot_inputs.artifacts)
    artifacts.setdefault("rewritten_layout_edges", 0)
    return commands, artifacts
