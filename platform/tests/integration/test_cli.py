import json
import shutil
from pathlib import Path

from genomelens.cli.main import main
from genomelens.core.summary_models import RunSummary, ScoringBlock, UiBlock
from genomelens.data.workspace.output_layout import create_output_layout


def _write_third_species(tmp_path: Path, sample: Path) -> tuple[Path, Path]:
    bed = tmp_path / "third.bed"
    cds = tmp_path / "third.cds"
    bed.write_text(
        (sample / "query.bed").read_text(encoding="utf-8").replace("qgene", "tgene"),
        encoding="utf-8",
    )
    cds.write_text(
        (sample / "query.cds").read_text(encoding="utf-8").replace("qgene", "tgene"),
        encoding="utf-8",
    )
    return bed, cds


def _copy_species_files(input_dir: Path, sample: Path, names: list[str]) -> None:
    input_dir.mkdir(parents=True, exist_ok=True)
    for name in names:
        shutil.copy2(sample / name, input_dir / name)


def _auto_args(input_dir: Path, outdir: Path) -> list[str]:
    return [str(input_dir), str(outdir)]


def test_cli_help() -> None:
    assert main(["--help"]) == 0


def test_cli_help_for_command(capsys) -> None:
    assert main(["help", "analyze", "mcscan"]) == 0
    help_command_output = capsys.readouterr().out

    assert main(["analyze", "mcscan", "--help"]) == 0
    direct_help_output = capsys.readouterr().out

    assert help_command_output == direct_help_output
    assert "参数页:" in help_command_output
    assert "help analyze mcscan jcvi local" in help_command_output
    assert "--jcvi-engine JCVI_ENGINE" not in help_command_output
    assert "兼容性:" not in help_command_output


def test_cli_help_for_command_uses_color_when_enabled(capsys, monkeypatch) -> None:
    monkeypatch.setenv("GENOMELENS_FORCE_COLOR", "1")

    assert main(["help", "analyze", "mcscan"]) == 0
    output = capsys.readouterr().out

    assert "\033[" in output
    assert "参数页:" in output


def test_cli_help_for_mcscan_jcvi_page(capsys) -> None:
    assert main(["help", "analyze", "mcscan", "jcvi", "local"]) == 0
    output = capsys.readouterr().out

    assert "genomelens analyze mcscan jcvi - 目标基因局部共线性" in output
    assert "--target-genes TARGET_GENES" in output
    assert "--split-targets" in output
    assert "--jcvi-engine JCVI_ENGINE" not in output


def test_cli_help_for_mcscan_jcvi_subtask(capsys) -> None:
    assert main(["help", "analyze", "mcscan", "jcvi", "graphics_dotplot"]) == 0
    output = capsys.readouterr().out

    assert "genomelens analyze mcscan jcvi graphics_dotplot" in output
    assert "input_dir output_dir" in output
    assert "共享参数页:" in output


def test_cli_help_for_mcscan_jcvi_histogram_subtask(capsys) -> None:
    assert main(["help", "analyze", "mcscan", "jcvi", "graphics_histogram"]) == 0
    output = capsys.readouterr().out

    assert "genomelens analyze mcscan jcvi graphics_histogram" in output
    assert "number_file output_dir" in output
    assert "histogram-columns" in output


def test_cli_help_for_analyze_run(capsys) -> None:
    assert main(["help", "analyze", "run"]) == 0
    output = capsys.readouterr().out

    assert "request_json" in output
    assert "--json" in output


