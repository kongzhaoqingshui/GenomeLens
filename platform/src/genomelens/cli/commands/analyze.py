"""`genomelens analyze` command registration."""

# region import
from __future__ import annotations

import argparse
from functools import partial

from genomelens.analysis.dispatcher import AnalysisDispatcher
from genomelens.analysis.methods.registry import (
    MethodPlugin,
    MethodRegistry,
    list_one_stop_workflows,
    list_submodules,
)
from genomelens.analysis.requests.loader import load_analysis_request
from genomelens.analysis.requests.models import AnalysisRequest
from genomelens.analysis.requests.normalizer import mcscan_template_request
from genomelens.analysis.requests.schema import analysis_request_json_schema
from genomelens.app.events.signal_bus import SignalBus
from genomelens.cli.ui import CliProgressReporter, ConsoleWriter, render_analysis_summary
from genomelens.core.summary_models import RunSummary

# endregion


_CONSOLE = ConsoleWriter()


def register(subparsers: argparse._SubParsersAction) -> None:
    """Register the analyze command and its subcommands."""

    parser = subparsers.add_parser("analyze", help="Run a GenomeLens analysis")
    nested = parser.add_subparsers(dest="analysis_command", required=True)

    run_parser = nested.add_parser("run", help="Run an AnalysisRequest JSON file")
    run_parser.add_argument("request_json", help="Path to an AnalysisRequest JSON file")
    run_parser.add_argument("-j", "--json", action="store_true", help="Print the raw JSON summary")
    run_parser.set_defaults(func=_run_request_json)

    template_parser = nested.add_parser("template", help="Print an AnalysisRequest template")
    template_parser.add_argument("method", choices=["mcscan"], nargs="?", default="mcscan", help="Analysis method")
    template_parser.set_defaults(func=_print_template)

    schema_parser = nested.add_parser("schema", help="Print the AnalysisRequest JSON schema")
    schema_parser.add_argument(
        "--with-capabilities",
        action="store_true",
        help="Include submodule and one-stop workflow metadata alongside the schema",
    )
    schema_parser.set_defaults(func=_print_schema)

    registry = MethodRegistry()
    for plugin in registry.list_all():
        method_parser = nested.add_parser(plugin.name, help=plugin.description)
        if plugin.name == "mcscan":
            backends = method_parser.add_subparsers(dest="mcscan_backend", title="MCscan backend", required=True)
            jcvi_parser = backends.add_parser("jcvi", help="Run the JCVI synteny workflow")
            plugin.add_cli_arguments(jcvi_parser)
            jcvi_parser.set_defaults(func=partial(_run_plugin, plugin=plugin))
        else:
            plugin.add_cli_arguments(method_parser)
            method_parser.set_defaults(func=partial(_run_plugin, plugin=plugin))


def _print_summary(summary: RunSummary | dict[str, object], json_output: bool = False) -> int:
    """Print the analysis summary."""

    run_summary = summary if isinstance(summary, RunSummary) else RunSummary.from_json(summary)

    writer = ConsoleWriter(json_mode=json_output)
    if json_output:
        writer.print_json(run_summary.to_json())
    else:
        writer.print_text(render_analysis_summary(run_summary))

    return 0 if run_summary.status == "SUCCEEDED" else 7


def _dispatch_request(request: AnalysisRequest, *, json_output: bool) -> RunSummary:
    """Dispatch a request and attach the compact progress renderer when needed."""

    signal_bus = SignalBus()
    reporter: CliProgressReporter | None = None

    if not json_output:
        reporter = CliProgressReporter(request)
        reporter.attach(signal_bus)

    try:
        return AnalysisDispatcher().dispatch(request, signal_bus=signal_bus)
    finally:
        if reporter is not None:
            reporter.finish()


def _run_plugin(args: argparse.Namespace, plugin: MethodPlugin) -> int:
    """Run a registered method command."""

    request = plugin.build_request(args)
    json_output = bool(getattr(args, "json", False))
    summary = _dispatch_request(request, json_output=json_output)
    return _print_summary(summary, json_output=json_output)


def _run_request_json(args: argparse.Namespace) -> int:
    """Run an analysis from an AnalysisRequest JSON file."""

    request = load_analysis_request(args.request_json)
    summary = _dispatch_request(request, json_output=bool(args.json))
    return _print_summary(summary, json_output=bool(args.json))


def _print_template(args: argparse.Namespace) -> int:
    """Print the template request for the selected method."""

    if args.method == "mcscan":
        _CONSOLE.print_json(mcscan_template_request().to_json())
        return 0

    raise ValueError(f"Unsupported template method: {args.method}")


def _print_schema(args: argparse.Namespace) -> int:
    """Print the AnalysisRequest JSON schema."""

    schema = analysis_request_json_schema()
    if getattr(args, "with_capabilities", False):
        payload: dict[str, object] = {
            "analysis_request_schema": schema,
            "submodules": [spec.to_json() for spec in list_submodules()],
            "one_stop_workflows": [spec.to_json() for spec in list_one_stop_workflows()],
        }
        _CONSOLE.print_json(payload)
    else:
        _CONSOLE.print_json(schema)
    return 0
