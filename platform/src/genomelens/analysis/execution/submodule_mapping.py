"""SubmoduleRequest 到内部执行请求的映射(mapping)"""

# region import
from __future__ import annotations

from pathlib import Path

from genomelens.analysis.execution.workflow_mapping import species_to_genome_input
from genomelens.analysis.planning.models import (
    HeatmapExecutionRequest,
    HistogramExecutionRequest,
    PairwiseArtifactInputs,
    SyntenyExecutionRequest,
)
from genomelens.analysis.requests.normalization.input_resolver import discover_species_from_directory
from genomelens.analysis.requests.submodule_models import SubmoduleRequest
from genomelens.app.errors.exceptions import InputValidationError
from genomelens.artifacts.bundles import ArtifactBundle, pairwise_core_bundle_from_paths
from genomelens.contracts.species import GenomeInputSpec, PreparedGenomeInputSpec, RawAnnotationInputSpec

# endregion


def _path(value: str) -> Path:
    """把字符串解析为已展开用户目录的 Path(路径)"""

    return Path(value).expanduser().resolve(strict=False)


def _optional_path(value: object) -> Path | None:
    """把可选端口值解析为 Path(路径)，空值时返回 None"""

    if not isinstance(value, str) or not value.strip():
        return None
    return _path(value)


def _str_param(parameters: dict[str, object], key: str, default: str = "") -> str:
    """安全读取字符串参数(按 key 取值，空值返回 default)"""

    value = parameters.get(key)
    if value is None:
        return default
    return str(value).strip()


def _int_param(parameters: dict[str, object], key: str, default: int) -> int:
    """安全读取整数参数(按 key 取值，空值返回 default)"""

    value = parameters.get(key, default)
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return default
    return default


def _float_param(parameters: dict[str, object], key: str, default: float) -> float:
    """安全读取浮点参数(按 key 取值，空值返回 default)"""

    value = parameters.get(key, default)
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return default
    return default


def _bool_param(parameters: dict[str, object], key: str, default: bool = False) -> bool:
    """安全读取布尔参数(按 key 取值，空值返回 default)"""

    value = parameters.get(key, default)
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    return bool(value)


def _str_list_param(parameters: dict[str, object], key: str) -> list[str]:
    """安全读取字符串列表参数(按 key 取值，非列表时返回空列表)"""

    value = parameters.get(key)
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _int_list_param(parameters: dict[str, object], key: str, default: list[int]) -> list[int]:
    """安全读取整数列表参数(按 key 取值，非列表时返回 default 副本)"""

    value = parameters.get(key)
    if not isinstance(value, list):
        return list(default)
    result: list[int] = []
    for item in value:
        try:
            result.append(int(item))
        except (TypeError, ValueError):
            continue
    return result if result else list(default)


def _pairwise_artifacts_from_ports(ports: dict[str, object]) -> PairwiseArtifactInputs | None:
    """把子模块 artifact 端口转换为内部的 pairwise 产物载荷(若无可复用产物则返回 None)"""

    artifacts = PairwiseArtifactInputs(
        blast_table=_optional_path(ports.get("blast_table")),
        anchors=_optional_path(ports.get("anchors")),
        simple=_optional_path(ports.get("simple")),
        blocks=_optional_path(ports.get("blocks")),
        merged_bed=_optional_path(ports.get("merged_bed")),
        layout=_optional_path(ports.get("layout") or ports.get("karyotype_layout")),
    )
    return artifacts if artifacts.has_any else None


def _artifact_bundles_from_ports(ports: dict[str, object]) -> list[ArtifactBundle]:
    """从子模块端口构建可复用的 artifact bundle(产物包)列表"""

    artifacts = _pairwise_artifacts_from_ports(ports)
    if artifacts is None:
        return []
    return [pairwise_core_bundle_from_paths(artifacts.to_path_dict())]


def _target_gene_ids(ports: dict[str, object], parameters: dict[str, object]) -> list[str]:
    """合并端口与参数中的目标基因列表(去重并过滤空值)"""

    raw = ports.get("target_genes") or parameters.get("target_genes")
    if isinstance(raw, list):
        return [str(item).strip() for item in raw if str(item).strip()]
    if isinstance(raw, str) and raw.strip():
        return [raw.strip()]
    return []