def test_analyze_template_mcscan(capsys) -> None:
    assert main(["analyze", "template", "mcscan"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["kind"] == "analysis_request"
    assert payload["method"] == "mcscan"
    assert payload["input"]["mode"] == "auto_directory"


def test_analyze_schema(capsys) -> None:
    assert main(["analyze", "schema"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert payload["properties"]["kind"]["const"] == "analysis_request"
    assert payload["properties"]["method"]["enum"] == ["mcscan"]


def test_check_json_short_option() -> None:
    assert main(["check", "-j"]) in {0, 5}


def test_config_init(tmp_path: Path) -> None:
    assert main(["config", "init", "--workspace", str(tmp_path / "work"), "--force"]) == 0
    assert (tmp_path / "work" / "genomelens.config.json").is_file()
    assert (tmp_path / "work" / "jcvi.config.json").is_file()


def test_analyze_mcscan_force_before_positionals_reuses_output_dir(tmp_path: Path, monkeypatch) -> None:
    from genomelens.analysis.methods.mcscan_request_mapping import to_mcscan_request

    root = Path(__file__).resolve().parents[3]
    sample = root / "references" / "samples" / "shell" / "bed_cds_minimal"
    input_dir = tmp_path / "input"
    _copy_species_files(input_dir, sample, ["query.bed", "query.cds", "subject.bed", "subject.cds"])
    outdir = tmp_path / "out"
    outdir.mkdir()
    (outdir / "existing.txt").write_text("already here", encoding="utf-8")
    jcvi_config = tmp_path / "jcvi.config.json"
    jcvi_config.write_text('{"schema_version": 2}\n', encoding="utf-8")
    captured = {}

    def fake_provider_run(_self, request, _signal_bus):
        mcscan_request = to_mcscan_request(request)
        captured["force"] = mcscan_request.force
        layout = create_output_layout(mcscan_request.outdir, force=mcscan_request.force)
        return RunSummary(
            status="SUCCEEDED",
            schema_version=2,
            workflow="mcscan",
            method="mcscan",
            task={"workflow": "mcscan"},
            species=[],
            final_figures=[],
            artifact_index=[],
            logs={},
            ui=UiBlock("SUCCEEDED", 1.0, [], str(layout.run_summary), str(layout.logs / "run.log")),
            scoring=ScoringBlock(),
        )

    monkeypatch.setattr("genomelens.analysis.methods.mcscan_provider.McscanWorkflowProvider.run", fake_provider_run)

    code = main(["analyze", "mcscan", "jcvi", "--force", str(input_dir), str(outdir), str(jcvi_config)])

    assert code == 0
    assert captured["force"] is True


def test_analyze_mcscan_jcvi_reuses_existing_execution_path(tmp_path: Path, monkeypatch) -> None:
    root = Path(__file__).resolve().parents[3]
    sample = root / "references" / "samples" / "shell" / "bed_cds_minimal"
    input_dir = tmp_path / "input"
    _copy_species_files(input_dir, sample, ["query.bed", "query.cds", "subject.bed", "subject.cds"])
    outdir = tmp_path / "out"
    captured = {}

    def fake_provider_run(_self, request, _signal_bus):
        captured["method"] = request.method
        captured["output"] = request.output.directory
        return RunSummary(
            status="SUCCEEDED",
            schema_version=2,
            workflow="mcscan",
            method="mcscan",
            task={"workflow": "mcscan"},
            species=[],
            final_figures=[],
            artifact_index=[],
            logs={},
            ui=UiBlock(
                "SUCCEEDED", 1.0, [], str(outdir / "report" / "run_summary.json"), str(outdir / "logs" / "run.log")
            ),
            scoring=ScoringBlock(),
        )

    monkeypatch.setattr("genomelens.analysis.methods.mcscan_provider.McscanWorkflowProvider.run", fake_provider_run)

    code = main(["analyze", "mcscan", "jcvi", str(input_dir), str(outdir), "--force"])

    assert code == 0
    assert captured["method"] == "mcscan"
    assert captured["output"] == str(outdir.resolve())


def test_analyze_mcscan_jcvi_subtask_sets_workflow(tmp_path: Path, monkeypatch) -> None:
    root = Path(__file__).resolve().parents[3]
    sample = root / "references" / "samples" / "shell" / "bed_cds_minimal"
    input_dir = tmp_path / "input"
    _copy_species_files(input_dir, sample, ["query.bed", "query.cds", "subject.bed", "subject.cds"])
    outdir = tmp_path / "out"
    captured = {}

    def fake_provider_run(_self, request, _signal_bus):
        captured["workflow"] = request.method_config["workflow"]
        return RunSummary(
            status="SUCCEEDED",
            schema_version=2,
            workflow="mcscan",
            method="mcscan",
            task={"workflow": "mcscan"},
            species=[],
            final_figures=[],
            artifact_index=[],
            logs={},
            ui=UiBlock(
                "SUCCEEDED", 1.0, [], str(outdir / "report" / "run_summary.json"), str(outdir / "logs" / "run.log")
            ),
            scoring=ScoringBlock(),
        )

    monkeypatch.setattr("genomelens.analysis.methods.mcscan_provider.McscanWorkflowProvider.run", fake_provider_run)

    code = main(["analyze", "mcscan", "jcvi", "graphics_dotplot", str(input_dir), str(outdir), "--force"])

    assert code == 0
    assert captured["workflow"] == "graphics_dotplot"


def test_analyze_mcscan_jcvi_histogram_subtask_sets_workflow(tmp_path: Path, monkeypatch) -> None:
    numbers = tmp_path / "numbers.txt"
    numbers.write_text("1\n2\n3\n", encoding="utf-8")
    outdir = tmp_path / "out"
    captured = {}

    def fake_provider_run(_self, request, _signal_bus):
        captured["workflow"] = request.method_config["workflow"]
        captured["input_mode"] = request.input.mode
        captured["species"] = request.input.species
        captured["histogram_inputs"] = request.method_config["histogram_inputs"]
        return RunSummary(
            status="SUCCEEDED",
            schema_version=2,
            workflow="mcscan",
            method="mcscan",
            task={"workflow": "mcscan"},
            species=[],
            final_figures=[],
            artifact_index=[],
            logs={},
            ui=UiBlock(
                "SUCCEEDED", 1.0, [], str(outdir / "report" / "run_summary.json"), str(outdir / "logs" / "run.log")
            ),
            scoring=ScoringBlock(),
        )

    monkeypatch.setattr("genomelens.analysis.methods.mcscan_provider.McscanWorkflowProvider.run", fake_provider_run)

    code = main(
        [
            "analyze",
            "mcscan",
            "jcvi",
            "graphics_histogram",
            str(numbers),
            str(outdir),
            "--histogram-columns",
            "0",
            "--force",
        ]
    )

    assert code == 0
    assert captured["workflow"] == "graphics_histogram"
    assert captured["input_mode"] == "method_specific"
    assert captured["species"] == []
    assert captured["histogram_inputs"] == [str(numbers.resolve())]


def test_analyze_mcscan_jcvi_subtask_overrides_workflow_flag(tmp_path: Path, monkeypatch) -> None:
    root = Path(__file__).resolve().parents[3]
    sample = root / "references" / "samples" / "shell" / "bed_cds_minimal"
    input_dir = tmp_path / "input"
    _copy_species_files(input_dir, sample, ["query.bed", "query.cds", "subject.bed", "subject.cds"])
    outdir = tmp_path / "out"
    captured = {}

    def fake_provider_run(_self, request, _signal_bus):
        captured["workflow"] = request.method_config["workflow"]
        return RunSummary(
            status="SUCCEEDED",
            schema_version=2,
            workflow="mcscan",
            method="mcscan",
            task={"workflow": "mcscan"},
            species=[],
            final_figures=[],
            artifact_index=[],
            logs={},
            ui=UiBlock(
                "SUCCEEDED", 1.0, [], str(outdir / "report" / "run_summary.json"), str(outdir / "logs" / "run.log")
            ),
            scoring=ScoringBlock(),
        )

    monkeypatch.setattr("genomelens.analysis.methods.mcscan_provider.McscanWorkflowProvider.run", fake_provider_run)

    code = main(
        [
            "analyze",
            "mcscan",
            "jcvi",
            "graphics_dotplot",
            str(input_dir),
            str(outdir),
            "--jcvi-workflow",
            "graphics_synteny",
            "--force",
        ]
    )

    assert code == 0
    assert captured["workflow"] == "graphics_dotplot"


def test_analyze_mcscan_log_level_overrides_verbose(tmp_path: Path, monkeypatch) -> None:
    root = Path(__file__).resolve().parents[3]
    sample = root / "references" / "samples" / "shell" / "bed_cds_minimal"
    input_dir = tmp_path / "input"
    _copy_species_files(input_dir, sample, ["query.bed", "query.cds", "subject.bed", "subject.cds"])
    outdir = tmp_path / "out"
    captured = {}

    def fake_provider_run(_self, request, _signal_bus):
        captured["log_level"] = request.options.log_level
        captured["verbose"] = request.options.verbose
        captured["console_log"] = request.options.console_log
        return RunSummary(
            status="SUCCEEDED",
            schema_version=2,
            workflow="mcscan",
            method="mcscan",
            task={"workflow": "mcscan"},
            species=[],
            final_figures=[],
            artifact_index=[],
            logs={},
            ui=UiBlock(
                "SUCCEEDED", 1.0, [], str(outdir / "report" / "run_summary.json"), str(outdir / "logs" / "run.log")
            ),
            scoring=ScoringBlock(),
        )

    monkeypatch.setattr("genomelens.analysis.methods.mcscan_provider.McscanWorkflowProvider.run", fake_provider_run)

    code = main(
        [
            "analyze",
            "mcscan",
            "jcvi",
            str(input_dir),
            str(outdir),
            "--force",
            "--verbose",
            "--log-level",
            "ERROR",
        ]
    )

    assert code == 0
    assert captured["log_level"] == "ERROR"
    assert captured["verbose"] is True
    assert captured["console_log"] is False


def test_analyze_mcscan_uses_configured_log_level(tmp_path: Path, monkeypatch) -> None:
    root = Path(__file__).resolve().parents[3]
    sample = root / "references" / "samples" / "shell" / "bed_cds_minimal"
    input_dir = tmp_path / "input-config-log"
    _copy_species_files(input_dir, sample, ["query.bed", "query.cds", "subject.bed", "subject.cds"])
    outdir = tmp_path / "out-config-log"
    config_path = tmp_path / "genomelens.config.json"
    config_path.write_text(
        json.dumps(
            {
                "schema_version": 2,
                "workspace_root": str(tmp_path / "work"),
                "temp_root": str(tmp_path / "work" / "temp"),
                "default_output_root": str(tmp_path / "work" / "results"),
                "log_level": "WARNING",
            }
        ),
        encoding="utf-8",
    )
    captured = {}

    def fake_provider_run(_self, request, _signal_bus):
        captured["log_level"] = request.options.log_level
        captured["console_log"] = request.options.console_log
        return RunSummary(
            status="SUCCEEDED",
            schema_version=2,
            workflow="mcscan",
            method="mcscan",
            task={"workflow": "mcscan"},
            species=[],
            final_figures=[],
            artifact_index=[],
            logs={},
            ui=UiBlock(
                "SUCCEEDED", 1.0, [], str(outdir / "report" / "run_summary.json"), str(outdir / "logs" / "run.log")
            ),
            scoring=ScoringBlock(),
        )

    monkeypatch.setattr("genomelens.analysis.methods.mcscan_provider.McscanWorkflowProvider.run", fake_provider_run)

    code = main(["analyze", "mcscan", "jcvi", "--config", str(config_path), str(input_dir), str(outdir), "--force"])

    assert code == 0
    assert captured["log_level"] == "WARNING"
    assert captured["console_log"] is False


def test_analyze_mcscan_default_cli_uses_progress_reporter(tmp_path: Path, monkeypatch, capsys) -> None:
    root = Path(__file__).resolve().parents[3]
    sample = root / "references" / "samples" / "shell" / "bed_cds_minimal"
    input_dir = tmp_path / "input-progress"
    _copy_species_files(input_dir, sample, ["query.bed", "query.cds", "subject.bed", "subject.cds"])
    outdir = tmp_path / "out-progress"

    def fake_provider_run(_self, _request, signal_bus):
        signal_bus.emit("state", state="VALIDATING_INPUTS")
        signal_bus.emit("state", state="PREPARING_WORKSPACE")
        signal_bus.emit("state", state="RUNNING_ENGINE")
        return RunSummary(
            status="SUCCEEDED",
            schema_version=2,
            workflow="mcscan",
            method="mcscan",
            task={"workflow": "mcscan"},
            species=[],
            final_figures=[],
            artifact_index=[],
            logs={},
            ui=UiBlock(
                "SUCCEEDED", 1.0, [], str(outdir / "report" / "run_summary.json"), str(outdir / "logs" / "run.log")
            ),
            scoring=ScoringBlock(),
        )

    monkeypatch.setattr("genomelens.analysis.methods.mcscan_provider.McscanWorkflowProvider.run", fake_provider_run)

    code = main(["analyze", "mcscan", "jcvi", str(input_dir), str(outdir), "--force"])
    captured = capsys.readouterr()

    assert code == 0
    assert "%" in captured.out
    assert "task_started" not in captured.out


def test_analyze_run_json_suppresses_progress_reporter(tmp_path: Path, monkeypatch, capsys) -> None:
    root = Path(__file__).resolve().parents[3]
    sample = root / "references" / "samples" / "shell" / "bed_cds_minimal"
    outdir = tmp_path / "out-json-run"
    request_path = tmp_path / "request.json"
    request_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "kind": "analysis_request",
                "method": "mcscan",
                "input": {
                    "mode": "bed_cds",
                    "species": [
                        {
                            "name": "query",
                            "input_mode": "bed_cds",
                            "bed": str(sample / "query.bed"),
                            "cds": str(sample / "query.cds"),
                        },
                        {
                            "name": "subject",
                            "input_mode": "bed_cds",
                            "bed": str(sample / "subject.bed"),
                            "cds": str(sample / "subject.cds"),
                        },
                    ],
                },
                "output": {
                    "directory": str(outdir),
                    "force": True,
                    "formats": ["png"],
                },
                "config": {},
                "options": {
                    "preset": "auto",
                    "min_block_size": 1,
                },
                "method_config": {
                    "workflow": "graphics_synteny",
                },
            }
        ),
        encoding="utf-8",
    )

    def fake_provider_run(_self, _request, signal_bus):
        signal_bus.emit("state", state="RUNNING_ENGINE")
        return RunSummary(
            status="SUCCEEDED",
            schema_version=2,
            workflow="mcscan",
            method="mcscan",
            task={"workflow": "mcscan"},
            species=[],
            final_figures=[],
            artifact_index=[],
            logs={},
            ui=UiBlock(
                "SUCCEEDED", 1.0, [], str(outdir / "report" / "run_summary.json"), str(outdir / "logs" / "run.log")
            ),
            scoring=ScoringBlock(),
        )

    monkeypatch.setattr("genomelens.analysis.methods.mcscan_provider.McscanWorkflowProvider.run", fake_provider_run)

    code = main(["analyze", "run", str(request_path), "--json"])
    captured = capsys.readouterr()

    assert code == 0
    assert captured.err == ""
    assert json.loads(captured.out)["status"] == "SUCCEEDED"


def test_analyze_run_dispatches_request_json(tmp_path: Path, monkeypatch) -> None:
    root = Path(__file__).resolve().parents[3]
    sample = root / "references" / "samples" / "shell" / "bed_cds_minimal"
    outdir = tmp_path / "out-run"
    request_path = tmp_path / "request.json"
    request_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "kind": "analysis_request",
                "method": "mcscan",
                "input": {
                    "mode": "bed_cds",
                    "species": [
                        {
                            "name": "query",
                            "input_mode": "bed_cds",
                            "bed": str(sample / "query.bed"),
                            "cds": str(sample / "query.cds"),
                        },
                        {
                            "name": "subject",
                            "input_mode": "bed_cds",
                            "bed": str(sample / "subject.bed"),
                            "cds": str(sample / "subject.cds"),
                        },
                    ],
                },
                "output": {
                    "directory": str(outdir),
                    "force": True,
                    "formats": ["png"],
                },
                "config": {},
                "options": {
                    "preset": "auto",
                    "min_block_size": 1,
                },
                "method_config": {
                    "workflow": "graphics_synteny",
                },
            }
        ),
        encoding="utf-8",
    )
    captured = {}

    def fake_provider_run(_self, request, _signal_bus):
        captured["method"] = request.method
        captured["output"] = request.output.directory
        return RunSummary(
            status="SUCCEEDED",
            schema_version=2,
            workflow="mcscan",
            method="mcscan",
            task={"workflow": "mcscan"},
            species=[],
            final_figures=[],
            artifact_index=[],
            logs={},
            ui=UiBlock(
                "SUCCEEDED", 1.0, [], str(outdir / "report" / "run_summary.json"), str(outdir / "logs" / "run.log")
            ),
            scoring=ScoringBlock(),
        )

    monkeypatch.setattr("genomelens.analysis.methods.mcscan_provider.McscanWorkflowProvider.run", fake_provider_run)

    code = main(["analyze", "run", str(request_path)])

    assert code == 0
    assert captured["method"] == "mcscan"
    assert captured["output"] == str(outdir)
    assert (outdir / "inputs" / "analysis_request.json").is_file()


