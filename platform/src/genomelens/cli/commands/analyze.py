"""`genomelens analyze` command registration."""

# region import
from __future__ import annotations

import argparse
import json

from genomelens.analysis.dispatchers.task_dispatcher import TaskDispatcher
from genomelens.analysis.requests.models import WorkflowOutput, WorkflowRequest, WorkflowRuntime
from genomelens.analysis.requests.normalizer import mcscan_auto_request_from_cli, mcscan_template_request
from genomelens.analysis.requests.schema import analysis_request_json_schema
from genomelens.analysis.requests.submodule_models import SubmoduleRequest, submodule_template_request
from genomelens.analysis.requests.submodule_schema import SUBMODULE_REQUEST_JSON_SCHEMA
from genomelens.analysis.requests.task_loader import load_task_request
from genomelens.analysis.workflows.onestop import get_onestop_registry
from genomelens.analysis.workflows.registry import (
    list_one_stop_workflows,
    list_submodules,
)
from genomelens.analysis.workflows.submodules import get_submodule_registry
from genomelens.app.errors.exceptions import InputValidationError
from genomelens.app.events.signal_bus import SignalBus
from genomelens.cli.ui import CliProgressReporter, ConsoleWriter, StyledArgumentParser, render_analysis_summary
from genomelens.contracts.summaries import RunSummary
from genomelens.utils.parsers import parse_formats

# endregion


_CONSOLE = ConsoleWriter()


def register(subparsers: argparse._SubParsersAction) -> None:
    """Register the analyze command and its subcommands."""

    parser = subparsers.add_parser("analyze", help="运行 GenomeLens 分析")
    nested = parser.add_subparsers(dest="analysis_command", required=True, parser_class=StyledArgumentParser)

    run_parser = nested.add_parser("run", help="运行任务请求 JSON 文件（workflow 或 submodule）")
    run_parser.add_argument("request_json", help="WorkflowRequest 或 SubmoduleRequest JSON 文件路径")
    run_parser.add_argument("-j", "--json", action="store_true", help="输出原始 JSON 摘要")
    run_parser.set_defaults(func=_run_request_json)

    template_parser = nested.add_parser("template", help="输出任务请求模板")
    template_parser.add_argument(
        "kind",
        choices=["workflow", "submodule"],
        help="模板类型",
    )
    template_parser.add_argument(
        "id",
        nargs="?",
        default="synteny",
        help="工作流 ID 或子模块 ID",
    )
    template_parser.set_defaults(func=_print_template)

    schema_parser = nested.add_parser("schema", help="输出任务请求 JSON Schema")
    schema_parser.add_argument(
        "--kind",
        choices=["workflow", "submodule", "union"],
        default="union",
        help="schema 类型",
    )
    schema_parser.add_argument(
        "--with-capabilities",
        action="store_true",
        help="在 schema 中同时包含子模块与一站式工作流元数据",
    )
    schema_parser.set_defaults(func=_print_schema)

    _register_workflow_command(nested)
    _register_submodule_command(nested)


