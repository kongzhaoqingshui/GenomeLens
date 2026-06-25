import json
import shutil
from pathlib import Path

from jcvi_genomelens.runtime.engine import run_manifest

ROOT = Path(__file__).resolve().parents[4]
SAMPLE = ROOT / "references" / "samples" / "shell" / "bed_cds_minimal"
BLAST_BIN = ROOT / "toolchains" / "blast" / "current" / "bin"


def _blast_executable(name: str) -> Path:
    candidate = shutil.which(name)
    if candidate:
        return Path(candidate).resolve()
    return (BLAST_BIN / f"{name}.exe").resolve()


def _manifest(workflow: str, *, extra_parameters: dict[str, object] | None = None) -> dict[str, object]:
    species = [
        {
            "name": "query",
            "role": "reference",
            "input_mode": "bed_cds",
            "bed": str(SAMPLE / "query.bed"),
            "cds": str(SAMPLE / "query.cds"),
        },
        {
            "name": "subject",
            "role": "target",
            "input_mode": "bed_cds",
            "bed": str(SAMPLE / "subject.bed"),
            "cds": str(SAMPLE / "subject.cds"),
        },
    ]
    return {
        "schema_version": 3,
        "workflow": workflow,
        "task": {
            "task_id": f"query__subject__{workflow}",
            "task_type": "pairwise_synteny",
            "workflow": workflow,
            "source": "pytest",
        },
        "inputs": {"species": species},
        "species": species,
        "toolchain": {
            "blastn": str(_blast_executable("blastn")),
            "makeblastdb": str(_blast_executable("makeblastdb")),
        },
        "parameters": {"threads": 1, "min_block_size": 1, "formats": ["png"], **(extra_parameters or {})},
        "expected_outputs": ["blast_table", "anchors", "simple", "blocks", "figures"],
    }


def _heatmap_manifest(matrix: Path, rowgroups: Path | None = None) -> dict[str, object]:
    options: dict[str, object] = {
        "formats": ["png"],
        "figsize": "6x4",
        "dpi": 150,
        "cmap": "viridis",
        "groups": True,
        "horizontalbar": True,
    }
    if rowgroups is not None:
        options["rowgroups"] = str(rowgroups)
    return {
        "schema_version": 3,
        "workflow": "graphics_heatmap",
        "task": {
            "task_id": "heatmap__graphics_heatmap",
            "task_type": "plot_heatmap",
            "workflow": "graphics_heatmap",
            "source": "pytest",
        },
        "toolchain": {},
        "inputs": {"matrix": str(matrix)},
        "parameters": options,
        "expected_outputs": ["figures", "heatmap_figures"],
    }


def _run_pairwise_artifacts(tmp_path: Path, *, subdir: str = "pairwise") -> dict[str, object]:
    """先跑一遍 pairwise 计算工作流，返回其产出的产物字典，供下游渲染工作流复用"""

    pairwise_manifest = tmp_path / f"{subdir}.json"
    pairwise_manifest.write_text(json.dumps(_manifest("pairwise")), encoding="utf-8")
    summary = json.loads(run_manifest(pairwise_manifest, tmp_path / subdir).read_text(encoding="utf-8"))
    assert summary["status"] == "ok"
    return summary["artifacts"]


def _render_manifest(
    workflow: str,
    pairwise_artifacts: dict[str, object],
    *,
    parameters: dict[str, object] | None = None,
) -> dict[str, object]:
    """构造复用上游 pairwise 产物的渲染工作流 manifest（渲染层绝不自行计算）"""

    data = _manifest(workflow)
    data["inputs"]["pairwise_artifacts"] = {
        key: pairwise_artifacts[key]
        for key in ("blast_table", "anchors", "simple", "blocks", "merged_bed", "layout")
        if pairwise_artifacts.get(key)
    }
    if parameters:
        data["parameters"] = {**data["parameters"], **parameters}
    return data


def test_engine_run_graphics_synteny(tmp_path: Path) -> None:
    pairwise_artifacts = _run_pairwise_artifacts(tmp_path)
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps(_render_manifest("graphics_synteny", pairwise_artifacts)), encoding="utf-8")
    summary_path = run_manifest(manifest, tmp_path / "engine")
    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    assert payload["status"] == "ok"
    assert payload["schema_version"] == 3
    assert payload["task"]["task_type"] == "pairwise_synteny"
    assert [item["role"] for item in payload["species"]] == ["reference", "target"]
    assert payload["distribution"] == "source"
    assert payload["runtime_mode"] in {"core", "accelerated"}
    assert isinstance(payload["loaded_extensions"], list)
    assert isinstance(payload["missing_extensions"], list)
    command_names = [command["name"] for command in payload["commands"]]
    # 渲染层只剩绘图命令，不再偷偷重算 blast/scan/mcscan
    assert command_names == [
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
    pairwise_artifacts = _run_pairwise_artifacts(tmp_path)
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps(_render_manifest("graphics_dotplot", pairwise_artifacts)), encoding="utf-8")
    summary_path = run_manifest(manifest, tmp_path / "engine")
    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    assert payload["status"] == "ok"
    assert [command["name"] for command in payload["commands"]] == ["jcvi.graphics.dotplot"]
    assert Path(payload["artifacts"]["dotplot_figures"][0]).is_file()


