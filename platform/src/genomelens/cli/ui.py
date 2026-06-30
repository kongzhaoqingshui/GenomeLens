"""CLI 展示层：集中管理颜色、字段和交互提示"""

# region import
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import threading
import time
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol, TextIO, cast

from genomelens._version import __version__
from genomelens.analysis.requests.models import WorkflowRequest
from genomelens.analysis.workflows.registry import list_workflow_plugins
from genomelens.analysis.workflows.submodules import SubModuleSpec, get_submodule_registry
from genomelens.app.events.signal_bus import Event, SignalBus
from genomelens.contracts.checks import CheckReport
from genomelens.contracts.summaries import RunSummary

# endregion


@dataclass(frozen=True)
class CliPalette:
    """终端字段配色，只保存 ANSI 控制序列"""

    # fmt: off
    reset: str = "\033[0m"  # 重置 ANSI 样式
    bold: str = "\033[1m"   # 粗体
    dim: str = "\033[2m"    # 暗淡
    blue: str = "\033[38;2;122;162;247m"     # 蓝色
    cyan: str = "\033[38;2;125;211;217m"     # 青色
    green: str = "\033[38;2;166;218;149m"    # 绿色
    yellow: str = "\033[38;2;238;212;139m"   # 黄色
    magenta: str = "\033[38;2;203;166;247m"  # 洋红
    red: str = "\033[38;2;238;135;135m"      # 红色
    gray: str = "\033[38;2;156;163;175m"     # 灰色
    # fmt: on


PALETTE = CliPalette()
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
    """将秒数渲染为 h:mm:ss 格式"""

    total = max(0, int(seconds))
    minutes, seconds = divmod(total, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours}:{minutes:02d}:{seconds:02d}"


def _progress_bar(progress: float, *, enabled: bool, width: int = 24) -> str:
    """渲染紧凑的单行进度条"""

    clamped = max(0.0, min(progress, 1.0))
    filled = min(width, max(0, int(round(clamped * width))))
    return _paint("=" * filled, PALETTE.magenta, enabled=enabled) + _paint(
        "-" * (width - filled),
        PALETTE.gray,
        enabled=enabled,
    )


