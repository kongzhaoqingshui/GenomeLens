import json
import logging
import os
import shutil
from pathlib import Path

import genomelens_haiant_plugin as plugin
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


def test_main_forwards_runtime_cli_invocations(tmp_path: Path, monkeypatch) -> None:
    runtime = tmp_path / "GenomeLens-runtime.exe"
    runtime.write_text("", encoding="utf-8")
    monkeypatch.setenv("GENOMELENS_PLUGIN_RUNTIME", str(runtime))
    captured: list[list[str]] = []
    monkeypatch.setattr(plugin, "run_runtime", lambda argv: captured.append(argv) or 0)

    assert plugin.main(["workbench"]) == 0
    assert plugin.main(["check", "--json"]) == 0
    assert plugin.main(["analyze", "template", "mcscan"]) == 0

    assert captured == [
        [str(runtime), "workbench"],
        [str(runtime), "check", "--json"],
        [str(runtime), "analyze", "template", "mcscan"],
    ]


def test_build_runtime_command_accepts_legacy_query_subject_fields(tmp_path: Path, monkeypatch) -> None:
    runtime = tmp_path / "GenomeLens-runtime.exe"
    runtime.write_text("", encoding="utf-8")
    monkeypatch.setenv("GENOMELENS_PLUGIN_RUNTIME", str(runtime))
    root = Path(__file__).resolve().parents[3]
    sample_dir = root / "references" / "samples" / "shell" / "bed_cds_minimal"
    params_payload = {
        "input_mode": "bed_cds",
        "query_name": "query",
        "subject_name": "subject",
        "query_bed": str(sample_dir / "query.bed"),
        "query_cds": str(sample_dir / "query.cds"),
        "subject_bed": str(sample_dir / "subject.bed"),
        "subject_cds": str(sample_dir / "subject.cds"),
        "output_dir": str(tmp_path / "legacy_output"),
        "workflow": "graphics_synteny",
    }
    params = tmp_path / "legacy_params_for_test.json"
    params.write_text(json.dumps(params_payload, ensure_ascii=False), encoding="utf-8")
    argv = build_runtime_command(params)

    request = json.loads(Path(argv[3]).read_text(encoding="utf-8"))
    assert request["input"]["species"][0]["name"] == "query"
    assert request["input"]["species"][1]["name"] == "subject"
    assert Path(request["input"]["species"][0]["bed"]).is_file()


def test_build_runtime_command_uses_plugin_root_for_installed_params(tmp_path: Path, monkeypatch) -> None:
    plugin_dir = tmp_path / "installed_plugin"
    input_dir = plugin_dir / "input"
    runtime = plugin_dir / "runtime" / "GenomeLens" / "GenomeLens-runtime.exe"
    input_dir.mkdir(parents=True)
    runtime.parent.mkdir(parents=True)
    runtime.write_text("", encoding="utf-8")
    for name in ["query.bed", "query.cds", "subject.bed", "subject.cds"]:
        (input_dir / name).write_text("x\n", encoding="utf-8")
    execute_params = tmp_path / "execute_params"
    execute_params.mkdir()
    params = execute_params / "params.json"
    params.write_text(
        """{
  "input_mode": "bed_cds",
  "species": [
    {"name": "query", "bed": "input/query.bed", "cds": "input/query.cds"},
    {"name": "subject", "bed": "input/subject.bed", "cds": "input/subject.cds"}
  ],
  "output_dir": "output"
}
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(plugin, "plugin_root", lambda: plugin_dir)
    monkeypatch.delenv("GENOMELENS_PLUGIN_RUNTIME", raising=False)
    argv = build_runtime_command(params)
    request = json.loads(Path(argv[3]).read_text(encoding="utf-8"))

    assert argv[:3] == [str(runtime), "analyze", "run"]
    assert Path(request["input"]["species"][0]["bed"]) == input_dir / "query.bed"
    assert Path(request["output"]["directory"]) == plugin_dir / "output"


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
        "workflow": "catalog_ortholog",
    }

    try:
        write_runtime_request(params, tmp_path)
    except PluginError as exc:
        assert "Unsupported HAIant workflow" in str(exc)
    else:
        raise AssertionError("PluginError was not raised")
