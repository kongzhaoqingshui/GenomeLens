"""真实 JCVI `graphics.synteny` workflow(工作流)"""

# region import
from __future__ import annotations

from pathlib import Path

from jcvi.graphics.synteny import main as jcvi_graphics_synteny
from jcvi_genomelens.manifest.models import EngineRunManifest
from jcvi_genomelens.runtime.command_runner import CommandAudit, run_python_step
from jcvi_genomelens.workflows.common import _assert_ok, build_figure_options, close_matplotlib_figures
from jcvi_genomelens.workflows.graphics.dotplot import draw_dotplots
from jcvi_genomelens.workflows.graphics.plot_optimization import prepare_synteny_plot_inputs
from jcvi_genomelens.workflows.pairwise.artifact_reuse import ensure_pairwise_artifacts
from jcvi_genomelens.workflows.pairwise.mcscan import _write_default_layout

# endregion


def run(manifest: EngineRunManifest, outdir: str | Path) -> tuple[list[CommandAudit], dict[str, object]]:
    """运行真实 pairwise MCscan(成对 MCscan) 制品，并绘制真实 JCVI synteny figure(共线性图)"""

    # 复用上游 pairwise 产出的 anchors/blocks/layout（缺产物即报错），再叠加 dotplot 和 synteny 图
    commands, artifacts = ensure_pairwise_artifacts(
        manifest,
        outdir,
        required_fields=("blocks",),
        ensure_merged_bed=True,
    )
    root = Path(outdir).expanduser().resolve(strict=False)
    if "layout" not in artifacts:
        if manifest.query is None or manifest.subject is None:
            raise ValueError("graphics_synteny requires query and subject species")
        layout = _write_default_layout(root / "synteny.layout", manifest.query.name, manifest.subject.name)
        artifacts["layout"] = str(layout)
    formats = manifest.options.formats or ["svg"]
    figures: list[str] = []
    dotplot_figures: list[str] = []
    if "anchors" in artifacts:
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
        close_matplotlib_figures()
        try:
            command = run_python_step(
                "jcvi.graphics.synteny",
                jcvi_graphics_synteny,
                [
                    str(plot_inputs.blocks),
                    str(plot_inputs.bed),
                    str(plot_inputs.layout),
                    *build_figure_options(manifest.options, fmt, plot_inputs.figsize),
                    "--outputprefix",
                    str(output_prefix),
                ],
                cwd=root,
            )
        finally:
            close_matplotlib_figures()
        commands.append(command)
        _assert_ok(command)
        figure = Path(f"{output_prefix}.{fmt}")
        if not figure.is_file() or figure.stat().st_size == 0:
            raise RuntimeError(f"JCVI synteny figure was not created: {figure}")
        figures.append(str(figure))
    # `figures` 是统一公开入口，细分列表则给 shell/GUI 做更精细展示
    artifacts["figures"] = figures
    artifacts["dotplot_figures"] = dotplot_figures
    artifacts["synteny_figures"] = [str(root / f"synteny.{fmt}") for fmt in formats]
    artifacts.update(plot_inputs.artifacts)
    return commands, artifacts
