import json
import shutil
from pathlib import Path

from genomelens.cli.main import main
from genomelens.contracts.summaries import RunSummary, ScoringBlock, UiBlock
from genomelens.data.workspace.output_layout import create_output_layout


def _write_third_species(tmp_path: Path, sample: Path) -> tuple[Path, Path]:
    """基于 query 样本生成第三个物种的 bed 与 cds 文件（仅用于多物种测试）"""
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
    """将样本文件复制到输入目录"""
    input_dir.mkdir(parents=True, exist_ok=True)
    for name in names:
        shutil.copy2(sample / name, input_dir / name)


def _auto_args(input_dir: Path, outdir: Path) -> list[str]:
    """生成默认 CLI 位置参数列表"""
    return [str(input_dir), str(outdir)]


def _blast_executable(root: Path, name: str) -> Path:
    """查找 blast 可执行文件路径，优先使用系统 PATH，否则回退到工具链目录"""
    candidate = shutil.which(name)
    if candidate:
        return Path(candidate).resolve()
    return (root / "toolchains" / "blast" / "current" / "bin" / f"{name}.exe").resolve()


def _workflow_request_payload(sample: Path, outdir: Path) -> dict[str, object]:
    """构造 synteny 工作流请求 JSON 负载（用于 analyze run 测试）"""
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
    """验证 --help 返回成功"""
    assert main(["--help"]) == 0


def test_cli_help_for_workflow(capsys) -> None:
    """验证 workflow 子命令 help 与直接 --help 输出一致，并列出可用工作流子命令"""
    assert main(["help", "analyze", "workflow"]) == 0
    help_command_output = capsys.readouterr().out

    assert main(["analyze", "workflow", "--help"]) == 0
    direct_help_output = capsys.readouterr().out

    assert help_command_output == direct_help_output
    assert "synteny" in help_command_output
    # workflow 父级 help 只展示子命令，具体参数应收束在 synteny 子命令 help 中
    assert "--jcvi-config" not in help_command_output


def test_cli_help_for_workflow_synteny(capsys) -> None:
    """验证 analyze workflow synteny help 包含具体运行参数"""
    assert main(["help", "analyze", "workflow", "synteny"]) == 0
    output = capsys.readouterr().out

    assert "--jcvi-config" in output
    assert "input" in output
    assert "output_dir" in output


def test_cli_help_for_submodule(capsys) -> None:
    """验证 submodule 父级 help 展示子模块发现列表"""
    assert main(["help", "analyze", "submodule"]) == 0
    output = capsys.readouterr().out

    assert "可用子模块" in output
    assert "jcvi.pairwise" in output
    assert "计算" in output
    assert "渲染" in output


def test_cli_help_for_submodule_module_id(capsys) -> None:
    """验证 analyze submodule <module_id> -h 仍展示运行参数"""
    assert main(["help", "analyze", "submodule", "jcvi.pairwise"]) == 0
    output = capsys.readouterr().out

    assert "module_id" in output
    assert "--input-ports" in output
    assert "--output-dir" in output


def test_cli_help_paginated_by_page(capsys) -> None:
    """验证 --page 分页只展示部分参数"""
    assert main(["help", "analyze", "workflow", "synteny", "--page", "1"]) == 0
    page1 = capsys.readouterr().out

    assert main(["help", "analyze", "workflow", "synteny", "--page", "2"]) == 0
    page2 = capsys.readouterr().out

    # 两页都应包含页码提示
    assert "页码 1/" in page1
    assert "页码 2/" in page2
    # 第二页不应与第一页完全相同（只要参数多于 10 个）
    assert page1 != page2


def test_cli_help_section_index(capsys) -> None:
    """验证 --section 不带值时显示参数类型索引"""
    assert main(["help", "analyze", "workflow", "synteny", "--section"]) == 0
    output = capsys.readouterr().out

    assert "参数类型索引" in output
    assert "MCscan 算法参数" in output
    assert "图件样式与自动优化" in output


def test_cli_help_section_by_number(capsys) -> None:
    """验证 --section 支持用编号选择参数组"""
    assert main(["help", "analyze", "workflow", "synteny", "--section", "4"]) == 0
    output = capsys.readouterr().out

    assert "图件样式与自动优化" in output
    assert "--glyphstyle" in output
    assert "MCscan 算法参数" not in output


