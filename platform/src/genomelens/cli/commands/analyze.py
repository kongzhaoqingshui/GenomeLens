"""`genomelens analyze` 命令注册"""

# region import
from __future__ import annotations

import argparse
import json
from functools import partial

from genomelens.analysis.dispatcher import AnalysisDispatcher
from genomelens.analysis.methods.registry import MethodPlugin, MethodRegistry
from genomelens.analysis.request_loader import load_analysis_request
from genomelens.analysis.request_normalizer import mcscan_template_request
from genomelens.analysis.request_schema import analysis_request_json_schema
from genomelens.cli.ui import render_analysis_summary
from genomelens.core.summary_models import RunSummary

# endregion


def register(subparsers: argparse._SubParsersAction) -> None:
    """注册 analyze 命令及其所有已注册方法子命令"""

    parser = subparsers.add_parser("analyze", help="运行 GenomeLens 分析")
    nested = parser.add_subparsers(dest="analysis_command", required=True)

    run_parser = nested.add_parser("run", help="运行 AnalysisRequest JSON")
    run_parser.add_argument("request_json", help="AnalysisRequest JSON 文件路径")
    run_parser.add_argument("-j", "--json", action="store_true", help="输出机器可读的原始 JSON 摘要")
    run_parser.set_defaults(func=_run_request_json)

    template_parser = nested.add_parser("template", help="输出 AnalysisRequest 示例")
    template_parser.add_argument("method", choices=["mcscan"], nargs="?", default="mcscan", help="分析方法")
    template_parser.set_defaults(func=_print_template)

    schema_parser = nested.add_parser("schema", help="输出 AnalysisRequest JSON schema")
    schema_parser.set_defaults(func=_print_schema)

    registry = MethodRegistry()
    for plugin in registry.list_all():
        method_parser = nested.add_parser(plugin.name, help=plugin.description)
        if plugin.name == "mcscan":
            backends = method_parser.add_subparsers(dest="mcscan_backend", title="MCscan 后端", required=True)
            jcvi_parser = backends.add_parser("jcvi", help="运行 JCVI 共线性分析与绘图")
            plugin.add_cli_arguments(jcvi_parser)
            jcvi_parser.set_defaults(func=partial(_run_plugin, plugin=plugin))
        else:
            plugin.add_cli_arguments(method_parser)
            method_parser.set_defaults(func=partial(_run_plugin, plugin=plugin))


def _print_summary(summary: RunSummary | dict[str, object], json_output: bool = False) -> int:
    """输出分析摘要"""

    run_summary = summary if isinstance(summary, RunSummary) else RunSummary.from_json(summary)

    if json_output:
        # JSON 模式保留原始结构，供插件、脚本或其他进程直接消费
        print(json.dumps(run_summary.to_json(), ensure_ascii=False, indent=2))
    else:
        print(render_analysis_summary(run_summary))

    return 0 if run_summary.status == "SUCCEEDED" else 7


def _run_plugin(args: argparse.Namespace, plugin: MethodPlugin) -> int:
    """运行任意已注册方法子命令"""

    request = plugin.build_request(args)
    summary = AnalysisDispatcher().dispatch(request)
    return _print_summary(summary, json_output=bool(getattr(args, "json", False)))


def _run_request_json(args: argparse.Namespace) -> int:
    """从 AnalysisRequest JSON 文件运行分析"""

    request = load_analysis_request(args.request_json)
    summary = AnalysisDispatcher().dispatch(request)
    return _print_summary(summary, json_output=bool(args.json))


def _print_template(args: argparse.Namespace) -> int:
    """输出指定方法的 AnalysisRequest 示例"""

    if args.method == "mcscan":
        print(json.dumps(mcscan_template_request().to_json(), ensure_ascii=False, indent=2))
        return 0

    raise ValueError(f"不支持的 template method(模板方法)：{args.method}")


def _print_schema(_args: argparse.Namespace) -> int:
    """输出 AnalysisRequest JSON schema"""

    print(json.dumps(analysis_request_json_schema(), ensure_ascii=False, indent=2))
    return 0
