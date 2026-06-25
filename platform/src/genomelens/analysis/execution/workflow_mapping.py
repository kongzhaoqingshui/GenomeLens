"""WorkflowRequest 到内部 synteny 执行请求的映射(mapping)"""

# region import
from __future__ import annotations

from pathlib import Path

from genomelens.analysis.planning.models import (
    PairwiseArtifactInputs,
    SyntenyExecutionRequest,
)
from genomelens.analysis.requests.models import WorkflowRequest, WorkflowSpeciesInput
from genomelens.analysis.requests.normalization.request_assembler import read_request_config
from genomelens.app.errors import messages
from genomelens.app.errors.exceptions import InputValidationError
from genomelens.artifacts.bundles import ArtifactBundle, pairwise_core_bundle_from_paths
from genomelens.contracts.species import GenomeInputSpec, PreparedGenomeInputSpec, RawAnnotationInputSpec

# endregion


def _configured(value: str, fallback: str) -> str:
    """在显式值与回退值(fallback)之间选择非空字符串"""

    return value if str(value).strip() else fallback


def _path(value: str) -> Path:
    """把字符串解析为已展开用户目录的 Path(路径)"""

    return Path(value).expanduser().resolve(strict=False)


def _optional_path(value: object) -> Path | None:
    """把可选端口值解析为 Path(路径)，空值时返回 None"""

    if not isinstance(value, str) or not value.strip():
        return None
    return _path(value)


def _input_ports(request: WorkflowRequest) -> dict[str, object]:
    """读取子模块输入端口字典(ports)"""

    raw = request.inputs.get("ports")
    return dict(raw) if isinstance(raw, dict) else {}


def _target_gene_ids(request: WorkflowRequest, ports: dict[str, object]) -> list[str]:
    """合并显式参数与 `target_genes` 端口中的目标基因列表(gene list)"""

    if request.parameters.local_synteny.target_gene_ids:
        return list(request.parameters.local_synteny.target_gene_ids)
    raw = ports.get("target_genes")
    if isinstance(raw, list):
        return [str(item).strip() for item in raw if str(item).strip()]
    if isinstance(raw, str) and raw.strip():
        return [raw.strip()]
    return []


def _pairwise_artifacts_from_ports(ports: dict[str, object]) -> PairwiseArtifactInputs | None:
    """把子模块 artifact 端口转换为内部的 pairwise 产物载荷(若无可复用产物则返回 None)"""

    artifacts = PairwiseArtifactInputs(
        blast_table=_optional_path(ports.get("blast_table")),
        anchors=_optional_path(ports.get("anchors")),
        simple=_optional_path(ports.get("simple")),
        blocks=_optional_path(ports.get("blocks")),
        merged_bed=_optional_path(ports.get("merged_bed")),
        layout=_optional_path(ports.get("layout")),
    )
    return artifacts if artifacts.has_any else None


def _artifact_bundles_from_ports(ports: dict[str, object]) -> list[ArtifactBundle]:
    """从子模块端口构建可复用的 artifact bundle(产物包)列表"""

    artifacts = _pairwise_artifacts_from_ports(ports)
    if artifacts is None:
        return []
    return [pairwise_core_bundle_from_paths(artifacts.to_path_dict())]


def species_to_genome_input(species: WorkflowSpeciesInput) -> GenomeInputSpec:
    """把 WorkflowSpeciesInput 转成内部 GenomeInputSpec(基因组输入规范)"""

    if species.input_mode == "bed_cds":
        return GenomeInputSpec(
            name=species.name,
            prepared=PreparedGenomeInputSpec(_path(species.bed), _path(species.cds)),
        )
    if species.input_mode == "gff_genome":
        return GenomeInputSpec(
            name=species.name,
            raw=RawAnnotationInputSpec(_path(species.gff), _path(species.genome)),
        )
    raise ValueError(f"不支持的物种输入模式：{species.input_mode}")


