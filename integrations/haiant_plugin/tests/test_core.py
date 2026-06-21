import logging
from pathlib import Path
from typing import cast

import pytest

from genomelens_haiant_plugin import (
    PluginError,
    build_analysis_request,
    build_analyze_run_command,
    close_adapter_logging,
    load_params,
    parse_bool,
    resolve_param_path,
    setup_adapter_logging,
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

    from genomelens_haiant_plugin._core import build_species_from_params

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
    logger = setup_adapter_logging(tmp_path)
    first_handler = _file_handler(logger)

    setup_adapter_logging(tmp_path)

    assert first_handler.stream is None
    close_adapter_logging()


def test_build_analyze_run_command_dispatches_cmd_files() -> None:
    request_path = Path("output/genomelens_request.json")
    exe = Path("C:/GenomeLens/genomelens.cmd")
    argv = build_analyze_run_command(str(exe), request_path)

    assert argv[:3] == ["cmd.exe", "/c", str(exe)]
    assert argv[3:] == ["analyze", "run", str(request_path)]


def test_build_analyze_run_command_dispatches_executables() -> None:
    request_path = Path("output/genomelens_request.json")
    exe = Path("C:/GenomeLens/GenomeLens-runtime.exe")
    argv = build_analyze_run_command(str(exe), request_path)

    assert argv == [str(exe), "analyze", "run", str(request_path)]