def test_engine_run_graphics_heatmap(tmp_path: Path) -> None:
    matrix = tmp_path / "matrix.csv"
    matrix.write_text(",grpA,,grpB,\n,g1,g2,g1,g2\ngene1,1,10,100,1000\ngene2,5,20,250,500\n", encoding="utf-8")
    rowgroups = tmp_path / "rowgroups.tsv"
    rowgroups.write_text("I\tgene1\nII\tgene2\n", encoding="utf-8")
    manifest = tmp_path / "heatmap.json"
    manifest.write_text(json.dumps(_heatmap_manifest(matrix, rowgroups)), encoding="utf-8")
    summary_path = run_manifest(manifest, tmp_path / "heatmap")
    payload = json.loads(summary_path.read_text(encoding="utf-8"))

    assert payload["status"] == "ok"
    assert [command["name"] for command in payload["commands"]] == ["jcvi.graphics.heatmap"]
    assert payload["task"]["task_type"] == "plot_heatmap"
    assert payload["artifacts"]["backend"] == "jcvi.graphics.heatmap"
    assert payload["artifacts"]["heatmap_cmap"] == "viridis"
    assert payload["artifacts"]["heatmap_groups"] is True
    assert payload["artifacts"]["heatmap_horizontalbar"] is True
    assert Path(payload["artifacts"]["matrix"]).is_file()
    assert Path(payload["artifacts"]["rowgroups"]).is_file()
    assert Path(payload["artifacts"]["heatmap_figures"][0]).is_file()
    assert any(item["artifact_type"] == "heatmap_figures" for item in payload["artifact_index"])


def test_engine_run_graphics_histogram(tmp_path: Path) -> None:
    numbers = tmp_path / "numbers.txt"
    numbers.write_text("1\n2\n2\n3\n5\n8\n13\n", encoding="utf-8")
    manifest = {
        "schema_version": 3,
        "workflow": "graphics_histogram",
        "task": {"task_id": "histogram", "task_type": "plot_histogram", "workflow": "graphics_histogram"},
        "species": [],
        "toolchain": {},
        "inputs": {"histogram_files": [str(numbers)]},
        "parameters": {
            "formats": ["png", "svg"],
            "dpi": 150,
            "histogram_columns": [0],
            "histogram_bins": 4,
            "histogram_vmin": 0,
            "histogram_xlabel": "Ks",
            "histogram_title": "Histogram",
            "histogram_fill": "#8fb9a8",
        },
        "expected_outputs": ["figures"],
        "meta": {"source": "pytest"},
    }
    manifest_path = tmp_path / "histogram.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    summary_path = run_manifest(manifest_path, tmp_path / "histogram")
    payload = json.loads(summary_path.read_text(encoding="utf-8"))

    assert payload["status"] == "ok"
    assert [command["name"] for command in payload["commands"]] == ["genomelens.graphics_histogram"]
    assert len(payload["artifacts"]["histogram_figures"]) == 2
    assert all(Path(path).is_file() for path in payload["artifacts"]["histogram_figures"])
    assert payload["artifacts"]["histogram_columns"] == [0]
    assert payload["artifacts"]["histogram_bins"] == 4
    assert payload["artifacts"]["backend"] == "genomelens.matplotlib.histogram"


def test_engine_run_graphics_karyotype(tmp_path: Path) -> None:
    pairwise_artifacts = _run_pairwise_artifacts(tmp_path)
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps(_render_manifest("graphics_karyotype", pairwise_artifacts)), encoding="utf-8")
    summary_path = run_manifest(manifest, tmp_path / "engine")
    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    assert payload["status"] == "ok"
    assert [command["name"] for command in payload["commands"]][-1] == "jcvi.graphics.karyotype"
    assert Path(payload["artifacts"]["karyotype_figures"][0]).is_file()
    assert Path(payload["artifacts"]["karyotype_seqids"]).is_file()
    assert Path(payload["artifacts"]["karyotype_layout"]).is_file()
    assert payload["artifacts"]["karyotype_renderer_variant"] == "vendored"
    assert payload["artifacts"]["optimize_karyotype_labels"] is False


