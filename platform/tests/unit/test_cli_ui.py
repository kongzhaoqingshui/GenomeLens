import argparse
import io
import threading
import time

from genomelens._version import __version__
from genomelens.analysis.requests.models import WorkflowOutput, WorkflowRequest, WorkflowSpeciesInput
from genomelens.app.events.signal_bus import SignalBus
from genomelens.cli.main import main
from genomelens.cli.ui import (
    PALETTE,
    CliProgressReporter,
    StyledArgumentParser,
    prompt_text,
    render_command_error,
    render_workbench_banner,
)


def _request(species_names: list[str]) -> WorkflowRequest:
    return WorkflowRequest(
        workflow_id="synteny",
        species=[WorkflowSpeciesInput(name=name, input_mode="bed_cds") for name in species_names],
        output=WorkflowOutput(directory="out"),
    )


def test_workbench_banner_plain_text() -> None:
    banner = render_workbench_banner(color=False)
    assert "GenomeLens" in banner
    assert f"Version {__version__}" in banner
    assert "常用命令" in banner
    assert "analyze workflow" in banner
    assert "analyze run" in banner
    assert "analyze template" in banner
    assert "可用分析方法" in banner
    assert "mcscan" in banner
    assert "\033[" not in banner


def test_prompt_and_error_plain_text() -> None:
    assert prompt_text(color=False) == "GenomeLens > "
    assert render_command_error(7, color=False) == "命令退出，退出码 7"


def test_styled_argument_parser_localizes_help() -> None:
    parser = StyledArgumentParser(prog="genomelens", description="中文说明")
    parser.add_argument("--flag", action="store_true", help="测试开关")
    subparsers = parser.add_subparsers(dest="command", title="命令")
    subparsers.add_parser("check", help="检查环境")

    help_text = parser.format_help()

    assert "用法:" in help_text
    assert "选项:" in help_text
    assert "命令:" in help_text
    assert "中文说明" in help_text
    assert "显示帮助信息并退出" in help_text


def test_styled_argument_parser_colors_argument_and_description(monkeypatch) -> None:
    monkeypatch.setenv("GENOMELENS_FORCE_COLOR", "1")
    parser = StyledArgumentParser(prog="genomelens", description="中文说明")
    parser.add_argument("--flag", action="store_true", help="测试开关")

    help_text = parser.format_help()

    assert "\033[38;2;125;211;217m--flag\033[0m" in help_text
    assert "\033[38;2;156;163;175m测试开关\033[0m" in help_text


def test_styled_argument_parser_colors_wrapped_positional_argument(monkeypatch) -> None:
    monkeypatch.setenv("GENOMELENS_FORCE_COLOR", "1")
    parser = StyledArgumentParser(
        prog="genomelens",
        formatter_class=lambda prog: argparse.HelpFormatter(prog, width=42),
    )
    parser.add_argument("jcvi_config_positional", nargs="?", help="optional JCVI config path")

    help_text = parser.format_help()

    assert "\033[38;2;125;211;217mjcvi_config_positional\033[0m" in help_text
    assert "\033[38;2;156;163;175moptional JCVI config\033[0m" in help_text
    assert "\033[38;2;156;163;175mpath\033[0m" in help_text


def test_workbench_exits_cleanly_on_keyboard_interrupt(monkeypatch) -> None:
    def raise_keyboard_interrupt(_prompt: str) -> str:
        raise KeyboardInterrupt

    monkeypatch.setattr("builtins.input", raise_keyboard_interrupt)

    assert main([]) == 0


def test_cli_progress_reporter_ignores_inner_success_until_all_pairs_finish() -> None:
    request = _request(["query", "subject", "third"])
    stream = io.StringIO()
    signal_bus = SignalBus()
    reporter = CliProgressReporter(request, color=False, stream=stream)
    reporter.attach(signal_bus)

    signal_bus.emit("state", state="RUNNING_ENGINE")
    signal_bus.emit("pair_started", index=1, query="query", subject="subject")
    signal_bus.emit("state", state="SUCCEEDED")
    signal_bus.emit("pair_finished", index=1, status="SUCCEEDED")
    signal_bus.emit("pair_started", index=2, query="query", subject="third")
    signal_bus.emit("state", state="FINALIZING")
    signal_bus.emit("pair_finished", index=3, status="SUCCEEDED")
    signal_bus.emit("state", state="SUCCEEDED")

    output = stream.getvalue()

    assert output.startswith("\n")
    assert "100%" in output
    assert "33%" not in output


def test_cli_progress_reporter_aligns_primary_field_in_noninteractive_mode() -> None:
    request = _request(["query", "subject"])
    stream = io.StringIO()
    signal_bus = SignalBus()
    reporter = CliProgressReporter(request, color=False, stream=stream)
    reporter.attach(signal_bus)

    signal_bus.emit("state", state="VALIDATING_INPUTS")
    signal_bus.emit("state", state="CHECKING_TOOLCHAIN")

    lines = [line for line in stream.getvalue().splitlines() if line]

    assert len(lines) >= 2
    assert lines[0].index("━") == lines[1].index("━")


def test_cli_progress_reporter_uses_gray_detail_text_when_colored() -> None:
    request = _request(["query", "subject"])
    stream = io.StringIO()
    signal_bus = SignalBus()
    reporter = CliProgressReporter(request, color=True, stream=stream)
    reporter.attach(signal_bus)

    signal_bus.emit("pair_started", index=1, query="query", subject="subject")

    output = stream.getvalue()

    assert f"{PALETTE.gray}query vs subject{PALETTE.reset}" in output


class _InteractiveBuffer(io.StringIO):
    def isatty(self) -> bool:
        return True


class _FakeClock:
    def __init__(self) -> None:
        self._value = 0.0
        self._lock = threading.Lock()

    def __call__(self) -> float:
        with self._lock:
            current = self._value
            self._value += 1.0
            return current


def test_cli_progress_reporter_updates_elapsed_without_new_state_events() -> None:
    request = _request(["query", "subject"])
    stream = _InteractiveBuffer()
    signal_bus = SignalBus()
    reporter = CliProgressReporter(
        request,
        color=False,
        stream=stream,
        tick_interval=0.05,
        clock=_FakeClock(),
    )
    reporter.attach(signal_bus)

    signal_bus.emit("state", state="RUNNING_ENGINE")
    time.sleep(0.12)
    reporter.finish()

    output = stream.getvalue()
    assert "0:00:01" in output
    assert "0:00:02" in output


def test_cli_progress_reporter_uses_runtime_pair_total_when_available() -> None:
    request = _request(["query", "subject", "third"])
    stream = io.StringIO()
    signal_bus = SignalBus()
    reporter = CliProgressReporter(request, color=False, stream=stream)
    reporter.attach(signal_bus)

    signal_bus.emit("pair_started", index=1, total=5, query="query", subject="subject")

    assert "0/5" in stream.getvalue()
