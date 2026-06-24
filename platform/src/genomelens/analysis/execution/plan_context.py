"""PlanRunContext：为复合 synteny 任务提供 plan 级复用上下文"""

# region import
from __future__ import annotations

import json
import shutil
from collections.abc import Mapping
from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path
from typing import TYPE_CHECKING

from genomelens.analysis.planning.models import PairwiseArtifactInputs, SyntenyExecutionRequest
from genomelens.contracts.species import GenomeInputSpec, PreparedGenomeInputSpec
from genomelens.data.logging.task_log import task_scope
from genomelens.engines.jcvi.adapter import JcviEngineAdapter
from genomelens.preprocessing.input_preparer import prepare_species_input
from genomelens.toolchain.runtime.resource_locator import LocatedResource
from genomelens.toolchain.runtime.toolchain_resolver import resolve_pairwise_toolchain

# endregion


if TYPE_CHECKING:
    import logging

    from genomelens.data.workspace.output_layout import OutputLayout


PREPROCESSING_CACHE_VERSION = "2026-06-24"
PAIRWISE_CACHE_VERSION = "2026-06-24"
PAIRWISE_CACHE_FIELDS = ("blast_table", "anchors", "simple", "blocks", "merged_bed", "layout")
PAIRWISE_CACHE_REQUIRED_FIELDS = ("anchors", "simple", "blocks")


@dataclass(frozen=True)
class PreparedSpeciesRecord:
    """PreparedSpeciesRecord：plan 级 species 预处理缓存条目"""

    fingerprint: str
    prepared: PreparedGenomeInputSpec
    summary: dict[str, object] | None = None


@dataclass(frozen=True)
class ResolvedPairwiseToolchain:
    """ResolvedPairwiseToolchain：复合任务共享的工具链与 probe 结果"""

    engine: LocatedResource
    blastn: LocatedResource
    makeblastdb: LocatedResource
    lastal_path: str
    lastdb_path: str
    probe: dict[str, object]