def test_engine_run_graphics_karyotype_with_label_overlap_fix(tmp_path: Path) -> None:
    pairwise_artifacts = _run_pairwise_artifacts(tmp_path)
    data = _render_manifest(
        "graphics_karyotype",
        pairwise_artifacts,
        parameters={"auto_optimization": {"optimize_karyotype_labels": True}},
    )
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps(data), encoding="utf-8")
    summary_path = run_manifest(manifest, tmp_path / "engine")
    payload = json.loads(summary_path.read_text(encoding="utf-8"))

    assert payload["status"] == "ok"
    assert payload["artifacts"]["karyotype_renderer_variant"] == "mirrored"
    assert payload["artifacts"]["optimize_karyotype_labels"] is True
    layout_text = Path(payload["artifacts"]["karyotype_layout"]).read_text(encoding="utf-8")
    assert "label_va" in layout_text
    assert "0.12, 0.88" in layout_text


def test_engine_run_pairwise_emit_ortholog(tmp_path: Path) -> None:
    # 合并后的 pairwise 计算工作流：emit_ortholog=True 时透传双向 ortholog 目录
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(_manifest("pairwise", extra_parameters={"emit_ortholog": True})),
        encoding="utf-8",
    )
    summary_path = run_manifest(manifest, tmp_path / "engine")
    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    assert payload["status"] == "ok"
    command_names = [command["name"] for command in payload["commands"]]
    assert "jcvi.compara.catalog.ortholog" in command_names
    assert Path(payload["artifacts"]["ortholog"]).stat().st_size > 0
    assert Path(payload["artifacts"]["reverse_ortholog"]).stat().st_size > 0
    assert Path(payload["artifacts"]["blast_table"]).stat().st_size > 0
    assert payload["artifacts"]["backend"] == "jcvi"


