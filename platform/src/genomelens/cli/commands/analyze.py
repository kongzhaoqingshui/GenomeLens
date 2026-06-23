"""`genomelens analyze` command registration."""

# region import
from __future__ import annotations

import argparse
import json
from pathlib import Path

from genomelens.analysis.dispatcher import AnalysisDispatcher
from genomelens.analysis.methods.registry import (
    list_one_stop_workflows,
    list_submodules,
)
from genomelens.analysis.requests.loader import load_analysis_request
from genomelens.analysis.requests.models import (
    AnalysisConfigRef,
    AnalysisInput,
    AnalysisOptions,
    AnalysisOutput,
    AnalysisRequest,
    McscanMethodConfig,
)
from genomelens.analysis.requests.normalizer import mcscan_auto_request_from_cli, mcscan_template_request
from genomelens.analysis.requests.schema import analysis_request_json_schema
from genomelens.app.errors.exceptions import InputValidationError
from genomelens.app.events.signal_bus import SignalBus
from genomelens.cli.ui import CliProgressReporter, ConsoleWriter, render_analysis_summary
from genomelens.core.summary_models import RunSummary
from genomelens.utils.parsers import parse_formats
from genomelens.workflow.onestop_registry import get_onestop_registry
from genomelens.workflow.submodule_registry import get_submodule_registry

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

    _register_workflow_command(nested)
    _register_submodule_command(nested)


def _register_workflow_command(nested: argparse._SubParsersAction) -> None:
    """注册 `analyze workflow` 一站式工作流命令"""

    workflow_parser = nested.add_parser("workflow", help="Run a one-stop workflow")
    workflow_parser.add_argument("workflow_id", help="One-stop workflow ID, e.g. pairwise_synteny")
    workflow_parser.add_argument("input", help="Input directory or primary file")
    workflow_parser.add_argument("output_dir", help="Output directory")
    workflow_parser.add_argument("-c", "--config", default="", help="GenomeLens project config JSON path")
    workflow_parser.add_argument("--jcvi-config", default="", help="JCVI method config JSON path")
    workflow_parser.add_argument("--jcvi-engine", default="", help="Explicit jcvi-genomelens executable")
    workflow_parser.add_argument("--blastn", default="", help="Explicit blastn executable")
    workflow_parser.add_argument("--makeblastdb", default="", help="Explicit makeblastdb executable")
    workflow_parser.add_argument("--reference", default="", help="Reference species name or 1-based index")
    workflow_parser.add_argument("--target-genes", default="", help="Target gene IDs for local synteny workflows")
    workflow_parser.add_argument("--up", type=int, default=None, help="Upstream window size for local synteny")
    workflow_parser.add_argument("--down", type=int, default=None, help="Downstream window size for local synteny")
    workflow_parser.add_argument("--align-soft", default="", help="Alignment backend: blast, last, diamond_blastp")
    workflow_parser.add_argument("--dbtype", default="", help="Sequence type: nucl or prot")
    workflow_parser.add_argument("--cscore", type=float, default=None, help="Homology cscore filter")
    workflow_parser.add_argument("--dist", type=int, default=None, help="Synteny anchor distance")
    workflow_parser.add_argument("--iter", type=int, default=None, help="Block filtering iterations")
    workflow_parser.add_argument("--min-block-size", type=int, default=None, help="Minimum block size")
    workflow_parser.add_argument("--split-targets", action="store_true", help="每个目标基因单独出图")
    workflow_parser.add_argument("--label-targets", action="store_true", help="在图中标注目标基因名称")
    workflow_parser.add_argument("--glyphstyle", choices=["box", "arrow"], default="", help="基因形状")
    workflow_parser.add_argument("--glyphcolor", choices=["orientation", "orthogroup"], default="", help="基因着色")
    workflow_parser.add_argument("--shadestyle", choices=["curve", "line"], default="", help="连线样式")
    workflow_parser.add_argument("--figsize", default="", help="画布尺寸，例如 10x5")
    workflow_parser.add_argument("--dpi", type=int, default=None, help="图片分辨率，默认 300")
    workflow_parser.add_argument("--optimize-figsize", action="store_true", help="自动推导 synteny 图件尺寸")
    workflow_parser.add_argument(
        "--rewrite-layout-links", action="store_true", help="将跨轨道 layout 连线改写为邻接轨道链"
    )
    workflow_parser.add_argument(
        "--optimize-karyotype-labels", action="store_true", help="自动优化全局核型图的轨道标签位置"
    )
    workflow_parser.add_argument(
        "--trim-cross-chromosome-blocks", action="store_true", help="切除跨染色体 block 基因行"
    )
    workflow_parser.add_argument(
        "--use-native-local-synteny-renderer",
        action="store_true",
        help="使用原生 matplotlib 局部共线性渲染器",
    )
    workflow_parser.add_argument("--formats", default="", help="Output formats, e.g. svg or svg,pdf")
    workflow_parser.add_argument("--threads", type=int, default=None, help="Thread count")
    workflow_parser.add_argument("--params", default="{}", help="JSON object of extra method parameters")
    workflow_parser.add_argument("--force", action="store_true", help="Reuse existing output directory")
    workflow_parser.add_argument("--verbose", action="store_true", help="Enable verbose engine logging")
    workflow_parser.add_argument("--log-level", default="", help="Set log level (DEBUG/INFO/WARNING/ERROR)")
    workflow_parser.add_argument("-j", "--json", action="store_true", help="Print the raw JSON summary")
    workflow_parser.set_defaults(func=_run_one_stop_workflow)