def test_analyze_mcscan_requires_backend(capsys) -> None:
    code = main(["analyze", "mcscan", "input", "output"])

    assert code == 2
    capsys.readouterr()


def test_analyze_mcscan_with_source_engine(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[3]
    sample = root / "references" / "samples" / "shell" / "bed_cds_minimal"
    input_dir = tmp_path / "input"
    _copy_species_files(input_dir, sample, ["query.bed", "query.cds", "subject.bed", "subject.cds"])
    outdir = tmp_path / "out"
    code = main(
        [
            "analyze",
            "mcscan",
            "jcvi",
            *_auto_args(input_dir, outdir),
            "--min-block-size",
            "1",
            "--force",
        ]
    )
    assert code == 0
    summary = json.loads((outdir / "report" / "run_summary.json").read_text(encoding="utf-8"))
    assert summary["status"] == "SUCCEEDED"
    assert summary["schema_version"] == 2
    assert summary["task"]["task_type"] == "pairwise_synteny"
    assert [item["role"] for item in summary["species"]] == ["query", "subject"]
    assert summary["jcvi_backend"] == "jcvi-genomelens-engine"
    assert summary["jcvi_distribution"] == "source"
    assert summary["jcvi_runtime_mode"] in {"core", "accelerated"}
    assert isinstance(summary["jcvi_loaded_extensions"], list)
    assert isinstance(summary["jcvi_missing_extensions"], list)
    assert summary["simplified_fallback"] is False
    assert Path(summary["blast_table"]).stat().st_size > 0
    assert Path(summary["anchors_path"]).is_file()
    assert any(item["artifact_type"] == "figure" for item in summary["artifact_index"])
    assert summary["ui"]["state"] == "SUCCEEDED"
    assert summary["ui"]["progress"] == 1.0
    assert summary["scoring"]["status"] == "not_run"
    engine_summary = json.loads(Path(summary["engine_summary_path"]).read_text(encoding="utf-8"))
    assert engine_summary["task"]["task_type"] == "pairwise_synteny"
    assert [item["role"] for item in engine_summary["species"]] == ["query", "subject"]
    assert [command["name"] for command in engine_summary["commands"]] == [
        "makeblastdb.exe",
        "blastn.exe",
        "jcvi.compara.synteny.scan",
        "jcvi.compara.synteny.simple",
        "jcvi.compara.synteny.mcscan",
        "jcvi.formats.bed.merge",
        "jcvi.graphics.dotplot",
        "jcvi.graphics.synteny",
    ]
    assert any(Path(path).name == "dotplot.svg" for path in summary["final_figures"])
    assert any(Path(path).name == "synteny.svg" for path in summary["final_figures"])
    request_snapshot = json.loads((outdir / "inputs" / "analysis_request.json").read_text(encoding="utf-8"))
    assert request_snapshot["kind"] == "analysis_request"
    assert request_snapshot["method"] == "mcscan"
    assert summary["analysis_request_path"] == str((outdir / "inputs" / "analysis_request.json").resolve())
    run_log = (outdir / "logs" / "run.log").read_text(encoding="utf-8")
    assert "task_started task_id=query__subject__graphics_synteny step=prepare_inputs" in run_log
    assert "task_finished task_id=query__subject__graphics_synteny step=run_engine status=SUCCEEDED" in run_log
    engine_log = (outdir / "intermediate" / "jcvi" / "run.log").read_text(encoding="utf-8")
    assert "task_started task_id=engine step=load_manifest" in engine_log
    assert "task_finished task_id=engine step=makeblastdb.exe status=SUCCEEDED" in engine_log
    assert "task_finished task_id=engine step=jcvi.graphics.synteny status=SUCCEEDED" in engine_log


def test_analyze_mcscan_with_three_species(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[3]
    sample = root / "references" / "samples" / "shell" / "bed_cds_minimal"
    third_bed, third_cds = _write_third_species(tmp_path, sample)
    input_dir = tmp_path / "input-multi"
    _copy_species_files(input_dir, sample, ["query.bed", "query.cds", "subject.bed", "subject.cds"])
    shutil.copy2(third_bed, input_dir / "third.bed")
    shutil.copy2(third_cds, input_dir / "third.cds")
    outdir = tmp_path / "out-multi"
    code = main(
        [
            "analyze",
            "mcscan",
            "jcvi",
            *_auto_args(input_dir, outdir),
            "--rewrite-layout-links",
            "--optimize-figsize",
            "--fix-karyotype-label-overlap",
            "--min-block-size",
            "1",
            "--force",
        ]
    )
    assert code == 0
    summary = json.loads((outdir / "report" / "run_summary.json").read_text(encoding="utf-8"))
    assert summary["status"] == "SUCCEEDED"
    assert summary["task"]["task_type"] == "multi_species_synteny"
    assert summary["species_count"] == 3
    assert summary["pairwise_job_count"] == 3
    assert {job["pair_id"] for job in summary["pairwise_jobs"]} == {
        "query__subject",
        "query__third",
        "subject__third",
    }
    assert all(job["status"] == "SUCCEEDED" for job in summary["pairwise_jobs"])
    assert all(Path(job["run_summary_path"]).is_file() for job in summary["pairwise_jobs"])
    assert any(Path(path).name.startswith("query__subject.") for path in summary["final_figures"])
    assert any(item["artifact_type"] == "figure" for item in summary["artifact_index"])
    # 全局多物种核型总图：所有 pairwise 成功后应聚合出至少一张总图。
    assert summary["global_figures"], "expected a global multi-species karyotype figure"
    assert all(Path(path).is_file() for path in summary["global_figures"])
    assert any(Path(path).name.startswith("global.") for path in summary["global_figures"])
    assert any(path in summary["final_figures"] for path in summary["global_figures"])
    request_snapshot = json.loads((outdir / "inputs" / "analysis_request.json").read_text(encoding="utf-8"))
    assert request_snapshot["method_config"]["fix_karyotype_label_overlap"] is True
    global_manifest = json.loads(
        (outdir / "intermediate" / "global_karyotype" / "global_manifest.json").read_text(encoding="utf-8")
    )
    assert global_manifest["options"]["rewrite_layout_links"] is True
    assert global_manifest["options"]["optimize_figsize"] is True
    assert global_manifest["options"]["fix_karyotype_label_overlap"] is True
    global_summary = json.loads(
        (outdir / "intermediate" / "global_karyotype" / "engine_run_summary.json").read_text(encoding="utf-8")
    )
    global_artifacts = global_summary["artifacts"]
    assert global_artifacts["rewritten_layout_edges"] >= 0
    assert global_artifacts["rewritten_track_order"]
    assert global_artifacts["optimized_figsize"]
    assert global_artifacts["karyotype_renderer_variant"] == "mirrored"
    assert global_artifacts["karyotype_label_overlap_fix"] is True
    global_layout = (outdir / "intermediate" / "global_karyotype" / "karyotype_global.layout").read_text(
        encoding="utf-8"
    )
    assert "label_va" in global_layout
    global_command = global_summary["commands"][-1]["argv"]
    assert "--figsize" in global_command
    run_log = (outdir / "logs" / "run.log").read_text(encoding="utf-8")
    assert "step=prepare_multi_species_workspace status=STARTED" in run_log
    assert "step=run_pairwise_job status=STARTED" in run_log
    assert "step=build_global_karyotype status=SUCCEEDED" in run_log
    assert (outdir / "intermediate" / "pairwise" / "query__subject" / "logs" / "run.log").is_file()


def test_analyze_mcscan_discovers_bed_cds_directory(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[3]
    sample = root / "references" / "samples" / "shell" / "bed_cds_minimal"
    input_dir = tmp_path / "input"
    _copy_species_files(input_dir, sample, ["query.bed", "query.cds", "subject.bed", "subject.cds"])
    outdir = tmp_path / "out-auto"

    code = main(
        [
            "analyze",
            "mcscan",
            "jcvi",
            str(input_dir),
            str(outdir),
            "--min-block-size",
            "1",
            "--force",
        ]
    )

    assert code == 0
    summary = json.loads((outdir / "report" / "run_summary.json").read_text(encoding="utf-8"))
    assert summary["status"] == "SUCCEEDED"
    assert [item["name"] for item in summary["species"]] == ["query", "subject"]


def test_analyze_run_request_json(tmp_path: Path, monkeypatch) -> None:
    root = Path(__file__).resolve().parents[3]
    sample = root / "references" / "samples" / "shell" / "bed_cds_minimal"
    input_dir = tmp_path / "input-run"
    _copy_species_files(input_dir, sample, ["query.bed", "query.cds", "subject.bed", "subject.cds"])
    outdir = tmp_path / "out-run"
    request_path = tmp_path / "request.json"
    captured = {}

    request_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "kind": "analysis_request",
                "method": "mcscan",
                "input": {
                    "mode": "auto_directory",
                    "directory": str(input_dir),
                },
                "output": {
                    "directory": str(outdir),
                    "force": True,
                    "formats": ["png"],
                },
                "config": {},
                "options": {
                    "preset": "auto",
                    "min_block_size": 1,
                },
                "method_config": {
                    "workflow": "graphics_synteny",
                },
            }
        ),
        encoding="utf-8",
    )

    def fake_provider_run(_self, request, _signal_bus):
        captured["species"] = [item.name for item in request.input.species]
        return RunSummary(
            status="SUCCEEDED",
            schema_version=2,
            workflow="mcscan",
            method="mcscan",
            task={"workflow": "mcscan"},
            species=[],
            final_figures=[],
            artifact_index=[],
            logs={},
            ui=UiBlock(
                "SUCCEEDED", 1.0, [], str(outdir / "report" / "run_summary.json"), str(outdir / "logs" / "run.log")
            ),
            scoring=ScoringBlock(),
        )

    monkeypatch.setattr("genomelens.analysis.methods.mcscan_provider.McscanWorkflowProvider.run", fake_provider_run)

    code = main(["analyze", "run", str(request_path)])

    assert code == 0
    assert captured["species"] == ["query", "subject"]
    request_snapshot = json.loads((outdir / "inputs" / "analysis_request.json").read_text(encoding="utf-8"))
    assert request_snapshot["kind"] == "analysis_request"
    assert request_snapshot["input"]["species"][0]["name"] == "query"


