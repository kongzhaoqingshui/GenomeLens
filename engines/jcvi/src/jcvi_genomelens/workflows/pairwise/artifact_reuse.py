"""两物种 pairwise 产物复用辅助函数"""

from __future__ import annotations

from pathlib import Path

from jcvi.formats.bed import merge as jcvi_bed_merge
from jcvi_genomelens.manifest.models import EngineRunManifest, PairwiseArtifacts
from jcvi_genomelens.runtime.command_runner import CommandAudit, run_python_step
from jcvi_genomelens.workflows.common import _assert_ok
from jcvi_genomelens.workflows.reuse.bundles import pairwise_artifacts_from_manifest


class MissingPairwiseArtifactsError(RuntimeError):
    """渲染工作流缺少必需的上游 pairwise 产物时抛出

    渲染层（render_*）绝不自行计算 pairwise；缺产物意味着上游 ``jcvi.pairwise``
    没有把对应端口接进来，应由调用方补齐输入端口，而非在渲染期偷偷重算。
    """


def ensure_pairwise_artifacts(
    manifest: EngineRunManifest,
    outdir: str | Path,
    *,
    required_fields: tuple[str, ...],
    ensure_merged_bed: bool = False,
) -> tuple[list[CommandAudit], dict[str, object]]:
    """复用上游预计算的 pairwise 产物；缺必需产物时报错（绝不重算）"""

    root = Path(outdir).expanduser().resolve(strict=False)
    root.mkdir(parents=True, exist_ok=True)
    precomputed = pairwise_artifacts_from_manifest(manifest)
    if precomputed is None or not _has_required_artifacts(precomputed, required_fields):
        missing = _missing_fields(precomputed, required_fields)
        raise MissingPairwiseArtifactsError(
            "缺少必需的上游 pairwise 产物："
            f"{', '.join(missing)}；请先运行 jcvi.pairwise 并将对应端口接入渲染模块。"
        )

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


def _missing_fields(artifacts: PairwiseArtifacts | None, required_fields: tuple[str, ...]) -> list[str]:
    if artifacts is None:
        return list(required_fields)
    missing: list[str] = []
    for field_name in required_fields:
        path = getattr(artifacts, field_name)
        if path is None or not path.is_file() or path.stat().st_size == 0:
            missing.append(field_name)
    return missing



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
