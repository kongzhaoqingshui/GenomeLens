"""多物种局部共线性 pairwise 产物聚合工具"""

# region import
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from genomelens.app.controller.runners._shared import copy_pairwise_figures, species_summary
from genomelens.core.jcvi_adapter.adapter import JcviEngineAdapter
from genomelens.core.summary_models import PairwiseJobSummary
from genomelens.toolchain.runtime.resource_locator import locate_engine

# endregion


if TYPE_CHECKING:
    from genomelens.core.jcvi_adapter.adapter_models import McscanRequest
    from genomelens.data.workspace.output_layout import OutputLayout


@dataclass
class _TargetAggregate:
    """单个目标基因窗口的多物种聚合缓存"""

    order: list[str] = field(default_factory=list)
    seen: set[str] = field(default_factory=set)
    species_hits: dict[str, dict[str, str]] = field(default_factory=dict)

    def add(self, species_name: str, reference_gene: str, subject_gene: str) -> None:
        """记录一行 reference -> subject 命中"""

        if reference_gene not in self.seen:
            self.seen.add(reference_gene)
            self.order.append(reference_gene)
        self.species_hits.setdefault(species_name, {})[reference_gene] = subject_gene


def _safe_prefix(value: str) -> str:
    """生成适合放进 BED accn 的物种前缀"""

    text = re.sub(r"[^0-9A-Za-z_.-]+", "_", value.strip())
    return text or "species"


def _scoped_accn(species_name: str, accn: str) -> str:
    """给 accn 增加物种作用域，避免多物种间 ID 冲突"""

    return f"{_safe_prefix(species_name)}__{accn}"


def _split_block_highlight(line: str) -> tuple[str | None, str]:
    """拆分 JCVI blocks 行首的 highlight 前缀"""

    if "*" not in line:
        return None, line
    highlight, body = line.split("*", 1)
    return highlight or None, body


def _first_subject(parts: list[str]) -> str:
    """读取 blocks 行中第一个可用 subject accn"""

    for item in parts[1:]:
        accn = item.strip()
        if accn and accn != ".":
            return accn
    return "."


def _read_engine_local_artifacts(path: str) -> list[dict[str, object]]:
    """从 pairwise engine summary 中读取 local_artifacts"""

    summary_path = Path(path)
    if not summary_path.is_file():
        return []

    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    artifacts = payload.get("artifacts")
    if not isinstance(artifacts, dict):
        return []
    local_artifacts = artifacts.get("local_artifacts")
    if not isinstance(local_artifacts, list):
        return []
    return [item for item in local_artifacts if isinstance(item, dict)]


def _add_blocks_to_aggregate(
    aggregate: _TargetAggregate,
    blocks_path: Path,
    species_name: str,
) -> None:
    """把一个 pairwise local blocks 文件合入目标窗口缓存"""

    if not blocks_path.is_file():
        return

    with blocks_path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            _highlight, body = _split_block_highlight(line)
            parts = body.split("\t")
            if len(parts) < 2:
                continue
            reference_gene = parts[0].strip()
            subject_gene = _first_subject(parts)
            if not reference_gene or subject_gene == ".":
                continue
            aggregate.add(species_name, reference_gene, subject_gene)


def _collect_target_aggregates(pairwise_jobs: list[PairwiseJobSummary]) -> dict[str, _TargetAggregate]:
    """从成功 pairwise 子任务收集按 target/window 分组的 local blocks"""

    aggregates: dict[str, _TargetAggregate] = {}
    for job in pairwise_jobs:
        if job.status != "SUCCEEDED":
            continue
        for item in _read_engine_local_artifacts(job.engine_summary_path):
            target = str(item.get("target") or "").strip()
            blocks = str(item.get("blocks") or "").strip()
            if not target or not blocks:
                continue
            aggregate = aggregates.setdefault(target, _TargetAggregate())
            _add_blocks_to_aggregate(aggregate, Path(blocks), job.species_b_name)
    return aggregates


def _rewrite_bed_lines(source: Path, species_name: str, seen: set[str]) -> list[str]:
    """读取 BED 并把第 4 列 accn 改写为带物种作用域的 ID"""

    lines: list[str] = []
    if not source.is_file():
        return lines

    with source.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.rstrip("\n\r")
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) < 4:
                continue
            scoped = _scoped_accn(species_name, parts[3].strip())
            if scoped in seen:
                continue
            seen.add(scoped)
            parts[3] = scoped
            lines.append("\t".join(parts))
    return lines


