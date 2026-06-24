import json
import logging
from pathlib import Path
from typing import Any, Callable, Protocol, cast

import pytest

from features.onestop import synteny_entry
from features.submodules import (
    catalog_ortholog_entry,
    dotplot_entry,
    global_karyotype_entry,
    heatmap_entry,
    histogram_entry,
    karyotype_entry,
    local_synteny_entry,
    mcscan_pairwise_entry,
    multi_local_synteny_entry,
    synteny_figure_entry,
)


class FeatureEntryModule(Protocol):
    def build_runtime_command(self, params_path: str | Path) -> list[str]: ...
    def main(self, argv: list[str] | None = None) -> int: ...


def _write_params_from_sample(
    tmp_path: Path, *, overrides: dict[str, Any] | None = None
) -> Path:
    root = Path(__file__).resolve().parents[3]
    sample_params = root / "references" / "samples" / "haiant" / "params.json"
    payload = cast(
        dict[str, Any],
        json.loads(sample_params.read_text(encoding="utf-8")),
    )

    genomelens_exe = tmp_path / "GenomeLens.cmd"
    genomelens_exe.write_text("@echo off\r\n", encoding="utf-8")

    sample_input_dir = (
        sample_params.parent / payload.get("input_dir", "../shell/bed_cds_minimal")
    ).resolve()
    payload["genomelens_exe"] = str(genomelens_exe)
    payload["input_dir"] = str(sample_input_dir)
    payload["output_dir"] = str(tmp_path / "output")
    payload["target_gene_ids"] = "qgene1"

    if overrides:
        payload.update(overrides)

    params_path = tmp_path / "params.json"
    params_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return params_path


def _submodule_argv(argv: list[str]) -> tuple[str, dict[str, object], str]:
    module_index = argv.index("submodule") + 1
    ports_index = argv.index("--input-ports") + 1
    output_index = argv.index("--output-dir") + 1
    return (
        argv[module_index],
        cast(dict[str, object], json.loads(argv[ports_index])),
        argv[output_index],
    )


def _touch(path: Path) -> str:
    path.write_text("", encoding="utf-8")
    return str(path)


# 每个子模块入口的最小可运行 override 工厂；返回喂给 ``_write_params_from_sample`` 的额外参数。
def _no_overrides(_tmp_path: Path) -> dict[str, Any]:
    return {}


def _dotplot_overrides(tmp_path: Path) -> dict[str, Any]:
    return {"anchors": _touch(tmp_path / "pair.anchors")}


def _blocks_overrides(tmp_path: Path) -> dict[str, Any]:
    return {"blocks": _touch(tmp_path / "pair.blocks")}


def _local_synteny_overrides(tmp_path: Path) -> dict[str, Any]:
    return {
        "blocks": _touch(tmp_path / "pair.blocks"),
        "target_genes": "qgene1,qgene2",
    }


def _histogram_overrides(tmp_path: Path) -> dict[str, Any]:
    return {"input_files": _touch(tmp_path / "numbers.txt"), "histogram_bins": 4}


def _heatmap_overrides(tmp_path: Path) -> dict[str, Any]:
    return {"input_file": _touch(tmp_path / "matrix.csv"), "cmap": "viridis"}


def _global_karyotype_overrides(_tmp_path: Path) -> dict[str, Any]:
    return {
        "tracks": '[{"name": "A", "bed": "A.bed"}]',
        "edges": '[{"i": 0, "j": 1, "simple": "A__B.simple"}]',
    }


def _multi_local_synteny_overrides(tmp_path: Path) -> dict[str, Any]:
    return {
        "tracks": '[{"name": "A", "bed": "A.bed"}]',
        "blocks": _touch(tmp_path / "all.blocks"),
        "bed": _touch(tmp_path / "all.bed"),
        "target_genes": "gene1,gene2",
    }


SUBMODULE_CASES: list[
    tuple[FeatureEntryModule, str, str, Callable[[Path], dict[str, Any]]]
] = [
    (
        cast(FeatureEntryModule, mcscan_pairwise_entry),
        "jcvi.mcscan_pairwise",
        "gljcvi_mcscan_pairwise",
        _no_overrides,
    ),
    (
        cast(FeatureEntryModule, catalog_ortholog_entry),
        "jcvi.catalog_ortholog",
        "gljcvi_catalog_ortholog",
        _no_overrides,
    ),
    (
        cast(FeatureEntryModule, dotplot_entry),
        "jcvi.graphics_dotplot",
        "gljcvi_dotplot",
        _dotplot_overrides,
    ),
    (
        cast(FeatureEntryModule, synteny_figure_entry),
        "jcvi.graphics_synteny",
        "gljcvi_synteny_figure",
        _blocks_overrides,
    ),
    (
        cast(FeatureEntryModule, karyotype_entry),
        "jcvi.graphics_karyotype",
        "gljcvi_karyotype",
        _blocks_overrides,
    ),
    (
        cast(FeatureEntryModule, local_synteny_entry),
        "jcvi.local_synteny",
        "gljcvi_local_synteny",
        _local_synteny_overrides,
    ),
    (
        cast(FeatureEntryModule, histogram_entry),
        "jcvi.graphics_histogram",
        "gljcvi_histogram",
        _histogram_overrides,
    ),
    (
        cast(FeatureEntryModule, heatmap_entry),
        "jcvi.graphics_heatmap",
        "gljcvi_heatmap",
        _heatmap_overrides,
    ),
    (
        cast(FeatureEntryModule, global_karyotype_entry),
        "jcvi.graphics_karyotype_global",
        "gljcvi_global_karyotype",
        _global_karyotype_overrides,
    ),
    (
        cast(FeatureEntryModule, multi_local_synteny_entry),
        "jcvi.local_synteny_multi",
        "gljcvi_multi_local_synteny",
        _multi_local_synteny_overrides,
    ),
]


