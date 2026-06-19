import json
import logging
import os
import shutil
from pathlib import Path

from genomelens_haiant_plugin import (
    PluginError,
    build_runtime_command,
    close_adapter_logging,
    parse_bool,
    setup_adapter_logging,
    write_runtime_request,
)


def test_parse_bool_forms() -> None:
    assert parse_bool("yes") is True
    assert parse_bool("0") is False


def _file_handler(logger: logging.Logger) -> logging.FileHandler:
    for handler in logger.handlers:
        if isinstance(handler, logging.FileHandler):
            return handler
    raise AssertionError("file handler not found")


def test_setup_adapter_logging_closes_previous_file_handler(tmp_path: Path) -> None:
    logger = setup_adapter_logging(tmp_path, "first")
    first_handler = _file_handler(logger)

    setup_adapter_logging(tmp_path, "second")

    assert first_handler.stream is None
    shutil.rmtree(tmp_path / "first")
    close_adapter_logging()


def test_build_runtime_command_resolves_relative_paths(
    tmp_path: Path, monkeypatch
) -> None:
    runtime = tmp_path / "GenomeLens-runtime.exe"
    runtime.write_text("", encoding="utf-8")
    monkeypatch.setenv("GENOMELENS_PLUGIN_RUNTIME", str(runtime))
    root = Path(__file__).resolve().parents[3]
    sample_params = root / "references" / "samples" / "haiant" / "params.json"
    params_payload = json.loads(sample_params.read_text(encoding="utf-8"))
    for item in params_payload["species"]:
        for key in ("bed", "cds", "gff", "genome"):
            if item.get(key):
                item[key] = str(
                    (sample_params.parent / item[key]).resolve(strict=False)
                )
    params_payload["output_dir"] = str(tmp_path / "output")
    params = tmp_path / "params.json"
    params.write_text(json.dumps(params_payload, ensure_ascii=False), encoding="utf-8")
    argv = build_runtime_command(params)
    assert argv[:3] == [str(runtime), "analyze", "run"]
    request_path = Path(argv[3])
    output_dir = Path(params_payload["output_dir"])
    assert output_dir.is_dir()
    assert request_path == output_dir / "genomelens_request.json"
    request = json.loads(request_path.read_text(encoding="utf-8"))
    assert request["method"] == "mcscan"
    assert request["options"]["threads"] == 2
    assert request["options"]["min_block_size"] == 1
    assert request["method_config"]["workflow"] == "graphics_synteny"
    assert request["method_config"]["allow_simplified_fallback"] is False
    assert not (output_dir / ".genomelens_plugin_input").exists()
    assert logging.getLogger("genomelens_haiant_plugin").handlers == []
    os.environ.pop("GENOMELENS_PLUGIN_RUNTIME", None)


def test_write_runtime_request_rejects_non_plugin_workflows(tmp_path: Path) -> None:
    sample = tmp_path / "sample.bed"
    sample.write_text("chr1\t1\t10\tgene1\n", encoding="utf-8")
    cds = tmp_path / "sample.cds"
    cds.write_text(">gene1\nATG\n", encoding="utf-8")
    params = {
        "species": [
            {"name": "query", "bed": str(sample), "cds": str(cds)},
            {"name": "subject", "bed": str(sample), "cds": str(cds)},
        ],
        "output_dir": str(tmp_path / "output"),
        "workflow": "bed_summary",
    }

    try:
        write_runtime_request(params, tmp_path)
    except PluginError as exc:
        assert "Unsupported HAIant workflow" in str(exc)
    else:
        raise AssertionError("PluginError was not raised")
