"""request_assembler(请求组装器)：把解析后的输入/选项组装成 AnalysisRequest"""

# region import
from __future__ import annotations

import argparse
from dataclasses import replace

from genomelens.analysis.requests.models import (
    AnalysisConfigRef,
    AnalysisInput,
    AnalysisOptions,
    AnalysisOutput,
    AnalysisRequest,
    McscanMethodConfig,
)
from genomelens.analysis.requests.normalization.input_resolver import _path_text, discover_species_from_directory
from genomelens.analysis.requests.normalization.option_merger import (
    _align_soft,
    _auto_optimization_dict,
    _cscore,
    _dbtype,
    _dist,
    _down,
    _dpi,
    _formats,
    _iter,
    _label_targets,
    _log_level,
    _min_block_size,
    _split_targets,
    _style_arg,
    _target_gene_ids,
    _threads,
    _up,
    _use_native_local_synteny_renderer,
    _workflow,
)
from genomelens.analysis.requests.normalization.reference_resolver import (
    _reference,
    _resolve_jcvi_config,
    _resolve_reference_index,
)
from genomelens.app.errors.exceptions import InputValidationError
from genomelens.data.config.config_models import ConfigModel
from genomelens.data.config.config_store import read_optional_config
from genomelens.workflow.port_system import PortSystem
from genomelens.workflow.submodule_registry import get_submodule_registry

# endregion


def _comma_split(text: str) -> list[str]:
    """按逗号拆分非空文本项"""

    return [item.strip() for item in text.split(",") if item.strip()]


def _histogram_inputs(args: argparse.Namespace) -> list[str]:
    """解析 histogram 输入文件列表"""

    primary = _path_text(args.input_dir)
    extras = _comma_split(str(getattr(args, "histogram_inputs", "") or ""))
    return [primary, *(_path_text(item) for item in extras)]


def _histogram_columns(args: argparse.Namespace) -> list[int]:
    """解析 histogram 列号列表"""

    raw = _comma_split(str(getattr(args, "histogram_columns", "") or ""))
    if not raw:
        return [0]
    return [int(item) for item in raw]


def read_request_config(request: AnalysisRequest) -> ConfigModel | None:
    """读取 request(请求) 引用的配置文件"""

    return read_optional_config(
        request.config.project_config,
        jcvi_config_path=request.config.method_config,
    )


def _build_mcscan_method_config(args: argparse.Namespace, config: ConfigModel | None) -> McscanMethodConfig:
    """根据 CLI 和配置构建 McscanMethodConfig"""

    # CLI 原始参数和 config 默认值会在这里收口成 method_config，后续 adapter 不再回头读 argparse
    return McscanMethodConfig(
        workflow=_workflow(args, config),
        jcvi_engine=args.jcvi_engine,
        blastn=args.blastn,
        makeblastdb=args.makeblastdb,
        jcvi_layout=args.jcvi_layout,
        jcvi_seqids=args.jcvi_seqids,
        allow_simplified_fallback=bool(args.allow_simplified_fallback),
        align_soft=_align_soft(args, config),
        dbtype=_dbtype(args, config),
        cscore=_cscore(args, config),
        dist=_dist(args, config),
        iter=_iter(args, config),
        target_gene_ids=_target_gene_ids(args, config),
        up=_up(args, config),
        down=_down(args, config),
        split_targets=_split_targets(args, config),
        label_targets=_label_targets(args, config),
        glyphstyle=_style_arg(args, config, "glyphstyle"),
        glyphcolor=_style_arg(args, config, "glyphcolor"),
        shadestyle=_style_arg(args, config, "shadestyle"),
        figsize=_style_arg(args, config, "figsize"),
        dpi=_dpi(args, config),
        auto_optimization=_auto_optimization_dict(args, config),
        use_native_local_synteny_renderer=_use_native_local_synteny_renderer(args, config),
        histogram_inputs=_histogram_inputs(args),
        histogram_columns=_histogram_columns(args),
        histogram_skip=int(getattr(args, "histogram_skip", 0) or 0),
        histogram_bins=int(getattr(args, "histogram_bins", 20) or 20),
        histogram_vmin=float(args.histogram_vmin) if getattr(args, "histogram_vmin", None) is not None else 0.0,
        histogram_vmax=float(args.histogram_vmax) if getattr(args, "histogram_vmax", None) is not None else None,
        histogram_xlabel=str(getattr(args, "histogram_xlabel", "") or "value"),
        histogram_title=str(getattr(args, "histogram_title", "") or ""),
        histogram_base=int(getattr(args, "histogram_base", 0) or 0),
        histogram_facet=bool(getattr(args, "histogram_facet", False)),
        histogram_fill=str(getattr(args, "histogram_fill", "") or "white"),
    )


