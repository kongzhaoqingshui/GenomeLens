"""真实 JCVI `graphics.heatmap` workflow(工作流)"""

# region import
from __future__ import annotations

import shutil
import sys
from pathlib import Path

from jcvi.graphics import heatmap as jcvi_graphics_heatmap
from jcvi_genomelens.manifest.models import EngineRunManifest
from jcvi_genomelens.runtime.command_runner import CommandAudit, run_python_step
from jcvi_genomelens.workflows.common import _assert_ok, close_matplotlib_figures

# endregion


def _run_heatmap_main(args: list[str]) -> object:
    """以进程内方式运行 `jcvi.graphics.heatmap.main()`"""

    original_argv = sys.argv[:]
    try:
        close_matplotlib_figures()
        sys.argv = ["jcvi.graphics.heatmap", *args]
        return jcvi_graphics_heatmap.main()
    finally:
        close_matplotlib_figures()
        sys.argv = original_argv


def _stage_input(source: Path, target: Path) -> Path:
    """把输入文件复制到工作目录，避免原地写图污染源目录"""

    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    return target


def run(manifest: EngineRunManifest, outdir: str | Path) -> tuple[list[CommandAudit], dict[str, object]]:
    """运行真实 JCVI heatmap(热图) 绘图"""

    if manifest.matrix is None:
        raise ValueError("graphics_heatmap requires a matrix input")

    root = Path(outdir).expanduser().resolve(strict=False)
    root.mkdir(parents=True, exist_ok=True)
    staged_matrix = _stage_input(manifest.matrix, root / "heatmap.csv")
    staged_rowgroups: Path | None = None
    if manifest.options.rowgroups is not None:
        staged_rowgroups = _stage_input(manifest.options.rowgroups, root / "heatmap.rowgroups.tsv")

    formats = manifest.options.formats or ["svg"]
    cmap = manifest.options.cmap or "jet"
    figures: list[str] = []
    commands: list[CommandAudit] = []
    for fmt in formats:
        argv: list[str] = []
        if manifest.options.groups:
            argv.append("--groups")
        if staged_rowgroups is not None:
            argv.extend(["--rowgroups", staged_rowgroups.name])
        if manifest.options.horizontalbar:
            argv.append("--horizontalbar")
        if manifest.options.figsize:
            argv.extend(["--figsize", manifest.options.figsize])
        if manifest.options.dpi > 0:
            argv.extend(["--dpi", str(manifest.options.dpi)])
        argv.extend(["--format", fmt, "--cmap", cmap, staged_matrix.name])
        command = run_python_step("jcvi.graphics.heatmap", _run_heatmap_main, argv, cwd=root)
        commands.append(command)
        _assert_ok(command)
        figure = root / f"{staged_matrix.stem}.{cmap}.{fmt}"
        if not figure.is_file() or figure.stat().st_size == 0:
            raise RuntimeError(f"JCVI heatmap figure was not created: {figure}")
        figures.append(str(figure))

    artifacts: dict[str, object] = {
        "figures": figures,
        "heatmap_figures": figures,
        "matrix": str(staged_matrix),
        "backend": "jcvi.graphics.heatmap",
        "heatmap_cmap": cmap,
        "heatmap_groups": manifest.options.groups,
        "heatmap_horizontalbar": manifest.options.horizontalbar,
    }
    if staged_rowgroups is not None:
        artifacts["rowgroups"] = str(staged_rowgroups)
    return commands, artifacts
