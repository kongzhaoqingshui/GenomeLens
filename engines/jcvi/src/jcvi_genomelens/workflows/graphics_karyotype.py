"""Real JCVI graphics.karyotype workflow."""

from __future__ import annotations

from pathlib import Path

from jcvi_genomelens.manifest_models import EngineRunManifest
from jcvi_genomelens.runtime.command_runner import CommandAudit, run_python_step
from jcvi_genomelens.workflows.common import _assert_ok
from jcvi_genomelens.workflows.karyotype_support import format_track_row, select_karyotype_renderer
from jcvi_genomelens.workflows.mcscan_pairwise import run as run_pairwise


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


def _write_default_seqids(path: Path, manifest: EngineRunManifest) -> Path:
    if manifest.query is None or manifest.subject is None:
        raise ValueError("karyotype seqids require query and subject species")

    query_seqids = ",".join(_seqids_from_bed(manifest.query.bed))
    subject_seqids = ",".join(_seqids_from_bed(manifest.subject.bed))
    path.write_text(f"{query_seqids}\n{subject_seqids}\n", encoding="utf-8")
    return path


def _write_default_layout(path: Path, manifest: EngineRunManifest, simple: str) -> Path:
    if manifest.query is None or manifest.subject is None:
        raise ValueError("karyotype layout requires query and subject species")

    optimize_labels = manifest.options.auto_optimization.get("optimize_karyotype_labels", False)
    header = (
        "# y, xstart, xend, rotation, color, label, va, bed, label_va"
        if optimize_labels
        else "# y, xstart, xend, rotation, color, label, va, bed"
    )
    path.write_text(
        "\n".join(
            [
                header,
                format_track_row(
                    0.65,
                    "#2f6f73",
                    manifest.query.name,
                    "bottom" if optimize_labels else "top",
                    manifest.query.bed,
                    optimize_labels=optimize_labels,
                ),
                format_track_row(
                    0.35,
                    "#b85c38",
                    manifest.subject.name,
                    "top",
                    manifest.subject.bed,
                    optimize_labels=optimize_labels,
                ),
                "# edges",
                f"e, 0, 1, {simple}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def run(manifest: EngineRunManifest, outdir: str | Path) -> tuple[list[CommandAudit], dict[str, object]]:
    """Run pairwise MCscan and render the karyotype figure."""

    if manifest.query is None or manifest.subject is None:
        raise ValueError("karyotype requires query and subject species")

    commands, artifacts = run_pairwise(manifest, outdir)
    root = Path(outdir).expanduser().resolve(strict=False)
    root.mkdir(parents=True, exist_ok=True)
    karyotype_main, renderer_variant = select_karyotype_renderer(
        manifest.options.auto_optimization.get("optimize_karyotype_labels", False)
    )
    seqids = (
        manifest.options.seqids
        if manifest.options.seqids
        else _write_default_seqids(root / "karyotype.seqids", manifest)
    )
    layout = (
        manifest.options.layout
        if manifest.options.layout
        else _write_default_layout(root / "karyotype.layout", manifest, str(artifacts["simple"]))
    )
    figsize = manifest.options.figsize
    figures: list[str] = []
    formats = manifest.options.formats or ["svg"]
    for fmt in formats:
        figure = root / f"karyotype.{fmt}"
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
            raise RuntimeError(f"JCVI karyotype figure was not created: {figure}")
        figures.append(str(figure))

    artifacts["figures"] = figures
    artifacts["karyotype_figures"] = figures
    artifacts["karyotype_seqids"] = str(seqids)
    artifacts["karyotype_layout"] = str(layout)
    artifacts["karyotype_renderer_variant"] = renderer_variant
    artifacts["optimize_karyotype_labels"] = manifest.options.auto_optimization.get("optimize_karyotype_labels", False)
    artifacts["backend"] = "jcvi.graphics.karyotype"
    return commands, artifacts
