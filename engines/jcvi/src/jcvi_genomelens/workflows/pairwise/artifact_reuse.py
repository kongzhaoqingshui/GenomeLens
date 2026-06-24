"""pairwise artifact 复用辅助：优先消费预计算产物，必要时回退完整 pairwise core"""

# region import
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from jcvi.formats.bed import merge as jcvi_bed_merge
from jcvi_genomelens.manifest.models import EngineRunManifest, PairwiseArtifacts
from jcvi_genomelens.runtime.command_runner import CommandAudit, run_python_step
from jcvi_genomelens.workflows.common import _assert_ok
from jcvi_genomelens.workflows.pairwise.mcscan import run as run_pairwise

# endregion

PairwiseFallbackRunner = Callable[[EngineRunManifest, str | Path], tuple[list[CommandAudit], dict[str, object]]]


def ensure_pairwise_artifacts(
    manifest: EngineRunManifest,
    outdir: str | Path,
    *,
    required_fields: tuple[str, ...],
    ensure_merged_bed: bool = False,
    fallback_runner: PairwiseFallbackRunner | None = None,
) -> tuple[list[CommandAudit], dict[str, object]]:
    """优先消费 `inputs.pairwise_artifacts`，缺失时回退完整 pairwise core"""

    root = Path(outdir).expanduser().resolve(strict=False)
    root.mkdir(parents=True, exist_ok=True)
    precomputed = manifest.pairwise_artifacts
    runner = fallback_runner or run_pairwise
    if precomputed is None or not _has_required_artifacts(precomputed, required_fields):
        return runner(manifest, root)

    commands: list[CommandAudit] = []
    artifacts = _artifacts_to_dict(precomputed)
    if ensure_merged_bed and "merged_bed" not in artifacts:
        merged_bed, command = _build_merged_bed(manifest, root)
        artifacts["merged_bed"] = str(merged_bed)
        commands.append(command)

    artifacts.setdefault("figures", [])
    artifacts.setdefault("simplified_fallback", False)
    artifacts.setdefault("backend", "jcvi")
    return commands, artifacts


def _has_required_artifacts(artifacts: PairwiseArtifacts, required_fields: tuple[str, ...]) -> bool:
    for field_name in required_fields:
        path = getattr(artifacts, field_name)
        if path is None or not path.is_file() or path.stat().st_size == 0:
            return False
    return True


def _artifacts_to_dict(artifacts: PairwiseArtifacts) -> dict[str, object]:
    data: dict[str, object] = {}
    for key in ("blast_table", "anchors", "simple", "blocks", "merged_bed", "layout"):
        value = getattr(artifacts, key)
        if value is not None:
            data[key] = str(value)
    return data


def _build_merged_bed(manifest: EngineRunManifest, root: Path) -> tuple[Path, CommandAudit]:
    if manifest.query is None or manifest.subject is None:
        raise ValueError("merged BED requires query and subject species")

    merged_bed = root / "all.bed"
    command = run_python_step(
        "jcvi.formats.bed.merge",
        jcvi_bed_merge,
        [str(manifest.query.bed), str(manifest.subject.bed), "-o", str(merged_bed)],
        cwd=root,
    )
    _assert_ok(command)
    if not merged_bed.is_file() or merged_bed.stat().st_size == 0:
        raise RuntimeError(f"Merged BED output is empty: {merged_bed}")
    return merged_bed, command
