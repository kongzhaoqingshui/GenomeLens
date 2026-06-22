"""CLI 展示层：集中管理颜色、字段和交互提示"""

# region import
from __future__ import annotations

import argparse
import os
import re
import sys
import threading
import time
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, TextIO, cast

from genomelens._version import __version__
from genomelens.analysis.methods.registry import list_methods
from genomelens.analysis.requests.models import AnalysisRequest
from genomelens.app.events.signal_bus import Event, SignalBus
from genomelens.core.summary_models import CheckReport, PairwiseJobSummary, RunSummary

# endregion


@dataclass(frozen=True)
class CliPalette:
    """终端字段配色，只保存 ANSI 控制序列"""

    reset: str = "\033[0m"
    bold: str = "\033[1m"
    dim: str = "\033[2m"
    blue: str = "\033[38;2;122;162;247m"
    cyan: str = "\033[38;2;125;211;217m"
    green: str = "\033[38;2;166;218;149m"
    yellow: str = "\033[38;2;238;212;139m"
    magenta: str = "\033[38;2;203;166;247m"
    red: str = "\033[38;2;238;135;135m"
    gray: str = "\033[38;2;156;163;175m"


PALETTE = CliPalette()
STATE_LABELS = {
    "PENDING": "Waiting",
    "VALIDATING_INPUTS": "Validating",
    "PREPROCESSING_ANNOTATIONS": "Preprocess",
    "PREPARING_WORKSPACE": "Preparing",
    "CHECKING_TOOLCHAIN": "Toolchain",
    "WRITING_MANIFEST": "Manifest",
    "RUNNING_ENGINE": "Running",
    "PARSING_ENGINE_SUMMARY": "Parsing",
    "FINALIZING": "Finalizing",
    "SUCCEEDED": "Completed",
    "FAILED": "Failed",
    "CANCELLED": "Cancelled",
}
STATE_PROGRESS = {
    "PENDING": 0.0,
    "VALIDATING_INPUTS": 0.08,
    "PREPROCESSING_ANNOTATIONS": 0.18,
    "PREPARING_WORKSPACE": 0.28,
    "CHECKING_TOOLCHAIN": 0.42,
    "WRITING_MANIFEST": 0.56,
    "RUNNING_ENGINE": 0.78,
    "PARSING_ENGINE_SUMMARY": 0.9,
    "FINALIZING": 0.96,
    "SUCCEEDED": 1.0,
    "FAILED": 1.0,
    "CANCELLED": 1.0,
}


# region 内部格式操作函数
def _supports_color(stream: TextIO | None = None) -> bool:
    """判断当前输出流是否适合显示 ANSI 颜色"""

    # 用户可以通过环境变量强制关闭/开启颜色
    if os.environ.get("NO_COLOR"):
        return False

    if os.environ.get("GENOMELENS_FORCE_COLOR"):
        return True

    # 默认只对真正的终端（TTY）启用颜色
    target = stream or sys.stdout

    return bool(getattr(target, "isatty", lambda: False)())


def _paint(text: str, color: str, *, enabled: bool) -> str:
    """按需为文本包裹 ANSI 颜色"""

    if not enabled:
        return text

    return f"{color}{text}{PALETTE.reset}"


def _visible_width(text: str) -> int:
    """计算去除 ANSI 序列后的显示宽度，CJK 字符按 2 列计"""

    # 先剥掉 ANSI 转义序列，再按字符计算宽度
    plain = re.sub(r"\033\[[0-9;]*m", "", text)

    width = 0
    for char in plain:
        width += 2 if unicodedata.east_asian_width(char) in {"F", "W"} else 1

    return width


def _boxed(lines: list[str], *, enabled: bool, min_width: int = 0) -> list[str]:
    """把若干内容行包进圆角边框(抄的 Claude CLI 风格)"""

    # 边框内宽度 = max(显式最小宽度, 所有行的可见宽度)
    inner = max([min_width, *(_visible_width(line) for line in lines)]) if lines else min_width

    border_color = PALETTE.blue
    top = _paint("╭" + "─" * (inner + 2) + "╮", border_color, enabled=enabled)
    bottom = _paint("╰" + "─" * (inner + 2) + "╯", border_color, enabled=enabled)
    bar = _paint("│", border_color, enabled=enabled)

    body = []

    # 每行右侧补空格，让内容与边框等宽
    for line in lines:
        padding = " " * (inner - _visible_width(line))
        body.append(f"{bar} {line}{padding} {bar}")

    return [top, *body, bottom]


# endregion