@pytest.mark.parametrize(
    ("module", "module_id", "logger_name", "make_overrides"),
    SUBMODULE_CASES,
    ids=[case[1] for case in SUBMODULE_CASES],
)
def test_submodule_entry_builds_submodule_command(
    tmp_path: Path,
    module: FeatureEntryModule,
    module_id: str,
    logger_name: str,
    make_overrides: Callable[[Path], dict[str, Any]],
) -> None:
    params_path = _write_params_from_sample(
        tmp_path, overrides=make_overrides(tmp_path)
    )

    argv = module.build_runtime_command(params_path)

    assert argv[:4] == ["cmd.exe", "/c", str(tmp_path / "GenomeLens.cmd"), "analyze"]
    assert argv[4] == "submodule"
    found_id, ports, output_dir = _submodule_argv(argv)
    assert found_id == module_id
    assert ports  # every submodule wires at least one input port
    assert output_dir == str(tmp_path / "output")
    assert argv[-1] == "--force"
    assert logging.getLogger(logger_name).handlers == []


def test_dotplot_entry_requires_anchors(tmp_path: Path) -> None:
    argv = dotplot_entry.build_runtime_command(
        _write_params_from_sample(tmp_path, overrides=_dotplot_overrides(tmp_path))
    )
    _module_id, ports, _output = _submodule_argv(argv)
    assert "anchors" in ports

    with pytest.raises(Exception, match="anchors"):
        dotplot_entry.build_runtime_command(
            _write_params_from_sample(tmp_path, overrides={"anchors": ""})
        )


def test_local_synteny_entry_splits_target_genes(tmp_path: Path) -> None:
    argv = local_synteny_entry.build_runtime_command(
        _write_params_from_sample(
            tmp_path, overrides=_local_synteny_overrides(tmp_path)
        )
    )
    _module_id, ports, _output = _submodule_argv(argv)
    assert ports["target_genes"] == ["qgene1", "qgene2"]
    assert "blocks" in ports


def test_histogram_entry_wires_numeric_files(tmp_path: Path) -> None:
    overrides = _histogram_overrides(tmp_path)
    argv = histogram_entry.build_runtime_command(
        _write_params_from_sample(tmp_path, overrides=overrides)
    )
    _module_id, ports, _output = _submodule_argv(argv)
    assert ports["numeric_files"] == [overrides["input_files"]]


def test_heatmap_entry_wires_matrix_csv(tmp_path: Path) -> None:
    overrides = _heatmap_overrides(tmp_path)
    argv = heatmap_entry.build_runtime_command(
        _write_params_from_sample(tmp_path, overrides=overrides)
    )
    _module_id, ports, _output = _submodule_argv(argv)
    assert ports["matrix_csv"] == overrides["input_file"]


def test_synteny_entry_builds_workflow_command(tmp_path: Path) -> None:
    params_path = _write_params_from_sample(tmp_path)

    argv = synteny_entry.build_runtime_command(params_path)

    assert argv[:4] == ["cmd.exe", "/c", str(tmp_path / "GenomeLens.cmd"), "analyze"]
    assert argv[4] == "workflow"
    assert argv[5] == "synteny"
    assert Path(argv[6]).is_dir()
    assert Path(argv[7]) == tmp_path / "output"
    assert argv[8] == "--jcvi-config"
    jcvi_config_path = Path(argv[9])
    assert jcvi_config_path == tmp_path / "output" / "jcvi.config.json"
    assert argv[10] == "--force"

    config = json.loads(jcvi_config_path.read_text(encoding="utf-8"))
    assert config["schema_version"] == 2
    assert config["mcscan"]["workflow"] == "local_synteny"
    assert config["local_synteny"]["target_gene_ids"] == ["qgene1"]
    assert config["runtime"]["threads"] == 2
    assert config["runtime"]["formats"] == ["png"]
    assert config["mcscan"]["min_block_size"] == 1
    assert config["mcscan"]["reference"] == "query"
    assert logging.getLogger("gljcvi_synteny").handlers == []


