import json
import shutil
from pathlib import Path

from genomelens.cli.main import main
from genomelens.contracts.summaries import RunSummary, ScoringBlock, UiBlock
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


def _blast_executable(root: Path, name: str) -> Path:
    candidate = shutil.which(name)
    if candidate:
        return Path(candidate).resolve()
    return (root / "toolchains" / "blast" / "current" / "bin" / f"{name}.exe").resolve()


def _workflow_request_payload(sample: Path, outdir: Path) -> dict[str, object]:
    return {
        "schema_version": 3,
        "kind": "workflow_request",
        "workflow_id": "synteny",
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
        "reference_index": 0,
        "inputs": {},
        "parameters": {},
        "output": {"directory": str(outdir), "force": True, "formats": ["png"]},
        "runtime": {"min_block_size": 1},
    }


def test_cli_help() -> None:
    assert main(["--help"]) == 0


def test_cli_help_for_workflow(capsys) -> None:
    assert main(["help", "analyze", "workflow"]) == 0
    help_command_output = capsys.readouterr().out

    assert main(["analyze", "workflow", "--help"]) == 0
    direct_help_output = capsys.readouterr().out

    assert help_command_output == direct_help_output
    assert "workflow_id" in help_command_output
    assert "--jcvi-config" in help_command_output


def test_cli_help_for_submodule(capsys) -> None:
    assert main(["help", "analyze", "submodule"]) == 0
    output = capsys.readouterr().out

    assert "module_id" in output
    assert "--input-ports" in output
    assert "--output-dir" in output


def test_cli_help_for_command_uses_color_when_enabled(capsys, monkeypatch) -> None:
    monkeypatch.setenv("GENOMELENS_FORCE_COLOR", "1")

    assert main(["help", "analyze", "workflow"]) == 0
    output = capsys.readouterr().out

    assert "\033[" in output
    assert "workflow_id" in output


def test_cli_help_for_analyze_run(capsys) -> None:
    assert main(["help", "analyze", "run"]) == 0
    output = capsys.readouterr().out

    assert "request_json" in output
    assert "--json" in output