def test_analyze_mcscan_with_explicit_jcvi_config(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[3]
    sample = root / "references" / "samples" / "shell" / "bed_cds_minimal"
    blast_bin = root / "toolchains" / "blast" / "current" / "bin"
    input_dir = tmp_path / "input-jcvi"
    _copy_species_files(input_dir, sample, ["query.bed", "query.cds", "subject.bed", "subject.cds"])
    jcvi_config_path = tmp_path / "jcvi.config.json"
    jcvi_config_path.write_text(
        json.dumps(
            {
                "schema_version": 2,
                "toolchain": {
                    "blastn_path": str(blast_bin / "blastn.exe"),
                    "makeblastdb_path": str(blast_bin / "makeblastdb.exe"),
                },
                "runtime": {
                    "threads": 1,
                    "formats": ["png"],
                },
                "mcscan": {
                    "min_block_size": 1,
                    "align_soft": "blast",
                    "cscore": 0.9,
                },
                "local_synteny": {
                    "dpi": 600,
                },
            }
        ),
        encoding="utf-8",
    )
    outdir = tmp_path / "out-jcvi"
    code = main(
        [
            "analyze",
            "mcscan",
            "jcvi",
            *_auto_args(input_dir, outdir),
            "--jcvi-config",
            str(jcvi_config_path),
            "--force",
        ]
    )
    assert code == 0
    request_snapshot = json.loads((outdir / "inputs" / "analysis_request.json").read_text(encoding="utf-8"))
    assert request_snapshot["config"]["method_config"] == str(jcvi_config_path.resolve())
    assert request_snapshot["method_config"]["cscore"] == 0.9
    assert request_snapshot["method_config"]["dpi"] == 600

    manifest = json.loads((outdir / "inputs" / "input_manifest.json").read_text(encoding="utf-8"))
    assert manifest["toolchain"]["blastn"] == str((blast_bin / "blastn.exe").resolve())
    assert manifest["options"]["cscore"] == 0.9
    assert manifest["options"]["dpi"] == 600
    assert manifest["options"]["threads"] == 1


def test_analyze_mcscan_with_positional_jcvi_config(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[3]
    sample = root / "references" / "samples" / "shell" / "bed_cds_minimal"
    blast_bin = root / "toolchains" / "blast" / "current" / "bin"
    input_dir = tmp_path / "input-pos"
    _copy_species_files(input_dir, sample, ["query.bed", "query.cds", "subject.bed", "subject.cds"])
    jcvi_config_path = tmp_path / "jcvi.config.json"
    jcvi_config_path.write_text(
        json.dumps(
            {
                "schema_version": 2,
                "toolchain": {
                    "blastn_path": str(blast_bin / "blastn.exe"),
                    "makeblastdb_path": str(blast_bin / "makeblastdb.exe"),
                },
                "runtime": {
                    "threads": 1,
                    "formats": ["png"],
                },
                "mcscan": {
                    "min_block_size": 1,
                    "cscore": 0.85,
                },
                "local_synteny": {
                    "dpi": 400,
                },
            }
        ),
        encoding="utf-8",
    )
    outdir = tmp_path / "out-pos"
    code = main(
        [
            "analyze",
            "mcscan",
            "jcvi",
            str(input_dir),
            str(outdir),
            str(jcvi_config_path),
            "--force",
        ]
    )
    assert code == 0
    request_snapshot = json.loads((outdir / "inputs" / "analysis_request.json").read_text(encoding="utf-8"))
    assert request_snapshot["config"]["method_config"] == str(jcvi_config_path.resolve())
    assert request_snapshot["method_config"]["cscore"] == 0.85
    assert request_snapshot["method_config"]["dpi"] == 400

    manifest = json.loads((outdir / "inputs" / "input_manifest.json").read_text(encoding="utf-8"))
    assert manifest["options"]["cscore"] == 0.85
    assert manifest["options"]["dpi"] == 400


def test_analyze_mcscan_uses_config_defaults(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[3]
    sample = root / "references" / "samples" / "shell" / "bed_cds_minimal"
    blast_bin = root / "toolchains" / "blast" / "current" / "bin"
    input_dir = tmp_path / "input-config"
    _copy_species_files(input_dir, sample, ["query.bed", "query.cds", "subject.bed", "subject.cds"])
    config_path = tmp_path / "genomelens.config.json"
    jcvi_config_path = tmp_path / "jcvi.config.json"
    config_path.write_text(
        json.dumps(
            {
                "schema_version": 2,
                "workspace_root": str(tmp_path / "work"),
                "temp_root": str(tmp_path / "work" / "temp"),
                "default_output_root": str(tmp_path / "work" / "results"),
                "jcvi_config_path": str(jcvi_config_path),
                "log_level": "INFO",
            }
        ),
        encoding="utf-8",
    )
    jcvi_config_path.write_text(
        json.dumps(
            {
                "schema_version": 2,
                "toolchain": {
                    "jcvi_engine_path": "",
                    "blastn_path": str(blast_bin / "blastn.exe"),
                    "makeblastdb_path": str(blast_bin / "makeblastdb.exe"),
                    "magick_path": "",
                },
                "runtime": {
                    "threads": 1,
                    "formats": ["png"],
                },
                "mcscan": {
                    "workflow": "graphics_synteny",
                    "min_block_size": 1,
                },
            }
        ),
        encoding="utf-8",
    )
    outdir = tmp_path / "out-config"
    code = main(
        [
            "analyze",
            "mcscan",
            "jcvi",
            "--config",
            str(config_path),
            *_auto_args(input_dir, outdir),
            "--force",
        ]
    )
    assert code == 0
    manifest = json.loads((outdir / "inputs" / "input_manifest.json").read_text(encoding="utf-8"))
    assert manifest["schema_version"] == 2
    assert manifest["task"]["workflow"] == "graphics_synteny"
    assert [item["role"] for item in manifest["species"]] == ["query", "subject"]
    assert manifest["toolchain"]["blastn"] == str((blast_bin / "blastn.exe").resolve())
    assert manifest["options"]["threads"] == 1
    assert manifest["options"]["min_block_size"] == 1


def test_analyze_mcscan_local_synteny_flags(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[3]
    sample = root / "references" / "samples" / "shell" / "bed_cds_minimal"
    input_dir = tmp_path / "input-local"
    _copy_species_files(input_dir, sample, ["query.bed", "query.cds", "subject.bed", "subject.cds"])
    outdir = tmp_path / "out-local"
    code = main(
        [
            "analyze",
            "mcscan",
            "jcvi",
            *_auto_args(input_dir, outdir),
            "--target-genes",
            "qgene2",
            "--up",
            "1",
            "--down",
            "1",
            "--split-targets",
            "--label-targets",
            "--align-soft",
            "blast",
            "--dbtype",
            "nucl",
            "--cscore",
            "0.7",
            "--dist",
            "20",
            "--iter",
            "1",
            "--glyphstyle",
            "arrow",
            "--glyphcolor",
            "orthogroup",
            "--shadestyle",
            "curve",
            "--dpi",
            "150",
            "--min-block-size",
            "1",
            "--force",
        ]
    )
    assert code == 0
    summary = json.loads((outdir / "report" / "run_summary.json").read_text(encoding="utf-8"))
    assert summary["status"] == "SUCCEEDED"
    assert summary["task"]["task_type"] == "pairwise_synteny"

    request_snapshot = json.loads((outdir / "inputs" / "analysis_request.json").read_text(encoding="utf-8"))
    method_config = request_snapshot["method_config"]
    assert method_config["target_gene_ids"] == ["qgene2"]
    assert method_config["up"] == 1
    assert method_config["down"] == 1
    assert method_config["split_targets"] is True
    assert method_config["label_targets"] is True
    assert method_config["glyphstyle"] == "arrow"
    assert method_config["glyphcolor"] == "orthogroup"
    assert method_config["shadestyle"] == "curve"
    assert method_config["dpi"] == 150

    # engine manifest 应携带 local_synteny 参数
    manifest = json.loads((outdir / "intermediate" / "jcvi" / "jcvi_engine_manifest.json").read_text(encoding="utf-8"))
    assert manifest["workflow"] == "local_synteny"
    assert manifest["options"]["target_gene_ids"] == ["qgene2"]

    # 局部共线性结果应落入 intermediate/local/
    local_dir = outdir / "intermediate" / "local"
    assert local_dir.is_dir()
    assert any(local_dir.glob("*.local.svg"))
    assert any(local_dir.glob("*.local.blocks"))
    assert any(local_dir.glob("*.local.bed"))
    assert any(local_dir.glob("*.local.layout"))
    assert summary["final_figures"]
    assert any("local" in Path(p).name for p in summary["final_figures"])


def test_analyze_mcscan_graphics_histogram_end_to_end(tmp_path: Path) -> None:
    numbers = tmp_path / "numbers.txt"
    numbers.write_text("1\n2\n2\n3\n5\n8\n13\n", encoding="utf-8-sig")
    outdir = tmp_path / "out-histogram"

    code = main(
        [
            "analyze",
            "mcscan",
            "jcvi",
            "graphics_histogram",
            str(numbers),
            str(outdir),
            "--formats",
            "png,svg",
            "--histogram-columns",
            "0",
            "--histogram-bins",
            "4",
            "--histogram-title",
            "Histogram",
            "--force",
        ]
    )

    assert code == 0
    summary = json.loads((outdir / "report" / "run_summary.json").read_text(encoding="utf-8"))
    assert summary["status"] == "SUCCEEDED"
    assert summary["jcvi_workflow"] == "graphics_histogram"
    assert summary["histogram_inputs"] == [str(numbers.resolve())]
    assert len(summary["final_figures"]) == 2
    assert all(Path(path).is_file() for path in summary["final_figures"])

    manifest = json.loads((outdir / "inputs" / "input_manifest.json").read_text(encoding="utf-8"))
    assert manifest["workflow"] == "graphics_histogram"
    assert manifest["options"]["histogram_inputs"] == [str(numbers.resolve())]
    assert manifest["options"]["histogram_bins"] == 4


def test_analyze_mcscan_reference_swap(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[3]
    sample = root / "references" / "samples" / "shell" / "bed_cds_minimal"
    input_dir = tmp_path / "input-ref"
    _copy_species_files(input_dir, sample, ["query.bed", "query.cds", "subject.bed", "subject.cds"])
    outdir = tmp_path / "out-ref"
    code = main(
        [
            "analyze",
            "mcscan",
            "jcvi",
            str(input_dir),
            str(outdir),
            "--reference",
            "subject",
            "--target-genes",
            "sgene2",
            "--up",
            "1",
            "--down",
            "1",
            "--min-block-size",
            "1",
            "--force",
        ]
    )
    assert code == 0
    summary = json.loads((outdir / "report" / "run_summary.json").read_text(encoding="utf-8"))
    assert summary["status"] == "SUCCEEDED"
    assert summary["species_a_name"] == "subject"
    assert summary["species_b_name"] == "query"

    manifest = json.loads((outdir / "intermediate" / "jcvi" / "jcvi_engine_manifest.json").read_text(encoding="utf-8"))
    assert manifest["workflow"] == "local_synteny"
    assert manifest["query"]["name"] == "subject"
    assert manifest["subject"]["name"] == "query"
    assert manifest["options"]["target_gene_ids"] == ["sgene2"]

    engine_summary = json.loads(
        (outdir / "intermediate" / "jcvi" / "engine_run_summary.json").read_text(encoding="utf-8")
    )
    local_artifacts = engine_summary["artifacts"]["local_artifacts"]
    assert [item["target"] for item in local_artifacts] == ["sgene2"]


def test_analyze_mcscan_reference_vs_targets_three_species(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[3]
    sample = root / "references" / "samples" / "shell" / "bed_cds_minimal"
    third_bed, third_cds = _write_third_species(tmp_path, sample)
    input_dir = tmp_path / "input-ref-multi"
    _copy_species_files(input_dir, sample, ["query.bed", "query.cds", "subject.bed", "subject.cds"])
    shutil.copy2(third_bed, input_dir / "third.bed")
    shutil.copy2(third_cds, input_dir / "third.cds")
    outdir = tmp_path / "out-ref-multi"
    code = main(
        [
            "analyze",
            "mcscan",
            "jcvi",
            str(input_dir),
            str(outdir),
            "--reference",
            "query",
            "--target-genes",
            "qgene2",
            "--rewrite-layout-links",
            "--optimize-figsize",
            "--up",
            "1",
            "--down",
            "1",
            "--min-block-size",
            "1",
            "--force",
        ]
    )
    assert code == 0
    summary = json.loads((outdir / "report" / "run_summary.json").read_text(encoding="utf-8"))
    assert summary["status"] == "SUCCEEDED"
    assert summary["pairing_strategy"] == "reference_vs_targets"
    assert summary["species_count"] == 3
    assert summary["pairwise_job_count"] == 2
    pair_ids = {job["pair_id"] for job in summary["pairwise_jobs"]}
    assert pair_ids == {"query__subject", "query__third"}
    assert all(job["status"] == "SUCCEEDED" for job in summary["pairwise_jobs"])
    assert summary["multi_species_local_figures"], "expected a multi-species local synteny figure"
    assert all(Path(path).is_file() for path in summary["multi_species_local_figures"])
    assert any(Path(path).name.startswith("multi_species_local.") for path in summary["multi_species_local_figures"])
    assert any(path in summary["final_figures"] for path in summary["multi_species_local_figures"])
    local_manifest = json.loads(
        (outdir / "intermediate" / "multi_species_local_synteny" / "local_synteny_multi_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    assert local_manifest["options"]["rewrite_layout_links"] is True
    assert local_manifest["options"]["optimize_figsize"] is True
    local_layout = (outdir / "intermediate" / "multi_species_local_synteny" / "local_multi.layout").read_text(
        encoding="utf-8"
    )
    assert "e, 0, 1, #c8c8c8" in local_layout
    assert "e, 1, 2, #c8c8c8" in local_layout
    assert "e, 0, 2, #c8c8c8" not in local_layout
    local_summary = json.loads(
        (outdir / "intermediate" / "multi_species_local_synteny" / "engine_run_summary.json").read_text(
            encoding="utf-8"
        )
    )
    local_artifacts = local_summary["artifacts"]
    assert local_artifacts["rewritten_layout_edges"] == 2
    assert local_artifacts["optimized_figsize"]
    local_command = local_summary["commands"][-1]["argv"]
    assert "--figsize" in local_command
    run_log = (outdir / "logs" / "run.log").read_text(encoding="utf-8")
    assert "step=prepare_multi_species_workspace status=STARTED" in run_log
    assert "step=run_pairwise_job status=STARTED" in run_log


def test_analyze_mcscan_config_defaults_exposed_in_init(tmp_path: Path) -> None:
    code = main(["config", "init", "--workspace", str(tmp_path / "work"), "--force"])
    assert code == 0
    jcvi_config = json.loads((tmp_path / "work" / "jcvi.config.json").read_text(encoding="utf-8"))
    assert jcvi_config["toolchain"]["lastal_path"] == ""
    assert jcvi_config["toolchain"]["lastdb_path"] == ""
    assert jcvi_config["runtime"]["threads"] == 4
    assert jcvi_config["runtime"]["formats"] == ["svg"]
    assert jcvi_config["mcscan"]["align_soft"] == "blast"
    assert jcvi_config["mcscan"]["dbtype"] == "nucl"
    assert jcvi_config["mcscan"]["cscore"] == 0.7
    assert jcvi_config["mcscan"]["dist"] == 20
    assert jcvi_config["mcscan"]["iter"] == 1
    assert jcvi_config["local_synteny"]["up"] == 20
    assert jcvi_config["local_synteny"]["down"] == 20
    assert jcvi_config["local_synteny"]["dpi"] == 300
    assert jcvi_config["local_synteny"]["fix_karyotype_label_overlap"] is False

    root = Path(__file__).resolve().parents[3]
    sample = root / "references" / "samples" / "shell" / "bed_cds_minimal"
    input_dir = tmp_path / "input-fallback"
    _copy_species_files(input_dir, sample, ["query.bed", "query.cds", "subject.bed", "subject.cds"])
    code = main(
        [
            "analyze",
            "mcscan",
            "jcvi",
            *_auto_args(input_dir, tmp_path / "out"),
            "--min-block-size",
            "1",
            "--allow-simplified-fallback",
            "--force",
        ]
    )
    assert code != 0