def test_synteny_entry_routes_without_targets(tmp_path: Path) -> None:
    params_path = _write_params_from_sample(tmp_path, overrides={"target_gene_ids": ""})

    argv = synteny_entry.build_runtime_command(params_path)

    assert argv[4] == "workflow"
    assert argv[5] == "synteny"
    config = json.loads(Path(argv[9]).read_text(encoding="utf-8"))
    assert config["mcscan"]["workflow"] == "graphics_synteny"
    assert config["local_synteny"]["target_gene_ids"] == []


def test_synteny_entry_optimize_auto_maps_all_flags(tmp_path: Path) -> None:
    params_path = _write_params_from_sample(tmp_path, overrides={"optimize_auto": True})

    argv = synteny_entry.build_runtime_command(params_path)

    config = json.loads(Path(argv[9]).read_text(encoding="utf-8"))
    auto_opt = config["local_synteny"]["auto_optimization"]
    assert auto_opt["optimize_figsize"] is True
    assert auto_opt["rewrite_layout_links"] is True
    assert auto_opt["optimize_karyotype_labels"] is True


def test_synteny_entry_uses_genomelens_path(tmp_path: Path) -> None:
    params_path = _write_params_from_sample(
        tmp_path,
        overrides={
            "genomelens_exe": "",
            "GenomeLens_Path": str(tmp_path / "GenomeLens.exe"),
        },
    )
    (tmp_path / "GenomeLens.exe").write_text("", encoding="utf-8")

    argv = synteny_entry.build_runtime_command(params_path)

    assert argv[0] == str(tmp_path / "GenomeLens.exe")


def test_synteny_entry_split_targets_maps_to_config(tmp_path: Path) -> None:
    params_path = _write_params_from_sample(tmp_path, overrides={"split_targets": True})

    argv = synteny_entry.build_runtime_command(params_path)

    config = json.loads(Path(argv[9]).read_text(encoding="utf-8"))
    assert config["local_synteny"]["split_targets"] is True


def test_synteny_entry_main_compresses_intermediates(tmp_path: Path) -> None:
    params_path = _write_params_from_sample(tmp_path, overrides={"target_gene_ids": ""})

    exit_code = synteny_entry.main([str(params_path)])

    assert exit_code == 0
    output_dir = tmp_path / "output"
    assert (output_dir / "intermediates.zip").is_file()
    assert (output_dir / "intermediates.zip.deletable").is_file()
    assert not (output_dir / "jcvi.config.json").exists()
    assert not (output_dir / "run.log").exists()

    import zipfile

    with zipfile.ZipFile(output_dir / "intermediates.zip") as zf:
        names = zf.namelist()
        assert "jcvi.config.json" in names
        assert "run.log" in names


def test_synteny_entry_main_skips_compression_on_failure(tmp_path: Path) -> None:
    params_path = _write_params_from_sample(
        tmp_path,
        overrides={"target_gene_ids": ""},
    )
    genomelens_exe = tmp_path / "GenomeLens.cmd"
    genomelens_exe.write_text("@echo off\r\nexit /b 1\r\n", encoding="utf-8")

    exit_code = synteny_entry.main([str(params_path)])

    assert exit_code == 1
    output_dir = tmp_path / "output"
    assert not (output_dir / "intermediates.zip").exists()
    assert (output_dir / "jcvi.config.json").is_file()
    assert (output_dir / "run.log").is_file()


@pytest.mark.parametrize(
    ("module", "label"),
    [
        (cast(FeatureEntryModule, synteny_entry), "synteny workflow"),
        (cast(FeatureEntryModule, mcscan_pairwise_entry), "MCscan pairwise"),
        (cast(FeatureEntryModule, catalog_ortholog_entry), "catalog_ortholog"),
        (cast(FeatureEntryModule, dotplot_entry), "dotplot"),
        (cast(FeatureEntryModule, synteny_figure_entry), "synteny figure"),
        (cast(FeatureEntryModule, karyotype_entry), "karyotype"),
        (cast(FeatureEntryModule, local_synteny_entry), "local synteny"),
        (cast(FeatureEntryModule, histogram_entry), "histogram"),
        (cast(FeatureEntryModule, heatmap_entry), "heatmap"),
        (cast(FeatureEntryModule, global_karyotype_entry), "global karyotype"),
        (
            cast(FeatureEntryModule, multi_local_synteny_entry),
            "multi-species local synteny",
        ),
    ],
)
def test_feature_entry_main_rejects_missing_params(
    capsys: pytest.CaptureFixture[str],
    module: FeatureEntryModule,
    label: str,
) -> None:
    exit_code = module.main([])

    assert exit_code == 2
    assert label in capsys.readouterr().err
