import json
import logging
from pathlib import Path

import pytest

from genomelens_haiant_plugin import (
    PluginError,
    build_analyze_submodule_command,
    close_adapter_logging,
    coerce_submodule_params,
    load_params,
    parse_bool,
    resolve_param_path,
    setup_adapter_logging,
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


def test_build_analyze_submodule_command_dispatches_cmd_files() -> None:
    argv = build_analyze_submodule_command(
        "C:/GenomeLens/genomelens.cmd",
        module_id="jcvi.graphics_dotplot",
        input_ports={"species_pair": "input", "anchors": "pair.anchors"},
        output_dir="output",
        force=True,
    )

    assert argv[:3] == ["cmd.exe", "/c", "C:\\GenomeLens\\genomelens.cmd"]
    assert argv[3:6] == ["analyze", "submodule", "jcvi.graphics_dotplot"]
    assert argv[6] == "--input-ports"
    assert json.loads(argv[7]) == {"species_pair": "input", "anchors": "pair.anchors"}
    assert argv[-1] == "--force"


def test_build_analyze_submodule_command_dispatches_executables() -> None:
    argv = build_analyze_submodule_command(
        "C:/GenomeLens/GenomeLens.exe",
        module_id="jcvi.mcscan_pairwise",
        input_ports={"species_pair": "input"},
        output_dir="output",
        params={"cscore": 0.7},
        formats=["png", "svg"],
        force=True,
    )

    assert argv[0] == "C:\\GenomeLens\\GenomeLens.exe"
    assert argv[1:3] == ["analyze", "submodule"]
    params_index = argv.index("--params") + 1
    assert json.loads(argv[params_index]) == {"cscore": 0.7}
    formats_index = argv.index("--formats") + 1
    assert argv[formats_index] == "png,svg"


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
    (tmp_path / "jcvi.config.json").write_text("{}", encoding="utf-8")
    (tmp_path / "run.log").write_text("log", encoding="utf-8")
    temp_dir = tmp_path / "temp"
    temp_dir.mkdir()
    (temp_dir / "anchors.txt").write_text("anchors", encoding="utf-8")

    archive = compress_output_intermediates(tmp_path)

    assert archive is not None
    assert archive.name == "intermediates.zip"
    assert (tmp_path / "intermediates.zip.deletable").is_file()
    assert not (tmp_path / "jcvi.config.json").exists()
    assert not (tmp_path / "run.log").exists()
    assert not (tmp_path / "temp").exists()
    assert (results_dir / "figure.png").is_file()

    import zipfile

    with zipfile.ZipFile(archive) as zf:
        names = zf.namelist()
        assert "jcvi.config.json" in names
        assert "run.log" in names
        assert "temp/anchors.txt" in names
