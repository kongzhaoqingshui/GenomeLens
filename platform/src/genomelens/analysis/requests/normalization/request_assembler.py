"""request_assembler(请求组装器)：把解析后的输入/选项组装成 WorkflowRequest"""

# region import
from __future__ import annotations

import argparse

from genomelens.analysis.requests.models import (
    HeatmapParameters,
    HistogramParameters,
    LocalSyntenyParameters,
    PlotParameters,
    SyntenyParameters,
    WorkflowOutput,
    WorkflowParameters,
    WorkflowRequest,
    WorkflowRuntime,
    workflow_template_request,
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


def read_request_config(request: WorkflowRequest) -> ConfigModel | None:
    """读取 request(请求) 引用的配置文件"""

    return read_optional_config(
        request.runtime.project_config,
        jcvi_config_path=request.runtime.engine_config,
    )


def _build_parameters(args: argparse.Namespace, config: ConfigModel | None) -> WorkflowParameters:
    """根据 CLI 和配置构建分组参数"""

    return WorkflowParameters(
        synteny=SyntenyParameters(
            align_soft=_align_soft(args, config),
            dbtype=_dbtype(args, config),
            cscore=_cscore(args, config),
            dist=_dist(args, config),
            iter=_iter(args, config),
            allow_simplified_fallback=bool(getattr(args, "allow_simplified_fallback", False)),
        ),
        local_synteny=LocalSyntenyParameters(
            target_gene_ids=_target_gene_ids(args, config),
            up=_up(args, config),
            down=_down(args, config),
            split_targets=_split_targets(args, config),
            label_targets=_label_targets(args, config),
            use_native_renderer=_use_native_local_synteny_renderer(args, config),
        ),
        plot=PlotParameters(
            glyphstyle=_style_arg(args, config, "glyphstyle"),
            glyphcolor=_style_arg(args, config, "glyphcolor"),
            shadestyle=_style_arg(args, config, "shadestyle"),
            figsize=_style_arg(args, config, "figsize"),
            dpi=_dpi(args, config),
            auto_optimization=_auto_optimization_dict(args, config),
        ),
        histogram=HistogramParameters(
            inputs=_histogram_inputs(args),
            columns=_histogram_columns(args),
            skip=int(getattr(args, "histogram_skip", 0) or 0),
            bins=int(getattr(args, "histogram_bins", 20) or 20),
            vmin=float(args.histogram_vmin) if getattr(args, "histogram_vmin", None) is not None else 0.0,
            vmax=float(args.histogram_vmax) if getattr(args, "histogram_vmax", None) is not None else None,
            xlabel=str(getattr(args, "histogram_xlabel", "") or "value"),
            title=str(getattr(args, "histogram_title", "") or ""),
            base=int(getattr(args, "histogram_base", 0) or 0),
            facet=bool(getattr(args, "histogram_facet", False)),
            fill=str(getattr(args, "histogram_fill", "") or "white"),
        ),
        heatmap=HeatmapParameters(
            matrix=str(getattr(args, "matrix", "") or ""),
            rowgroups=str(getattr(args, "rowgroups", "") or getattr(args, "jcvi_layout", "") or ""),
            cmap=str(getattr(args, "cmap", "") or ""),
            groups=bool(getattr(args, "groups", False)),
            horizontalbar=bool(getattr(args, "horizontalbar", False)),
        ),
    )


def _workflow_id_from_engine_workflow(engine_workflow: str) -> str:
    """把底层 JCVI workflow 映射到公开 workflow_id"""

    if engine_workflow == "graphics_histogram":
        return "graphics_histogram"
    if engine_workflow == "graphics_heatmap":
        return "graphics_heatmap"
    if engine_workflow == "local_synteny":
        return "local_synteny"
    return "synteny"


def mcscan_auto_request_from_cli(args: argparse.Namespace) -> WorkflowRequest:
    """把 MCscan 相关 CLI 参数转成 WorkflowRequest(工作流请求)"""

    jcvi_config_path = _resolve_jcvi_config(args)
    runtime_probe = WorkflowRuntime(
        project_config=str(getattr(args, "config", "") or ""),
        engine_config=jcvi_config_path,
    )
    config = read_request_config(WorkflowRequest(workflow_id="synteny", runtime=runtime_probe))
    parameters = _build_parameters(args, config)
    engine_workflow = _workflow(args, config)
    workflow_id = _workflow_id_from_engine_workflow(engine_workflow)

    if workflow_id in {"graphics_histogram", "graphics_heatmap"}:
        species = []
        reference_index = 0
    else:
        input_dir = _path_text(args.input_dir)
        species = discover_species_from_directory(input_dir)
        reference_index = _resolve_reference_index(_reference(args, config), species)

    return WorkflowRequest(
        workflow_id=workflow_id,
        species=species,
        reference_index=reference_index,
        inputs={},
        output=WorkflowOutput(
            directory=_path_text(args.output_dir),
            force=bool(args.force),
            formats=_formats(args, config),
        ),
        runtime=WorkflowRuntime(
            project_config=str(getattr(args, "config", "") or ""),
            engine_config=jcvi_config_path,
            jcvi_engine=str(getattr(args, "jcvi_engine", "") or ""),
            blastn=str(getattr(args, "blastn", "") or ""),
            makeblastdb=str(getattr(args, "makeblastdb", "") or ""),
            threads=_threads(args, config),
            min_block_size=_min_block_size(args, config),
            log_level=_log_level(args, config),
            verbose=bool(getattr(args, "verbose", False)),
            console_log=False,
        ),
        parameters=parameters,
    )


def normalize_analysis_request(request: WorkflowRequest) -> WorkflowRequest:
    """补齐 request(请求) 中可推导的输入字段"""

    if request.is_plot_only or request.species:
        return request
    raw_input_dir = request.inputs.get("directory") or request.inputs.get("input_dir")
    if not raw_input_dir:
        return request
    species = discover_species_from_directory(str(raw_input_dir))
    return WorkflowRequest(
        workflow_id=request.workflow_id,
        species=species,
        reference_index=request.reference_index,
        inputs=request.inputs,
        parameters=request.parameters,
        output=request.output,
        runtime=request.runtime,
        schema_version=request.schema_version,
        kind=request.kind,
    )


def mcscan_template_request() -> WorkflowRequest:
    """返回 WorkflowRequest(JSON 请求) 模板"""

    return workflow_template_request()


def validate_target_genes_in_reference(request: WorkflowRequest) -> None:
    """在请求阶段尽早发现目标基因与参考物种不匹配的问题"""

    target_gene_ids = request.parameters.local_synteny.target_gene_ids
    if not target_gene_ids:
        return
    if not (0 <= request.reference_index < len(request.species)):
        return

    reference_input = request.species[request.reference_index]
    if reference_input.input_mode != "bed_cds" or not reference_input.bed:
        return

    from pathlib import Path

    bed_path = Path(reference_input.bed).expanduser().resolve(strict=False)
    if not bed_path.is_file():
        return

    accns: set[str] = set()
    with bed_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) >= 4:
                accns.add(parts[3].strip())
    if not any(gene.strip() in accns for gene in target_gene_ids):
        raise InputValidationError(f"目标基因不属于参考物种 {reference_input.name}：{', '.join(target_gene_ids)}")