def _pair_count(request: WorkflowRequest) -> int:
    """根据请求估算总 pairwise 数量"""

    species_count = len(request.species)
    if species_count < 2:
        return 1

    if request.target_gene_ids:
        return max(1, species_count - 1)

    return max(1, species_count * (species_count - 1) // 2)


def _default_pair_label(request: WorkflowRequest) -> str:
    """为单 pair 或初始状态提供默认标签"""

    species = request.species
    if len(species) >= 2:
        return f"{species[0].name} vs {species[1].name}"
    if species:
        return species[0].name
    return ""


# region 统一 CLI 输出层
class ConsoleWriter:
    """统一 CLI 输出层：明确 stdout/stderr 边界，支持 JSON/文本模式切换"""

    def __init__(self, *, color: bool | None = None, json_mode: bool = False) -> None:
        self._color = _supports_color() if color is None else color
        self._json_mode = json_mode

    def print_json(self, data: dict[str, object] | list[object]) -> None:
        """机器可读输出统一走 stdout"""

        print(json.dumps(data, ensure_ascii=False, indent=2))

    def print_text(self, text: str, *, file: TextIO | None = None) -> None:
        """人读文本默认走 stderr；json_mode 下走 stdout 方便与 JSON 输出统一捕获"""

        target = file or (sys.stdout if self._json_mode else sys.stderr)
        print(text, file=target)

    def print_error(self, text: str) -> None:
        """错误信息始终走 stderr"""

        print(text, file=sys.stderr)


# endregion


# region 工作台与提示相关函数
@dataclass(frozen=True)
class ProgressTheme:
    """紧凑 CLI 进度行的视觉主题 (Visual theme for compact CLI progress lines)"""

    # fmt: off
    label_color: str = PALETTE.blue       # 标签颜色
    meta_color: str = PALETTE.cyan        # 元信息颜色
    detail_color: str = PALETTE.gray      # 细节颜色
    bar_color: str = PALETTE.blue         # 进度条填充色
    bar_accent_color: str = PALETTE.cyan  # 进度条高亮色
    empty_color: str = PALETTE.gray       # 进度条空白色
    bar_width: int = 24  # 进度条宽度
    field_gap: int = 2   # 字段间距
    # fmt: on


@dataclass(frozen=True)
class ProgressFrame:
    """CLI 渲染的通用进度快照 (Generic progress snapshot rendered by the CLI)"""

    # fmt: off
    label: str         # 当前状态标签
    progress: float    # 进度百分比（0.0-1.0）
    summary: str = ""  # 概要文本
    detail: str = ""   # 详细文本
    # fmt: on


class ProgressAdapter(Protocol):
    """将 SignalBus 事件转换为可复用进度帧的适配器
    (Adapter that translates SignalBus events into reusable progress frames)
    """

    label_width: int

    def current_frame(self) -> ProgressFrame:
        """返回当前 progress frame(进度帧)"""
        ...

    def apply(self, event: Event) -> ProgressFrame | None:
        """从事件更新内部状态并返回下一帧"""
        ...


def _pad_visible(text: str, width: int) -> str:
    """按可见宽度填充文本，使进度列保持对齐
    (Pad text by its visible width so progress columns stay aligned)
    """

    return text + " " * max(0, width - _visible_width(text))


def _progress_duration_text(seconds: float) -> str:
    """将秒数渲染为 h:mm:ss 格式 (Render elapsed seconds as h:mm:ss)"""

    total = max(0, int(seconds))
    minutes, seconds = divmod(total, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours}:{minutes:02d}:{seconds:02d}"


def _render_progress_bar(progress: float, *, theme: ProgressTheme, enabled: bool) -> str:
    """使用现有 GenomeLens 配色渲染双色进度条
    (Render a two-tone progress bar using the existing GenomeLens palette)
    """

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
    """基于 SignalBus 的可复用 CLI 工作流进度渲染器
    (Reusable SignalBus-backed progress renderer for CLI workflows)
    """

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
        """订阅共享 SignalBus 上的进度相关事件
        (Subscribe to progress-related events on the shared SignalBus)
        """

        signal_bus.subscribe(self.handle)

    def handle(self, event: Event) -> None:
        """当适配器产生下一帧时渲染它
        (Render the next frame when the adapter yields one)
        """

        frame = self._adapter.apply(event)
        if frame is not None:
            self._render(frame)

    def finish(self) -> None:
        """在交互式终端上干净地关闭实时进度行
        (Close the live progress line cleanly on interactive terminals)
        """

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
    """将当前 MCscan 工作流事件转换为可复用进度帧
    (Translate current MCscan workflow events into reusable progress frames)
    """

    def __init__(self, request: WorkflowRequest) -> None:
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

        # 解析/收尾/终止态意味着 pairwise 计算实质上已经结束；
        # 即使最后一个 pair_finished 事件尚未到达，也不应把进度拉回 80%+
        if self._state in {"PARSING_ENGINE_SUMMARY", "FINALIZING", "SUCCEEDED", "FAILED", "CANCELLED"}:
            if self._state in {"SUCCEEDED", "FAILED", "CANCELLED"}:
                return 1.0
            return max(0.92, STATE_PROGRESS.get(self._state, 0.96))

        pair_phase = STATE_PROGRESS.get(self._state, 0.0)
        active_completed = max(self._completed_pairs, self._active_pair_index - 1)
        return min(0.9, 0.12 + ((active_completed + pair_phase) / self._total_pairs) * 0.78)


class CliProgressReporter(SignalBusProgressReporter):
    """基于可复用渲染器的向后兼容 MCscan 进度报告器
    (Backward-compatible MCscan progress reporter built on the reusable renderer)
    """

    def __init__(
        self,
        request: WorkflowRequest,
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
    # 方法列表直接读注册表，workbench 首页不会再维护一份手写清单
    methods = [
        f"{_paint(spec.name, PALETTE.cyan, enabled=enabled)}"
        f"{_paint('  ' + spec.description, PALETTE.gray, enabled=enabled)}"
        + ("" if spec.stable else _paint("  (预览)", PALETTE.yellow, enabled=enabled))
        for spec in list_workflow_plugins()
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
        ("analyze workflow", "运行一站式共线性分析"),
        ("analyze run <request.json>", "运行外部 WorkflowRequest"),
        ("analyze template mcscan", "输出 JSON 请求示例"),
        ("check", "检查环境与工具链"),
        ("config init --workspace .work", "初始化配置文件"),
        ("help <cmd>", "查看指定命令参数"),
        ("clear", "清屏"),
        ("exit", "退出"),
    ]

    lines = ["", *[f"  {line}" for line in boxed], "", f"  {_paint('常用命令', PALETTE.bold, enabled=enabled)}"]

    for command, description in commands:
        # 命令列宽固定，保证中英文混排时依然能大致对齐
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


# region 分页帮助
@dataclass(frozen=True)
class _HelpSection:
    """帮助文本中的一个 section（如"位置参数"、"图件样式与自动优化"）"""

    title: str
    lines: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class _HelpArgumentItem:
    """帮助文本中的一个参数项（含可能折行的说明）"""

    section: str
    lines: list[str] = field(default_factory=list)


def _strip_ansi(text: str) -> str:
    """移除 ANSI 颜色转义序列，用于在彩色 help 中做结构判断"""

    return re.sub(r"\033\[[0-9;]*m", "", text)


def _is_section_header(line: str) -> bool:
    """判断一行是否为 section header（去颜色后无缩进且以冒号结尾）"""

    plain = _strip_ansi(line)
    stripped = plain.strip()
    return bool(stripped) and stripped.endswith(":") and not plain.startswith(" ")


def _leading_spaces(line: str) -> int:
    """计算去色后的前导空格数"""

    plain = _strip_ansi(line)
    return len(plain) - len(plain.lstrip())


def _reformat_usage_lines(lines: list[str], *, enabled: bool = False) -> list[str]:
    """把 argparse 折行的 usage 重整为简洁、带语法高亮的多行格式"""

    # 先在纯文本上判断结构，再对结果重新着色
    plain_usage = _strip_ansi(" ".join(line.strip() for line in lines if line.strip()))
    if not plain_usage:
        return lines

    # 剥离前缀
    for prefix in ("用法:", "usage:"):
        if plain_usage.startswith(prefix):
            plain_usage = plain_usage[len(prefix) :].strip()
            break

    # 分离 prog 与参数；prog 是第一段非选项 token
    parts = plain_usage.split()
    prog_parts: list[str] = []
    args_parts: list[str] = []
    in_args = False
    for part in parts:
        if in_args:
            args_parts.append(part)
        elif part.startswith("[") or part.startswith("-"):
            in_args = True
            args_parts.append(part)
        else:
            prog_parts.append(part)

    prog = " ".join(prog_parts) if prog_parts else ""
    args = " ".join(args_parts)

    if not prog:
        return lines

    result = [_paint("命令格式", PALETTE.bold + PALETTE.blue, enabled=enabled)]
    result.append("  " + _paint(prog, PALETTE.cyan, enabled=enabled))

    if args:
        # 把选项与其占位符合并成一个逻辑单元，例如 [--jcvi-config JCVI_CONFIG]
        raw_tokens = args.split()
        tokens: list[str] = []
        for token in raw_tokens:
            if tokens and not tokens[-1].endswith("]"):
                tokens[-1] = tokens[-1] + " " + token
            else:
                tokens.append(token)

        max_width = 72
        indent = "    "
        current = indent
        for token in tokens:
            # 可选参数/标志用灰色，必填位置参数用默认白色加粗
            if token.startswith("[") or token.startswith("-"):
                colored_token = _paint(token, PALETTE.gray, enabled=enabled)
            else:
                colored_token = _paint(token, PALETTE.bold, enabled=enabled)
            candidate = current + " " + colored_token if current != indent else current + colored_token
            if _visible_width(candidate) > max_width and current != indent:
                result.append(current)
                current = indent + colored_token
            else:
                current = candidate
        if current != indent:
            result.append(current)

    return result


def _parse_help_sections(text: str, *, enabled: bool = False) -> tuple[list[str], list[_HelpSection]]:
    """把 argparse help 文本解析为 (header_lines, sections)；用法 section 会被重整"""

    lines = text.splitlines()
    header_lines: list[str] = []
    sections: list[_HelpSection] = []

    current_title = ""
    current_lines: list[str] = []
    i = 0
    n = len(lines)

    def flush() -> None:
        nonlocal current_title, current_lines
        if current_title or current_lines:
            sections.append(_HelpSection(title=current_title, lines=current_lines))
            current_title = ""
            current_lines = []

    while i < n:
        line = lines[i]
        plain = _strip_ansi(line)

        # argparse 把 "用法: prog ..." 放在同一行，后续缩进行是 continuation
        if plain.lstrip().startswith(("用法:", "usage:")):
            flush()
            colon_idx = line.find(":")
            usage_content = [line[colon_idx + 1 :].strip() if colon_idx >= 0 else line]
            i += 1
            while i < n:
                next_line = lines[i]
                next_plain = _strip_ansi(next_line)
                if not next_plain.strip():
                    i += 1
                    continue
                # 下一个 section header 或非缩进行表示 usage 结束
                if not next_plain.startswith(" ") or _is_section_header(next_line):
                    break
                usage_content.append(next_line)
                i += 1
            header_lines.extend(_reformat_usage_lines(usage_content, enabled=enabled))
            continue

        if _is_section_header(line):
            flush()
            current_title = _strip_ansi(line).strip().rstrip(":")
            current_lines = []
        elif not current_title and not sections:
            header_lines.append(line)
        else:
            current_lines.append(line)

        i += 1

    flush()
    return header_lines, sections


def _extract_argument_items(sections: list[_HelpSection]) -> list[_HelpArgumentItem]:
    """从 section 中提取独立参数项，识别被折行的说明"""

    items: list[_HelpArgumentItem] = []
    for section in sections:
        if section.title == "用法":
            continue
        current: _HelpArgumentItem | None = None
        for line in section.lines:
            if not line.strip():
                if current is not None:
                    items.append(current)
                    current = None
                continue

            if _leading_spaces(line) <= 4:
                if current is not None:
                    items.append(current)
                current = _HelpArgumentItem(section=section.title, lines=[line])
            elif current is not None:
                current = _HelpArgumentItem(section=current.section, lines=[*current.lines, line])

        if current is not None:
            items.append(current)

    return items


def _paginate_argument_items(
    items: list[_HelpArgumentItem], page: int, page_size: int
) -> tuple[list[_HelpArgumentItem], int, int]:
    """对参数项列表做分页，返回 (当前页项, 实际页码, 总页数)"""

    total_pages = max(1, (len(items) + page_size - 1) // page_size)
    page = max(1, min(page, total_pages))
    start = (page - 1) * page_size
    end = min(start + page_size, len(items))
    return items[start:end], page, total_pages


def _render_help_header(prog: str, enabled: bool) -> list[str]:
    """渲染顶部帮助标题：复用工作台的圆角边框风格"""

    title = _paint("✦ GenomeLens 帮助", PALETTE.bold + PALETTE.blue, enabled=enabled)
    cmd = _paint(prog, PALETTE.cyan, enabled=enabled)
    return ["", *_boxed([title, cmd], enabled=enabled, min_width=76), ""]


def _render_help_footer(nav_text: str, enabled: bool) -> list[str]:
    """渲染底部导航：同样使用圆角边框风格"""

    return ["", *_boxed([nav_text], enabled=enabled, min_width=76), ""]


def _indent_help_lines(lines: list[str], prefix: str = "  ") -> list[str]:
    """给 help 内容统一加缩进，空行保持空行"""

    return [prefix + line if line.strip() else line for line in lines]


def _render_section_index(
    header_lines: list[str],
    sections: list[_HelpSection],
    *,
    prog: str = "",
    enabled: bool = False,
) -> str:
    """当 --section 不带值时，渲染参数类型索引"""

    lines: list[str] = []
    if prog:
        lines.extend(_render_help_header(prog, enabled))
    lines.extend(header_lines)

    lines.append(_paint("参数类型索引", PALETTE.bold + PALETTE.blue, enabled=enabled))
    sep = _paint("  " + "─" * 78, PALETTE.gray, enabled=enabled)
    lines.append(sep)

    num_col_w = 6
    name_col_w = 38
    count_col_w = 8
    header_num = _paint("编号", PALETTE.bold, enabled=enabled)
    header_name = _paint("参数组", PALETTE.bold, enabled=enabled)
    header_count = _paint("参数数", PALETTE.bold, enabled=enabled)
    lines.append(
        "  "
        + header_num
        + " " * (num_col_w - _visible_width(header_num))
        + header_name
        + " " * (name_col_w - _visible_width(header_name))
        + header_count
        + " " * (count_col_w - _visible_width(header_count))
    )
    lines.append(sep)

    argument_sections = [
        s for s in sections if _strip_ansi(s.title) not in {"用法", "位置参数", "可选参数"} and s.title.strip()
    ]

    for i, section in enumerate(argument_sections, 1):
        title = _strip_ansi(section.title)
        # 统计该 section 下的一级参数项数量
        count = sum(1 for line in section.lines if _leading_spaces(line) <= 4 and line.strip())
        num = _paint(str(i), PALETTE.cyan, enabled=enabled)
        name = _paint(title, PALETTE.yellow, enabled=enabled)
        count_text = _paint(str(count), PALETTE.green, enabled=enabled)
        lines.append(
            "  "
            + num
            + " " * (num_col_w - _visible_width(num))
            + name
            + " " * (name_col_w - _visible_width(name))
            + count_text
            + " 项"
        )

    lines.append(sep)
    section_hint = _paint("--section <编号或名称>", PALETTE.cyan, enabled=enabled)
    page_hint = _paint("--page N", PALETTE.cyan, enabled=enabled)
    nav = (
        _paint("查看某一组：", PALETTE.gray, enabled=enabled)
        + section_hint
        + _paint("  ·  ", PALETTE.gray, enabled=enabled)
        + _paint("翻页查看全部：", PALETTE.gray, enabled=enabled)
        + page_hint
    )
    lines.extend(_render_help_footer(nav, enabled=enabled))

    return "\n".join(_indent_help_lines(lines))


def _render_help_page(
    header_lines: list[str],
    sections: list[_HelpSection],
    page_items: list[_HelpArgumentItem],
    page: int,
    total_pages: int,
    *,
    prog: str = "",
    enabled: bool = False,
) -> str:
    """渲染某一页的 help 内容，按原始 section 分组，带视觉分隔"""

    lines: list[str] = []
    if prog:
        lines.extend(_render_help_header(prog, enabled))
    lines.extend(header_lines)

    by_section: dict[str, list[_HelpArgumentItem]] = {}
    for item in page_items:
        by_section.setdefault(item.section, []).append(item)

    for section_title in by_section:
        lines.append(_paint(section_title, PALETTE.bold + PALETTE.blue, enabled=enabled))
        for item in by_section[section_title]:
            lines.extend(item.lines)
        lines.append("")

    # 底部导航
    page_hint = _paint("--page N", PALETTE.cyan, enabled=enabled)
    section_hint = _paint("--section <类型>", PALETTE.cyan, enabled=enabled)
    nav = f"页码 {page}/{total_pages}  ·  {page_hint} 翻页  ·  {section_hint} 按组查看"
    lines.extend(_render_help_footer(nav, enabled=enabled))

    return "\n".join(_indent_help_lines(lines))


# 常用 section 英文/拼音别名到中文关键词的映射，方便用户按类型查看帮助
_HELP_SECTION_ALIASES: dict[str, list[str]] = {
    "figure": ["图件", "figure"],
    "mcscan": ["mcscan"],
    "species": ["物种", "局部共线性"],
    "toolchain": ["工具链"],
    "runtime": ["运行时", "输出"],
}


def _resolve_section_by_query(sections: list[_HelpSection], section_query: str) -> list[_HelpSection]:
    """根据查询字符串匹配 section；支持编号、中文标题、英文别名"""

    query = section_query.lower().strip()

    # 先尝试按编号匹配
    argument_sections = [
        s for s in sections if _strip_ansi(s.title) not in {"用法", "位置参数", "可选参数"} and s.title.strip()
    ]
    if query.isdigit():
        idx = int(query) - 1
        if 0 <= idx < len(argument_sections):
            return [argument_sections[idx]]
        return []

    keywords = [q.lower() for q in _HELP_SECTION_ALIASES.get(query, [section_query])]

    def _matches(section: _HelpSection) -> bool:
        plain_title = _strip_ansi(section.title).lower()
        for kw in keywords:
            if kw in plain_title:
                return True
        for line in section.lines:
            plain = _strip_ansi(line).lower()
            for kw in keywords:
                if kw in plain:
                    return True
        return False

    return [s for s in sections if _matches(s)]


def _render_help_section(
    header_lines: list[str],
    sections: list[_HelpSection],
    section_query: str,
    *,
    prog: str = "",
    enabled: bool = False,
) -> str:
    """渲染匹配的参数组；支持编号、英文别名与参数名子串匹配"""

    matched = _resolve_section_by_query(sections, section_query)
    if not matched:
        available = "、".join(_strip_ansi(s.title) for s in sections if _strip_ansi(s.title) not in {"用法"})
        return f"未找到参数组 '{section_query}'。可用参数组：{available}"

    lines: list[str] = []
    if prog:
        lines.extend(_render_help_header(prog, enabled))
    lines.extend(header_lines)

    for section in matched:
        lines.append(_paint(section.title, PALETTE.bold + PALETTE.blue, enabled=enabled))
        lines.extend(section.lines)
        lines.append("")

    section_hint = _paint("--section <类型>", PALETTE.cyan, enabled=enabled)
    page_hint = _paint("--page N", PALETTE.cyan, enabled=enabled)
    nav = f"{section_hint} 切换参数组  ·  {page_hint} 在同一组内翻页"
    lines.extend(_render_help_footer(nav, enabled=enabled))

    return "\n".join(_indent_help_lines(lines))


def paginate_help(
    text: str,
    *,
    page: int | None = None,
    section: str | None = None,
    page_size: int = 10,
    color: bool | None = None,
    prog: str = "",
) -> str:
    """对 argparse help 文本应用分页：按页、按参数组或显示参数组索引"""

    enabled = _supports_color() if color is None else color
    header_lines, sections = _parse_help_sections(text, enabled=enabled)

    if section is not None:
        if not section.strip():
            return _render_section_index(header_lines, sections, prog=prog, enabled=enabled)
        return _render_help_section(header_lines, sections, section, prog=prog, enabled=enabled)

    items = _extract_argument_items(sections)
    page_items, actual_page, total_pages = _paginate_argument_items(items, page or 1, page_size)
    return _render_help_page(
        header_lines,
        sections,
        page_items,
        actual_page,
        total_pages,
        prog=prog,
        enabled=enabled,
    )


def render_submodule_discovery(*, page: int = 1, page_size: int = 10, color: bool | None = None) -> str:
    """渲染子模块发现列表，按 category 分组并支持分页"""

    enabled = _supports_color() if color is None else color
    registry = get_submodule_registry()
    specs = registry.list_all()

    order = ["计算", "渲染", "混合", "其他"]
    by_category: dict[str, list[SubModuleSpec]] = {}
    for spec in specs:
        by_category.setdefault(spec.category, []).append(spec)

    flat_items: list[tuple[str, SubModuleSpec]] = []
    for category in order:
        flat_items.extend((category, spec) for spec in by_category.get(category, []))

    total_pages = max(1, (len(flat_items) + page_size - 1) // page_size)
    page = max(1, min(page, total_pages))
    start = (page - 1) * page_size
    page_items = flat_items[start : start + page_size]

    lines: list[str] = [
        "",
        _paint("可用子模块 (按 category 分组)", PALETTE.bold + PALETTE.blue, enabled=enabled),
        _paint("使用 'analyze submodule <module_id> -h' 查看具体运行参数", PALETTE.gray, enabled=enabled),
        "",
    ]

    current_category = ""
    for category, spec in page_items:
        if category != current_category:
            lines.append(_paint(category, PALETTE.bold + PALETTE.cyan, enabled=enabled))
            current_category = category

        id_text = _paint(spec.module_id, PALETTE.cyan, enabled=enabled)
        name_text = _paint(spec.name[:22], PALETTE.yellow, enabled=enabled)
        domain_text = _paint(f"[{spec.domain}]", PALETTE.gray, enabled=enabled)
        kind_text = _paint(spec.module_kind, PALETTE.gray, enabled=enabled)
        desc_text = _paint(spec.description, PALETTE.gray, enabled=enabled)

        # 所有字段都着色且颜色序列长度固定，f-string 宽度 ≈ 可见宽度
        lines.append(f"  {id_text:<46} {name_text:<24} {domain_text} {kind_text:<12} {desc_text}")

    lines.extend(
        [
            "",
            _paint(f"页码 {page}/{total_pages}  (使用 --page N 翻页)", PALETTE.gray, enabled=enabled),
            _paint(
                "提示：使用 'genomelens workflow describe <module_id>' 查看完整 JSON 元数据",
                PALETTE.gray,
                enabled=enabled,
            ),
            "",
        ]
    )

    return "\n".join(lines)


# endregion


# region 帮助文本本地化与着色
def _localize_help(text: str) -> str:
    """把 argparse 默认英文 help 标题替换为中文"""

    replacements = {
        "usage:": "用法:",
        "options:": "选项:",
        "optional arguments:": "可选参数:",
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

    for line in text.splitlines():
        stripped = line.strip()

        # 标题行：用法 / 选项 / 位置参数 / 子命令名
        if stripped in {"用法:", "选项:", "位置参数:"} or stripped.endswith(":"):
            lines.append(_paint(line, PALETTE.bold + PALETTE.blue, enabled=True))
            continue

        # 被折行的说明文字（缩进 ≥20 空格）：大间距下说明可能折到很右侧，
        # 必须优先识别，避免被 argument_only_line 误当成参数名。
        wrapped = wrapped_description_line.match(line)

        if wrapped:
            prefix, description = wrapped.groups()
            lines.append(prefix + _paint(description, PALETTE.gray, enabled=True))
            continue

        # 标准参数行：缩进 + 参数 + 间隙 + 说明
        match = argument_line.match(line)

        if match:
            prefix, argument, gap, description = match.groups()

            # {} 包裹的是子命令占位符，用蓝色；普通参数用青色
            # `{subcommands}` 这类占位符用蓝色，其余普通参数保持青色
            argument_color = PALETTE.blue if argument.startswith("{") else PALETTE.cyan
            lines.append(
                prefix
                + _paint(argument, argument_color, enabled=True)
                + gap
                + _paint(description, PALETTE.gray, enabled=True)
            )
            continue

        # 只有参数名、说明在下一行的参数行
        match = argument_only_line.match(line)

        if match and _looks_like_argument_name(stripped):
            prefix, argument = match.groups()
            argument_color = PALETTE.blue if argument.startswith("{") else PALETTE.cyan
            lines.append(prefix + _paint(argument, argument_color, enabled=True))
        else:
            lines.append(line)

    return "\n".join(lines) + ("\n" if text.endswith("\n") else "")


def _looks_like_argument_name(text: str) -> bool:
    return text.startswith(("-", "{")) or bool(re.fullmatch(r"[A-Za-z0-9_][\w-]*", text))


def print_parser_help(parser: argparse.ArgumentParser, file: TextIO | None = None) -> None:
    """使用统一路径输出 parser help(参数帮助)"""

    # argparse 没有公开 _print_message，但 format_help() 已被覆盖，这里复用内部方法保证一致
    parser._print_message(parser.format_help(), file or sys.stdout)  # noqa: SLF001 - argparse 只公开 print_help 包装


class SpaciousHelpFormatter(argparse.HelpFormatter):
    """加大 help 文本与选项名之间的间距，提升长参数名可读性"""

    # argparse 默认 _max_help_position=24；提升到 32 后，短参数名与说明之间
    # 有足够空白，长参数名也能保持清晰对齐，同时不会拉得过宽。
    _max_help_position = 32

    def __init__(self, prog: str = "") -> None:
        # 强制 help 文本从第 32 列开始：argparse 默认会取
        # min(_action_max_length + 2, _max_help_position)，因此把
        # _action_max_length 推到足够大，才能让 _max_help_position 生效。
        # 同时保证总宽度 >= _max_help_position + 80，让说明列仍有充足空间。
        try:
            term_width = os.get_terminal_size().columns
        except OSError:
            term_width = 160
        width = max(term_width, self._max_help_position + 80)
        super().__init__(prog, max_help_position=self._max_help_position, width=width)
        self._action_max_length = self._max_help_position - 2


class StyledArgumentParser(argparse.ArgumentParser):
    """StyledArgumentParser(带样式参数解析器)：只处理 CLI 帮助信息 展示"""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """初始化参数解析器，并把默认 help 文案换成中文"""

        kwargs.setdefault("formatter_class", SpaciousHelpFormatter)
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

    # 既支持直接喂 dataclass，也支持命令层传来的原始 JSON dict
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

    # analyze 命令和 workbench 都复用这条摘要渲染路径
    run_summary = summary if isinstance(summary, RunSummary) else RunSummary.from_json(summary)
    enabled = _supports_color() if color is None else color
    md = run_summary.extensions

    status = run_summary.status
    status_color = PALETTE.green if status == "SUCCEEDED" else PALETTE.red

    task = run_summary.task
    task_type = str(task.get("task_type") or "")
    workflow = str(run_summary.workflow or task.get("workflow") or "")

    species = run_summary.species
    species_names = [str(item.get("name")) for item in species if isinstance(item, dict)]
    # 多物种摘要优先信任 extensions 里的显式 species_count，缺失时再回退到 species 列表长度
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
    child_runs = run_summary.child_runs
    if child_runs:
        total = len(child_runs)
        succeeded = sum(1 for item in child_runs if item.status == "SUCCEEDED")

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
        # 摘要路径优先来自 logs；ui 块作为同一 schema 内的展示兜底
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