@dataclass
class PlanRunContext:
    """PlanRunContext：复合任务中的共享上下文与缓存统计"""

    # fmt: off
    root_outdir: Path
    cache_root: Path
    toolchain: ResolvedPairwiseToolchain
    prepared_species: dict[str, PreparedSpeciesRecord] = field(default_factory=dict)
    pairwise_cache_index: dict[str, dict[str, str]] = field(default_factory=dict)
    species_cache_hits: int = 0
    species_cache_misses: int = 0
    pairwise_cache_hits: int = 0
    pairwise_cache_misses: int = 0
    pairwise_cache_writes: int = 0
    # fmt: on

    @property
    def pairwise_cache_index_path(self) -> Path:
        """返回 pairwise cache index JSON 路径"""

        return self.cache_root / "pairwise" / "index.json"

    def prepared_for(self, species: GenomeInputSpec) -> PreparedSpeciesRecord | None:
        """按 species 指纹读取已准备好的 BED/CDS 记录"""

        return self.prepared_species.get(species_fingerprint(species))

    def lookup_pairwise_cache(self, cache_key: str) -> PairwiseArtifactInputs | None:
        """查找并验证当前输出目录内可复用的 pairwise core 产物"""

        payload = self.pairwise_cache_index.get(cache_key)
        if payload is None:
            self.pairwise_cache_misses += 1
            return None

        artifacts = pairwise_artifacts_from_json(payload)
        if not _validate_pairwise_artifacts(artifacts, required_fields=PAIRWISE_CACHE_REQUIRED_FIELDS):
            self.pairwise_cache_misses += 1
            return None

        self.pairwise_cache_hits += 1
        return artifacts

    def store_pairwise_cache(self, cache_key: str, artifacts: PairwiseArtifactInputs) -> PairwiseArtifactInputs | None:
        """把本次 pairwise core 产物复制到当前输出目录内缓存"""

        if not _validate_pairwise_artifacts(artifacts, required_fields=PAIRWISE_CACHE_REQUIRED_FIELDS):
            return None

        target_dir = self.cache_root / "pairwise" / cache_key
        target_dir.mkdir(parents=True, exist_ok=True)
        stored = _copy_pairwise_artifacts(artifacts, target_dir)
        if stored is None:
            return None

        self.pairwise_cache_index[cache_key] = stored.to_manifest_json()
        self.pairwise_cache_writes += 1
        self._flush_pairwise_cache_index()
        return stored

    def extension_stats(self) -> dict[str, object]:
        """生成可写入 RunSummary.extensions 的 plan 级统计"""

        return {
            "plan_context": {
                "species_cache_hits": self.species_cache_hits,
                "species_cache_misses": self.species_cache_misses,
                "pairwise_cache_hits": self.pairwise_cache_hits,
                "pairwise_cache_misses": self.pairwise_cache_misses,
                "pairwise_cache_writes": self.pairwise_cache_writes,
                "toolchain_reused": True,
                "probe_reused": True,
            }
        }

    def _flush_pairwise_cache_index(self) -> None:
        self.pairwise_cache_index_path.parent.mkdir(parents=True, exist_ok=True)
        self.pairwise_cache_index_path.write_text(
            json.dumps(self.pairwise_cache_index, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )


def build_plan_run_context(
    requests: list[SyntenyExecutionRequest],
    layout: OutputLayout,
    logger: logging.Logger,
) -> PlanRunContext:
    """为复合任务构建共享的工具链、probe 与 species 预处理上下文"""

    exemplar = requests[0]
    with task_scope(
        logger,
        task_id=exemplar.task_id,
        step="prepare_plan_context",
        context={"pairs": len(requests), "cache_root": str(layout.cache)},
    ):
        with task_scope(logger, task_id=exemplar.task_id, step="resolve_toolchain_once"):
            engine, blastn, makeblastdb, lastal_path, lastdb_path = resolve_pairwise_toolchain(
                jcvi_engine=exemplar.jcvi_engine,
                blastn_path=exemplar.blastn_path,
                makeblastdb_path=exemplar.makeblastdb_path,
                lastal_path=exemplar.lastal_path,
                lastdb_path=exemplar.lastdb_path,
                align_soft=exemplar.align_soft,
            )

        adapter = JcviEngineAdapter(engine.path)
        with task_scope(
            logger,
            task_id=exemplar.task_id,
            step="probe_engine_once",
            context={"engine": engine.path},
        ):
            probe = adapter.probe()

        context = PlanRunContext(
            root_outdir=layout.root,
            cache_root=layout.cache,
            toolchain=ResolvedPairwiseToolchain(
                engine=engine,
                blastn=blastn,
                makeblastdb=makeblastdb,
                lastal_path=lastal_path,
                lastdb_path=lastdb_path,
                probe=probe,
            ),
            pairwise_cache_index=_load_pairwise_cache_index(layout.cache / "pairwise" / "index.json"),
        )

        species_count = len({species_fingerprint(item) for request in requests for item in request.species})
        with task_scope(
            logger,
            task_id=exemplar.task_id,
            step="prepare_species_cache",
            context={"species_count": species_count},
        ):
            for request in requests:
                for species in request.species:
                    fingerprint = species_fingerprint(species)
                    if fingerprint in context.prepared_species:
                        context.species_cache_hits += 1
                        continue

                    prepared_dir = layout.cache / "prepared" / fingerprint
                    prepared_dir.mkdir(parents=True, exist_ok=True)
                    prepared, summary = prepare_species_input(species, prepared_dir)
                    context.prepared_species[fingerprint] = PreparedSpeciesRecord(
                        fingerprint=fingerprint,
                        prepared=prepared,
                        summary=summary,
                    )
                    context.species_cache_misses += 1

        return context


def species_fingerprint(species: GenomeInputSpec) -> str:
    """根据 species 输入模式和文件元数据计算稳定指纹"""

    if species.prepared is not None:
        parts = {
            "mode": species.mode,
            "name": species.name,
            "bed": _path_signature(species.prepared.bed),
            "cds": _path_signature(species.prepared.cds),
        }
    elif species.raw is not None:
        parts = {
            "mode": species.mode,
            "name": species.name,
            "preprocess_version": PREPROCESSING_CACHE_VERSION,
            "gff": _path_signature(species.raw.gff),
            "genome": _path_signature(species.raw.genome),
        }
    else:
        parts = {"mode": "unknown", "name": species.name}
    return _stable_hash(parts)


def pairwise_cache_key(
    request: SyntenyExecutionRequest,
    query_record: PreparedSpeciesRecord,
    subject_record: PreparedSpeciesRecord,
    probe: dict[str, object],
) -> str:
    """根据 prepared 输入与关键参数计算 pairwise core 缓存键"""

    payload = {
        "version": PAIRWISE_CACHE_VERSION,
        "query": query_record.fingerprint,
        "subject": subject_record.fingerprint,
        "align_soft": request.align_soft,
        "dbtype": request.dbtype,
        "cscore": request.cscore,
        "dist": request.dist,
        "iter": request.iter,
        "min_block_size": request.min_block_size,
        "engine_version": str(probe.get("engine_version", "")),
        "patchset": str(probe.get("patchset", "")),
        "runtime_mode": str(probe.get("runtime_mode", "")),
    }
    return _stable_hash(payload)


def pairwise_artifacts_from_json(data: dict[str, str]) -> PairwiseArtifactInputs:
    """把 cache index JSON 条目转回 PairwiseArtifactInputs"""

    values: dict[str, Path] = {}
    for key in PAIRWISE_CACHE_FIELDS:
        raw = data.get(key)
        if raw:
            values[key] = Path(raw).expanduser().resolve(strict=False)
    return PairwiseArtifactInputs(**values)


def _path_signature(path: Path) -> dict[str, object]:
    resolved = path.expanduser().resolve(strict=False)
    try:
        stat = resolved.stat()
        size = stat.st_size
        mtime_ns = stat.st_mtime_ns
    except FileNotFoundError:
        size = -1
        mtime_ns = -1
    return {"path": str(resolved), "size": size, "mtime_ns": mtime_ns}


def _stable_hash(payload: Mapping[str, object]) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return sha256(raw.encode("utf-8")).hexdigest()


def _validate_pairwise_artifacts(
    artifacts: PairwiseArtifactInputs,
    *,
    required_fields: tuple[str, ...],
) -> bool:
    for key in required_fields:
        path = getattr(artifacts, key)
        if path is None or not path.is_file() or path.stat().st_size == 0:
            return False
    for key in PAIRWISE_CACHE_FIELDS:
        path = getattr(artifacts, key)
        if path is not None and (not path.is_file() or path.stat().st_size == 0):
            return False
    return True


def _copy_pairwise_artifacts(artifacts: PairwiseArtifactInputs, target_dir: Path) -> PairwiseArtifactInputs | None:
    copied: dict[str, Path] = {}
    for key in PAIRWISE_CACHE_FIELDS:
        source = getattr(artifacts, key)
        if source is None:
            continue
        if not source.is_file() or source.stat().st_size == 0:
            return None
        target = target_dir / source.name
        shutil.copy2(source, target)
        copied[key] = target
    return PairwiseArtifactInputs(**copied)


def _load_pairwise_cache_index(path: Path) -> dict[str, dict[str, str]]:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    if not isinstance(payload, dict):
        return {}
    result: dict[str, dict[str, str]] = {}
    for key, value in payload.items():
        if isinstance(key, str) and isinstance(value, dict):
            result[key] = {str(item_key): str(item_value) for item_key, item_value in value.items()}
    return result