def _write_multi_local_bed(path: Path, request: McscanRequest, pairwise_jobs: list[PairwiseJobSummary]) -> Path:
    """写出多物种局部图使用的合并 BED"""

    seen: set[str] = set()
    lines: list[str] = []
    query_bed = next((Path(job.query_bed) for job in pairwise_jobs if job.query_bed), None)
    if query_bed is not None:
        lines.extend(_rewrite_bed_lines(query_bed, request.query.name, seen))

    for job in pairwise_jobs:
        if job.status != "SUCCEEDED" or not job.subject_bed:
            continue
        lines.extend(_rewrite_bed_lines(Path(job.subject_bed), job.species_b_name, seen))

    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return path


def _write_multi_local_blocks(
    path: Path,
    request: McscanRequest,
    pairwise_jobs: list[PairwiseJobSummary],
    aggregates: dict[str, _TargetAggregate],
) -> tuple[Path, list[str]]:
    """写出多物种局部总图 blocks，并返回重写后的目标基因标签"""

    target_names = [job.species_b_name for job in pairwise_jobs if job.status == "SUCCEEDED"]
    target_names = list(dict.fromkeys(target_names))
    target_gene_ids = set(request.target_gene_ids)
    scoped_target_gene_ids = [_scoped_accn(request.query.name, gene) for gene in request.target_gene_ids]

    lines: list[str] = []
    for target in sorted(aggregates):
        aggregate = aggregates[target]
        for reference_gene in aggregate.order:
            row = [_scoped_accn(request.query.name, reference_gene)]
            for species_name in target_names:
                subject_gene = aggregate.species_hits.get(species_name, {}).get(reference_gene, ".")
                row.append("." if subject_gene == "." else _scoped_accn(species_name, subject_gene))
            prefix = "r*" if reference_gene in target_gene_ids else ""
            lines.append(prefix + "\t".join(row))

    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return path, scoped_target_gene_ids


def build_multi_species_local_synteny(
    request: McscanRequest,
    pairwise_jobs: list[PairwiseJobSummary],
    layout: OutputLayout,
) -> list[str]:
    """把 reference-vs-targets 局部共线性结果聚合成多物种总图"""

    if len(request.species) < 3 or not request.target_gene_ids:
        return []

    successful_targets = [job for job in pairwise_jobs if job.status == "SUCCEEDED" and job.species_b_name]
    if len({job.species_b_name for job in successful_targets}) < 2:
        return []

    try:
        aggregates = _collect_target_aggregates(successful_targets)
        if not aggregates:
            return []

        engine = locate_engine(explicit=request.jcvi_engine)
        if not engine.ok:
            return []

        local_dir = layout.intermediate / "multi_species_local_synteny"
        local_dir.mkdir(parents=True, exist_ok=True)
        blocks, scoped_targets = _write_multi_local_blocks(
            local_dir / "local_synteny_multi.blocks", request, successful_targets, aggregates
        )
        bed = _write_multi_local_bed(local_dir / "local_synteny_multi.bed", request, successful_targets)
        if not blocks.stat().st_size or not bed.stat().st_size:
            return []

        tracks = [{"name": request.query.name, "bed": str(successful_targets[0].query_bed)}]
        tracks.extend({"name": job.species_b_name, "bed": job.subject_bed} for job in successful_targets)

        adapter = JcviEngineAdapter(engine.path)
        manifest = adapter.build_multi_local_synteny_manifest(
            tracks=tracks,
            blocks=blocks,
            bed=bed,
            formats=request.formats,
            target_gene_ids=scoped_targets,
            label_targets=request.label_targets,
            glyphstyle=request.glyphstyle,
            glyphcolor=request.glyphcolor,
            shadestyle=request.shadestyle,
            figsize=request.figsize,
            dpi=request.dpi,
            auto_optimization=request.auto_optimization,
            use_native_local_synteny_renderer=request.use_native_local_synteny_renderer,
            task={"workflow": "local_synteny_multi", "task_type": "multi_species_local_synteny"},
            species=species_summary(request),
        )
        manifest_path = local_dir / "local_synteny_multi_manifest.json"
        adapter.write_manifest(manifest, manifest_path)
        result = adapter.run_manifest(manifest_path, local_dir)
        figures = [
            str(item)
            for item in cast(
                list[Any],
                result.artifacts.get("multi_species_local_figures") or result.artifacts.get("figures") or [],
            )
        ]
        return copy_pairwise_figures("multi_species_local", figures, layout.figures)
    except Exception:  # noqa: BLE001 - 多物种局部总图是增量产物，失败不影响 pairwise 结果
        return []
