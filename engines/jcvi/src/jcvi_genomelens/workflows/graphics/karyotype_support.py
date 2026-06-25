"""Helpers shared by GenomeLens karyotype workflows"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

KaryotypeMain = Callable[[list[str]], object]

DEFAULT_XSTART = 0.10
DEFAULT_XEND = 0.90
FIXED_XSTART = 0.12
FIXED_XEND = 0.88


def default_label_va(va: str) -> str:
    """Infer the opposite-side track label position from circle placement"""

    return "top" if va == "bottom" else "bottom" if va == "top" else "center"


def select_karyotype_renderer(optimize_labels: bool) -> tuple[KaryotypeMain, str]:
    """返回 karyotype 绘图入口和稳定变体名"""

    if optimize_labels:
        from jcvi_genomelens.graphics.karyotype import mirrored

        return mirrored.main, "mirrored"

    from jcvi.graphics.karyotype import main as vendored_karyotype_main

    return vendored_karyotype_main, "vendored"


def format_track_row(
    y: float,
    color: str,
    label: str,
    va: str,
    bed: Path,
    *,
    optimize_labels: bool,
) -> str:
    """Format an auto-generated karyotype track row"""

    xstart = FIXED_XSTART if optimize_labels else DEFAULT_XSTART
    xend = FIXED_XEND if optimize_labels else DEFAULT_XEND
    row = f"{y:.4f}, {xstart:.2f}, {xend:.2f}, 0, {color}, {label}, {va}, {bed}"
    if optimize_labels:
        row += f", {default_label_va(va)}"
    return row
