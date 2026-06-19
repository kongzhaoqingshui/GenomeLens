"""BED summary workflow backed by ``jcvi.formats.bed``."""

# region import
from __future__ import annotations

import json
from pathlib import Path

from jcvi.formats.bed import Bed, BedSummary
from jcvi_genomelens.manifest_models import EngineRunManifest, GenomeSpec
from jcvi_genomelens.runtime.command_runner import CommandAudit, run_python_step
from jcvi_genomelens.workflows.common import _assert_ok

# endregion


def _summary_payload(species: str, bed_path: Path) -> dict[str, object]:
    bed = Bed(str(bed_path))
    summary = BedSummary(bed)
    longest_span, longest_name = max(summary.mspans)
    shortest_span, shortest_name = min(summary.mspans)
    per_seqid = {}
    for seqid, subbeds in bed.sub_beds():
        seq_summary = BedSummary(subbeds)
        per_seqid[seqid] = {
            "feature_count": seq_summary.nfeats,
            "unique_bases": seq_summary.unique_bases,
            "total_bases": seq_summary.total_bases,
            "coverage": seq_summary.coverage,
        }

    return {
        "species": species,
        "bed": str(bed_path),
        "seqid_count": summary.nseqids,
        "feature_count": summary.nfeats,
        "unique_bases": summary.unique_bases,
        "total_bases": summary.total_bases,
        "coverage": summary.coverage,
        "longest_feature": {"name": longest_name, "span": longest_span},
        "shortest_feature": {"name": shortest_name, "span": shortest_span},
        "per_seqid": per_seqid,
    }


def _write_summary(species: str, bed_path: Path, json_path: Path, tsv_path: Path) -> None:
    payload = _summary_payload(species, bed_path)
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tsv_path.write_text(
        "\t".join(["species", "seqids", "features", "unique_bases", "total_bases", "coverage"]) + "\n"
        + "\t".join(
            [
                str(payload["species"]),
                str(payload["seqid_count"]),
                str(payload["feature_count"]),
                str(payload["unique_bases"]),
                str(payload["total_bases"]),
                f"{float(payload['coverage']):.3f}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def _run_bed_summary(args: list[str]) -> None:
    species, bed_path, json_path, tsv_path = args
    _write_summary(species, Path(bed_path), Path(json_path), Path(tsv_path))


def _run_one(spec: GenomeSpec, root: Path) -> tuple[CommandAudit, dict[str, str]]:
    json_path = root / f"{spec.name}.bed_summary.json"
    tsv_path = root / f"{spec.name}.bed_summary.tsv"
    command = run_python_step(
        "jcvi.formats.bed.summary",
        _run_bed_summary,
        [spec.name, str(spec.bed), str(json_path), str(tsv_path)],
        cwd=root,
    )
    _assert_ok(command)
    for path in [json_path, tsv_path]:
        if not path.is_file() or path.stat().st_size == 0:
            raise RuntimeError(f"JCVI BED summary artifact was not created: {path}")
    return command, {"json": str(json_path), "tsv": str(tsv_path)}


def run(manifest: EngineRunManifest, outdir: str | Path) -> tuple[list[CommandAudit], dict[str, object]]:
    """Summarize query and subject BED inputs using JCVI's BED parser."""

    if manifest.query is None or manifest.subject is None:
        raise ValueError("bed_summary requires query and subject species")

    root = Path(outdir).expanduser().resolve(strict=False)
    root.mkdir(parents=True, exist_ok=True)
    query_command, query_artifacts = _run_one(manifest.query, root)
    subject_command, subject_artifacts = _run_one(manifest.subject, root)

    return [
        query_command,
        subject_command,
    ], {
        "query_bed_summary": query_artifacts["json"],
        "query_bed_summary_tsv": query_artifacts["tsv"],
        "subject_bed_summary": subject_artifacts["json"],
        "subject_bed_summary_tsv": subject_artifacts["tsv"],
        "figures": [],
        "simplified_fallback": False,
        "backend": "jcvi.formats.bed.summary",
    }
