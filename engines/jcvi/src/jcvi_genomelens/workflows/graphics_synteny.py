"""真实 JCVI `graphics.synteny` workflow(工作流)"""

# region import
from __future__ import annotations

from pathlib import Path

from jcvi.graphics.synteny import main as jcvi_graphics_synteny
from jcvi_genomelens.manifest_models import EngineRunManifest
from jcvi_genomelens.runtime.command_runner import CommandAudit, run_python_step
from jcvi_genomelens.workflows.common import _assert_ok
from jcvi_genomelens.workflows.graphics_dotplot import draw_dotplots
from jcvi_genomelens.workflows.mcscan_pairwise import run as run_pairwise
from jcvi_genomelens.workflows.plot_optimization import prepare_synteny_plot_inputs

# endregion


def _figure_options(manifest: EngineRunManifest, fmt: str, figsize: str) -> list[str]:
    args: list[str] = []
    if figsize:
        args.extend(["--figsize", figsize])
    if manifest.options.dpi:
        args.extend(["--dpi", str(manifest.options.dpi)])
    args.extend(["--format", fmt, "--notex"])
    if manifest.options.glyphstyle:
        args.extend(["--glyphstyle", manifest.options.glyphstyle])
    if manifest.options.glyphcolor:
        args.extend(["--glyphcolor", manifest.options.glyphcolor])
    if manifest.options.shadestyle:
        args.extend(["--shadestyle", manifest.options.shadestyle])
    return args


def run(manifest: EngineRunManifest, outdir: str | Path) -> tuple[list[CommandAudit], dict[str, object]]:
    """运行真实 pairwise MCscan(成对 MCscan) 制品，并绘制真实 JCVI synteny figure(共线性图)"""

    # 先复用 pairwise 主流程产出 anchors/blocks/layout，再叠加 dotplot 和 synteny 图。
    commands, artifacts = run_pairwise(manifest, outdir)
    root = Path(outdir).expanduser().resolve(strict=False)
    formats = manifest.options.formats or ["png"]
    figures: list[str] = []
    dotplot_commands, dotplot_figures = draw_dotplots(manifest, root, artifacts)
    commands.extend(dotplot_commands)
    figures.extend(dotplot_figures)
    plot_inputs = prepare_synteny_plot_inputs(
        blocks=Path(str(artifacts["blocks"])),
        bed=Path(str(artifacts["merged_bed"])),
        layout=Path(str(artifacts["layout"])),
        root=root,
        stem="synteny.optimized",
        options=manifest.options,
    )
    for fmt in formats:
        output_prefix = root / "synteny"
        command = run_python_step(
            "jcvi.graphics.synteny",
            jcvi_graphics_synteny,
            [
                str(plot_inputs.blocks),
                str(plot_inputs.bed),
                str(plot_inputs.layout),
                *_figure_options(manifest, fmt, plot_inputs.figsize),
                "--outputprefix",
                str(output_prefix),
            ],
            cwd=root,
        )
        commands.append(command)
        _assert_ok(command)
        figure = Path(f"{output_prefix}.{fmt}")
        if not figure.is_file() or figure.stat().st_size == 0:
            raise RuntimeError(f"JCVI synteny figure was not created: {figure}")
        figures.append(str(figure))
    # `figures` 是统一公开入口，细分列表则给 shell/GUI 做更精细展示。
    artifacts["figures"] = figures
    artifacts["dotplot_figures"] = dotplot_figures
    artifacts["synteny_figures"] = [str(root / f"synteny.{fmt}") for fmt in formats]
    artifacts.update(plot_inputs.artifacts)
    return commands, artifacts
