import json
from pathlib import Path

from jcvi_genomelens.manifest_loader import load_manifest


def test_manifest_loader(tmp_path: Path) -> None:
    bed = tmp_path / "a.bed"
    cds = tmp_path / "a.cds"
    bed.write_text("chr1\t0\t3\tgene1\t0\t+\n", encoding="utf-8")
    cds.write_text(">gene1\nATG\n", encoding="utf-8")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": 2,
                "workflow": "graphics_synteny",
                "task": {
                    "task_id": "q__s__graphics_synteny",
                    "task_type": "pairwise_synteny",
                    "workflow": "graphics_synteny",
                    "source": "pytest",
                },
                "species": [
                    {"name": "q", "role": "query", "input_mode": "bed_cds", "bed": str(bed), "cds": str(cds)},
                    {"name": "s", "role": "subject", "input_mode": "bed_cds", "bed": str(bed), "cds": str(cds)},
                ],
                "query": {"name": "q", "bed": str(bed), "cds": str(cds)},
                "subject": {"name": "s", "bed": str(bed), "cds": str(cds)},
                "toolchain": {
                    "blastn": "",
                    "makeblastdb": "",
                    "lastal": "",
                    "lastdb": "",
                },
                "options": {
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
            }
        ),
        encoding="utf-8",
    )
    loaded = load_manifest(manifest)
    assert loaded.workflow == "graphics_synteny"
    assert loaded.query.name == "q"
    assert loaded.schema_version == 2
    assert loaded.task["task_type"] == "pairwise_synteny"
    assert loaded.options.align_soft == "blast"
    assert loaded.options.dbtype == "nucl"
    assert loaded.options.cscore == 0.7
    assert loaded.options.dist == 20
    assert loaded.options.iter == 1
    assert loaded.options.target_gene_ids == ["AT1G01010"]
    assert loaded.options.up == 20
    assert loaded.options.down == 20
    assert loaded.options.label_targets is True
    assert loaded.options.glyphstyle == "arrow"
    assert loaded.options.figsize == "10x5"
    assert loaded.options.dpi == 300
    assert loaded.options.auto_optimization["optimize_figsize"] is True
    assert loaded.options.auto_optimization["rewrite_layout_links"] is True
    assert loaded.options.auto_optimization["optimize_karyotype_labels"] is True
    assert loaded.toolchain.lastal is None
    assert loaded.toolchain.lastdb is None


def test_manifest_loader_heatmap(tmp_path: Path) -> None:
    matrix = tmp_path / "heatmap.csv"
    matrix.write_text("gene,s1,s2\ng1,1,2\ng2,3,4\n", encoding="utf-8")
    rowgroups = tmp_path / "rowgroups.tsv"
    rowgroups.write_text("I\tg1\nII\tg2\n", encoding="utf-8")
    manifest = tmp_path / "heatmap_manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": 2,
                "workflow": "graphics_heatmap",
                "task": {
                    "task_id": "heatmap__graphics_heatmap",
                    "task_type": "plot_heatmap",
                    "workflow": "graphics_heatmap",
                    "source": "pytest",
                },
                "toolchain": {},
                "matrix": str(matrix),
                "options": {
                    "formats": ["png"],
                    "figsize": "7x5",
                    "dpi": 200,
                    "cmap": "viridis",
                    "groups": True,
                    "rowgroups": str(rowgroups),
                    "horizontalbar": True,
                },
                "expected_outputs": ["figures", "heatmap_figures"],
            }
        ),
        encoding="utf-8",
    )
    loaded = load_manifest(manifest)
    assert loaded.workflow == "graphics_heatmap"
    assert loaded.matrix == matrix.resolve(strict=False)
    assert loaded.options.formats == ["png"]
    assert loaded.options.figsize == "7x5"
    assert loaded.options.dpi == 200
    assert loaded.options.cmap == "viridis"
    assert loaded.options.groups is True
    assert loaded.options.rowgroups == rowgroups.resolve(strict=False)
    assert loaded.options.horizontalbar is True


def test_manifest_loader_sub_module_id(tmp_path: Path) -> None:
    bed = tmp_path / "a.bed"
    cds = tmp_path / "a.cds"
    bed.write_text("chr1\t0\t3\tgene1\t0\t+\n", encoding="utf-8")
    cds.write_text(">gene1\nATG\n", encoding="utf-8")
    manifest = tmp_path / "submodule_manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": 2,
                "workflow": "graphics_dotplot",
                "sub_module_id": "jcvi.graphics_dotplot",
                "query": {"name": "q", "bed": str(bed), "cds": str(cds)},
                "subject": {"name": "s", "bed": str(bed), "cds": str(cds)},
                "toolchain": {},
                "options": {"formats": ["svg"]},
            }
        ),
        encoding="utf-8",
    )
    loaded = load_manifest(manifest)
    assert loaded.sub_module_id == "jcvi.graphics_dotplot"