# region 进度渲染
def _duration_text(seconds: float) -> str:
    """Render elapsed seconds as h:mm:ss."""

    total = max(0, int(seconds))
    minutes, seconds = divmod(total, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours}:{minutes:02d}:{seconds:02d}"


def _progress_bar(progress: float, *, enabled: bool, width: int = 24) -> str:
    """Render a compact single-line progress bar."""

    clamped = max(0.0, min(progress, 1.0))
    filled = min(width, max(0, int(round(clamped * width))))
    return _paint("=" * filled, PALETTE.magenta, enabled=enabled) + _paint(
        "-" * (width - filled),
        PALETTE.gray,
        enabled=enabled,
    )


def _pair_count(request: AnalysisRequest) -> int:
    """根据请求估算总 pairwise 数量"""

    species_count = len(request.input.species)
    if species_count < 2:
        return 1

    if request.method_config.get("target_gene_ids"):
        return max(1, species_count - 1)

    return max(1, species_count * (species_count - 1) // 2)


def _default_pair_label(request: AnalysisRequest) -> str:
    """为单 pair 或初始状态提供默认标签"""

    species = request.input.species
    if len(species) >= 2:
        return f"{species[0].name} vs {species[1].name}"
    if species:
        return species[0].name
    return ""


class _LegacyCliProgressReporter:
    """CLI 进度条/状态行渲染器"""

    def __init__(
        self,
        request: AnalysisRequest,
        *,
        color: bool | None = None,
        stream: TextIO | None = None,
    ) -> None:
        self._request = request
        self._stream = stream or sys.stdout
        self._enabled = _supports_color(self._stream) if color is None else color
        self._interactive = bool(getattr(self._stream, "isatty", lambda: False)())
        self._started_at = time.perf_counter()
        self._total_pairs = _pair_count(request)
        self._completed_pairs = 0
        self._active_pair_index = 1
        self._active_pair_label = _default_pair_label(request)
        self._state = "PENDING"
        self._last_line = ""
        self._last_width = 0

    def attach(self, signal_bus: SignalBus) -> None:
        """订阅 SignalBus 事件"""

        signal_bus.subscribe(self.handle)

    def handle(self, event: Event) -> None:
        """消费状态与 pair 事件并刷新输出"""

        if event.name == "state":
            state = str(event.payload.get("state") or "")
            if state:
                if self._total_pairs > 1 and state == "SUCCEEDED" and self._completed_pairs < self._total_pairs:
                    return
                self._state = state
                self._render()
            return

        if event.name == "pair_started":
            raw_index = event.payload.get("index")
            if raw_index is not None:
                self._active_pair_index = int(cast(int, raw_index))
            query = str(event.payload.get("query") or "")
            subject = str(event.payload.get("subject") or "")
            self._active_pair_label = f"{query} vs {subject}" if query and subject else self._active_pair_label
            self._render()
            return

        if event.name == "pair_finished":
            raw_index = event.payload.get("index")
            if raw_index is not None:
                self._active_pair_index = int(cast(int, raw_index))
            self._completed_pairs = max(self._completed_pairs, self._active_pair_index)
            status = str(event.payload.get("status") or "")
            if status == "FAILED":
                self._state = "FAILED"
            self._render()

    def finish(self) -> None:
        """结束渲染，确保交互式终端换行"""

        if self._interactive and self._last_line:
            self._stream.write("\n")
            self._stream.flush()
            self._last_line = ""
            self._last_width = 0

    def _overall_progress(self) -> float:
        if self._total_pairs <= 1:
            return STATE_PROGRESS.get(self._state, 0.0)

        if self._state in {"PENDING", "VALIDATING_INPUTS", "PREPARING_WORKSPACE"}:
            return min(0.12, STATE_PROGRESS.get(self._state, 0.0) * 0.4)

        if self._state in {"SUCCEEDED", "FAILED", "CANCELLED"} and self._completed_pairs >= self._total_pairs:
            return 1.0

        if self._completed_pairs >= self._total_pairs:
            return max(0.92, STATE_PROGRESS.get(self._state, 0.96))

        pair_phase = STATE_PROGRESS.get(self._state, 0.0)
        active_completed = max(self._completed_pairs, self._active_pair_index - 1)
        return min(0.9, 0.12 + ((active_completed + pair_phase) / self._total_pairs) * 0.78)

    def _line_text(self) -> str:
        progress = self._overall_progress()
        percent = f"{int(round(progress * 100)):>3}%"
        elapsed = _duration_text(time.perf_counter() - self._started_at)
        state_label = STATE_LABELS.get(self._state, self._state)
        pair_text = ""

        if self._total_pairs > 1:
            pair_text = f"{self._completed_pairs}/{self._total_pairs} {self._active_pair_label}".strip()
        elif self._active_pair_label:
            pair_text = self._active_pair_label

        line = f"{state_label:<10} {_progress_bar(progress, enabled=self._enabled)} {percent} {elapsed}"
        if pair_text:
            line = f"{line}  {pair_text}"
        return line

    def _render(self) -> None:
        line = self._line_text()
        if line == self._last_line:
            return

        if self._interactive:
            width = max(self._last_width, _visible_width(line))
            padded = line + " " * max(0, width - _visible_width(line))
            self._stream.write("\r" + padded)
            self._stream.flush()
            self._last_width = width
        else:
            self._stream.write(line + "\n")
            self._stream.flush()

        self._last_line = line


# endregion


# region 工作台与提示相关函数
@dataclass(frozen=True)
class ProgressTheme:
    """Visual theme for compact CLI progress lines"""

    label_color: str = PALETTE.blue
    meta_color: str = PALETTE.cyan
    detail_color: str = PALETTE.gray
    bar_color: str = PALETTE.blue
    bar_accent_color: str = PALETTE.cyan
    empty_color: str = PALETTE.gray
    bar_width: int = 24
    field_gap: int = 2


@dataclass(frozen=True)
class ProgressFrame:
    """Generic progress snapshot rendered by the CLI"""

    label: str
    progress: float
    summary: str = ""
    detail: str = ""


class ProgressAdapter(Protocol):
    """Adapter that translates SignalBus events into reusable progress frames"""

    label_width: int

    def current_frame(self) -> ProgressFrame:
        """返回当前 progress frame(进度帧)"""
        ...

    def apply(self, event: Event) -> ProgressFrame | None:
        """从事件更新内部状态并返回下一帧"""
        ...


def _pad_visible(text: str, width: int) -> str:
    """Pad text by its visible width so progress columns stay aligned"""

    return text + " " * max(0, width - _visible_width(text))


def _progress_duration_text(seconds: float) -> str:
    """Render elapsed seconds as h:mm:ss"""

    total = max(0, int(seconds))
    minutes, seconds = divmod(total, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours}:{minutes:02d}:{seconds:02d}"


def _render_progress_bar(progress: float, *, theme: ProgressTheme, enabled: bool) -> str:
    """Render a two-tone progress bar using the existing GenomeLens palette"""

    clamped = max(0.0, min(progress, 1.0))
    filled = min(theme.bar_width, max(0, int(round(clamped * theme.bar_width))))
    empty = theme.bar_width - filled

    if filled <= 0:
        filled_text = ""
    elif filled == 1:
        filled_text = _paint("━", theme.bar_accent_color, enabled=enabled)
    else:
        filled_text = _paint("━" * (filled - 1), theme.bar_color, enabled=enabled) + _paint(
            "━",
            theme.bar_accent_color,
            enabled=enabled,
        )

    return filled_text + _paint("─" * empty, theme.empty_color, enabled=enabled)


class SignalBusProgressReporter:
    """Reusable SignalBus-backed progress renderer for CLI workflows"""

    def __init__(
        self,
        adapter: ProgressAdapter,
        *,
        color: bool | None = None,
        stream: TextIO | None = None,
        theme: ProgressTheme | None = None,
        tick_interval: float = 1.0,
        clock: Callable[[], float] | None = None,
    ) -> None:
        self._adapter = adapter
        self._stream = stream or sys.stderr
        self._theme = theme or ProgressTheme()
        self._enabled = _supports_color(self._stream) if color is None else color
        self._interactive = bool(getattr(self._stream, "isatty", lambda: False)())
        self._clock = clock or time.perf_counter
        self._tick_interval = max(0.05, tick_interval)
        self._started_at = self._clock()
        self._render_started = False
        self._last_line = ""
        self._last_width = 0
        self._render_lock = threading.Lock()
        self._ticker_stop = threading.Event()
        self._ticker_thread: threading.Thread | None = None

    def attach(self, signal_bus: SignalBus) -> None:
        """Subscribe to progress-related events on the shared SignalBus"""

        signal_bus.subscribe(self.handle)

    def handle(self, event: Event) -> None:
        """Render the next frame when the adapter yields one"""

        frame = self._adapter.apply(event)
        if frame is not None:
            self._render(frame)

    def finish(self) -> None:
        """Close the live progress line cleanly on interactive terminals"""

        self._stop_ticker()
        with self._render_lock:
            if self._interactive and self._last_line:
                self._stream.write("\n")
                self._stream.flush()
                self._last_line = ""
                self._last_width = 0

    def _line_text(self, frame: ProgressFrame) -> str:
        label = _paint(
            _pad_visible(frame.label, self._adapter.label_width),
            self._theme.label_color,
            enabled=self._enabled,
        )
        bar = _render_progress_bar(frame.progress, theme=self._theme, enabled=self._enabled)
        percent = _paint(
            f"{int(round(frame.progress * 100)):>3}%",
            self._theme.meta_color,
            enabled=self._enabled,
        )
        elapsed = _paint(
            _progress_duration_text(self._clock() - self._started_at),
            self._theme.label_color,
            enabled=self._enabled,
        )
        segments = [label, " " * self._theme.field_gap, bar, " " * self._theme.field_gap, percent, " ", elapsed]

        if frame.summary:
            segments.extend(
                [
                    " " * self._theme.field_gap,
                    _paint(frame.summary, self._theme.meta_color, enabled=self._enabled),
                ]
            )
        if frame.detail:
            segments.extend([" ", _paint(frame.detail, self._theme.detail_color, enabled=self._enabled)])

        return "".join(segments)

    def _render(self, frame: ProgressFrame) -> None:
        with self._render_lock:
            line = self._line_text(frame)
            if line == self._last_line:
                return

            if not self._render_started:
                self._stream.write("\n")
                self._render_started = True

            if self._interactive:
                width = max(self._last_width, _visible_width(line))
                padded = line + " " * max(0, width - _visible_width(line))
                self._stream.write("\r" + padded)
                self._stream.flush()
                self._last_width = width
            else:
                self._stream.write(line + "\n")
                self._stream.flush()

            self._last_line = line
            if self._interactive and self._ticker_thread is None:
                self._start_ticker()

    def _start_ticker(self) -> None:
        if self._ticker_thread is not None:
            return
        self._ticker_stop.clear()
        self._ticker_thread = threading.Thread(target=self._ticker_loop, name="genomelens-progress-ticker", daemon=True)
        self._ticker_thread.start()

    def _stop_ticker(self) -> None:
        self._ticker_stop.set()
        if self._ticker_thread is not None and self._ticker_thread.is_alive():
            self._ticker_thread.join(timeout=self._tick_interval * 2)
        self._ticker_thread = None

    def _ticker_loop(self) -> None:
        while not self._ticker_stop.wait(self._tick_interval):
            self._render(self._adapter.current_frame())


PROGRESS_STATE_LABELS = {
    "PENDING": "Queued",
    "VALIDATING_INPUTS": "Validating",
    "PREPROCESSING_ANNOTATIONS": "Preprocessing",
    "PREPARING_WORKSPACE": "Preparing",
    "CHECKING_TOOLCHAIN": "Toolchain",
    "WRITING_MANIFEST": "Manifest",
    "RUNNING_ENGINE": "Running",
    "PARSING_ENGINE_SUMMARY": "Parsing",
    "FINALIZING": "Finalizing",
    "SUCCEEDED": "Completed",
    "FAILED": "Failed",
    "CANCELLED": "Cancelled",
}


class McscanProgressAdapter:
    """Translate current MCscan workflow events into reusable progress frames"""

    def __init__(self, request: AnalysisRequest) -> None:
        self._request = request
        self._state = "PENDING"
        self._total_pairs = _pair_count(request)
        self._completed_pairs = 0
        self._active_pair_index = 1
        self._active_pair_label = _default_pair_label(request)
        self.label_width = max(_visible_width(label) for label in PROGRESS_STATE_LABELS.values())

    def current_frame(self) -> ProgressFrame:
        summary = f"{self._completed_pairs}/{self._total_pairs}" if self._total_pairs > 1 else ""
        detail = self._active_pair_label if self._active_pair_label else ""
        return ProgressFrame(
            label=PROGRESS_STATE_LABELS.get(self._state, self._state),
            progress=self._overall_progress(),
            summary=summary,
            detail=detail,
        )

    def apply(self, event: Event) -> ProgressFrame | None:
        if event.name == "state":
            state = str(event.payload.get("state") or "")
            if not state:
                return None
            if self._total_pairs > 1 and state == "SUCCEEDED" and self._completed_pairs < self._total_pairs:
                return None
            self._state = state
            return self.current_frame()

        if event.name == "pair_started":
            raw_total = event.payload.get("total")
            if raw_total is not None:
                self._total_pairs = max(1, int(cast(int, raw_total)))
            raw_index = event.payload.get("index")
            if raw_index is not None:
                self._active_pair_index = int(cast(int, raw_index))
            query = str(event.payload.get("query") or "")
            subject = str(event.payload.get("subject") or "")
            if query and subject:
                self._active_pair_label = f"{query} vs {subject}"
            return self.current_frame()

        if event.name == "pair_finished":
            raw_total = event.payload.get("total")
            if raw_total is not None:
                self._total_pairs = max(1, int(cast(int, raw_total)))
            raw_index = event.payload.get("index")
            if raw_index is not None:
                self._active_pair_index = int(cast(int, raw_index))
            self._completed_pairs = max(self._completed_pairs, self._active_pair_index)
            status = str(event.payload.get("status") or "")
            if status == "FAILED":
                self._state = "FAILED"
            return self.current_frame()

        return None

    def _overall_progress(self) -> float:
        if self._total_pairs <= 1:
            return STATE_PROGRESS.get(self._state, 0.0)

        if self._state in {"PENDING", "VALIDATING_INPUTS", "PREPARING_WORKSPACE"}:
            return min(0.12, STATE_PROGRESS.get(self._state, 0.0) * 0.4)

        if self._state in {"SUCCEEDED", "FAILED", "CANCELLED"} and self._completed_pairs >= self._total_pairs:
            return 1.0

        if self._completed_pairs >= self._total_pairs:
            return max(0.92, STATE_PROGRESS.get(self._state, 0.96))

        pair_phase = STATE_PROGRESS.get(self._state, 0.0)
        active_completed = max(self._completed_pairs, self._active_pair_index - 1)
        return min(0.9, 0.12 + ((active_completed + pair_phase) / self._total_pairs) * 0.78)


class CliProgressReporter(SignalBusProgressReporter):
    """Backward-compatible MCscan progress reporter built on the reusable renderer"""

    def __init__(
        self,
        request: AnalysisRequest,
        *,
        color: bool | None = None,
        stream: TextIO | None = None,
        theme: ProgressTheme | None = None,
        tick_interval: float = 1.0,
        clock: Callable[[], float] | None = None,
    ) -> None:
        super().__init__(
            McscanProgressAdapter(request),
            color=color,
            stream=stream or sys.stdout,
            theme=theme,
            tick_interval=tick_interval,
            clock=clock,
        )


def render_workbench_banner(*, color: bool | None = None) -> str:
    """生成 workbench 入口字段，向 Claude CLI 风格靠拢"""

    enabled = _supports_color() if color is None else color

    title = _paint("✦ GenomeLens", PALETTE.bold + PALETTE.blue, enabled=enabled)
    subtitle = _paint("比较基因组学工作台", PALETTE.gray, enabled=enabled)
    status = _paint("● 就绪", PALETTE.green, enabled=enabled)
    version = _paint(f"Version {__version__}", PALETTE.gray, enabled=enabled)
    core = (
        f"{_paint('外壳', PALETTE.cyan, enabled=enabled)} "
        f"{_paint('→', PALETTE.gray, enabled=enabled)} "
        f"{_paint('jcvi-genomelens 引擎', PALETTE.blue, enabled=enabled)}"
    )

    # 从注册表读取可用分析方法，stable=False 的标记为预览
    # 方法列表直接读注册表，workbench 首页不会再维护一份手写清单。
    methods = [
        f"{_paint(spec.name, PALETTE.cyan, enabled=enabled)}"
        f"{_paint('  ' + spec.description, PALETTE.gray, enabled=enabled)}"
        + ("" if spec.stable else _paint("  (预览)", PALETTE.yellow, enabled=enabled))
        for spec in list_methods()
    ]

    header = [
        f"{title}  {subtitle}",
        f"{status}    {core}",
        version,
    ]
    method_lines = [_paint("可用分析方法", PALETTE.bold, enabled=enabled), *[f"  {line}" for line in methods]]

    # 把标题、状态、方法列表包进圆角边框
    boxed = _boxed([*header, "", *method_lines], enabled=enabled, min_width=52)

    # 工作台支持的常用命令示例
    commands = [
        ("analyze mcscan jcvi <in> <out>", "自动发现物种并运行共线性分析"),
        ("analyze run <request.json>", "运行外部 AnalysisRequest"),
        ("analyze template mcscan", "输出 JSON 请求示例"),
        ("check", "检查环境与工具链"),
        ("config init --workspace .work", "初始化配置文件"),
        ("help <cmd>", "查看指定命令参数"),
        ("clear", "清屏"),
        ("exit", "退出"),
    ]

    lines = ["", *[f"  {line}" for line in boxed], "", f"  {_paint('常用命令', PALETTE.bold, enabled=enabled)}"]

    for command, description in commands:
        # 命令列宽固定，保证中英文混排时依然能大致对齐。
        command_cell = f"{command:<36}"
        lines.append(
            f"    {_paint(command_cell, PALETTE.cyan, enabled=enabled)} "
            f"{_paint(description, PALETTE.gray, enabled=enabled)}"
        )

    lines.extend(["", f"  {_paint('提示', PALETTE.dim, enabled=enabled)} 输入 help 查看完整命令。", ""])

    return "\n".join(lines)


def clear_screen() -> None:
    """清屏：优先使用 ANSI 清屏序列，回退到打印空行"""

    if _supports_color():
        sys.stdout.write("\033[2J\033[H")
        sys.stdout.flush()
    else:
        print("\n" * 40)


def prompt_text(*, color: bool | None = None) -> str:
    """返回交互式 prompt(提示符)"""

    enabled = _supports_color() if color is None else color

    return _paint("GenomeLens", PALETTE.blue, enabled=enabled) + _paint(" > ", PALETTE.dim, enabled=enabled)


def render_command_error(code: int, *, color: bool | None = None) -> str:
    """生成 workbench 中子命令失败提示"""

    enabled = _supports_color() if color is None else color
    label = _paint("命令退出", PALETTE.red, enabled=enabled)

    return f"{label}，退出码 {code}"


# endregion


# region 帮助文本本地化与着色
def _localize_help(text: str) -> str:
    """把 argparse 默认英文 help 标题替换为中文"""

    replacements = {
        "usage:": "用法:",
        "options:": "选项:",
        "positional arguments:": "位置参数:",
    }

    for source, target in replacements.items():
        text = text.replace(source, target)

    return text


def _color_help(text: str, *, enabled: bool) -> str:
    """对 argparse help 文本按行着色：标题加粗、参数名青色、说明灰色"""

    if not enabled:
        return text

    lines: list[str] = []

    # 匹配 "  --flag  说明文字" 这类行
    argument_line = re.compile(r"^(\s{2,})(\S.*?)(\s{2,})(\S.*)$")

    # 匹配只有参数名、没有说明的行（说明被折行到下一行）
    argument_only_line = re.compile(r"^(\s{2,})([-\w{].*)$")

    # 匹配被折行的说明文字（缩进 ≥20 空格）
    wrapped_description_line = re.compile(r"^(\s{20,})(\S.*)$")

    expects_wrapped_description = False

    for line in text.splitlines():
        stripped = line.strip()

        # 标题行：用法 / 选项 / 位置参数 / 子命令名
        if stripped in {"用法:", "选项:", "位置参数:"} or stripped.endswith(":"):
            lines.append(_paint(line, PALETTE.bold + PALETTE.blue, enabled=True))
            expects_wrapped_description = False
            continue

        # 上一行是只有参数名的行，这行应该是被折行的说明
        wrapped = wrapped_description_line.match(line) if expects_wrapped_description else None

        if wrapped:
            prefix, description = wrapped.groups()
            lines.append(prefix + _paint(description, PALETTE.gray, enabled=True))
            expects_wrapped_description = True
            continue

        # 标准参数行：缩进 + 参数 + 间隙 + 说明
        match = argument_line.match(line)

        if match:
            prefix, argument, gap, description = match.groups()

            # {} 包裹的是子命令占位符，用蓝色；普通参数用青色
            # `{subcommands}` 这类占位符用蓝色，其余普通参数保持青色。
            argument_color = PALETTE.blue if argument.startswith("{") else PALETTE.cyan
            lines.append(
                prefix
                + _paint(argument, argument_color, enabled=True)
                + gap
                + _paint(description, PALETTE.gray, enabled=True)
            )
            expects_wrapped_description = False
            continue

        # 只有参数名、说明在下一行的参数行
        match = argument_only_line.match(line)

        if match and _looks_like_argument_name(stripped):
            prefix, argument = match.groups()
            argument_color = PALETTE.blue if argument.startswith("{") else PALETTE.cyan
            lines.append(prefix + _paint(argument, argument_color, enabled=True))
            expects_wrapped_description = True
        else:
            lines.append(line)
            expects_wrapped_description = False

    return "\n".join(lines) + ("\n" if text.endswith("\n") else "")


def _looks_like_argument_name(text: str) -> bool:
    return text.startswith(("-", "{")) or bool(re.fullmatch(r"[A-Za-z0-9_][\w-]*", text))


def print_parser_help(parser: argparse.ArgumentParser, file: TextIO | None = None) -> None:
    """使用统一路径输出 parser help(参数帮助)"""

    # argparse 没有公开 _print_message，但 format_help() 已被覆盖，这里复用内部方法保证一致
    parser._print_message(parser.format_help(), file or sys.stdout)  # noqa: SLF001 - argparse 只公开 print_help 包装


class StyledArgumentParser(argparse.ArgumentParser):
    """StyledArgumentParser(带样式参数解析器)：只处理 CLI 帮助信息 展示"""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """初始化参数解析器，并把默认 help 文案换成中文"""

        add_help = bool(kwargs.pop("add_help", True))
        super().__init__(*args, add_help=False, **kwargs)

        if add_help:
            self.add_argument(
                "-h",
                "--help",
                action="help",
                default=argparse.SUPPRESS,
                help="显示帮助信息并退出",
            )

    def format_help(self) -> str:
        """返回中文化、按需带颜色的 help 文本"""

        text = _localize_help(super().format_help())

        return _color_help(text, enabled=_supports_color())

    def print_help(self, file: TextIO | None = None) -> None:  # type: ignore[reportIncompatibleMethodOverride]
        """通过统一函数输出 help，供 `-h/--help` 与 `help xxx` 共用"""

        print_parser_help(self, file=file)


# endregion


# region 报告渲染函数
def render_check_report(payload: CheckReport | dict[str, object], *, color: bool | None = None) -> str:
    """生成整理后的 check(检查) 文本报告"""

    # 既支持直接喂 dataclass，也支持命令层传来的原始 JSON dict。
    report = payload if isinstance(payload, CheckReport) else CheckReport.from_json(payload)
    enabled = _supports_color() if color is None else color
    status = report.status
    status_color = PALETTE.green if status == "ok" else PALETTE.red

    lines = [
        "",
        f"{_paint('GenomeLens 环境检查', PALETTE.bold + PALETTE.blue, enabled=enabled)}",
        f"{_paint('状态', PALETTE.gray, enabled=enabled)} {_paint(status, status_color, enabled=enabled)}",
        "",
        _paint("工具链", PALETTE.bold + PALETTE.blue, enabled=enabled),
    ]

    labels = {
        "blastn": "BLAST+ blastn",
        "makeblastdb": "BLAST+ makeblastdb",
        "magick": "ImageMagick",
        "jcvi_engine": "JCVI 引擎",
    }

    for key, label in labels.items():
        item = getattr(report, key)

        item_status = item.status
        marker = "OK" if item_status == "ok" else "!!"
        marker_color = PALETTE.green if item_status == "ok" else PALETTE.red
        detail = item.path or item.message
        label_cell = f"{label:<20}"

        lines.append(
            f"  {_paint(marker, marker_color, enabled=enabled)} "
            f"{_paint(label_cell, PALETTE.cyan, enabled=enabled)} "
            f"{_paint(detail, PALETTE.gray, enabled=enabled)}"
        )

    # 可选：显示工具链安装尝试记录
    attempts = report.install_attempts

    if attempts:
        lines.extend(["", _paint("安装尝试", PALETTE.bold + PALETTE.blue, enabled=enabled)])

        for attempt in attempts:
            lines.append(
                f"  {attempt.get('name', '')}: {attempt.get('status', '')} "
                f"{attempt.get('path') or attempt.get('message') or ''}"
            )

    lines.append("")

    return "\n".join(lines)


def render_analysis_summary(summary: RunSummary | dict[str, object], *, color: bool | None = None) -> str:
    """生成整理后的 analyze(分析) 文本摘要"""

    # analyze 命令和 workbench 都复用这条摘要渲染路径。
    run_summary = summary if isinstance(summary, RunSummary) else RunSummary.from_json(summary)
    enabled = _supports_color() if color is None else color
    md = run_summary.method_data

    status = run_summary.status
    status_color = PALETTE.green if status == "SUCCEEDED" else PALETTE.red

    task = run_summary.task
    task_type = str(task.get("task_type") or "")
    workflow = str(run_summary.workflow or task.get("workflow") or "")

    species = run_summary.species
    species_names = [str(item.get("name")) for item in species if isinstance(item, dict)]
    # 多物种摘要优先信任 method_data 里的显式 species_count，缺失时再回退到 species 列表长度。
    species_count_value = md.get("species_count")
    species_count = int(species_count_value) if isinstance(species_count_value, int) else len(species_names)
    lines = [
        "",
        _paint("GenomeLens 分析完成", PALETTE.bold + PALETTE.blue, enabled=enabled),
        f"{_paint('状态', PALETTE.gray, enabled=enabled)} {_paint(status, status_color, enabled=enabled)}",
        f"{_paint('工作流', PALETTE.gray, enabled=enabled)} {_paint(workflow, PALETTE.cyan, enabled=enabled)}",
    ]

    if task_type:
        lines.append(
            f"{_paint('任务类型', PALETTE.gray, enabled=enabled)} {_paint(task_type, PALETTE.cyan, enabled=enabled)}"
        )

    if species_count >= 2:
        lines.append(
            f"{_paint('物种', PALETTE.gray, enabled=enabled)} "
            f"{_paint(str(species_count), PALETTE.cyan, enabled=enabled)} "
            f"{_paint('(' + ', '.join(species_names) + ')', PALETTE.gray, enabled=enabled)}"
        )

    # 多物种汇总时显示配对子任务成功数
    raw_pairwise_jobs = md.get("pairwise_jobs")
    pairwise_jobs = (
        [PairwiseJobSummary.from_json(item) for item in raw_pairwise_jobs if isinstance(item, dict)]
        if isinstance(raw_pairwise_jobs, list)
        else []
    )
    if pairwise_jobs:
        total = len(pairwise_jobs)
        succeeded = sum(1 for item in pairwise_jobs if item.status == "SUCCEEDED")

        lines.append(
            f"{_paint('配对子任务', PALETTE.gray, enabled=enabled)} "
            f"{_paint(f'{succeeded}/{total} 成功', PALETTE.cyan if succeeded == total else PALETTE.yellow, enabled=enabled)}"  # noqa: E501
        )

    # 多物种全局核型总图数量
    raw_global_figures = md.get("global_figures")
    global_figures = [str(item) for item in raw_global_figures] if isinstance(raw_global_figures, list) else []
    if global_figures:
        lines.append(
            f"{_paint('全局总图', PALETTE.gray, enabled=enabled)} "
            f"{_paint(str(len(global_figures)), PALETTE.cyan, enabled=enabled)} 张"
        )

    # 列出最终产出的图件文件名
    final_figures = run_summary.final_figures

    if final_figures:
        lines.extend(["", _paint("主要图件", PALETTE.bold + PALETTE.blue, enabled=enabled)])

        for figure in final_figures:
            name = Path(str(figure)).name
            lines.append(
                f"  {_paint('-', PALETTE.cyan, enabled=enabled)} {_paint(name, PALETTE.gray, enabled=enabled)}"
            )  # noqa: E501

    # 关键中间产物：anchors / simple / blocks / blast table
    artifact_keys = {
        "anchors_path": "anchors",
        "simple_path": "simple",
        "blocks_path": "blocks",
        "blast_table": "blast table",
    }
    artifacts: list[str] = []

    for key, label in artifact_keys.items():
        value = md.get(key)

        if value:
            artifacts.append(f"{label}: {Path(str(value)).name}")

    if artifacts:
        lines.extend(["", _paint("关键中间结果", PALETTE.bold + PALETTE.blue, enabled=enabled)])

        for artifact in artifacts:
            lines.append(
                f"  {_paint('-', PALETTE.cyan, enabled=enabled)} {_paint(artifact, PALETTE.gray, enabled=enabled)}"
            )

    # 从 logs 或 ui 块里找运行摘要路径
    run_summary_path = ""

    logs = run_summary.logs

    if isinstance(logs, dict):
        # 新摘要优先从 logs 里拿回写路径，兼容旧结构时再回退到 ui 块。
        run_summary_path = str(logs.get("run_summary") or "")

    if not run_summary_path:
        ui = run_summary.ui
        run_summary_path = ui.summary_path

    if run_summary_path:
        lines.extend(
            [
                "",
                f"{_paint('运行摘要', PALETTE.gray, enabled=enabled)} "
                f"{_paint(run_summary_path, PALETTE.gray, enabled=enabled)}",
            ]
        )  # noqa: E501

    run_log_path = ""
    if isinstance(logs, dict):
        run_log_path = str(logs.get("run_log") or "")

    if run_log_path:
        lines.append(
            f"{_paint('运行日志', PALETTE.gray, enabled=enabled)} {_paint(run_log_path, PALETTE.gray, enabled=enabled)}"
        )

    lines.append("")

    return "\n".join(lines)


# endregion
