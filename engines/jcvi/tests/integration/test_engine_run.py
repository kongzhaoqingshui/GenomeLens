import json
from pathlib import Path

from jcvi_genomelens.engine_runtime import run_manifest

ROOT = Path(__file__).resolve().parents[4]
SAMPLE = ROOT / "references" / "samples" / "shell" / "bed_cds_minimal"
BLAST_BIN = ROOT / "toolchains" / "blast" / "current" / "bin"


def _manifest(workflow: str) -> dict[str, object]:
    return {
        "schema_version": 2,
        "workflow": workflow,
        "task": {
            "task_id": f"query__subject__{workflow}",
            "task_type": "pairwise_synteny",
            "workflow": workflow,
            "source": "pytest",
        },
        "species": [
            {
                "name": "query",
                "role": "query",
                "input_mode": "bed_cds",
                "bed": str(SAMPLE / "query.bed"),
                "cds": str(SAMPLE / "query.cds"),
            },
            {
                "name": "subject",
                "role": "subject",
                "input_mode": "bed_cds",
                "bed": str(SAMPLE / "subject.bed"),
                "cds": str(SAMPLE / "subject.cds"),
            },
        ],
        "query": {"name": "query", "bed": str(SAMPLE / "query.bed"), "cds": str(SAMPLE / "query.cds")},
        "subject": {
            "name": "subject",
            "bed": str(SAMPLE / "subject.bed"),
            "cds": str(SAMPLE / "subject.cds"),
        },
        "toolchain": {
            "blastn": str(BLAST_BIN / "blastn.exe"),
            "makeblastdb": str(BLAST_BIN / "makeblastdb.exe"),
        },
        "options": {"threads": 1, "min_block_size": 1, "formats": ["png"]},
        "expected_outputs": ["blast_table", "anchors", "simple", "blocks", "figures"],
    }


def test_engine_run_graphics_synteny(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps(_manifest("graphics_synteny")), encoding="utf-8")
    summary_path = run_manifest(manifest, tmp_path / "engine")
    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    assert payload["status"] == "ok"
    assert payload["schema_version"] == 2
    assert payload["task"]["task_type"] == "pairwise_synteny"
    assert [item["role"] for item in payload["species"]] == ["query", "subject"]
    assert payload["distribution"] == "source"
    assert payload["runtime_mode"] in {"core", "accelerated"}
    assert isinstance(payload["loaded_extensions"], list)
    assert isinstance(payload["missing_extensions"], list)
    command_names = [command["name"] for command in payload["commands"]]
    assert command_names == [
        "makeblastdb.exe",
        "blastn.exe",
        "jcvi.compara.synteny.scan",
        "jcvi.compara.synteny.simple",
        "jcvi.compara.synteny.mcscan",
        "jcvi.formats.bed.merge",
        "jcvi.graphics.dotplot",
        "jcvi.graphics.synteny",
    ]
    assert Path(payload["artifacts"]["blast_table"]).stat().st_size > 0
    assert Path(payload["artifacts"]["anchors"]).is_file()
    assert Path(payload["artifacts"]["dotplot_figures"][0]).is_file()
    assert Path(payload["artifacts"]["synteny_figures"][0]).is_file()
    assert any(item["artifact_type"] == "dotplot_figures" for item in payload["artifact_index"])
    assert any(item["preview"] for item in payload["artifact_index"])
    assert payload["artifacts"]["simplified_fallback"] is False


def test_engine_run_graphics_dotplot(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps(_manifest("graphics_dotplot")), encoding="utf-8")
    summary_path = run_manifest(manifest, tmp_path / "engine")
    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    assert payload["status"] == "ok"
    assert [command["name"] for command in payload["commands"]][-1] == "jcvi.graphics.dotplot"
    assert Path(payload["artifacts"]["dotplot_figures"][0]).is_file()


def test_engine_run_graphics_karyotype(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps(_manifest("graphics_karyotype")), encoding="utf-8")
    summary_path = run_manifest(manifest, tmp_path / "engine")
    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    assert payload["status"] == "ok"
    assert [command["name"] for command in payload["commands"]][-1] == "jcvi.graphics.karyotype"
    assert Path(payload["artifacts"]["karyotype_figures"][0]).is_file()
    assert Path(payload["artifacts"]["karyotype_seqids"]).is_file()
    assert Path(payload["artifacts"]["karyotype_layout"]).is_file()


def test_engine_run_catalog_ortholog(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps(_manifest("catalog_ortholog")), encoding="utf-8")
    summary_path = run_manifest(manifest, tmp_path / "engine")
    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    assert payload["status"] == "ok"
    assert [command["name"] for command in payload["commands"]] == ["jcvi.compara.catalog.ortholog"]
    command_stderr = payload["commands"][0]["stderr"]
    assert "Objective value = 4" in command_stderr
    assert "MCscan blocks written" in command_stderr
    assert Path(payload["artifacts"]["ortholog"]).stat().st_size > 0
    assert Path(payload["artifacts"]["reverse_ortholog"]).stat().st_size > 0
    assert Path(payload["artifacts"]["blast_table"]).stat().st_size > 0
    assert payload["artifacts"]["backend"] == "jcvi.catalog.ortholog"


def test_engine_run_bed_summary(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps(_manifest("bed_summary")), encoding="utf-8")
    summary_path = run_manifest(manifest, tmp_path / "engine")
    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    assert payload["status"] == "ok"
    assert [command["name"] for command in payload["commands"]] == [
        "jcvi.formats.bed.summary",
        "jcvi.formats.bed.summary",
    ]
    query_summary = Path(payload["artifacts"]["query_bed_summary"])
    subject_summary = Path(payload["artifacts"]["subject_bed_summary"])
    assert query_summary.is_file()
    assert subject_summary.is_file()
    query_payload = json.loads(query_summary.read_text(encoding="utf-8"))
    assert query_payload["species"] == "query"
    assert query_payload["feature_count"] == 4
    assert query_payload["seqid_count"] == 1
    assert payload["artifacts"]["backend"] == "jcvi.formats.bed.summary"