def _register_submodule_command(nested: argparse._SubParsersAction) -> None:
    """注册 `analyze submodule` 可编排子模块命令"""

    submodule_parser = nested.add_parser("submodule", help="Run a single composable submodule")
    submodule_parser.add_argument("module_id", help="Submodule ID, e.g. jcvi.graphics_histogram")
    submodule_parser.add_argument("--input-ports", required=True, help="JSON object mapping port_id to value")
    submodule_parser.add_argument("--output-dir", required=True, help="Output directory")
    submodule_parser.add_argument(
        "--input-dir",
        default="",
        help="Optional input directory when ports reference species by name",
    )
    submodule_parser.add_argument("-c", "--config", default="", help="GenomeLens project config JSON path")
    submodule_parser.add_argument("--jcvi-config", default="", help="JCVI method config JSON path")
    submodule_parser.add_argument("--jcvi-engine", default="", help="Explicit jcvi-genomelens executable")
    submodule_parser.add_argument("--formats", default="", help="Output formats, e.g. svg or svg,pdf")
    submodule_parser.add_argument("--threads", type=int, default=None, help="Thread count")
    submodule_parser.add_argument("--min-block-size", type=int, default=None, help="Minimum block size")
    submodule_parser.add_argument("--params", default="{}", help="JSON object of extra method parameters")
    submodule_parser.add_argument("--force", action="store_true", help="Reuse existing output directory")
    submodule_parser.add_argument("-j", "--json", action="store_true", help="Print the raw JSON summary")
    submodule_parser.set_defaults(func=_run_submodule)


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


def _parse_params(text: str) -> dict[str, object]:
    """解析 --params JSON 字符串"""

    raw = str(text or "{}").strip()
    if not raw:
        return {}
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise InputValidationError("--params must be a JSON object")
    return data


def _resolve_formats(formats_text: str, config_path: str) -> list[str]:
    """解析格式字符串，未提供时尝试读取配置"""

    if str(formats_text).strip():
        return parse_formats(formats_text)

    from genomelens.data.config.config_store import read_optional_config

    config = read_optional_config(config_path)
    if config is not None:
        return list(config.runtime.default_formats)
    return ["svg"]


