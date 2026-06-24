import json
from pathlib import Path

import pytest

from jcvi_genomelens.manifest.loader import ManifestError, load_manifest


def test_manifest_loader_pairwise_schema_v3(tmp_path: Path) -> None:
    bed = tmp_path / "a.bed"
    cds = tmp_path / "a.cds"
    bed.write_text("chr1\t0\t3\tgene1\t0\t+\n", encoding="utf-8")
    cds.write_text(">gene1\nATG\n", encoding="utf-8")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": 3,
                "workflow": "graphics_synteny",
                "task": {
                    "task_id": "q__s__graphics_synteny",
                    "task_type": "pairwise_synteny",
                    "workflow": "graphics_synteny",
                },
                "inputs": {
                    "species": [
                        {"name": "q", "role": "reference", "input_mode": "bed_cds", "bed": str(bed), "cds": str(cds)},
                        {"name": "s", "role": "target", "input_mode": "bed_cds", "bed": str(bed), "cds": str(cds)},
                    ]
                },
                "toolchain": {"blastn": "", "makeblastdb": "", "lastal": "", "lastdb": ""},
                "parameters": {
                    "threads": 1,
                    "min_block_size": 1,
                    "formats": ["png"],
                    "align_soft": "blast",
                    "dbtype": "nucl",
                    "cscore": 0.7,
                    "dist": 20,
                    "iter": 1,
                    "target_gene_ids": ["AT1G01010"],
                    "up": 20,
                    "down": 20,
                    "split_targets": False,
                    "label_targets": True,
                    "glyphstyle": "arrow",
                    "glyphcolor": "orthogroup",
                    "shadestyle": "curve",
                    "figsize": "10x5",
                    "dpi": 300,
                    "auto_optimization": {
                        "optimize_figsize": True,
                        "rewrite_layout_links": True,
                        "optimize_karyotype_labels": True,
                    },
                },
                "expected_outputs": ["blast_table", "figures"],
                "meta": {},
            }
        ),
        encoding="utf-8",
    )

    loaded = load_manifest(manifest)

    assert loaded.workflow == "graphics_synteny"
    assert loaded.query is not None
    assert loaded.subject is not None
    assert loaded.query.name == "q"
    assert loaded.subject.name == "s"
    assert loaded.schema_version == 3
    assert loaded.task["task_type"] == "pairwise_synteny"
    assert loaded.options.formats == ["png"]
    assert loaded.options.target_gene_ids == ["AT1G01010"]
    assert loaded.options.auto_optimization["rewrite_layout_links"] is True


def test_manifest_loader_heatmap_schema_v3(tmp_path: Path) -> None:
    matrix = tmp_path / "heatmap.csv"
    matrix.write_text("gene,s1,s2\ng1,1,2\ng2,3,4\n", encoding="utf-8")
    rowgroups = tmp_path / "rowgroups.tsv"
    rowgroups.write_text("I\tg1\nII\tg2\n", encoding="utf-8")
    manifest = tmp_path / "heatmap_manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": 3,
                "workflow": "graphics_heatmap",
                "task": {"task_id": "heatmap", "task_type": "plot_heatmap", "workflow": "graphics_heatmap"},
                "inputs": {"matrix": str(matrix)},
                "toolchain": {},
                "parameters": {
                    "formats": ["png"],
                    "figsize": "7x5",
                    "dpi": 200,
                    "cmap": "viridis",
                    "groups": True,
                    "rowgroups": str(rowgroups),
                    "horizontalbar": True,
                },
                "expected_outputs": ["figures", "heatmap_figures"],
                "meta": {},
            }
        ),
        encoding="utf-8",
    )

    loaded = load_manifest(manifest)

    assert loaded.workflow == "graphics_heatmap"
    assert loaded.matrix == matrix.resolve(strict=False)
    assert loaded.options.formats == ["png"]
    assert loaded.options.rowgroups == rowgroups.resolve(strict=False)
    assert loaded.options.horizontalbar is True


def test_manifest_loader_pairwise_artifact_bundles_round_trip(tmp_path: Path) -> None:
    bed = tmp_path / "a.bed"
    cds = tmp_path / "a.cds"
    blocks = tmp_path / "a.blocks"
    bed.write_text("chr1\t0\t3\tgene1\t0\t+\n", encoding="utf-8")
    cds.write_text(">gene1\nATG\n", encoding="utf-8")
    blocks.write_text("g1\tg2\n", encoding="utf-8")
    manifest = tmp_path / "bundle_manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": 3,
                "workflow": "graphics_synteny",
                "task": {"task_id": "bundle", "task_type": "pairwise_synteny", "workflow": "graphics_synteny"},
                "inputs": {
                    "species": [
                        {"name": "q", "role": "reference", "input_mode": "bed_cds", "bed": str(bed), "cds": str(cds)},
                        {"name": "s", "role": "target", "input_mode": "bed_cds", "bed": str(bed), "cds": str(cds)},
                    ],
                    "artifact_bundles": [{"bundle_type": "pairwise_core", "artifacts": {"blocks": str(blocks)}}],
                },
                "toolchain": {},
                "parameters": {"formats": ["svg"]},
                "expected_outputs": ["blocks"],
                "meta": {},
            }
        ),
        encoding="utf-8",
    )

    loaded = load_manifest(manifest)

    assert len(loaded.artifact_bundles) == 1
    assert loaded.artifact_bundles[0].bundle_type == "pairwise_core"
    assert loaded.artifact_bundles[0].artifact_path("blocks") == blocks.resolve(strict=False)
    assert loaded.pairwise_artifacts is not None
    assert loaded.pairwise_artifacts.blocks == blocks.resolve(strict=False)


def test_manifest_loader_rejects_v2_top_level_query_subject(tmp_path: Path) -> None:
    manifest = tmp_path / "legacy_manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": 2,
                "workflow": "graphics_synteny",
                "query": {"name": "q", "bed": "q.bed", "cds": "q.cds"},
                "subject": {"name": "s", "bed": "s.bed", "cds": "s.cds"},
                "toolchain": {},
                "options": {},
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ManifestError, match="schema_version"):
        load_manifest(manifest)