def test_engine_run_graphics_karyotype_global(tmp_path: Path) -> None:
    # 先跑一对 pairwise 拿到真实 .anchors.simple，再喂给全局总图工作流。
    pairwise_manifest = tmp_path / "pairwise.json"
    pairwise_manifest.write_text(json.dumps(_manifest("mcscan_pairwise")), encoding="utf-8")
    pairwise_summary = json.loads(run_manifest(pairwise_manifest, tmp_path / "pairwise").read_text(encoding="utf-8"))
    assert pairwise_summary["status"] == "ok"
    simple = pairwise_summary["artifacts"]["simple"]
    assert Path(simple).is_file()

    third_bed = tmp_path / "third.bed"
    third_bed.write_text((SAMPLE / "subject.bed").read_text(encoding="utf-8"), encoding="utf-8")
    global_manifest = {
        "schema_version": 2,
        "workflow": "graphics_karyotype_global",
        "task": {"task_id": "global", "task_type": "multi_species_synteny", "source": "pytest"},
        "tracks": [
            {"name": "query", "bed": str(SAMPLE / "query.bed")},
            {"name": "subject", "bed": str(SAMPLE / "subject.bed")},
            {"name": "third", "bed": str(third_bed)},
        ],
        "edges": [
            {"i": 0, "j": 1, "simple": simple},
            {"i": 0, "j": 2, "simple": simple},
        ],
        "toolchain": {},
        "options": {"formats": ["png"], "optimize_figsize": True, "rewrite_layout_links": True},
        "expected_outputs": ["figures"],
    }
    manifest = tmp_path / "global.json"
    manifest.write_text(json.dumps(global_manifest), encoding="utf-8")
    summary_path = run_manifest(manifest, tmp_path / "global")
    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    assert payload["status"] == "ok"
    assert [command["name"] for command in payload["commands"]] == ["jcvi.graphics.karyotype"]
    assert payload["artifacts"]["track_count"] == 3
    assert payload["artifacts"]["edge_count"] == 2
    assert payload["artifacts"]["rewritten_layout_edges"] == 2
    assert payload["artifacts"]["rewritten_track_order"] == ["subject", "query", "third"]
    assert payload["artifacts"]["optimized_figsize"]
    assert "--figsize" in payload["commands"][0]["argv"]
    assert Path(payload["artifacts"]["global_karyotype_figures"][0]).is_file()
    assert Path(payload["artifacts"]["global_karyotype_seqids"]).is_file()
    assert Path(payload["artifacts"]["global_karyotype_layout"]).is_file()


def test_engine_run_local_synteny_multi(tmp_path: Path) -> None:
    bed = tmp_path / "local_multi.bed"
    bed.write_text(
        "\n".join(
            [
                "qchr1\t0\t10\tqgene1\t0\t+",
                "qchr1\t10\t20\tqgene2\t0\t+",
                "schr1\t0\t10\tsgene1\t0\t+",
                "schr1\t10\t20\tsgene2\t0\t+",
                "tchr1\t0\t10\ttgene1\t0\t+",
                "tchr1\t10\t20\ttgene2\t0\t+",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    blocks = tmp_path / "local_multi.blocks"
    blocks.write_text("qgene1\tsgene1\ttgene1\nqgene2\tsgene2\ttgene2\n", encoding="utf-8")
    manifest = {
        "schema_version": 2,
        "workflow": "local_synteny_multi",
        "task": {"task_id": "local", "task_type": "multi_species_local_synteny", "source": "pytest"},
        "tracks": [
            {"name": "query", "bed": str(bed)},
            {"name": "subject", "bed": str(bed)},
            {"name": "third", "bed": str(bed)},
        ],
        "blocks": str(blocks),
        "bed": str(bed),
        "toolchain": {},
        "options": {
            "formats": ["png"],
            "target_gene_ids": ["qgene1"],
            "optimize_figsize": True,
            "rewrite_layout_links": True,
        },
        "expected_outputs": ["figures"],
    }
    manifest_path = tmp_path / "local_multi.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    summary_path = run_manifest(manifest_path, tmp_path / "local")
    payload = json.loads(summary_path.read_text(encoding="utf-8"))

    assert payload["status"] == "ok"
    assert [command["name"] for command in payload["commands"]] == ["jcvi.graphics.synteny"]
    assert payload["artifacts"]["rewritten_layout_edges"] == 2
    assert payload["artifacts"]["optimized_figsize"]
    assert "--figsize" in payload["commands"][0]["argv"]
    layout_text = Path(payload["artifacts"]["multi_species_local_layout"]).read_text(encoding="utf-8")
    assert "e, 0, 1, #c8c8c8" in layout_text
    assert "e, 1, 2, #c8c8c8" in layout_text
    assert "e, 0, 2, #c8c8c8" not in layout_text
    assert Path(payload["artifacts"]["multi_species_local_figures"][0]).is_file()


def test_engine_rejects_simplified_fallback(tmp_path: Path) -> None:
    data = _manifest("graphics_synteny")
    data["options"] = {**data["options"], "allow_simplified_fallback": True}
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps(data), encoding="utf-8")
    summary_path = run_manifest(manifest, tmp_path / "engine")
    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    assert payload["status"] == "failed"
    assert payload["runtime_mode"] in {"core", "accelerated"}
    assert "allow_simplified_fallback is not implemented" in payload["error"]["message"]
