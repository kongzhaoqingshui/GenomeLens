"""执行摘要的 artifact(产物) 索引构造工具"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import TYPE_CHECKING

from genomelens.analysis.planning.models import SyntenyExecutionRequest
from genomelens.contracts.artifacts import ArtifactRecord

if TYPE_CHECKING:
    from genomelens.engines.jcvi.models import JcviRunResult


def artifact_record(
    artifact_id: str,
    artifact_type: str,
    path: object,
    produced_by: str,
    *,
    preview: bool = False,
) -> dict[str, object] | None:
    """把 artifact 路径转换为可序列化记录"""

    if not path:
        return None

    text = str(path)
    suffix = Path(text).suffix.lower().lstrip(".")

    return ArtifactRecord(
        artifact_id=artifact_id,
        artifact_type=artifact_type,
        path=text,
        produced_by=produced_by,
        format=suffix,
        preview=preview,
    ).to_json()


def artifact_index(
    request: SyntenyExecutionRequest,
    engine_result: JcviRunResult,
    final_figures: list[str],
    *,
    manifest_path: Path,
    run_log: Path,
) -> list[dict[str, object]]:
    """构建 pairwise 执行结果的 artifact 索引"""

    records: list[dict[str, object]] = []

    for artifact_id, artifact_type, value in [
        ("input_manifest", "manifest", manifest_path),
        ("engine_summary", "summary", engine_result.summary_path),
        ("run_log", "log", run_log),
        ("blast_table", "blast_table", engine_result.artifacts.get("blast_table", "")),
        ("anchors", "anchors", engine_result.artifacts.get("anchors", "")),
        ("simple", "simple", engine_result.artifacts.get("simple", "")),
        ("blocks", "blocks", engine_result.artifacts.get("blocks", "")),
    ]:
        record = artifact_record(artifact_id, artifact_type, value, request.jcvi_workflow)
        if record:
            records.append(record)

    for index, figure in enumerate(final_figures, start=1):
        record = artifact_record(f"figure_{index}", "figure", figure, request.jcvi_workflow, preview=True)
        if record:
            records.append(record)

    return records


def copy_pairwise_figures(pair_id: str, figures: list[str], target_dir: Path) -> list[str]:
    """把 pairwise 图件复制到顶层 figures 目录"""

    target_dir.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []

    for figure in figures:
        source = Path(figure)
        if source.is_file():
            target = target_dir / f"{pair_id}.{source.name}"
            shutil.copy2(source, target)
            copied.append(str(target))

    return copied
