import json
import logging
from pathlib import Path

import pytest

from genomelens_haiant_plugin import (
    PluginError,
    build_run_command,
    build_submodule_request,
    build_submodule_runtime_command,
    build_workflow_request,
    build_workflow_runtime_command,
    close_adapter_logging,
    coerce_submodule_params,
    load_params,
    parse_bool,
    resolve_param_path,
    setup_adapter_logging,
    write_request_json,
)


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


def test_setup_adapter_logging_closes_previous_file_handler(tmp_path: Path) -> None:
    logger = setup_adapter_logging(tmp_path)
    first_handler = _file_handler(logger)

    setup_adapter_logging(tmp_path)

    assert first_handler.stream is None
    close_adapter_logging()


def test_write_request_json_writes_pretty_json(tmp_path: Path) -> None:
    path = write_request_json(tmp_path, {"schema_version": 3, "kind": "test"})

    assert path == tmp_path / "request.json"
    assert path.is_file()
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload == {"schema_version": 3, "kind": "test"}


def test_build_run_command_dispatches_cmd_files() -> None:
    argv = build_run_command("C:/GenomeLens/genomelens.cmd", "output/request.json")

    assert argv[:3] == ["cmd.exe", "/c", "C:\\GenomeLens\\genomelens.cmd"]
    assert argv[3:] == ["analyze", "run", "output/request.json"]


def test_build_run_command_dispatches_executables() -> None:
    argv = build_run_command("C:/GenomeLens/GenomeLens.exe", "output/request.json")

    assert argv[0] == "C:\\GenomeLens\\GenomeLens.exe"
    assert argv[1:] == ["analyze", "run", "output/request.json"]


def test_build_workflow_request_includes_species_and_parameters(tmp_path: Path) -> None:
    species_dir = tmp_path / "species"
    species_dir.mkdir(parents=True)
    (species_dir / "query.bed").write_text("chr1\t1\t100\tg1\n", encoding="utf-8")
    (species_dir / "query.cds").write_text(">g1\nATGC\n", encoding="utf-8")
    (species_dir / "subject.bed").write_text("chr1\t1\t100\tg1\n", encoding="utf-8")
    (species_dir / "subject.cds").write_text(">g1\nATGC\n", encoding="utf-8")

    params = {
        "input_dir": str(species_dir),
        "reference": "query",
        "target_gene_ids": "qgene1",
        "align_soft": "blast",
        "min_block_size": 3,
        "threads": 4,
        "formats": "png",
        "optimize_auto": True,
    }

    request = build_workflow_request(params, tmp_path, tmp_path / "output")

    assert request["schema_version"] == 3
    assert request["kind"] == "workflow_request"
    assert request["workflow_id"] == "synteny"
    assert len(request["species"]) == 2
    assert request["reference_index"] == 0
    assert request["parameters"]["synteny"]["min_block_size"] == 3
    assert request["parameters"]["local_synteny"]["target_gene_ids"] == ["qgene1"]
    assert request["output"]["formats"] == ["png"]
    assert request["runtime"]["threads"] == 4
    assert (
        request["parameters"]["plot"]["auto_optimization"]["optimize_figsize"] is True
    )


def test_build_submodule_request_assembles_ports_and_parameters() -> None:
    request = build_submodule_request(
        "jcvi.graphics_histogram",
        {"numeric_files": ["values.txt"]},
        {"bins": 10},
        "output",
        formats=["svg"],
        threads=2,
    )

    assert request["schema_version"] == 3
    assert request["kind"] == "submodule_request"
    assert request["module_id"] == "jcvi.graphics_histogram"
    assert request["inputs"]["numeric_files"] == ["values.txt"]
    assert request["parameters"] == {"bins": 10}
    assert request["output"]["formats"] == ["svg"]
    assert request["runtime"]["threads"] == 2