def _toolchain_paths(request: WorkflowRequest) -> dict[str, str]:
    """合并显式 runtime 与配置文件中的工具链路径(toolchain paths)"""

    config = read_request_config(request)
    toolchain = config.toolchain if config else None
    runtime = request.runtime
    return {
        "engine_path": _configured(runtime.jcvi_engine, toolchain.jcvi_engine_path if toolchain else ""),
        "blastn_path": _configured(runtime.blastn, toolchain.blastn_path if toolchain else ""),
        "makeblastdb_path": _configured(runtime.makeblastdb, toolchain.makeblastdb_path if toolchain else ""),
        "lastal_path": _configured(runtime.lastal, toolchain.lastal_path if toolchain else ""),
        "lastdb_path": _configured(runtime.lastdb, toolchain.lastdb_path if toolchain else ""),
    }


def build_synteny_request(
    request: WorkflowRequest,
    *,
    reference: GenomeInputSpec,
    target: GenomeInputSpec,
    additional_species: list[GenomeInputSpec] | None = None,
    outdir: Path,
    engine_workflow: str,
    force: bool,
) -> SyntenyExecutionRequest:
    """构建单个 synteny pair 的内部执行请求"""

    runtime = request.runtime
    params = request.parameters
    toolchain = _toolchain_paths(request)
    ports = _input_ports(request)
    target_gene_ids = _target_gene_ids(request, ports)
    precomputed_artifacts = _pairwise_artifacts_from_ports(ports)
    return SyntenyExecutionRequest(
        reference=reference,
        target=target,
        additional_species=list(additional_species or []),
        outdir=outdir,
        threads=int(runtime.threads if runtime.threads is not None else 4),
        min_block_size=int(request.parameters.synteny.min_block_size),
        formats=request.output.formats,
        force=force,
        engine_workflow=engine_workflow,
        log_level=str(runtime.log_level or "INFO").upper(),
        verbose=bool(runtime.verbose),
        console_log=bool(runtime.console_log),
        precomputed_artifacts=precomputed_artifacts,
        artifact_bundles=_artifact_bundles_from_ports(ports),
        input_ports=ports,
        align_soft=params.synteny.align_soft,
        dbtype=params.synteny.dbtype,
        cscore=params.synteny.cscore,
        dist=params.synteny.dist,
        iter=params.synteny.iter,
        allow_simplified_fallback=params.synteny.allow_simplified_fallback,
        target_gene_ids=target_gene_ids,
        up=params.local_synteny.up,
        down=params.local_synteny.down,
        split_targets=params.local_synteny.split_targets,
        label_targets=params.local_synteny.label_targets,
        glyphstyle=params.plot.glyphstyle,
        glyphcolor=params.plot.glyphcolor,
        shadestyle=params.plot.shadestyle,
        figsize=params.plot.figsize,
        dpi=params.plot.dpi,
        auto_optimization=dict(params.plot.auto_optimization),
        use_native_local_synteny_renderer=params.local_synteny.use_native_renderer,
        layout_path=str(_optional_path(ports.get("layout") or ports.get("karyotype_layout")) or ""),
        seqids_path=str(_optional_path(ports.get("karyotype_seqids")) or ""),
        **toolchain,
    )


def to_mcscan_request(request: WorkflowRequest) -> SyntenyExecutionRequest:
    """Build the primary pairwise synteny request for a two-species workflow
    (为双物种工作流构建主 pairwise synteny 请求)
    """

    species = validate_workflow_species(request)
    reference = species[request.reference_index]
    target = next((item for index, item in enumerate(species) if index != request.reference_index), None)
    if target is None:
        raise InputValidationError(messages.REQUEST_TOO_FEW_SPECIES)
    engine_workflow = "local_synteny" if request.is_local_synteny else "graphics_synteny"
    return build_synteny_request(
        request,
        reference=reference,
        target=target,
        outdir=_path(request.output.directory),
        engine_workflow=engine_workflow,
        force=bool(request.output.force),
    )


def validate_workflow_species(request: WorkflowRequest) -> list[GenomeInputSpec]:
    """校验并转换 species[](物种列表)"""

    species = [species_to_genome_input(item) for item in request.species]
    if len(species) < 2 and request.workflow_id == "synteny":
        raise InputValidationError(messages.REQUEST_TOO_FEW_SPECIES)
    if not (0 <= request.reference_index < len(species)) and species:
        raise InputValidationError(messages.REQUEST_REFERENCE_INDEX_OUT_OF_RANGE.format(index=request.reference_index))
    return species


__all__ = [
    "build_synteny_request",
    "species_to_genome_input",
    "to_mcscan_request",
    "validate_workflow_species",
]
