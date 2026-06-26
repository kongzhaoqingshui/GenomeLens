"""GenomeLens 顶层 argparse 入口"""

# region import
from __future__ import annotations

import argparse
import shlex
import sys

from genomelens._version import __version__
from genomelens.app.errors.error_reporter import exit_code_for, format_user_error
from genomelens.cli.commands import analyze, check, clean, config, workflow
from genomelens.cli.ui import (
    ConsoleWriter,
    StyledArgumentParser,
    clear_screen,
    paginate_help,
    prompt_text,
    render_command_error,
    render_submodule_discovery,
    render_workbench_banner,
)

# endregion


_CONSOLE = ConsoleWriter()


def build_parser() -> argparse.ArgumentParser:
    """构建完整命令树"""

    parser = StyledArgumentParser(
        prog="genomelens",
        description="GenomeLens 共线性分析工作台",
        epilog="提示：不带参数运行会进入彩色交互工作台",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"GenomeLens Shell {__version__}",
        help="显示版本号并退出",
    )  # 注册基础信息

    subparsers = parser.add_subparsers(dest="command", title="命令", parser_class=StyledArgumentParser)

    # region 通过引用注册的核心功能类命令树
    check.register(subparsers)
    config.register(subparsers)
    analyze.register(subparsers)  # 核心功能命令 - 分析
    clean.register(subparsers)
    workflow.register(subparsers)

    # endregion

    # region 仅在 main 下注册的辅助功能类命令树
    # 帮助
    help_parser = subparsers.add_parser("help", help="显示指定命令的参数说明")
    help_parser.add_argument("command_path", nargs="*", metavar="COMMAND", help="命令路径，例如 analyze workflow")
    help_parser.add_argument("-c", "--command", default="", help='命令路径字符串，例如 "analyze workflow"')
    help_parser.add_argument("--page", type=int, default=None, help="帮助页码（默认 1）")
    help_parser.add_argument(
        "--section",
        nargs="?",
        const="",
        default=None,
        help="按参数组名过滤帮助；不带值时显示参数组索引",
    )
    help_parser.set_defaults(func=run_help)

    # 进入交互式工作台
    workbench_parser = subparsers.add_parser("workbench", help="进入交互式工作台")
    workbench_parser.set_defaults(func=run_workbench)

    # endregion

    return parser


# region 一些内部函数
def _subparser_map(parser: argparse.ArgumentParser) -> dict[str, argparse.ArgumentParser]:
    # argparse 没有公开 API 暴露子解析器树，因此这里统一封装一次内部遍历
    for action in parser._actions:  # noqa: SLF001 - argparse 没有公开的子命令遍历 API
        if isinstance(action, argparse._SubParsersAction):  # noqa: SLF001 - 只读 argparse 内部结构
            return dict(action.choices)
    return {}


def _find_parser(root: argparse.ArgumentParser, command_path: list[str]) -> argparse.ArgumentParser | None:
    parser = root
    for name in command_path:
        children = _subparser_map(parser)
        if name not in children:
            return None
        parser = children[name]
    return parser


# endregion


# region 帮助/运行工作台
HELP_FLAGS = {"-h", "--help"}


def _extract_help_page(argv: list[str]) -> tuple[list[str], int | None, str | None]:
    """从 argv 中提取 --page/--section，返回 (清理后的路径, 页码, 参数组)

    --section 不带值时返回空字符串，用于显示参数类型索引。
    """

    page: int | None = None
    section: str | None = None
    result: list[str] = []
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--page":
            if i + 1 < len(argv):
                try:
                    page = int(argv[i + 1])
                except ValueError:
                    result.extend([arg, argv[i + 1]])
                i += 2
                continue
        elif arg.startswith("--page="):
            try:
                page = int(arg.split("=", 1)[1])
            except ValueError:
                result.append(arg)
        elif arg == "--section":
            # 不带值表示请求索引；带值则消费下一项
            if i + 1 < len(argv) and not argv[i + 1].startswith("-"):
                section = argv[i + 1]
                i += 2
            else:
                section = ""
                i += 1
            continue
        elif arg.startswith("--section="):
            section = arg.split("=", 1)[1]
        elif arg in HELP_FLAGS:
            i += 1
            continue
        else:
            result.append(arg)
        i += 1

    return result, page, section


def _handle_help(root: argparse.ArgumentParser, argv: list[str]) -> int:
    """统一处理 -h/--help 与 help 命令，支持分页与子模块发现"""

    clean_argv, page, section = _extract_help_page(argv)

    # analyze submodule -h（无 module_id）应展示子模块发现列表
    if clean_argv == ["analyze", "submodule"]:
        _CONSOLE.print_text(render_submodule_discovery(page=page or 1), file=sys.stdout)
        return 0

    parser = _find_parser(root, clean_argv) if clean_argv else root
    if parser is None and clean_argv[:2] == ["analyze", "submodule"]:
        # analyze submodule <module_id> -h 应展示该子命令的运行参数帮助
        parser = _find_parser(root, ["analyze", "submodule"])
    if parser is None:
        _CONSOLE.print_error(f"未知命令：{' '.join(clean_argv)}")
        return 2

    text = parser.format_help()
    output = paginate_help(text, page=page, section=section, prog=parser.prog)
    _CONSOLE.print_text(output, file=sys.stdout)
    return 0


def run_help(args: argparse.Namespace) -> int:
    """显示指定命令的帮助文本"""

    root = build_parser()
    command_path = shlex.split(args.command) if args.command else list(args.command_path)
    argv = [*command_path, "--help"]
    if getattr(args, "page", None) is not None:
        argv.extend(["--page", str(args.page)])
    if getattr(args, "section", None) is not None:
        argv.extend(["--section", str(args.section)])
    return _handle_help(root, argv)


def run_workbench(_args: argparse.Namespace | None = None) -> int:
    """运行一个轻量交互式 workbench(工作台)"""

    _CONSOLE.print_text(render_workbench_banner(), file=sys.stdout)
    while True:
        try:
            line = input(prompt_text()).strip()
        except (EOFError, KeyboardInterrupt):
            _CONSOLE.print_text("")
            return 0

        if not line:
            continue
        if line.lower() in {"exit", "quit"}:
            return 0
        if line.lower() in {"clear", "cls"}:
            clear_screen()
            continue

        # 交互工作台复用主入口，这样帮助、错误码和命令行为与普通 CLI 完全一致
        code = main(shlex.split(line))
        if code:
            _CONSOLE.print_error(render_command_error(code))

    return 0


# endregion


def main(argv: list[str] | None = None) -> int:
    """GenomeLens 顶层入口：解析参数并分发到对应子命令"""
    if argv is None:
        argv = sys.argv[1:]

    # 没有参数时直接进入工作台
    if not argv:
        return run_workbench()

    parser = build_parser()

    # 帮助请求统一走分页壳，避免 argparse 默认 help action 直接退出
    if any(flag in argv for flag in HELP_FLAGS):
        return _handle_help(parser, argv)

    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        # argparse 默认直接退出进程；这里收口成整数返回码，方便测试和工作台复用
        return int(exc.code or 0)

    if not hasattr(args, "func"):
        parser.print_help()
        return 2

    try:
        return int(args.func(args) or 0)
    except Exception as exc:
        # CLI 边界统一转成用户可读错误与稳定退出码
        _CONSOLE.print_error(format_user_error(exc))
        return exit_code_for(exc)


if __name__ == "__main__":  # 简单的启动
    raise SystemExit(main())
