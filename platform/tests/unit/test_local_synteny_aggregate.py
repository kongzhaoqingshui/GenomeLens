import json
from pathlib import Path

from genomelens.analysis.execution_models import McscanExecutionRequest
from genomelens.app.controller.runners.local_synteny_aggregate import (
    _collect_target_aggregates,
    _write_multi_local_bed,
    _write_multi_local_blocks,
)
from genomelens.core.models import GenomeInputSpec, PreparedGenomeInputSpec
from genomelens.core.summary_models import PairwiseJobSummary


def _prepared(name: str, bed: Path) -> GenomeInputSpec:
    cds = bed.with_suffix(".cds")
    cds.write_text(f">{name}\nATGC\n", encoding="utf-8")
    return GenomeInputSpec(name=name, prepared=PreparedGenomeInputSpec(bed=bed, cds=cds))


def _write_bed(path: Path, prefix: str) -> Path:
    path.write_text(
        "\n".join(
            [
                f"{prefix}chr1\t1\t10\tqgene2\t0\t+",
                f"{prefix}chr1\t11\t20\tqgene3\t0\t+",
                f"{prefix}chr1\t21\t30\tshared\t0\t+",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def _job(tmp_path: Path, pair_id: str, target_name: str, query_bed: Path, subject_bed: Path) -> PairwiseJobSummary:
    blocks = tmp_path / f"{pair_id}.local.blocks"
    blocks.write_text("r*qgene2\tshared\nqgene3\tshared\n", encoding="utf-8")
    engine_summary = tmp_path / f"{pair_id}.engine.json"
    engine_summary.write_text(
        json.dumps({"artifacts": {"local_artifacts": [{"target": "qgene2", "blocks": str(blocks)}]}}),
        encoding="utf-8",
    )
    return PairwiseJobSummary(
        pair_id=pair_id,
        species_a_name="query",
        species_b_name=target_name,
        status="SUCCEEDED",
        outdir=str(tmp_path / pair_id),
        engine_summary_path=str(engine_summary),
        query_bed=str(query_bed),
        subject_bed=str(subject_bed),
    )


def test_multi_local_aggregate_scopes_gene_ids_per_species(tmp_path: Path) -> None:
    query_bed = _write_bed(tmp_path / "query.bed", "q")
    subject_bed = _write_bed(tmp_path / "subject.bed", "s")
    third_bed = _write_bed(tmp_path / "third.bed", "t")
    request = McscanExecutionRequest(
        query=_prepared("query", query_bed),
        subject=_prepared("subject", subject_bed),
        additional_species=[_prepared("third", third_bed)],
        outdir=tmp_path / "out",
        target_gene_ids=["qgene2"],
    )
    jobs = [
        _job(tmp_path, "query__subject", "subject", query_bed, subject_bed),
        _job(tmp_path, "query__third", "third", query_bed, third_bed),
    ]

    aggregates = _collect_target_aggregates(jobs)
    blocks, scoped_targets = _write_multi_local_blocks(tmp_path / "multi.blocks", request, jobs, aggregates)
    bed = _write_multi_local_bed(tmp_path / "multi.bed", request, jobs)

    assert scoped_targets == ["query__qgene2"]
    assert "r*query__qgene2\tsubject__shared\tthird__shared" in blocks.read_text(encoding="utf-8")
    bed_text = bed.read_text(encoding="utf-8")
    assert "query__qgene2" in bed_text
    assert "subject__shared" in bed_text
    assert "third__shared" in bed_text


def test_multi_local_aggregate_preserves_multiple_subject_hits(tmp_path: Path) -> None:
    query_bed = _write_bed(tmp_path / "query.bed", "q")
    subject_bed = _write_bed(tmp_path / "subject.bed", "s")
    third_bed = _write_bed(tmp_path / "third.bed", "t")
    request = McscanExecutionRequest(
        query=_prepared("query", query_bed),
        subject=_prepared("subject", subject_bed),
        additional_species=[_prepared("third", third_bed)],
        outdir=tmp_path / "out",
        target_gene_ids=["qgene2"],
    )
    blocks = tmp_path / "query__subject.local.blocks"
    blocks.write_text("r*qgene2\tshared\tqgene3\n", encoding="utf-8")
    engine_summary = tmp_path / "query__subject.engine.json"
    engine_summary.write_text(
        json.dumps({"artifacts": {"local_artifacts": [{"target": "qgene2", "blocks": str(blocks)}]}}),
        encoding="utf-8",
    )
    jobs = [
        PairwiseJobSummary(
            pair_id="query__subject",
            species_a_name="query",
            species_b_name="subject",
            status="SUCCEEDED",
            outdir=str(tmp_path / "query__subject"),
            engine_summary_path=str(engine_summary),
            query_bed=str(query_bed),
            subject_bed=str(subject_bed),
        ),
        _job(tmp_path, "query__third", "third", query_bed, third_bed),
    ]

    aggregates = _collect_target_aggregates(jobs)
    blocks_path, _scoped_targets = _write_multi_local_blocks(tmp_path / "multi.blocks", request, jobs, aggregates)
    rows = blocks_path.read_text(encoding="utf-8").splitlines()

    assert "r*query__qgene2\tsubject__shared\tthird__shared" in rows
    assert "r*query__qgene2\tsubject__qgene3\t." in rows