def test_build_submodule_runtime_command_writes_request_and_returns_argv(
    tmp_path: Path,
) -> None:
    argv = build_submodule_runtime_command(
        tmp_path / "GenomeLens.exe",
        module_id="jcvi.graphics_histogram",
        inputs={"numeric_files": ["values.txt"]},
        parameters={"bins": 10},
        output_dir=tmp_path / "output",
    )

    assert argv[0] == str(tmp_path / "GenomeLens.exe")
    assert argv[1:3] == ["analyze", "run"]
    request_path = Path(argv[3])
    assert request_path.name == "submodule_request.json"
    assert (
        json.loads(request_path.read_text(encoding="utf-8"))["module_id"]
        == "jcvi.graphics_histogram"
    )


def test_build_workflow_runtime_command_writes_request_and_returns_argv(
    tmp_path: Path,
) -> None:
    species_dir = tmp_path / "species"
    species_dir.mkdir(parents=True)
    (species_dir / "query.bed").write_text("chr1\t1\t100\tg1\n", encoding="utf-8")
    (species_dir / "query.cds").write_text(">g1\nATGC\n", encoding="utf-8")
    (species_dir / "subject.bed").write_text("chr1\t1\t100\tg1\n", encoding="utf-8")
    (species_dir / "subject.cds").write_text(">g1\nATGC\n", encoding="utf-8")

    params = {"input_dir": str(species_dir), "formats": "svg"}
    argv = build_workflow_runtime_command(
        tmp_path / "GenomeLens.exe", params, tmp_path, tmp_path / "output"
    )

    assert argv[0] == str(tmp_path / "GenomeLens.exe")
    assert argv[1:3] == ["analyze", "run"]
    request_path = Path(argv[3])
    assert request_path.name == "workflow_request.json"
    assert (
        json.loads(request_path.read_text(encoding="utf-8"))["workflow_id"] == "synteny"
    )


def test_coerce_submodule_params_coerces_declared_types(tmp_path: Path) -> None:
    rowgroups = tmp_path / "rows.txt"
    rowgroups.write_text("a\n", encoding="utf-8")
    raw = {
        "dpi": "300",
        "cscore": "0.7",
        "groups": "true",
        "figsize": "8x6",
        "rowgroups": str(rowgroups),
        "histogram_columns": "0,1,2",
        "blank": "",
        "absent": None,
    }
    declared = [
        ("dpi", "int"),
        ("cscore", "float"),
        ("groups", "bool"),
        ("figsize", "str"),
        ("rowgroups", "path"),
        ("histogram_columns", "int_array"),
        ("blank", "str"),
        ("absent", "str"),
        ("missing", "str"),
    ]

    out = coerce_submodule_params(raw, tmp_path, declared)

    assert out["dpi"] == 300
    assert out["cscore"] == 0.7
    assert out["groups"] is True
    assert out["figsize"] == "8x6"
    assert Path(str(out["rowgroups"])).is_absolute()
    assert out["histogram_columns"] == [0, 1, 2]
    # blank / None / missing keys are dropped so the submodule keeps its defaults
    assert "blank" not in out
    assert "absent" not in out
    assert "missing" not in out


def test_compress_output_intermediates_packs_and_cleans(tmp_path: Path) -> None:
    from genomelens_haiant_plugin._core import compress_output_intermediates

    results_dir = tmp_path / "results"
    results_dir.mkdir()
    (results_dir / "figure.png").write_text("figure", encoding="utf-8")
    (tmp_path / "workflow_request.json").write_text("{}", encoding="utf-8")
    (tmp_path / "run.log").write_text("log", encoding="utf-8")
    temp_dir = tmp_path / "temp"
    temp_dir.mkdir()
    (temp_dir / "anchors.txt").write_text("anchors", encoding="utf-8")

    archive = compress_output_intermediates(tmp_path)

    assert archive is not None
    assert archive.name == "intermediates.zip"
    assert (tmp_path / "intermediates.zip.deletable").is_file()
    assert not (tmp_path / "workflow_request.json").exists()
    assert not (tmp_path / "run.log").exists()
    assert not (tmp_path / "temp").exists()
    assert (results_dir / "figure.png").is_file()

    import zipfile

    with zipfile.ZipFile(archive) as zf:
        names = zf.namelist()
        assert "workflow_request.json" in names
        assert "run.log" in names
        assert "temp/anchors.txt" in names