def _register_workflow_command(nested: argparse._SubParsersAction) -> None:
    """注册 `analyze workflow` 一站式工作流命令"""

    workflow_parser = nested.add_parser("workflow", help="运行 synteny 一站式共线性分析工作流")
    workflow_parser.add_argument("workflow_id", help="一站式工作流 ID，例如 synteny")
    workflow_parser.add_argument("input", help="输入目录或主文件")
    workflow_parser.add_argument("output_dir", help="输出目录")

    species_group = workflow_parser.add_argument_group("物种与局部共线性")
    species_group.add_argument("--reference", default="", help="参考物种名称或 1-based 索引")
    species_group.add_argument("--target-genes", default="", help="局部共线性工作流的目标基因 ID")
    species_group.add_argument("--up", type=int, default=None, help="局部共线性上游窗口大小")
    species_group.add_argument("--down", type=int, default=None, help="局部共线性下游窗口大小")
    species_group.add_argument("--split-targets", action="store_true", help="每个目标基因单独出图")
    species_group.add_argument("--label-targets", action="store_true", help="在图中标注目标基因名称")

    mcscan_group = workflow_parser.add_argument_group("MCscan 算法参数")
    mcscan_group.add_argument("--align-soft", default="", help="比对后端：blast、last、diamond_blastp")
    mcscan_group.add_argument("--dbtype", default="", help="序列类型：nucl 或 prot")
    mcscan_group.add_argument("--cscore", type=float, default=None, help="同源匹配 cscore 过滤阈值")
    mcscan_group.add_argument("--dist", type=int, default=None, help="共线性锚点距离")
    mcscan_group.add_argument("--iter", type=int, default=None, help="区块过滤迭代次数")
    mcscan_group.add_argument("--min-block-size", type=int, default=None, help="最小区块基因数")

    figure_group = workflow_parser.add_argument_group("图件样式与自动优化")
    figure_group.add_argument("--glyphstyle", choices=["box", "arrow"], default="", help="基因形状")
    figure_group.add_argument("--glyphcolor", choices=["orientation", "orthogroup"], default="", help="基因着色")
    figure_group.add_argument("--shadestyle", choices=["curve", "line"], default="", help="连线样式")
    figure_group.add_argument("--figsize", default="", help="画布尺寸，例如 10x5")
    figure_group.add_argument("--dpi", type=int, default=None, help="图片分辨率，默认 300")
    figure_group.add_argument("--optimize-figsize", action="store_true", help="自动推导 synteny 图件尺寸")
    figure_group.add_argument(
        "--rewrite-layout-links", action="store_true", help="将跨轨道 layout 连线改写为邻接轨道链"
    )
    figure_group.add_argument(
        "--optimize-karyotype-labels", action="store_true", help="自动优化全局核型图的轨道标签位置"
    )
    figure_group.add_argument("--trim-cross-chromosome-blocks", action="store_true", help="切除跨染色体 block 基因行")
    figure_group.add_argument(
        "--use-native-local-synteny-renderer",
        action="store_true",
        help="使用原生 matplotlib 局部共线性渲染器",
    )

    toolchain_group = workflow_parser.add_argument_group("工具链与配置")
    toolchain_group.add_argument("-c", "--config", default="", help="GenomeLens 项目配置 JSON 路径")
    toolchain_group.add_argument("--jcvi-config", default="", help="JCVI 方法配置 JSON 路径")
    toolchain_group.add_argument("--jcvi-engine", default="", help="显式指定 jcvi-genomelens 可执行文件")
    toolchain_group.add_argument("--blastn", default="", help="显式指定 blastn 可执行文件")
    toolchain_group.add_argument("--makeblastdb", default="", help="显式指定 makeblastdb 可执行文件")

    runtime_group = workflow_parser.add_argument_group("运行时与输出")
    runtime_group.add_argument("--formats", default="", help="输出图片格式，例如 svg 或 svg,pdf")
    runtime_group.add_argument("--threads", type=int, default=None, help="工作线程数")
    runtime_group.add_argument("--params", default="{}", help="额外方法参数的 JSON 对象")
    runtime_group.add_argument("--force", action="store_true", help="复用已有输出目录")
    runtime_group.add_argument("--verbose", action="store_true", help="开启引擎详细日志")
    runtime_group.add_argument("--log-level", default="", help="设置日志级别（DEBUG/INFO/WARNING/ERROR）")
    runtime_group.add_argument("-j", "--json", action="store_true", help="输出原始 JSON 摘要")
    workflow_parser.set_defaults(func=_run_one_stop_workflow)


def _register_submodule_command(nested: argparse._SubParsersAction) -> None:
    """注册 `analyze submodule` 可编排子模块命令"""

    submodule_parser = nested.add_parser("submodule", help="运行单个可编排子模块")
    submodule_parser.add_argument("module_id", help="子模块 ID，例如 jcvi.graphics_histogram")
    submodule_parser.add_argument("--input-ports", required=True, help="端口绑定 JSON 对象，键为 port_id")
    submodule_parser.add_argument("--output-dir", required=True, help="输出目录")
    submodule_parser.add_argument(
        "--input-dir",
        default="",
        help="当端口按名称引用物种时的可选输入目录",
    )

    toolchain_group = submodule_parser.add_argument_group("工具链与配置")
    toolchain_group.add_argument("-c", "--config", default="", help="GenomeLens 项目配置 JSON 路径")
    toolchain_group.add_argument("--jcvi-config", default="", help="JCVI 方法配置 JSON 路径")
    toolchain_group.add_argument("--jcvi-engine", default="", help="显式指定 jcvi-genomelens 可执行文件")

    runtime_group = submodule_parser.add_argument_group("运行时与输出")
    runtime_group.add_argument("--formats", default="", help="输出图片格式，例如 svg 或 svg,pdf")
    runtime_group.add_argument("--threads", type=int, default=None, help="工作线程数")
    runtime_group.add_argument("--params", default="{}", help="额外方法参数的 JSON 对象")
    runtime_group.add_argument("--force", action="store_true", help="复用已有输出目录")
    runtime_group.add_argument("-j", "--json", action="store_true", help="输出原始 JSON 摘要")
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


def _dispatch_request(request: WorkflowRequest | SubmoduleRequest, *, json_output: bool) -> RunSummary:
    """Dispatch a request and attach the compact progress renderer when needed."""

    signal_bus = SignalBus()
    reporter: CliProgressReporter | None = None

    if not json_output and isinstance(request, WorkflowRequest):
        reporter = CliProgressReporter(request)
        reporter.attach(signal_bus)

    try:
        return TaskDispatcher().dispatch(request, signal_bus=signal_bus)
    finally:
        if reporter is not None:
            reporter.finish()


