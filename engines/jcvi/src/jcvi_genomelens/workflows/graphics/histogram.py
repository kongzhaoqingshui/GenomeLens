"""GenomeLens histogram workflow：读取数值文件并使用 matplotlib 绘制直方图"""

# region import
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import matplotlib
import numpy as np
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from jcvi_genomelens.manifest.models import EngineRunManifest
from jcvi_genomelens.runtime.command_runner import CommandAudit, run_python_step
from jcvi_genomelens.workflows.common import _assert_ok

# endregion


matplotlib.use("Agg")
import matplotlib.pyplot as plt


@dataclass(frozen=True)
class _HistogramSeries:
    """单个 histogram 序列的数据与标签"""

    label: str
    path: str
    column: int
    values: np.ndarray


def _read_column(path: Path, column: int, skip: int) -> np.ndarray:
    """读取一个文件中的单列数值"""

    values: list[float] = []
    with path.open("r", encoding="utf-8-sig") as handle:
        for index, raw_line in enumerate(handle):
            if index < skip:
                continue
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if column >= len(parts):
                raise RuntimeError(f"Column {column} is out of range in {path} at line {index + 1}")
            try:
                values.append(float(parts[column]))
            except ValueError as exc:
                raise RuntimeError(f"Non-numeric value in {path} at line {index + 1}: {parts[column]}") from exc
    if not values:
        raise RuntimeError(f"No numeric values were read from {path} column {column}")
    return np.asarray(values, dtype=float)


def _series_label(path: Path, column: int, *, multi_input: bool, multi_column: bool) -> str:
    """根据输入文件与列号生成序列标签"""

    if multi_input or multi_column:
        return f"{path.stem}:col{column}"
    return path.stem


def _load_series(
    paths: list[Path],
    columns: list[int],
    *,
    skip: int,
    vmin: float | None,
    vmax: float | None,
    base: int,
) -> list[_HistogramSeries]:
    """从输入文件加载一个或多个 histogram 序列"""

    series: list[_HistogramSeries] = []
    multi_input = len(paths) > 1
    multi_column = len(columns) > 1
    for path in paths:
        for column in columns:
            values = _read_column(path, column, skip)
            if base > 0:
                values = values[values > 0]
            if vmin is not None:
                values = values[values >= vmin]
            if vmax is not None:
                values = values[values <= vmax]
            if values.size == 0:
                raise RuntimeError(f"No values remain after filtering for {path} column {column}")
            series.append(
                _HistogramSeries(
                    label=_series_label(path, column, multi_input=multi_input, multi_column=multi_column),
                    path=str(path),
                    column=column,
                    values=values,
                )
            )
    return series


def _resolve_bounds(series: list[_HistogramSeries], vmin: float | None, vmax: float | None) -> tuple[float, float]:
    """解析最终使用的数值边界"""

    all_values = np.concatenate([item.values for item in series])
    lower = float(np.min(all_values)) if vmin is None else float(vmin)
    upper = float(np.max(all_values)) if vmax is None else float(vmax)
    if lower >= upper:
        raise RuntimeError(f"Histogram bounds are invalid: vmin={lower}, vmax={upper}")
    return lower, upper


def _build_bin_edges(vmin: float, vmax: float, bins: int, base: int) -> np.ndarray:
    """根据数值范围构建 bin 边界"""

    if base > 0:
        if vmin <= 0 or vmax <= 0:
            raise RuntimeError("Log histogram requires positive values after filtering")
        return np.logspace(np.log(vmin) / np.log(base), np.log(vmax) / np.log(base), bins + 1, base=base)
    return np.linspace(vmin, vmax, bins + 1)


def _render_overlay(
    ax: Axes,
    series: list[_HistogramSeries],
    *,
    bin_edges: np.ndarray,
    fill: str,
) -> None:
    """在同一张坐标轴上叠加多个序列"""

    colors = plt.get_cmap("tab10")(np.linspace(0, 1, max(len(series), 1)))
    alpha = 0.85 if len(series) == 1 else 0.55
    for index, item in enumerate(series):
        color = fill if len(series) == 1 else colors[index]
        ax.hist(
            item.values,
            bins=bin_edges.tolist(),
            alpha=alpha,
            label=item.label,
            color=color,
            edgecolor="#1f3b4d",
        )
    if len(series) > 1:
        ax.legend(frameon=False)


def _render_facets(
    figure: Figure,
    series: list[_HistogramSeries],
    *,
    bin_edges: np.ndarray,
    fill: str,
) -> None:
    """把多个序列绘制到分面子图中"""

    count = len(series)
    cols = 2 if count > 1 else 1
    rows = int(np.ceil(count / cols))
    axes = figure.subplots(rows, cols, squeeze=False)
    for axis in axes.flat[count:]:
        axis.remove()
    for axis, item in zip(axes.flat, series, strict=False):
        axis.hist(item.values, bins=bin_edges.tolist(), color=fill, edgecolor="#1f3b4d")
        axis.set_title(item.label)
        axis.set_ylabel("Count")


