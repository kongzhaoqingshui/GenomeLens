import json
import logging
import shutil
from pathlib import Path
from typing import cast

import pytest

from genomelens_haiant_plugin import (
    PluginError,
    build_analysis_request,
    build_runtime_command,
    build_species_from_params,
    close_adapter_logging,
    load_params,
    parse_bool,
    resolve_param_path,
    setup_logging,
    write_runtime_request,
)


def _write_species_files(root: Path) -> dict[str, object]:
    query_bed = root / "query.bed"
    query_cds = root / "query.cds"
    subject_bed = root / "subject.bed"
    subject_cds = root / "subject.cds"
    query_bed.write_text(
        "chr1\t1\t10\tqgene1\nchr1\t20\t30\tqgene2\n", encoding="utf-8"
    )
    query_cds.write_text(">qgene1\nATG\n>qgene2\nATG\n", encoding="utf-8")
    subject_bed.write_text("chr1\t1\t10\tsgene1\n", encoding="utf-8")
    subject_cds.write_text(">sgene1\nATG\n", encoding="utf-8")
    return {
        "input_mode": "bed_cds",
        "species": [
            {"name": "query", "bed": "query.bed", "cds": "query.cds"},
            {"name": "subject", "bed": "subject.bed", "cds": "subject.cds"},
        ],
        "output_dir": "output",
    }


def _file_handler(logger: logging.Logger) -> logging.FileHandler:
    for handler in logger.handlers:
        if isinstance(handler, logging.FileHandler):
            return handler
    raise AssertionError("file handler not found")


def test_load_params_returns_payload_and_base_dir(tmp_path: Path) -> None:
    params = tmp_path / "params.json"
    params.write_text('{"output_dir":"output"}\n', encoding="utf-8-sig")

    payload, base = load_params(params)

    assert payload["output_dir"] == "output"
    assert base == tmp_path


def test_resolve_param_path_rejects_missing_required_value(tmp_path: Path) -> None:
    with pytest.raises(PluginError, match="Required path field is empty"):
        resolve_param_path(tmp_path, "", required=True)


def test_parse_bool_forms() -> None:
    assert parse_bool("yes") is True
    assert parse_bool("0") is False


def test_build_species_from_params_resolves_relative_files(tmp_path: Path) -> None:
    params = _write_species_files(tmp_path)

    species = build_species_from_params(params, tmp_path)

    assert species[0]["name"] == "query"
    assert Path(str(species[0]["bed"])).is_absolute()
    assert Path(str(species[1]["cds"])).is_absolute()


def test_build_analysis_request_for_local_synteny_supports_csv_target_ids(
    tmp_path: Path,
) -> None:
    params = _write_species_files(tmp_path)
    params.update(
        {
            "reference": "query",
            "target_gene_ids": "qgene1,qgene2",
            "up": 1,
            "down": 2,
            "split_targets": "true",
            "label_targets": "1",
        }
    )

    request = build_analysis_request(params, tmp_path, workflow="local_synteny")
    input_block = cast(dict[str, object], request["input"])
    method_config = cast(dict[str, object], request["method_config"])

    assert input_block["reference_index"] == 0
    assert method_config["workflow"] == "local_synteny"
    assert method_config["target_gene_ids"] == ["qgene1", "qgene2"]
    assert method_config["up"] == 1
    assert method_config["down"] == 2
    assert method_config["split_targets"] is True
    assert method_config["label_targets"] is True


def test_setup_adapter_logging_closes_previous_file_handler(tmp_path: Path) -> None:
    logger = setup_logging(tmp_path, "first")
    first_handler = _file_handler(logger)

    setup_logging(tmp_path, "second")

    assert first_handler.stream is None
    shutil.rmtree(tmp_path / "first")
    close_adapter_logging()


def test_build_runtime_command_keeps_legacy_graphics_synteny_flow(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runtime = tmp_path / "GenomeLens-runtime.exe"
    runtime.write_text("", encoding="utf-8")
    monkeypatch.setenv("GENOMELENS_PLUGIN_RUNTIME", str(runtime))
    params = _write_species_files(tmp_path)
    params.update(
        {
            "workflow": "graphics_synteny",
            "threads": 2,
            "min_block_size": 1,
        }
    )
    params_path = tmp_path / "params.json"
    params_path.write_text(json.dumps(params, ensure_ascii=False), encoding="utf-8")

    argv = build_runtime_command(params_path)

    assert argv[:3] == [str(runtime), "analyze", "run"]
    request = json.loads(Path(argv[3]).read_text(encoding="utf-8"))
    options = cast(dict[str, object], request["options"])
    method_config = cast(dict[str, object], request["method_config"])
    assert request["method"] == "mcscan"
    assert options["threads"] == 2
    assert options["min_block_size"] == 1
    assert method_config["workflow"] == "graphics_synteny"
    assert logging.getLogger("genomelens_haiant_plugin").handlers == []


def test_write_runtime_request_rejects_non_plugin_workflows(tmp_path: Path) -> None:
    params = _write_species_files(tmp_path)
    params["workflow"] = "catalog_ortholog"

    with pytest.raises(PluginError, match="Unsupported HAIant workflow"):
        write_runtime_request(params, tmp_path)
