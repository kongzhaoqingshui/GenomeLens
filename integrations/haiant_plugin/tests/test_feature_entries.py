import json
import logging
from pathlib import Path
from typing import Any, Protocol, cast

import pytest

from features import (
    auto_entry,
    catalog_ortholog_entry,
    dotplot_entry,
    karyotype_entry,
    local_synteny_entry,
    synteny_entry,
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


@pytest.mark.parametrize(
    ("module", "workflow", "logger_name"),
    [
        (
            cast(FeatureEntryModule, dotplot_entry),
            "graphics_dotplot",
            "gljcvi_dotplot",
        ),
        (
            cast(FeatureEntryModule, synteny_entry),
            "graphics_synteny",
            "gljcvi_synteny",
        ),
        (
            cast(FeatureEntryModule, karyotype_entry),
            "graphics_karyotype",
            "gljcvi_karyotype",
        ),
        (
            cast(FeatureEntryModule, catalog_ortholog_entry),
            "catalog_ortholog",
            "gljcvi_catalog_ortholog",
        ),
        (
            cast(FeatureEntryModule, local_synteny_entry),
            "local_synteny",
            "gljcvi_local_synteny",
        ),
    ],
)
def test_feature_entry_builds_request_and_command(
    tmp_path: Path,
    module: FeatureEntryModule,
    workflow: str,
    logger_name: str,
) -> None:
    params_path = _write_params_from_sample(tmp_path)

    argv = module.build_runtime_command(params_path)

    assert argv[:4] == ["cmd.exe", "/c", str(tmp_path / "GenomeLens.cmd"), "analyze"]
    assert argv[4] == "run"
    request_path = Path(argv[5])
    assert request_path.name == "genomelens_request.json"

    request = json.loads(request_path.read_text(encoding="utf-8"))
    assert request["method"] == "mcscan"
    assert request["method_config"]["workflow"] == workflow
    assert request["output"]["directory"] == str(tmp_path / "output")
    assert request["options"]["threads"] == 2
    assert request["options"]["min_block_size"] == 1
    assert logging.getLogger(logger_name).handlers == []


def test_auto_entry_builds_mcscan_jcvi_command(tmp_path: Path) -> None:
    params_path = _write_params_from_sample(tmp_path)

    argv = auto_entry.build_runtime_command(params_path)

    assert argv[:4] == ["cmd.exe", "/c", str(tmp_path / "GenomeLens.cmd"), "analyze"]
    assert argv[4] == "workflow"
    assert argv[5] == "reference_vs_targets"
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
    assert logging.getLogger("gljcvi_auto").handlers == []


def test_auto_entry_global_synteny_without_targets(tmp_path: Path) -> None:
    params_path = _write_params_from_sample(tmp_path, overrides={"target_gene_ids": ""})

    argv = auto_entry.build_runtime_command(params_path)

    assert argv[4] == "workflow"
    assert argv[5] == "pairwise_synteny"
    config = json.loads(Path(argv[9]).read_text(encoding="utf-8"))
    assert config["mcscan"]["workflow"] == "graphics_synteny"
    assert config["local_synteny"]["target_gene_ids"] == []


def test_auto_entry_optimize_auto_maps_all_flags(tmp_path: Path) -> None:
    params_path = _write_params_from_sample(tmp_path, overrides={"optimize_auto": True})

    argv = auto_entry.build_runtime_command(params_path)

    config = json.loads(Path(argv[9]).read_text(encoding="utf-8"))
    auto_opt = config["local_synteny"]["auto_optimization"]
    assert auto_opt["optimize_figsize"] is True
    assert auto_opt["rewrite_layout_links"] is True
    assert auto_opt["optimize_karyotype_labels"] is True


def test_auto_entry_uses_genomelens_path(tmp_path: Path) -> None:
    params_path = _write_params_from_sample(
        tmp_path,
        overrides={
            "genomelens_exe": "",
            "GenomeLens_Path": str(tmp_path / "GenomeLens.exe"),
        },
    )
    (tmp_path / "GenomeLens.exe").write_text("", encoding="utf-8")

    argv = auto_entry.build_runtime_command(params_path)

    assert argv[0] == str(tmp_path / "GenomeLens.exe")


def test_auto_entry_split_targets_maps_to_config(tmp_path: Path) -> None:
    params_path = _write_params_from_sample(tmp_path, overrides={"split_targets": True})

    argv = auto_entry.build_runtime_command(params_path)

    config = json.loads(Path(argv[9]).read_text(encoding="utf-8"))
    assert config["local_synteny"]["split_targets"] is True


def test_auto_entry_main_compresses_intermediates(tmp_path: Path) -> None:
    params_path = _write_params_from_sample(tmp_path, overrides={"target_gene_ids": ""})

    exit_code = auto_entry.main([str(params_path)])

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


def test_auto_entry_main_skips_compression_on_failure(tmp_path: Path) -> None:
    params_path = _write_params_from_sample(
        tmp_path,
        overrides={"target_gene_ids": ""},
    )
    genomelens_exe = tmp_path / "GenomeLens.cmd"
    genomelens_exe.write_text("@echo off\r\nexit /b 1\r\n", encoding="utf-8")

    exit_code = auto_entry.main([str(params_path)])

    assert exit_code == 1
    output_dir = tmp_path / "output"
    assert not (output_dir / "intermediates.zip").exists()
    assert (output_dir / "jcvi.config.json").is_file()
    assert (output_dir / "run.log").is_file()


@pytest.mark.parametrize(
    ("module", "label"),
    [
        (cast(FeatureEntryModule, dotplot_entry), "dotplot"),
        (cast(FeatureEntryModule, synteny_entry), "synteny"),
        (cast(FeatureEntryModule, karyotype_entry), "karyotype"),
        (
            cast(FeatureEntryModule, catalog_ortholog_entry),
            "catalog_ortholog",
        ),
        (
            cast(FeatureEntryModule, local_synteny_entry),
            "local synteny",
        ),
        (
            cast(FeatureEntryModule, auto_entry),
            "MCscan auto workflow",
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