def test_analyze_template_synteny(capsys) -> None:
    assert main(["analyze", "template", "workflow", "synteny"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["kind"] == "workflow_request"
    assert payload["workflow_id"] == "synteny"
    assert payload["schema_version"] == 3


def test_analyze_schema(capsys) -> None:
    assert main(["analyze", "schema"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    workflow_schema = payload["$defs"]["workflow_request"]
    assert workflow_schema["properties"]["kind"]["const"] == "workflow_request"
    assert workflow_schema["properties"]["workflow_id"]["enum"] == ["synteny"]
    assert payload["$defs"]["submodule_request"]["properties"]["kind"]["const"] == "submodule_request"


def test_check_json_short_option() -> None:
    assert main(["check", "-j"]) in {0, 5}


def test_config_init(tmp_path: Path) -> None:
    assert main(["config", "init", "--workspace", str(tmp_path / "work"), "--force"]) == 0
    assert (tmp_path / "work" / "genomelens.config.json").is_file()
    assert (tmp_path / "work" / "jcvi.config.json").is_file()


def test_analyze_workflow_force_before_positionals_reuses_output_dir(tmp_path: Path, monkeypatch) -> None:
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

    def fake_dispatch(_self, request, signal_bus=None):
        captured["force"] = request.output.force
        layout = create_output_layout(Path(request.output.directory), force=request.output.force)
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

    monkeypatch.setattr("genomelens.analysis.dispatchers.task_dispatcher.TaskDispatcher.dispatch", fake_dispatch)

    code = main(
        [
            "analyze",
            "workflow",
            "synteny",
            "--force",
            str(input_dir),
            str(outdir),
            "--jcvi-config",
            str(jcvi_config),
        ]
    )

    assert code == 0
    assert captured["force"] is True


def test_analyze_workflow_reuses_existing_execution_path(tmp_path: Path, monkeypatch) -> None:
    root = Path(__file__).resolve().parents[3]
    sample = root / "references" / "samples" / "shell" / "bed_cds_minimal"
    input_dir = tmp_path / "input"
    _copy_species_files(input_dir, sample, ["query.bed", "query.cds", "subject.bed", "subject.cds"])
    outdir = tmp_path / "out"
    captured = {}

    def fake_dispatch(_self, request, signal_bus=None):
        captured["workflow_id"] = request.workflow_id
        captured["output"] = request.output.directory
        return RunSummary(
            status="SUCCEEDED",
            schema_version=3,
            workflow="synteny",
            task={"workflow": "synteny"},
            species=[],
            final_figures=[],
            artifact_index=[],
            logs={},
            ui=UiBlock(
                "SUCCEEDED", 1.0, [], str(outdir / "report" / "run_summary.json"), str(outdir / "logs" / "run.log")
            ),
            scoring=ScoringBlock(),
        )

    monkeypatch.setattr("genomelens.analysis.dispatchers.task_dispatcher.TaskDispatcher.dispatch", fake_dispatch)

    code = main(["analyze", "workflow", "synteny", str(input_dir), str(outdir), "--force"])

    assert code == 0
    assert captured["workflow_id"] == "synteny"
    assert captured["output"] == str(outdir.resolve())


def test_analyze_workflow_log_level_overrides_verbose(tmp_path: Path, monkeypatch) -> None:
    root = Path(__file__).resolve().parents[3]
    sample = root / "references" / "samples" / "shell" / "bed_cds_minimal"
    input_dir = tmp_path / "input"
    _copy_species_files(input_dir, sample, ["query.bed", "query.cds", "subject.bed", "subject.cds"])
    outdir = tmp_path / "out"
    captured = {}

    def fake_dispatch(_self, request, signal_bus=None):
        captured["log_level"] = request.runtime.log_level
        captured["verbose"] = request.runtime.verbose
        captured["console_log"] = request.runtime.console_log
        return RunSummary(
            status="SUCCEEDED",
            schema_version=3,
            workflow="synteny",
            task={"workflow": "synteny"},
            species=[],
            final_figures=[],
            artifact_index=[],
            logs={},
            ui=UiBlock(
                "SUCCEEDED", 1.0, [], str(outdir / "report" / "run_summary.json"), str(outdir / "logs" / "run.log")
            ),
            scoring=ScoringBlock(),
        )

    monkeypatch.setattr("genomelens.analysis.dispatchers.task_dispatcher.TaskDispatcher.dispatch", fake_dispatch)

    code = main(
        [
            "analyze",
            "workflow",
            "synteny",
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


def test_analyze_workflow_uses_configured_log_level(tmp_path: Path, monkeypatch) -> None:
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

    def fake_dispatch(_self, request, signal_bus=None):
        captured["log_level"] = request.runtime.log_level
        captured["console_log"] = request.runtime.console_log
        return RunSummary(
            status="SUCCEEDED",
            schema_version=3,
            workflow="synteny",
            task={"workflow": "synteny"},
            species=[],
            final_figures=[],
            artifact_index=[],
            logs={},
            ui=UiBlock(
                "SUCCEEDED", 1.0, [], str(outdir / "report" / "run_summary.json"), str(outdir / "logs" / "run.log")
            ),
            scoring=ScoringBlock(),
        )

    monkeypatch.setattr("genomelens.analysis.dispatchers.task_dispatcher.TaskDispatcher.dispatch", fake_dispatch)

    code = main(
        [
            "analyze",
            "workflow",
            "synteny",
            "--config",
            str(config_path),
            str(input_dir),
            str(outdir),
            "--force",
        ]
    )

    assert code == 0
    assert captured["log_level"] == "WARNING"
    assert captured["console_log"] is False


def test_analyze_workflow_default_cli_uses_progress_reporter(tmp_path: Path, monkeypatch, capsys) -> None:
    root = Path(__file__).resolve().parents[3]
    sample = root / "references" / "samples" / "shell" / "bed_cds_minimal"
    input_dir = tmp_path / "input-progress"
    _copy_species_files(input_dir, sample, ["query.bed", "query.cds", "subject.bed", "subject.cds"])
    outdir = tmp_path / "out-progress"

    def fake_dispatch(_self, _request, signal_bus=None):
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

    monkeypatch.setattr("genomelens.analysis.dispatchers.task_dispatcher.TaskDispatcher.dispatch", fake_dispatch)

    code = main(["analyze", "workflow", "synteny", str(input_dir), str(outdir), "--force"])
    captured = capsys.readouterr()

    assert code == 0
    assert "%" in captured.out
    assert "task_started" not in captured.out


def test_analyze_run_json_suppresses_progress_reporter(tmp_path: Path, monkeypatch, capsys) -> None:
    root = Path(__file__).resolve().parents[3]
    sample = root / "references" / "samples" / "shell" / "bed_cds_minimal"
    outdir = tmp_path / "out-json-run"
    request_path = tmp_path / "request.json"
    request_path.write_text(json.dumps(_workflow_request_payload(sample, outdir)), encoding="utf-8")

    def fake_dispatch(_self, request, signal_bus=None):
        signal_bus.emit("state", state="RUNNING_ENGINE")
        return RunSummary(
            status="SUCCEEDED",
            schema_version=3,
            workflow=request.workflow_id,
            task={"workflow": request.workflow_id},
            species=[],
            final_figures=[],
            artifact_index=[],
            logs={},
            ui=UiBlock(
                "SUCCEEDED", 1.0, [], str(outdir / "report" / "run_summary.json"), str(outdir / "logs" / "run.log")
            ),
            scoring=ScoringBlock(),
        )

    monkeypatch.setattr("genomelens.analysis.dispatchers.task_dispatcher.TaskDispatcher.dispatch", fake_dispatch)

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
    request_path.write_text(json.dumps(_workflow_request_payload(sample, outdir)), encoding="utf-8")
    captured = {}

    def fake_dispatch(_self, request, signal_bus=None):
        captured["workflow_id"] = request.workflow_id
        captured["output"] = request.output.directory
        layout = create_output_layout(Path(request.output.directory), force=True)
        return RunSummary(
            status="SUCCEEDED",
            schema_version=3,
            workflow=request.workflow_id,
            task={"workflow": request.workflow_id},
            species=[],
            final_figures=[],
            artifact_index=[],
            logs={},
            ui=UiBlock("SUCCEEDED", 1.0, [], str(layout.run_summary), str(layout.logs / "run.log")),
            scoring=ScoringBlock(),
        )

    monkeypatch.setattr("genomelens.analysis.dispatchers.task_dispatcher.TaskDispatcher.dispatch", fake_dispatch)

    code = main(["analyze", "run", str(request_path)])

    assert code == 0
    assert captured["workflow_id"] == "synteny"
    assert captured["output"] == str(outdir)


def test_analyze_run_request_json(tmp_path: Path, monkeypatch) -> None:
    root = Path(__file__).resolve().parents[3]
    sample = root / "references" / "samples" / "shell" / "bed_cds_minimal"
    outdir = tmp_path / "out-run"
    request_path = tmp_path / "request.json"
    captured = {}
    request_path.write_text(json.dumps(_workflow_request_payload(sample, outdir)), encoding="utf-8")

    def fake_dispatch(_self, request, signal_bus=None):
        captured["species"] = [item.name for item in request.species]
        layout = create_output_layout(Path(request.output.directory), force=True)
        return RunSummary(
            status="SUCCEEDED",
            schema_version=3,
            workflow=request.workflow_id,
            task={"workflow": request.workflow_id},
            species=[],
            final_figures=[],
            artifact_index=[],
            logs={},
            ui=UiBlock("SUCCEEDED", 1.0, [], str(layout.run_summary), str(layout.logs / "run.log")),
            scoring=ScoringBlock(),
        )

    monkeypatch.setattr("genomelens.analysis.dispatchers.task_dispatcher.TaskDispatcher.dispatch", fake_dispatch)

    code = main(["analyze", "run", str(request_path)])

    assert code == 0
    assert captured["species"] == ["query", "subject"]


def test_analyze_workflow_synteny_pairwise_with_source_engine(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[3]
    sample = root / "references" / "samples" / "shell" / "bed_cds_minimal"
    input_dir = tmp_path / "input"
    _copy_species_files(input_dir, sample, ["query.bed", "query.cds", "subject.bed", "subject.cds"])
    outdir = tmp_path / "out"
    code = main(
        [
            "analyze",
            "workflow",
            "synteny",
            *_auto_args(input_dir, outdir),
            "--min-block-size",
            "1",
            "--force",
        ]
    )
    assert code == 0
    summary = json.loads((outdir / "report" / "run_summary.json").read_text(encoding="utf-8"))
    extensions = summary["extensions"]
    assert summary["status"] == "SUCCEEDED"
    assert summary["task"]["task_type"] == "pairwise_synteny"
    assert [item["role"] for item in summary["species"]] == ["reference", "target"]
    assert extensions["jcvi_backend"] == "jcvi-genomelens-engine"
    assert extensions["jcvi_distribution"] == "source"
    assert extensions["jcvi_runtime_mode"] in {"core", "accelerated"}
    assert isinstance(extensions["jcvi_loaded_extensions"], list)
    assert isinstance(extensions["jcvi_missing_extensions"], list)
    assert extensions["simplified_fallback"] is False
    assert Path(extensions["blast_table"]).stat().st_size > 0
    assert Path(extensions["anchors_path"]).is_file()
    assert any(item["artifact_type"] == "figure" for item in summary["artifact_index"])
    assert summary["ui"]["state"] == "SUCCEEDED"
    assert summary["ui"]["progress"] == 1.0
    assert summary["scoring"]["status"] == "not_run"
    engine_summary = json.loads(Path(extensions["engine_summary_path"]).read_text(encoding="utf-8"))
    assert engine_summary["task"]["task_type"] == "pairwise_synteny"
    assert [item["role"] for item in engine_summary["species"]] == ["reference", "target"]
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
    request_snapshot = json.loads((outdir / "inputs" / "workflow_request.json").read_text(encoding="utf-8"))
    assert request_snapshot["kind"] == "workflow_request"
    assert request_snapshot["workflow_id"] == "synteny"
    assert summary["analysis_request_path"] == str((outdir / "inputs" / "workflow_request.json").resolve())
    run_log = (outdir / "logs" / "run.log").read_text(encoding="utf-8")
    assert "task_started task_id=query__subject__graphics_synteny step=prepare_inputs" in run_log
    assert "task_finished task_id=query__subject__graphics_synteny step=run_engine status=SUCCEEDED" in run_log
    engine_log = (outdir / "intermediate" / "jcvi" / "run.log").read_text(encoding="utf-8")
    assert "task_started task_id=engine step=load_manifest" in engine_log
    assert "task_finished task_id=engine step=makeblastdb.exe status=SUCCEEDED" in engine_log
    assert "task_finished task_id=engine step=jcvi.graphics.synteny status=SUCCEEDED" in engine_log


def test_analyze_workflow_synteny_multi_species(tmp_path: Path) -> None:
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
            "workflow",
            "synteny",
            *_auto_args(input_dir, outdir),
            "--rewrite-layout-links",
            "--optimize-figsize",
            "--optimize-karyotype-labels",
            "--min-block-size",
            "1",
            "--force",
        ]
    )
    assert code == 0
    summary = json.loads((outdir / "report" / "run_summary.json").read_text(encoding="utf-8"))
    extensions = summary["extensions"]
    assert summary["status"] == "SUCCEEDED"
    assert summary["task"]["task_type"] == "multi_species_synteny"
    assert extensions["species_count"] == 3
    assert len(summary["child_runs"]) == 3
    assert {job["pair_id"] for job in summary["child_runs"]} == {
        "query__subject",
        "query__third",
        "subject__third",
    }
    assert all(job["status"] == "SUCCEEDED" for job in summary["child_runs"])
    assert all(Path(job["run_summary_path"]).is_file() for job in summary["child_runs"])
    assert any(Path(path).name.startswith("query__subject.") for path in summary["final_figures"])
    assert any(item["artifact_type"] == "figure" for item in summary["artifact_index"])
    # 全局多物种核型总图：所有 pairwise 成功后应聚合出至少一张总图。
    assert extensions["global_figures"], "expected a global multi-species karyotype figure"
    assert all(Path(path).is_file() for path in extensions["global_figures"])
    assert any(Path(path).name.startswith("global.") for path in extensions["global_figures"])
    assert any(path in summary["final_figures"] for path in extensions["global_figures"])
    request_snapshot = json.loads((outdir / "inputs" / "workflow_request.json").read_text(encoding="utf-8"))
    assert request_snapshot["workflow_id"] == "synteny"
    assert request_snapshot["parameters"]["plot"]["auto_optimization"]["optimize_karyotype_labels"] is True
    assert request_snapshot["parameters"]["plot"]["auto_optimization"]["optimize_figsize"] is True
    assert request_snapshot["parameters"]["plot"]["auto_optimization"]["rewrite_layout_links"] is True
    global_manifest = json.loads(
        (outdir / "intermediate" / "global_karyotype" / "global_manifest.json").read_text(encoding="utf-8")
    )
    assert global_manifest["parameters"]["auto_optimization"]["rewrite_layout_links"] is True
    assert global_manifest["parameters"]["auto_optimization"]["optimize_figsize"] is True
    assert global_manifest["parameters"]["auto_optimization"]["optimize_karyotype_labels"] is True
    global_summary = json.loads(
        (outdir / "intermediate" / "global_karyotype" / "engine_run_summary.json").read_text(encoding="utf-8")
    )
    global_artifacts = global_summary["artifacts"]
    assert global_artifacts["rewritten_layout_edges"] >= 0
    assert global_artifacts["rewritten_track_order"]
    assert global_artifacts["optimized_figsize"]
    assert global_artifacts["karyotype_renderer_variant"] == "mirrored"
    assert global_artifacts["optimize_karyotype_labels"] is True
    global_layout = (outdir / "intermediate" / "global_karyotype" / "karyotype_global.layout").read_text(
        encoding="utf-8"
    )
    assert "label_va" in global_layout
    global_command = global_summary["commands"][-1]["argv"]
    assert "--figsize" in global_command
    run_log = (outdir / "logs" / "run.log").read_text(encoding="utf-8")
    assert "task_id=query__subject step=run_pairwise_job status=STARTED" in run_log
    assert "step=run_pairwise_job status=STARTED" in run_log
    assert "step=build_global_karyotype status=SUCCEEDED" in run_log
    assert (outdir / "intermediate" / "pairwise" / "query__subject" / "logs" / "run.log").is_file()


def test_analyze_workflow_synteny_pairwise_discovers_bed_cds_directory(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[3]
    sample = root / "references" / "samples" / "shell" / "bed_cds_minimal"
    input_dir = tmp_path / "input"
    _copy_species_files(input_dir, sample, ["query.bed", "query.cds", "subject.bed", "subject.cds"])
    outdir = tmp_path / "out-auto"

    code = main(
        [
            "analyze",
            "workflow",
            "synteny",
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


def test_analyze_workflow_synteny_pairwise_with_explicit_jcvi_config(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[3]
    sample = root / "references" / "samples" / "shell" / "bed_cds_minimal"
    blastn_path = _blast_executable(root, "blastn")
    makeblastdb_path = _blast_executable(root, "makeblastdb")
    input_dir = tmp_path / "input-jcvi"
    _copy_species_files(input_dir, sample, ["query.bed", "query.cds", "subject.bed", "subject.cds"])
    jcvi_config_path = tmp_path / "jcvi.config.json"
    jcvi_config_path.write_text(
        json.dumps(
            {
                "schema_version": 2,
                "toolchain": {
                    "blastn_path": str(blastn_path),
                    "makeblastdb_path": str(makeblastdb_path),
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
            "workflow",
            "synteny",
            *_auto_args(input_dir, outdir),
            "--jcvi-config",
            str(jcvi_config_path),
            "--threads",
            "1",
            "--force",
        ]
    )
    assert code == 0
    request_snapshot = json.loads((outdir / "inputs" / "workflow_request.json").read_text(encoding="utf-8"))
    assert request_snapshot["runtime"]["engine_config"] == str(jcvi_config_path.resolve())
    assert request_snapshot["parameters"]["synteny"]["cscore"] == 0.9
    assert request_snapshot["parameters"]["plot"]["dpi"] == 600

    manifest = json.loads((outdir / "inputs" / "input_manifest.json").read_text(encoding="utf-8"))
    assert manifest["toolchain"]["blastn"] == str(blastn_path)
    assert manifest["parameters"]["cscore"] == 0.9
    assert manifest["parameters"]["dpi"] == 600
    assert manifest["parameters"]["threads"] == 1


def test_analyze_workflow_synteny_pairwise_uses_config_defaults(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[3]
    sample = root / "references" / "samples" / "shell" / "bed_cds_minimal"
    blastn_path = _blast_executable(root, "blastn")
    makeblastdb_path = _blast_executable(root, "makeblastdb")
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
                    "blastn_path": str(blastn_path),
                    "makeblastdb_path": str(makeblastdb_path),
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
            "workflow",
            "synteny",
            "--config",
            str(config_path),
            *_auto_args(input_dir, outdir),
            "--force",
        ]
    )
    assert code == 0
    manifest = json.loads((outdir / "inputs" / "input_manifest.json").read_text(encoding="utf-8"))
    assert manifest["schema_version"] == 3
    assert manifest["workflow"] == "graphics_synteny"
    assert [item["role"] for item in manifest["species"]] == ["reference", "target"]
    assert manifest["toolchain"]["blastn"] == str(blastn_path)
    assert manifest["parameters"]["threads"] == 1
    assert manifest["parameters"]["min_block_size"] == 1


def test_analyze_workflow_synteny_reference_vs_targets_local_synteny_flags(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[3]
    sample = root / "references" / "samples" / "shell" / "bed_cds_minimal"
    input_dir = tmp_path / "input-local"
    _copy_species_files(input_dir, sample, ["query.bed", "query.cds", "subject.bed", "subject.cds"])
    outdir = tmp_path / "out-local"
    code = main(
        [
            "analyze",
            "workflow",
            "synteny",
            *_auto_args(input_dir, outdir),
            "--reference",
            "query",
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
    assert summary["task"]["task_type"] == "reference_vs_targets"

    request_snapshot = json.loads((outdir / "inputs" / "workflow_request.json").read_text(encoding="utf-8"))
    local_params = request_snapshot["parameters"]["local_synteny"]
    plot_params = request_snapshot["parameters"]["plot"]
    assert local_params["target_gene_ids"] == ["qgene2"]
    assert local_params["up"] == 1
    assert local_params["down"] == 1
    assert local_params["split_targets"] is True
    assert local_params["label_targets"] is True
    assert plot_params["glyphstyle"] == "arrow"
    assert plot_params["glyphcolor"] == "orthogroup"
    assert plot_params["shadestyle"] == "curve"
    assert plot_params["dpi"] == 150

    # engine manifest 应携带局部共线性参数
    manifest = json.loads(
        (outdir / "intermediate" / "pairwise" / "query__subject" / "inputs" / "input_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    assert manifest["task"]["workflow"] == "local_synteny"

    # 局部共线性总图应存在
    assert summary["extensions"]["multi_species_local_figures"]
    assert all(Path(path).is_file() for path in summary["extensions"]["multi_species_local_figures"])
    assert summary["final_figures"]
    assert any(path in summary["final_figures"] for path in summary["extensions"]["multi_species_local_figures"])


def test_analyze_workflow_synteny_reference_vs_targets_reference_swap(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[3]
    sample = root / "references" / "samples" / "shell" / "bed_cds_minimal"
    input_dir = tmp_path / "input-ref"
    _copy_species_files(input_dir, sample, ["query.bed", "query.cds", "subject.bed", "subject.cds"])
    outdir = tmp_path / "out-ref"
    code = main(
        [
            "analyze",
            "workflow",
            "synteny",
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
    assert summary["extensions"]["reference_name"] == "subject"
    assert summary["child_runs"][0]["species_a_name"] == "subject"
    assert summary["child_runs"][0]["species_b_name"] == "query"

    manifest = json.loads(
        (outdir / "intermediate" / "pairwise" / "subject__query" / "inputs" / "input_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    # Target genes route synteny into local_synteny pairwise steps.
    assert manifest["schema_version"] == 3
    assert manifest["workflow"] == "local_synteny"

    engine_summary = json.loads(
        (
            outdir
            / "intermediate"
            / "pairwise"
            / "subject__query"
            / "intermediate"
            / "jcvi"
            / "engine_run_summary.json"
        ).read_text(encoding="utf-8")
    )
    local_artifacts = engine_summary["artifacts"]["local_artifacts"]
    assert [item["target"] for item in local_artifacts] == ["sgene2"]


def test_analyze_workflow_synteny_reference_vs_targets_three_species(tmp_path: Path) -> None:
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
            "workflow",
            "synteny",
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
    assert summary["extensions"]["pairing_strategy"] == "reference_vs_targets"
    assert summary["extensions"]["species_count"] == 3
    assert summary["extensions"]["pairwise_job_count"] == 2
    pair_ids = {job["pair_id"] for job in summary["child_runs"]}
    assert pair_ids == {"query__subject", "query__third"}
    assert all(job["status"] == "SUCCEEDED" for job in summary["child_runs"])
    local_figures = summary["extensions"]["multi_species_local_figures"]
    assert local_figures, "expected a multi-species local synteny figure"
    assert all(Path(path).is_file() for path in local_figures)
    assert any(Path(path).name.startswith("multi_species_local.") for path in local_figures)
    assert any(path in summary["final_figures"] for path in local_figures)
    local_manifest = json.loads(
        (outdir / "intermediate" / "multi_species_local_synteny" / "local_synteny_multi_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    assert local_manifest["parameters"]["auto_optimization"]["rewrite_layout_links"] is True
    assert local_manifest["parameters"]["auto_optimization"]["optimize_figsize"] is True
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
    assert "task_id=query__subject step=run_pairwise_job status=STARTED" in run_log
    assert "step=build_multi_local_synteny status=SUCCEEDED" in run_log
    assert "step=run_pairwise_job status=STARTED" in run_log


def test_analyze_mcscan_config_defaults_exposed_in_init(tmp_path: Path) -> None:
    code = main(["config", "init", "--workspace", str(tmp_path / "work"), "--force"])
    assert code == 0
    jcvi_config = json.loads((tmp_path / "work" / "jcvi.config.json").read_text(encoding="utf-8"))
    assert jcvi_config["schema_version"] == 3
    assert jcvi_config["synteny"]["align_soft"] == "blast"
    assert jcvi_config["synteny"]["dbtype"] == "nucl"
    assert jcvi_config["synteny"]["cscore"] == 0.7
    assert jcvi_config["synteny"]["dist"] == 20
    assert jcvi_config["synteny"]["iter"] == 1
    assert jcvi_config["synteny"]["min_block_size"] == 5
    assert jcvi_config["local_synteny"]["up"] == 20
    assert jcvi_config["local_synteny"]["down"] == 20
    assert jcvi_config["plot"]["dpi"] == 300
    assert jcvi_config["plot"]["auto_optimization"]["optimize_karyotype_labels"] is False
    assert jcvi_config["plot"]["auto_optimization"]["optimize_figsize"] is False
    assert jcvi_config["plot"]["auto_optimization"]["rewrite_layout_links"] is False


def test_analyze_workflow_synteny_pairwise_end_to_end(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[3]
    sample = root / "references" / "samples" / "shell" / "bed_cds_minimal"
    input_dir = tmp_path / "input-workflow"
    _copy_species_files(input_dir, sample, ["query.bed", "query.cds", "subject.bed", "subject.cds"])
    outdir = tmp_path / "out-workflow"

    code = main(
        [
            "analyze",
            "workflow",
            "synteny",
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
    assert summary["task"]["task_type"] == "pairwise_synteny"

    request_snapshot = json.loads((outdir / "inputs" / "workflow_request.json").read_text(encoding="utf-8"))
    assert request_snapshot["kind"] == "workflow_request"
    assert request_snapshot["schema_version"] == 3
    assert request_snapshot["workflow_id"] == "synteny"


def test_analyze_submodule_mcscan_pairwise_end_to_end(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[3]
    sample = root / "references" / "samples" / "shell" / "bed_cds_minimal"
    input_dir = tmp_path / "input-submodule"
    _copy_species_files(input_dir, sample, ["query.bed", "query.cds", "subject.bed", "subject.cds"])
    outdir = tmp_path / "out-submodule"

    code = main(
        [
            "analyze",
            "submodule",
            "jcvi.mcscan_pairwise",
            "--input-ports",
            json.dumps({"species_pair": str(input_dir)}),
            "--output-dir",
            str(outdir),
            "--params",
            json.dumps({"min_block_size": 1}),
            "--force",
        ]
    )
    assert code == 0
    summary = json.loads((outdir / "report" / "run_summary.json").read_text(encoding="utf-8"))
    assert summary["status"] == "SUCCEEDED"
    assert summary["task"]["task_type"] == "pairwise_synteny"

    request_snapshot = json.loads((outdir / "inputs" / "submodule_request.json").read_text(encoding="utf-8"))
    assert request_snapshot["kind"] == "submodule_request"
    assert request_snapshot["module_id"] == "jcvi.mcscan_pairwise"
    assert request_snapshot["inputs"]["species_pair"] == str(input_dir)


def test_analyze_submodule_graphics_dotplot_reuses_pairwise_artifacts(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[3]
    sample = root / "references" / "samples" / "shell" / "bed_cds_minimal"
    input_dir = tmp_path / "input-submodule-reuse"
    _copy_species_files(input_dir, sample, ["query.bed", "query.cds", "subject.bed", "subject.cds"])

    pairwise_out = tmp_path / "out-submodule-pairwise"
    code = main(
        [
            "analyze",
            "submodule",
            "jcvi.mcscan_pairwise",
            "--input-ports",
            json.dumps({"species_pair": str(input_dir)}),
            "--output-dir",
            str(pairwise_out),
            "--params",
            json.dumps({"min_block_size": 1}),
            "--force",
        ]
    )
    assert code == 0

    pairwise_summary = json.loads((pairwise_out / "report" / "run_summary.json").read_text(encoding="utf-8"))
    anchors_path = pairwise_summary["extensions"]["anchors_path"]

    dotplot_out = tmp_path / "out-submodule-dotplot"
    code = main(
        [
            "analyze",
            "submodule",
            "jcvi.graphics_dotplot",
            "--input-ports",
            json.dumps({"species_pair": str(input_dir), "anchors": anchors_path}),
            "--output-dir",
            str(dotplot_out),
            "--force",
        ]
    )
    assert code == 0

    dotplot_summary = json.loads((dotplot_out / "report" / "run_summary.json").read_text(encoding="utf-8"))
    assert dotplot_summary["status"] == "SUCCEEDED"
    engine_summary = json.loads(Path(dotplot_summary["extensions"]["engine_summary_path"]).read_text(encoding="utf-8"))
    assert [command["name"] for command in engine_summary["commands"]] == ["jcvi.graphics.dotplot"]


def test_analyze_submodule_graphics_histogram_end_to_end(tmp_path: Path) -> None:
    numbers = tmp_path / "numbers-sub.txt"
    numbers.write_text("1\n2\n2\n3\n5\n8\n13\n", encoding="utf-8-sig")
    outdir = tmp_path / "out-sub-histogram"

    code = main(
        [
            "analyze",
            "submodule",
            "jcvi.graphics_histogram",
            "--input-ports",
            json.dumps({"numeric_files": [str(numbers)]}),
            "--output-dir",
            str(outdir),
            "--params",
            json.dumps({"histogram_bins": 4}),
            "--force",
        ]
    )
    assert code == 0
    summary = json.loads((outdir / "report" / "run_summary.json").read_text(encoding="utf-8"))
    assert summary["status"] == "SUCCEEDED"
    assert summary["task"]["task_type"] == "plot_histogram"

    request_snapshot = json.loads((outdir / "inputs" / "submodule_request.json").read_text(encoding="utf-8"))
    assert request_snapshot["kind"] == "submodule_request"
    assert request_snapshot["module_id"] == "jcvi.graphics_histogram"
    assert request_snapshot["inputs"]["numeric_files"] == [str(numbers)]