def _parse_species_pair(value: object) -> tuple[GenomeInputSpec, GenomeInputSpec]:
    """从 species_pair 端口解析出两个物种的 GenomeInputSpec(基因组输入规范)"""

    if isinstance(value, dict):
        reference = _species_from_dict(value.get("reference") or value.get("ref") or {})
        target = _species_from_dict(value.get("target") or value.get("subject") or {})
        if reference and target:
            return reference, target
        raise InputValidationError("species_pair 字典必须包含 reference 与 target 两个物种")

    if isinstance(value, str) and value.strip():
        directory = Path(value).expanduser().resolve(strict=False)
        if directory.is_dir():
            species = discover_species_from_directory(str(directory))
            if len(species) < 2:
                raise InputValidationError(f"目录中至少要有两个物种：{directory}")
            return species_to_genome_input(species[0]), species_to_genome_input(species[1])
        raise InputValidationError(f"species_pair 路径不是目录：{directory}")

    raise InputValidationError("species_pair 必须是目录路径或包含 reference/target 的字典")


def _species_from_dict(data: object) -> GenomeInputSpec | None:
    """从字典构造 GenomeInputSpec(基因组输入规范)"""

    if not isinstance(data, dict):
        return None
    name = str(data.get("name") or "").strip()
    bed = str(data.get("bed") or "").strip()
    cds = str(data.get("cds") or "").strip()
    gff = str(data.get("gff") or "").strip()
    genome = str(data.get("genome") or "").strip()

    if not name:
        return None
    if bed and cds:
        return GenomeInputSpec(name=name, prepared=PreparedGenomeInputSpec(_path(bed), _path(cds)))
    if gff and genome:
        return GenomeInputSpec(name=name, raw=RawAnnotationInputSpec(_path(gff), _path(genome)))
    return None


def _auto_optimization(parameters: dict[str, object]) -> dict[str, bool]:
    """读取自动优化参数(返回 optimize_figsize / rewrite_layout_links / optimize_karyotype_labels 字典)"""

    return {
        "optimize_figsize": _bool_param(parameters, "optimize_figsize"),
        "rewrite_layout_links": _bool_param(parameters, "rewrite_layout_links"),
        "optimize_karyotype_labels": _bool_param(parameters, "optimize_karyotype_labels"),
    }


def to_histogram_request(request: SubmoduleRequest) -> HistogramExecutionRequest:
    """把 graphics_histogram 子模块请求转为内部 HistogramExecutionRequest(直方图执行请求)"""

    ports = request.inputs
    parameters = request.parameters
    numeric_files = ports.get("numeric_files")
    inputs: list[Path]
    if isinstance(numeric_files, list):
        inputs = [_path(str(item)) for item in numeric_files]
    elif isinstance(numeric_files, str):
        inputs = [_path(numeric_files)]
    else:
        inputs = []
    if not inputs:
        raise InputValidationError("graphics_histogram 需要 numeric_files 输入端口")

    # 兼容 SubmoduleRequest 中不带 histogram_ 前缀的键(key)
    prefix_keys = {
        "histogram_columns": "columns",
        "histogram_skip": "skip",
        "histogram_bins": "bins",
        "histogram_vmin": "vmin",
        "histogram_vmax": "vmax",
        "histogram_xlabel": "xlabel",
        "histogram_title": "title",
        "histogram_base": "base",
        "histogram_facet": "facet",
        "histogram_fill": "fill",
    }
    normalized: dict[str, object] = dict(parameters)
    for prefixed, plain in prefix_keys.items():
        if prefixed in normalized and plain not in normalized:
            normalized[plain] = normalized[prefixed]

    columns = _int_list_param(normalized, "columns", [0])
    vmin_raw = normalized.get("vmin")
    vmax_raw = normalized.get("vmax")

    return HistogramExecutionRequest(
        inputs=inputs,
        outdir=_path(request.output.directory),
        columns=columns,
        formats=request.output.formats,
        engine_path=request.runtime.jcvi_engine,
        force=request.output.force,
        histogram_skip=_int_param(normalized, "skip", 0),
        histogram_bins=_int_param(normalized, "bins", 20),
        histogram_vmin=_float_param(normalized, "vmin", 0.0) if vmin_raw is not None else None,
        histogram_vmax=_float_param(normalized, "vmax", 0.0) if vmax_raw is not None else None,
        histogram_xlabel=_str_param(normalized, "xlabel", "value"),
        histogram_title=_str_param(normalized, "title", ""),
        histogram_base=_int_param(normalized, "base", 0),
        histogram_facet=_bool_param(normalized, "facet", False),
        histogram_fill=_str_param(normalized, "fill", "white"),
        dpi=_int_param(normalized, "dpi", 300),
        log_level=str(request.runtime.log_level or "INFO").upper(),
        verbose=request.runtime.verbose,
        console_log=request.runtime.console_log,
    )