def _run_request_json(args: argparse.Namespace) -> int:
    """Run an analysis from a task request JSON file."""

    request = load_task_request(args.request_json)
    summary = _dispatch_request(request, json_output=bool(args.json))
    return _print_summary(summary, json_output=bool(args.json))


def _print_template(args: argparse.Namespace) -> int:
    """Print the template request for the selected kind and id."""

    if args.kind == "workflow":
        if args.id != "synteny":
            raise InputValidationError(f"Unsupported workflow: {args.id}")
        _CONSOLE.print_json(mcscan_template_request().to_json())
        return 0

    if args.kind == "submodule":
        _CONSOLE.print_json(submodule_template_request(args.id).to_json())
        return 0

    raise ValueError(f"Unsupported template kind: {args.kind}")


def _print_schema(args: argparse.Namespace) -> int:
    """Print the requested JSON schema."""

    kind = getattr(args, "kind", "union")
    if kind == "workflow":
        schema = analysis_request_json_schema()
    elif kind == "submodule":
        schema = SUBMODULE_REQUEST_JSON_SCHEMA
    else:
        schema = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "schema_version": 3,
            "oneOf": [
                {"$ref": "#/$defs/workflow_request"},
                {"$ref": "#/$defs/submodule_request"},
            ],
            "$defs": {
                "workflow_request": analysis_request_json_schema(),
                "submodule_request": SUBMODULE_REQUEST_JSON_SCHEMA,
            },
        }

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
    """执行单一集成一站式工作流"""

    registry = get_onestop_registry()
    spec = registry.get(args.workflow_id)
    if spec is None:
        raise InputValidationError(f"未知的一站式工作流：{args.workflow_id}")

    params = _parse_params(args.params)
    request = _build_synteny_one_stop_request(args, params)

    json_output = bool(args.json)
    summary = _dispatch_request(request, json_output=json_output)
    return _print_summary(summary, json_output=json_output)


def _build_synteny_one_stop_request(args: argparse.Namespace, params: dict[str, object]) -> WorkflowRequest:
    """为 synteny 一站式工作流构造 WorkflowRequest

    底层实际执行路径由 WorkflowPlanner 根据物种数与目标基因自动展开，
    CLI 层只需统一构造 WorkflowRequest(workflow_id="synteny")。
    """

    ns = _base_mcscan_namespace(args, jcvi_workflow="graphics_synteny")
    request = mcscan_auto_request_from_cli(ns)
    if not params:
        return request

    data = request.to_json()
    parameters: dict[str, object] = dict(data.get("parameters") or {})
    for key, value in params.items():
        if key in {"align_soft", "dbtype", "cscore", "dist", "iter", "min_block_size", "allow_simplified_fallback"}:
            synteny: dict[str, object] = dict(parameters.get("synteny") or {})
            synteny[key] = value
            parameters["synteny"] = synteny
        elif key in {"up", "down", "split_targets", "label_targets", "use_native_renderer"}:
            local: dict[str, object] = dict(parameters.get("local_synteny") or {})
            local[key] = value
            parameters["local_synteny"] = local
        elif key in {"glyphstyle", "glyphcolor", "shadestyle", "figsize", "dpi", "auto_optimization"}:
            plot: dict[str, object] = dict(parameters.get("plot") or {})
            plot[key] = value
            parameters["plot"] = plot
        else:
            extras: dict[str, object] = dict(parameters.get("extras") or {})
            extras[key] = value
            parameters["extras"] = extras
    data["parameters"] = parameters
    return WorkflowRequest.from_json(data)


def _run_submodule(args: argparse.Namespace) -> int:
    """执行单个可编排子模块"""

    registry = get_submodule_registry()
    spec = registry.get(args.module_id)
    if spec is None:
        raise InputValidationError(f"未知的子模块：{args.module_id}")

    try:
        ports: dict[str, object] = json.loads(args.input_ports)
    except json.JSONDecodeError as exc:
        raise InputValidationError(f"--input-ports 不是合法 JSON：{exc}") from exc
    if not isinstance(ports, dict):
        raise InputValidationError("--input-ports 必须是一个 JSON 对象")

    params = _parse_params(args.params)

    request = SubmoduleRequest(
        module_id=args.module_id,
        inputs=ports,
        parameters=params,
        output=WorkflowOutput(
            directory=args.output_dir,
            force=bool(args.force),
            formats=_resolve_formats(args.formats, args.config),
        ),
        runtime=WorkflowRuntime(
            project_config=args.config,
            engine_config=args.jcvi_config,
            jcvi_engine=args.jcvi_engine,
            blastn=getattr(args, "blastn", "") or "",
            makeblastdb=getattr(args, "makeblastdb", "") or "",
            threads=args.threads,
            log_level=getattr(args, "log_level", "") or "INFO",
            verbose=False,
        ),
    )

    json_output = bool(args.json)
    summary = _dispatch_request(request, json_output=json_output)
    return _print_summary(summary, json_output=json_output)