def _render_histogram(
    series: list[_HistogramSeries],
    *,
    outdir: Path,
    formats: list[str],
    bins: int,
    vmin: float | None,
    vmax: float | None,
    xlabel: str,
    title: str,
    base: int,
    facet: bool,
    fill: str,
    dpi: int,
) -> list[str]:
    """执行实际的 matplotlib 渲染"""

    lower, upper = _resolve_bounds(series, vmin, vmax)
    bin_edges = _build_bin_edges(lower, upper, bins, base)
    resolved_title = title or Path(series[0].path).name
    figures: list[str] = []
    for fmt in formats:
        figure = plt.figure(figsize=(10, 6), dpi=dpi)
        if facet and len(series) > 1:
            _render_facets(figure, series, bin_edges=bin_edges, fill=fill)
            axes = [axis for axis in figure.axes if axis.has_data()]
            for axis in axes:
                axis.set_xlabel(xlabel)
                if base > 0:
                    axis.set_xscale("log", base=base)
        else:
            axis = figure.add_subplot(111)
            _render_overlay(axis, series, bin_edges=bin_edges, fill=fill)
            axis.set_xlabel(xlabel)
            axis.set_ylabel("Count")
            if base > 0:
                axis.set_xscale("log", base=base)
        figure.suptitle(resolved_title)
        figure.tight_layout()
        path = outdir / f"histogram.{fmt}"
        figure.savefig(path, dpi=dpi, bbox_inches="tight")
        plt.close(figure)
        figures.append(str(path))
    return figures


def _run_from_config(argv: list[str]) -> None:
    """从 workflow 写出的 JSON 配置中执行渲染"""

    if len(argv) != 1:
        raise RuntimeError("graphics_histogram expects exactly one config path argument")
    config_path = Path(argv[0]).expanduser().resolve(strict=False)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    outdir = Path(str(config["outdir"])).expanduser().resolve(strict=False)
    inputs = [Path(str(item)).expanduser().resolve(strict=False) for item in config["inputs"]]
    columns = [int(item) for item in config["columns"]]
    series = _load_series(
        inputs,
        columns,
        skip=int(config["skip"]),
        vmin=config.get("vmin"),
        vmax=config.get("vmax"),
        base=int(config["base"]),
    )
    _render_histogram(
        series,
        outdir=outdir,
        formats=[str(item) for item in config["formats"]],
        bins=int(config["bins"]),
        vmin=config.get("vmin"),
        vmax=config.get("vmax"),
        xlabel=str(config["xlabel"]),
        title=str(config["title"]),
        base=int(config["base"]),
        facet=bool(config["facet"]),
        fill=str(config["fill"]),
        dpi=int(config["dpi"]),
    )


def run(manifest: EngineRunManifest, outdir: str | Path) -> tuple[list[CommandAudit], dict[str, object]]:
    """运行 graphics_histogram workflow"""

    root = Path(outdir).expanduser().resolve(strict=False)
    root.mkdir(parents=True, exist_ok=True)
    config_path = root / "histogram.render.json"
    config_path.write_text(
        json.dumps(
            {
                "outdir": str(root),
                "inputs": [str(path) for path in manifest.options.histogram_inputs],
                "columns": list(manifest.options.histogram_columns),
                "skip": manifest.options.histogram_skip,
                "bins": manifest.options.histogram_bins,
                "vmin": manifest.options.histogram_vmin,
                "vmax": manifest.options.histogram_vmax,
                "xlabel": manifest.options.histogram_xlabel,
                "title": manifest.options.histogram_title,
                "base": manifest.options.histogram_base,
                "facet": manifest.options.histogram_facet,
                "fill": manifest.options.histogram_fill,
                "formats": list(manifest.options.formats or ["svg"]),
                "dpi": manifest.options.dpi,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    command = run_python_step(
        "genomelens.graphics_histogram",
        _run_from_config,
        [str(config_path)],
        cwd=root,
    )
    _assert_ok(command)

    figures = [str(root / f"histogram.{fmt}") for fmt in (manifest.options.formats or ["svg"])]
    for figure in figures:
        path = Path(figure)
        if not path.is_file() or path.stat().st_size == 0:
            raise RuntimeError(f"Histogram figure was not created: {path}")

    artifacts: dict[str, object] = {
        "figures": figures,
        "histogram_figures": figures,
        "histogram_render_config": str(config_path),
        "histogram_input_files": [str(path) for path in manifest.options.histogram_inputs],
        "histogram_columns": list(manifest.options.histogram_columns),
        "histogram_skip": manifest.options.histogram_skip,
        "histogram_bins": manifest.options.histogram_bins,
        "histogram_vmin": manifest.options.histogram_vmin,
        "histogram_vmax": manifest.options.histogram_vmax,
        "histogram_xlabel": manifest.options.histogram_xlabel,
        "histogram_title": manifest.options.histogram_title,
        "histogram_base": manifest.options.histogram_base,
        "histogram_facet": manifest.options.histogram_facet,
        "histogram_fill": manifest.options.histogram_fill,
        "backend": "genomelens.matplotlib.histogram",
    }
    return [command], artifacts