def to_heatmap_request(request: SubmoduleRequest) -> HeatmapExecutionRequest:
    """把 graphics_heatmap 子模块请求转为内部 HeatmapExecutionRequest(热图执行请求)"""

    ports = request.inputs
    parameters = request.parameters
    matrix = _optional_path(ports.get("matrix_csv") or ports.get("matrix"))
    if matrix is None or not matrix.is_file():
        raise InputValidationError("graphics_heatmap 需要有效的 matrix_csv 输入端口")

    rowgroups = _optional_path(parameters.get("rowgroups") or ports.get("rowgroups"))
    if rowgroups is not None and not rowgroups.is_file():
        raise InputValidationError(f"行分组文件不存在：{rowgroups}")

    return HeatmapExecutionRequest(
        matrix=matrix,
        outdir=_path(request.output.directory),
        formats=request.output.formats,
        engine_path=request.runtime.jcvi_engine,
        figsize=_str_param(parameters, "figsize"),
        dpi=_int_param(parameters, "dpi", 300),
        cmap=_str_param(parameters, "cmap"),
        groups=_bool_param(parameters, "groups", False),
        rowgroups=rowgroups,
        horizontalbar=_bool_param(parameters, "horizontalbar", False),
        force=request.output.force,
        log_level=str(request.runtime.log_level or "INFO").upper(),
    )


def to_synteny_like_request(request: SubmoduleRequest, engine_workflow: str) -> SyntenyExecutionRequest:
    """把 synteny-like 子模块请求转为内部 SyntenyExecutionRequest(共线性执行请求)"""

    ports = request.inputs
    parameters = request.parameters
    reference, target = _parse_species_pair(ports.get("species_pair"))
    outdir = _path(request.output.directory)
    precomputed_artifacts = _pairwise_artifacts_from_ports(ports)
    target_gene_ids = _target_gene_ids(ports, parameters)

    return SyntenyExecutionRequest(
        reference=reference,
        target=target,
        outdir=outdir,
        threads=request.runtime.threads or 4,
        min_block_size=_int_param(parameters, "min_block_size", 5),
        formats=request.output.formats,
        force=request.output.force,
        engine_workflow=engine_workflow,
        log_level=str(request.runtime.log_level or "INFO").upper(),
        verbose=request.runtime.verbose,
        console_log=request.runtime.console_log,
        precomputed_artifacts=precomputed_artifacts,
        artifact_bundles=_artifact_bundles_from_ports(ports),
        input_ports=dict(ports),
        align_soft=_str_param(parameters, "align_soft", "blast"),
        dbtype=_str_param(parameters, "dbtype", "nucl"),
        emit_ortholog=_bool_param(parameters, "emit_ortholog", False),
        cscore=_float_param(parameters, "cscore", 0.7),
        dist=_int_param(parameters, "dist", 20),
        iter=_int_param(parameters, "iter", 1),
        target_gene_ids=target_gene_ids,
        up=_int_param(parameters, "up", 20),
        down=_int_param(parameters, "down", 20),
        split_targets=_bool_param(parameters, "split_targets", False),
        label_targets=_bool_param(parameters, "label_targets", False),
        glyphstyle=_str_param(parameters, "glyphstyle"),
        glyphcolor=_str_param(parameters, "glyphcolor"),
        shadestyle=_str_param(parameters, "shadestyle"),
        figsize=_str_param(parameters, "figsize"),
        dpi=_int_param(parameters, "dpi", 300),
        auto_optimization=_auto_optimization(parameters),
        use_native_local_synteny_renderer=_bool_param(parameters, "use_native_local_synteny_renderer", False),
        layout_path=str(_optional_path(ports.get("layout") or ports.get("karyotype_layout")) or ""),
        seqids_path=str(_optional_path(ports.get("karyotype_seqids")) or ""),
        engine_path=request.runtime.jcvi_engine,
        blastn_path=request.runtime.blastn,
        makeblastdb_path=request.runtime.makeblastdb,
        lastal_path=request.runtime.lastal,
        lastdb_path=request.runtime.lastdb,
    )


__all__ = [
    "to_histogram_request",
    "to_heatmap_request",
    "to_synteny_like_request",
]