def mcscan_auto_request_from_cli(args: argparse.Namespace) -> AnalysisRequest:
    """把 MCscan 相关 CLI 参数转成 AnalysisRequest(分析请求)"""

    jcvi_config_path = _resolve_jcvi_config(args)
    config_ref = AnalysisConfigRef(project_config=args.config, method_config=jcvi_config_path)

    # 先用最小 request 读取配置文件，避免在目录发现前重复手写同一套优先级逻辑
    base_request = AnalysisRequest(
        method="mcscan",
        input=AnalysisInput(mode="auto_directory"),
        output=AnalysisOutput(directory=""),
        config=config_ref,
    )
    config = read_request_config(base_request)

    method_config = _build_mcscan_method_config(args, config)
    if method_config.workflow == "graphics_histogram":
        analysis_input = AnalysisInput(
            mode="method_specific",
            directory=_path_text(args.input_dir),
            species=[],
        )
    else:
        input_dir = _path_text(args.input_dir)
        discovered = discover_species_from_directory(input_dir)
        reference_index = _resolve_reference_index(_reference(args, config), discovered)
        analysis_input = AnalysisInput(
            mode="auto_directory",
            directory=input_dir,
            species=discovered,
            reference_index=reference_index,
        )
    return AnalysisRequest(
        method="mcscan",
        input=analysis_input,
        output=AnalysisOutput(
            directory=_path_text(args.output_dir),
            force=bool(args.force),
            formats=_formats(args, config),
        ),
        config=config_ref,
        options=AnalysisOptions(
            preset="auto",
            threads=_threads(args, config),
            min_block_size=_min_block_size(args, config),
            log_level=_log_level(args, config),
            verbose=bool(getattr(args, "verbose", False)),
            console_log=False,
        ),
        method_config=method_config.to_json(),
    )


def _expand_submodule_ports(request: AnalysisRequest) -> AnalysisRequest:
    """把子模块端口绑定展开到 request 的 input/method_config，使 dispatcher 可校验"""

    if request.task_kind != "sub_module" or not request.sub_module_id:
        return request

    registry = get_submodule_registry()
    spec = registry.get(request.sub_module_id)
    if spec is None:
        return request

    errors = PortSystem.validate_bindings(spec.inputs, request.port_bindings)
    if errors:
        raise InputValidationError("; ".join(errors))

    bindings = request.port_bindings
    method_config = dict(request.method_config)
    method_config["workflow"] = spec.engine_workflow

    if spec.engine_workflow == "graphics_histogram":
        raw_numeric = bindings.get("numeric_files")
        numeric_files = list(raw_numeric) if isinstance(raw_numeric, list) else []
        if not numeric_files:
            raise InputValidationError("graphics_histogram 子模块缺少 numeric_files 端口绑定")
        method_config["histogram_inputs"] = numeric_files
        method_config.setdefault("histogram_columns", [0])
        return replace(
            request,
            input=AnalysisInput(
                mode="method_specific",
                directory=str(numeric_files[0]),
                species=[],
                reference_index=0,
            ),
            method_config=method_config,
        )

    if spec.engine_workflow == "graphics_heatmap":
        matrix = bindings.get("matrix_csv")
        if not isinstance(matrix, str) or not matrix:
            raise InputValidationError("graphics_heatmap 子模块缺少 matrix_csv 端口绑定")
        method_config["matrix"] = matrix
        return replace(
            request,
            input=AnalysisInput(
                mode="method_specific",
                directory=str(matrix),
                species=[],
                reference_index=0,
            ),
            method_config=method_config,
        )

    if spec.engine_workflow == "mcscan_pairwise":
        species_pair = bindings.get("species_pair")
        if isinstance(species_pair, list) and len(species_pair) == 2:
            input_dir = str(request.input.directory) if request.input.directory else ""
        elif isinstance(species_pair, str):
            input_dir = species_pair
        else:
            raise InputValidationError("mcscan_pairwise 子模块的 species_pair 端口应为目录路径或两个物种名")
        return replace(
            request,
            input=AnalysisInput(
                mode="auto_directory",
                directory=input_dir,
                species=[],
                reference_index=0,
            ),
            method_config=method_config,
        )

    return request


def normalize_analysis_request(request: AnalysisRequest) -> AnalysisRequest:
    """补齐 request(请求) 中可推导的输入字段"""

    if request.method != "mcscan":
        return request

    if request.task_kind == "sub_module":
        request = _expand_submodule_ports(request)

    if request.input.mode != "auto_directory" or request.input.species:
        return request
    if not request.input.directory:
        raise InputValidationError("auto_directory request 缺少 input.directory")

    # 外部入口只要给出目录，就在这里补齐 species[]，让后续 dispatcher 总是消费完整请求
    return AnalysisRequest(
        method=request.method,
        input=AnalysisInput(
            mode=request.input.mode,
            directory=_path_text(request.input.directory),
            species=discover_species_from_directory(request.input.directory),
            reference_index=request.input.reference_index,
        ),
        output=request.output,
        config=request.config,
        options=request.options,
        method_config=request.method_config,
        schema_version=request.schema_version,
        kind=request.kind,
        task_kind=request.task_kind,
        one_stop_workflow_id=request.one_stop_workflow_id,
        sub_module_id=request.sub_module_id,
        port_bindings=request.port_bindings,
        composition=request.composition,
    )


def mcscan_template_request() -> AnalysisRequest:
    """返回 mcscan 方法的 request(JSON 请求) 模板"""

    return AnalysisRequest(
        method="mcscan",
        input=AnalysisInput(
            mode="auto_directory",
            directory="input",
            species=[],
        ),
        output=AnalysisOutput(
            directory="output",
            force=False,
            formats=["svg"],
        ),
        config=AnalysisConfigRef(
            project_config="workspace/genomelens.config.json",
            method_config="workspace/jcvi.config.json",
        ),
        options=AnalysisOptions(
            preset="auto",
            threads=None,
            min_block_size=None,
        ),
        method_config=McscanMethodConfig(workflow="graphics_synteny").to_json(),
    )