def _base_mcscan_namespace(args: argparse.Namespace, *, jcvi_workflow: str) -> argparse.Namespace:
    """构造可传给 mcscan_auto_request_from_cli 的 Namespace"""

    ns = argparse.Namespace()
    ns.input_dir = args.input
    ns.output_dir = args.output_dir
    ns.config = args.config
    ns.jcvi_config = args.jcvi_config
    ns.jcvi_engine = args.jcvi_engine
    ns.blastn = args.blastn
    ns.makeblastdb = args.makeblastdb
    ns.reference = getattr(args, "reference", "")
    ns.target_genes = getattr(args, "target_genes", "")
    ns.formats = args.formats
    ns.force = bool(args.force)
    ns.threads = args.threads
    ns.jcvi_workflow = jcvi_workflow
    ns.align_soft = getattr(args, "align_soft", "")
    ns.dbtype = getattr(args, "dbtype", "")
    ns.cscore = getattr(args, "cscore", None)
    ns.dist = getattr(args, "dist", None)
    ns.iter = getattr(args, "iter", None)
    ns.min_block_size = getattr(args, "min_block_size", None)
    ns.up = getattr(args, "up", None)
    ns.down = getattr(args, "down", None)
    ns.split_targets = bool(getattr(args, "split_targets", False))
    ns.label_targets = bool(getattr(args, "label_targets", False))
    ns.glyphstyle = getattr(args, "glyphstyle", "")
    ns.glyphcolor = getattr(args, "glyphcolor", "")
    ns.shadestyle = getattr(args, "shadestyle", "")
    ns.figsize = getattr(args, "figsize", "")
    ns.dpi = getattr(args, "dpi", None)
    ns.optimize_figsize = bool(getattr(args, "optimize_figsize", False))
    ns.rewrite_layout_links = bool(getattr(args, "rewrite_layout_links", False))
    ns.optimize_karyotype_labels = bool(getattr(args, "optimize_karyotype_labels", False))
    ns.trim_cross_chromosome_blocks = bool(getattr(args, "trim_cross_chromosome_blocks", False))
    ns.histogram_inputs = ""
    ns.histogram_columns = "0"
    ns.histogram_skip = 0
    ns.histogram_bins = 20
    ns.histogram_vmin = None
    ns.histogram_vmax = None
    ns.histogram_xlabel = "value"
    ns.histogram_title = ""
    ns.histogram_base = 0
    ns.histogram_facet = False
    ns.histogram_fill = "white"
    ns.allow_simplified_fallback = False
    ns.verbose = bool(getattr(args, "verbose", False))
    ns.log_level = getattr(args, "log_level", "")
    ns.jcvi_layout = ""
    ns.jcvi_seqids = ""
    ns.use_native_local_synteny_renderer = bool(getattr(args, "use_native_local_synteny_renderer", False))
    return ns


def _run_one_stop_workflow(args: argparse.Namespace) -> int:
    """执行一站式工作流"""

    registry = get_onestop_registry()
    spec = registry.get(args.workflow_id)
    if spec is None:
        raise InputValidationError(f"未知的一站式工作流：{args.workflow_id}")

    params = _parse_params(args.params)

    if args.workflow_id == "histogram_plot":
        request = _build_histogram_one_stop_request(args, params)
    elif args.workflow_id == "heatmap_plot":
        request = _build_heatmap_one_stop_request(args, params)
    else:
        request = _build_mcscan_one_stop_request(args, params)

    json_output = bool(args.json)
    summary = _dispatch_request(request, json_output=json_output)
    return _print_summary(summary, json_output=json_output)


def _build_mcscan_one_stop_request(args: argparse.Namespace, params: dict[str, object]) -> AnalysisRequest:
    """为 MCscan 类一站式工作流构造 AnalysisRequest"""

    # reference_vs_targets 需要 pairwise 子任务产出局部共线性产物，
    # 因此底层 JCVI workflow 使用 local_synteny；其余 MCscan 类工作流默认 graphics_synteny
    if args.workflow_id == "reference_vs_targets":
        jcvi_workflow = "local_synteny"
    else:
        jcvi_workflow = "graphics_synteny"

    ns = _base_mcscan_namespace(args, jcvi_workflow=jcvi_workflow)
    request = mcscan_auto_request_from_cli(ns)
    method_config = dict(request.method_config)
    method_config.update(params)
    return AnalysisRequest(
        method=request.method,
        input=request.input,
        output=request.output,
        config=request.config,
        options=request.options,
        method_config=method_config,
        schema_version=request.schema_version,
        kind=request.kind,
        task_kind="one_stop",
        one_stop_workflow_id=args.workflow_id,
    )