def test_cli_help_paginated_by_section(capsys) -> None:
    """验证 --section 按参数组过滤帮助"""
    assert main(["help", "analyze", "workflow", "synteny", "--section", "figure"]) == 0
    output = capsys.readouterr().out

    assert "图件样式与自动优化" in output
    assert "--glyphstyle" in output
    # 其它组标题不应出现
    assert "MCscan 算法参数" not in output
    assert "工具链与配置" not in output
    assert "运行时与输出" not in output


def test_cli_help_paginated_invalid_section(capsys) -> None:
    """验证 --section 匹配不到时给出可用参数组列表"""
    assert main(["help", "analyze", "workflow", "synteny", "--section", "notexist"]) == 0
    output = capsys.readouterr().out

    assert "未找到参数组" in output
    assert "图件样式与自动优化" in output


def test_cli_help_for_analyze_run(capsys) -> None:
    """验证 analyze run 的 help 包含 request_json 与 --json 参数"""
    assert main(["help", "analyze", "run"]) == 0
    output = capsys.readouterr().out

    assert "request_json" in output
    assert "--json" in output


def test_analyze_template_synteny(capsys) -> None:
    """验证 analyze template synteny 输出符合 V3 协议"""
    assert main(["analyze", "template", "workflow", "synteny"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["kind"] == "workflow_request"
    assert payload["workflow_id"] == "synteny"
    assert payload["schema_version"] == 3


def test_analyze_schema(capsys) -> None:
    """验证 analyze schema 输出包含 workflow_request 与 submodule_request 定义"""
    assert main(["analyze", "schema"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    workflow_schema = payload["$defs"]["workflow_request"]
    assert workflow_schema["properties"]["kind"]["const"] == "workflow_request"
    assert workflow_schema["properties"]["workflow_id"]["enum"] == ["synteny"]
    assert payload["$defs"]["submodule_request"]["properties"]["kind"]["const"] == "submodule_request"


def test_check_json_short_option() -> None:
    """验证 check -j 短选项返回预期退出码"""
    assert main(["check", "-j"]) in {0, 5}


def test_config_init(tmp_path: Path) -> None:
    """验证 config init 创建 genomelens 与 jcvi 配置文件"""
    assert main(["config", "init", "--workspace", str(tmp_path / "work"), "--force"]) == 0
    assert (tmp_path / "work" / "genomelens.config.json").is_file()
    assert (tmp_path / "work" / "jcvi.config.json").is_file()


def test_analyze_workflow_force_before_positionals_reuses_output_dir(tmp_path: Path, monkeypatch) -> None:
    """验证 --force 在位置参数之前时仍可复用输出目录"""
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
    """验证分析工作流可复用已有执行路径（execution path）"""
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
    """验证 --log-level 显式值会覆盖 --verbose 的默认 log_level"""
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
    """验证配置文件中的 log_level 会被正确传递到运行时"""
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
    """验证默认 CLI 模式使用进度报告器（progress reporter）并输出百分比"""
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
    """验证 --json 模式抑制进度报告器，仅输出 JSON 结果"""
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
    """验证 analyze run 正确分发自定义请求 JSON"""
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
    """验证 analyze run 正确解析请求 JSON 中的物种列表"""
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
    """验证 synteny 成对工作流（pairwise synteny）端到端执行，使用 source engine"""
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
    # 渲染回合（graphics_synteny）只承担出图，pairwise 计算已拆分到独立子目录
    assert [command["name"] for command in engine_summary["commands"]] == [
        "jcvi.graphics.dotplot",
        "jcvi.graphics.synteny",
    ]
    # pairwise 计算回合在 jcvi/pairwise/ 子目录留下完整的同源比对与共线性命令链
    pairwise_summary = json.loads(
        (Path(extensions["engine_summary_path"]).parent / "pairwise" / "engine_run_summary.json").read_text(
            encoding="utf-8"
        )
    )
    assert [command["name"] for command in pairwise_summary["commands"]] == [
        "makeblastdb.exe",
        "blastn.exe",
        "jcvi.compara.synteny.scan",
        "jcvi.compara.synteny.simple",
        "jcvi.compara.synteny.mcscan",
        "jcvi.formats.bed.merge",
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
    assert "task_finished task_id=engine step=jcvi.graphics.synteny status=SUCCEEDED" in engine_log
    # 同源比对命令在拆分出的 pairwise 计算回合日志中
    pairwise_engine_log = (outdir / "intermediate" / "jcvi" / "pairwise" / "run.log").read_text(encoding="utf-8")
    assert "task_finished task_id=engine step=makeblastdb.exe status=SUCCEEDED" in pairwise_engine_log


def test_analyze_workflow_synteny_multi_species(tmp_path: Path) -> None:
    """验证 synteny 多物种（multi-species）端到端执行，包含全局核型总图与局部共线性图"""
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
    # 全局多物种核型总图：所有 pairwise 成功后应聚合出至少一张总图
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
    """验证 synteny 成对工作流可自动从目录发现 bed/cds 文件"""
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
    """验证通过 --jcvi-config 显式指定引擎配置后，参数被正确注入工作流"""
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
    """验证 genomelens.config.json 与 jcvi.config.json 的默认值被正确加载"""
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
    """验证 reference_vs_targets 模式下的局部共线性（local synteny）参数被正确传递"""
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
    assert summary["extensions"]["global_figures"]
    assert all(Path(path).is_file() for path in summary["extensions"]["global_figures"])
    assert summary["final_figures"]
    assert any(path in summary["final_figures"] for path in summary["extensions"]["multi_species_local_figures"])
    assert any(path in summary["final_figures"] for path in summary["extensions"]["global_figures"])


def test_analyze_workflow_synteny_reference_vs_targets_reference_swap(tmp_path: Path) -> None:
    """验证 reference_vs_targets 模式支持 reference 与 target 互换"""
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
    # 目标基因（target genes）会将 synteny 路由到 local_synteny pairwise 步骤
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
    """验证 reference_vs_targets 三物种模式正确生成局部共线性与全局核型图"""
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
    global_figures = summary["extensions"]["global_figures"]
    assert local_figures, "expected a multi-species local synteny figure"
    assert global_figures, "expected a global core synteny figure"
    assert all(Path(path).is_file() for path in local_figures)
    assert all(Path(path).is_file() for path in global_figures)
    assert any(Path(path).name.startswith("multi_species_local.") for path in local_figures)
    assert any(Path(path).name.startswith("global.") for path in global_figures)
    assert any(path in summary["final_figures"] for path in local_figures)
    assert any(path in summary["final_figures"] for path in global_figures)
    global_manifest = json.loads(
        (outdir / "intermediate" / "global_karyotype" / "global_manifest.json").read_text(encoding="utf-8")
    )
    assert global_manifest["workflow"] == "graphics_karyotype_global"
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
    assert "step=build_global_karyotype status=SUCCEEDED" in run_log
    assert "step=build_multi_local_synteny status=SUCCEEDED" in run_log
    assert "step=run_pairwise_job status=STARTED" in run_log


def test_analyze_mcscan_config_defaults_exposed_in_init(tmp_path: Path) -> None:
    """验证 config init 暴露的 mcscan 默认值与预期一致"""
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
    """验证 synteny 成对工作流端到端执行（无 mock）"""
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


def test_analyze_submodule_pairwise_end_to_end(tmp_path: Path) -> None:
    """验证 jcvi.pairwise 子模块端到端执行"""
    root = Path(__file__).resolve().parents[3]
    sample = root / "references" / "samples" / "shell" / "bed_cds_minimal"
    input_dir = tmp_path / "input-submodule"
    _copy_species_files(input_dir, sample, ["query.bed", "query.cds", "subject.bed", "subject.cds"])
    outdir = tmp_path / "out-submodule"

    code = main(
        [
            "analyze",
            "submodule",
            "jcvi.pairwise",
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
    assert request_snapshot["module_id"] == "jcvi.pairwise"
    assert request_snapshot["inputs"]["species_pair"] == str(input_dir)


def test_analyze_submodule_graphics_dotplot_reuses_pairwise_artifacts(tmp_path: Path) -> None:
    """验证 graphics_dotplot 子模块可复用 jcvi.pairwise 生成的锚点文件（anchors）"""
    root = Path(__file__).resolve().parents[3]
    sample = root / "references" / "samples" / "shell" / "bed_cds_minimal"
    input_dir = tmp_path / "input-submodule-reuse"
    _copy_species_files(input_dir, sample, ["query.bed", "query.cds", "subject.bed", "subject.cds"])

    pairwise_out = tmp_path / "out-submodule-pairwise"
    code = main(
        [
            "analyze",
            "submodule",
            "jcvi.pairwise",
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
    """验证 graphics_histogram 子模块端到端执行"""
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