def test_engine_run_graphics_karyotype_global(tmp_path: Path) -> None:
    # 先跑一对 pairwise 拿到真实 .anchors.simple，再喂给全局总图工作流
    pairwise_manifest = tmp_path / "pairwise.json"
    pairwise_manifest.write_text(json.dumps(_manifest("pairwise")), encoding="utf-8")
    pairwise_summary = json.loads(run_manifest(pairwise_manifest, tmp_path / "pairwise").read_text(encoding="utf-8"))
    assert pairwise_summary["status"] == "ok"
    simple = pairwise_summary["artifacts"]["simple"]
    assert Path(simple).is_file()

    third_bed = tmp_path / "third.bed"
    third_bed.write_text((SAMPLE / "subject.bed").read_text(encoding="utf-8"), encoding="utf-8")
    global_manifest = {
        "schema_version": 3,
        "workflow": "graphics_karyotype_global",
        "task": {"task_id": "global", "task_type": "multi_species_synteny", "source": "pytest"},
        "inputs": {
            "tracks": [
                {"name": "query", "bed": str(SAMPLE / "query.bed")},
                {"name": "subject", "bed": str(SAMPLE / "subject.bed")},
                {"name": "third", "bed": str(third_bed)},
            ],
            "edges": [
                {"i": 0, "j": 1, "simple": simple},
                {"i": 0, "j": 2, "simple": simple},
            ],
        },
        "toolchain": {},
        "parameters": {
            "formats": ["png"],
            "auto_optimization": {
                "optimize_figsize": True,
                "rewrite_layout_links": True,
            },
        },
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
    assert payload["artifacts"]["karyotype_renderer_variant"] == "vendored"
    assert payload["artifacts"]["optimize_karyotype_labels"] is False
    assert "--figsize" in payload["commands"][0]["argv"]
    assert Path(payload["artifacts"]["global_karyotype_figures"][0]).is_file()
    assert Path(payload["artifacts"]["global_karyotype_seqids"]).is_file()
    assert Path(payload["artifacts"]["global_karyotype_layout"]).is_file()


def test_engine_run_graphics_karyotype_global_with_label_overlap_fix(tmp_path: Path) -> None:
    pairwise_manifest = tmp_path / "pairwise.json"
    pairwise_manifest.write_text(json.dumps(_manifest("pairwise")), encoding="utf-8")
    pairwise_summary = json.loads(run_manifest(pairwise_manifest, tmp_path / "pairwise").read_text(encoding="utf-8"))
    simple = pairwise_summary["artifacts"]["simple"]

    third_bed = tmp_path / "third.bed"
    third_bed.write_text((SAMPLE / "subject.bed").read_text(encoding="utf-8"), encoding="utf-8")
    global_manifest = {
        "schema_version": 3,
        "workflow": "graphics_karyotype_global",
        "task": {"task_id": "global", "task_type": "multi_species_synteny", "source": "pytest"},
        "inputs": {
            "tracks": [
                {"name": "query", "bed": str(SAMPLE / "query.bed")},
                {"name": "subject", "bed": str(SAMPLE / "subject.bed")},
                {"name": "third", "bed": str(third_bed)},
            ],
            "edges": [
                {"i": 0, "j": 1, "simple": simple},
                {"i": 0, "j": 2, "simple": simple},
            ],
        },
        "toolchain": {},
        "parameters": {
            "formats": ["png"],
            "auto_optimization": {
                "optimize_figsize": True,
                "rewrite_layout_links": True,
                "optimize_karyotype_labels": True,
            },
        },
        "expected_outputs": ["figures"],
    }
    manifest = tmp_path / "global.json"
    manifest.write_text(json.dumps(global_manifest), encoding="utf-8")
    summary_path = run_manifest(manifest, tmp_path / "global")
    payload = json.loads(summary_path.read_text(encoding="utf-8"))

    assert payload["status"] == "ok"
    assert payload["artifacts"]["karyotype_renderer_variant"] == "mirrored"
    assert payload["artifacts"]["optimize_karyotype_labels"] is True
    layout_text = Path(payload["artifacts"]["global_karyotype_layout"]).read_text(encoding="utf-8")
    assert "label_va" in layout_text
    assert "0.12, 0.88" in layout_text


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
        "schema_version": 3,
        "workflow": "local_synteny_multi",
        "task": {"task_id": "local", "task_type": "multi_species_local_synteny", "source": "pytest"},
        "inputs": {
            "tracks": [
                {"name": "query", "bed": str(bed)},
                {"name": "subject", "bed": str(bed)},
                {"name": "third", "bed": str(bed)},
            ],
            "blocks": str(blocks),
            "bed": str(bed),
        },
        "toolchain": {},
        "parameters": {
            "formats": ["png"],
            "target_gene_ids": ["qgene1"],
            "auto_optimization": {
                "optimize_figsize": True,
                "rewrite_layout_links": True,
            },
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


def test_engine_run_local_synteny_multi_native_renderer(tmp_path: Path) -> None:
    bed = tmp_path / "local_multi.bed"
    bed.write_text(
        "\n".join(
            [
                "qchr1\t0\t10\tqgene1\t0\t+",
                "qchr1\t10\t20\tqgene2\t0\t+",
                "schr5\t0\t10\tsgene1\t0\t+",
                "schr2\t2000000\t2000010\tsgene2\t0\t+",
                "tchr1\t0\t10\ttgene1\t0\t+",
                "tchr3\t100\t110\ttgene2\t0\t+",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    blocks = tmp_path / "local_multi.blocks"
    blocks.write_text("r*qgene1\tsgene1\ttgene1\nqgene2\tsgene2\ttgene2\n", encoding="utf-8")
    manifest = {
        "schema_version": 3,
        "workflow": "local_synteny_multi",
        "task": {"task_id": "local-native", "task_type": "multi_species_local_synteny", "source": "pytest"},
        "inputs": {
            "tracks": [
                {"name": "query", "bed": str(bed)},
                {"name": "subject", "bed": str(bed)},
                {"name": "third", "bed": str(bed)},
            ],
            "blocks": str(blocks),
            "bed": str(bed),
        },
        "toolchain": {},
        "parameters": {
            "formats": ["svg"],
            "target_gene_ids": ["qgene1"],
            "use_native_local_synteny_renderer": True,
            "auto_optimization": {
                "optimize_figsize": True,
            },
        },
        "expected_outputs": ["figures"],
    }
    manifest_path = tmp_path / "local_multi_native.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    summary_path = run_manifest(manifest_path, tmp_path / "local-native")
    payload = json.loads(summary_path.read_text(encoding="utf-8"))

    assert payload["status"] == "ok"
    assert [command["name"] for command in payload["commands"]] == ["local_synteny_renderer"]
    assert payload["artifacts"]["backend"] == "local_synteny_renderer"
    figure = Path(payload["artifacts"]["multi_species_local_figures"][0])
    assert figure.is_file()
    content = figure.read_text(encoding="utf-8")
    assert "schr5" in content
    assert "schr2" in content


def test_engine_rejects_simplified_fallback(tmp_path: Path) -> None:
    data = _manifest("graphics_synteny")
    data["parameters"] = {**data["parameters"], "allow_simplified_fallback": True}
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps(data), encoding="utf-8")
    summary_path = run_manifest(manifest, tmp_path / "engine")
    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    assert payload["status"] == "failed"
    assert payload["runtime_mode"] in {"core", "accelerated"}
    assert "allow_simplified_fallback is not implemented" in payload["error"]["message"]