def _build_histogram_one_stop_request(args: argparse.Namespace, params: dict[str, object]) -> AnalysisRequest:
    """为 histogram_plot 一站式工作流构造 AnalysisRequest"""

    ns = _base_mcscan_namespace(args, jcvi_workflow="graphics_histogram")
    request = mcscan_auto_request_from_cli(ns)
    method_config = dict(request.method_config)
    method_config.update(params)
    return AnalysisRequest(
        method=request.method,
        input=request.input,
        output=request.output,
        config=request.config,
        options=request.options,
        method_config=method_config,
        schema_version=request.schema_version,
        kind=request.kind,
        task_kind="one_stop",
        one_stop_workflow_id="histogram_plot",
    )


def _build_heatmap_one_stop_request(args: argparse.Namespace, params: dict[str, object]) -> AnalysisRequest:
    """为 heatmap_plot 一站式工作流构造 AnalysisRequest"""

    matrix = Path(args.input).expanduser().resolve(strict=False)
    if not matrix.is_file():
        raise InputValidationError(f"热图矩阵文件不存在：{matrix}")

    config_ref = AnalysisConfigRef(project_config=args.config, method_config=args.jcvi_config)
    method_config = McscanMethodConfig(
        workflow="graphics_heatmap",
        jcvi_engine=args.jcvi_engine,
        matrix=str(matrix),
    ).to_json()
    method_config.update(params)
    # --params 中的 rowgroups 对应 McscanMethodConfig.jcvi_layout
    if "rowgroups" in method_config:
        method_config["jcvi_layout"] = method_config.pop("rowgroups")

    return AnalysisRequest(
        method="mcscan",
        input=AnalysisInput(mode="method_specific", directory=str(matrix), species=[]),
        output=AnalysisOutput(
            directory=args.output_dir,
            force=bool(args.force),
            formats=_resolve_formats(args.formats, args.config),
        ),
        config=config_ref,
        options=AnalysisOptions(preset="auto"),
        method_config=method_config,
        task_kind="one_stop",
        one_stop_workflow_id="heatmap_plot",
    )


def _submodule_input_mode(engine_workflow: str) -> str:
    """根据子模块底层 workflow 选择输入模式"""

    if engine_workflow in {"mcscan_pairwise", "graphics_heatmap"}:
        return "auto_directory"
    return "method_specific"


def _run_submodule(args: argparse.Namespace) -> int:
    """执行单个可编排子模块"""

    registry = get_submodule_registry()
    spec = registry.get(args.module_id)
    if spec is None:
        raise InputValidationError(f"未知的子模块：{args.module_id}")

    try:
        port_bindings: dict[str, object] = json.loads(args.input_ports)
    except json.JSONDecodeError as exc:
        raise InputValidationError(f"--input-ports 不是合法 JSON：{exc}") from exc
    if not isinstance(port_bindings, dict):
        raise InputValidationError("--input-ports 必须是一个 JSON 对象")

    params = _parse_params(args.params)
    method_config = McscanMethodConfig(workflow=spec.engine_workflow).to_json()
    method_config.update(params)

    request = AnalysisRequest(
        method="mcscan",
        input=AnalysisInput(
            mode=_submodule_input_mode(spec.engine_workflow),
            directory=args.input_dir,
            species=[],
            reference_index=0,
        ),
        output=AnalysisOutput(
            directory=args.output_dir,
            force=bool(args.force),
            formats=_resolve_formats(args.formats, args.config),
        ),
        config=AnalysisConfigRef(project_config=args.config, method_config=args.jcvi_config),
        options=AnalysisOptions(preset="auto", threads=args.threads, min_block_size=args.min_block_size),
        method_config=method_config,
        task_kind="sub_module",
        sub_module_id=args.module_id,
        port_bindings=port_bindings,
    )

    json_output = bool(args.json)
    summary = _dispatch_request(request, json_output=json_output)
    return _print_summary(summary, json_output=json_output)
