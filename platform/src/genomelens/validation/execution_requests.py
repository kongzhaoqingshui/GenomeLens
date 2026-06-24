"""shell workflow(外壳工作流) 的输入与选项校验"""

# region import
from __future__ import annotations

from pathlib import Path

from genomelens.analysis.planning.models import HistogramExecutionRequest, SyntenyExecutionRequest
from genomelens.app.errors.exceptions import InputValidationError
from genomelens.engines.jcvi.command_mapping import SUPPORTED_WORKFLOWS, normalize_workflow
from genomelens.validation.files import require_existing_file
from genomelens.validation.genome_inputs import validate_genome_input

# endregion


def validate_request(request: SyntenyExecutionRequest) -> None:
    """校验完整 MCscan 请求"""

    species = request.species
    if len(species) < 2:
        raise InputValidationError("at least two species are required")

    names = [item.name for item in species]
    if len(set(names)) != len(names):
        raise InputValidationError("species names must be unique")

    for index, spec in enumerate(species, start=1):
        validate_genome_input(spec, f"species[{index}] {spec.name}")

    if request.threads < 1:
        raise InputValidationError("--threads must be >= 1")

    if request.min_block_size < 1:
        raise InputValidationError("--min-block-size must be >= 1")

    workflow = normalize_workflow(request.jcvi_workflow)
    if workflow not in SUPPORTED_WORKFLOWS:
        raise InputValidationError(f"unsupported JCVI workflow: {request.jcvi_workflow}")

    if workflow == "local_synteny" and not request.target_gene_ids:
        raise InputValidationError("local_synteny workflow requires --target-genes")

    if request.allow_simplified_fallback:
        raise InputValidationError("allow_simplified_fallback is not implemented for production JCVI workflows")

    for optional_path, label in [(request.jcvi_layout, "layout"), (request.jcvi_seqids, "seqids")]:
        if optional_path and not Path(optional_path).expanduser().is_file():
            raise InputValidationError(f"{label} path does not exist: {optional_path}")

    # 显式工具路径一旦给出，就要求其真实可用；否则后面 locator 的报错会更绕
    for optional_path, label in [(request.blastn_path, "blastn"), (request.makeblastdb_path, "makeblastdb")]:
        if optional_path and not Path(optional_path).expanduser().is_file():
            raise InputValidationError(f"{label} path does not exist: {optional_path}")


def validate_histogram_request(request: HistogramExecutionRequest) -> None:
    """校验 plot-only histogram(纯绘图直方图) 请求"""

    if not request.inputs:
        raise InputValidationError("graphics_histogram requires at least one input file")

    for path in request.inputs:
        require_existing_file(path, "histogram input")

    if not request.columns:
        raise InputValidationError("graphics_histogram requires at least one column index")

    if any(index < 0 for index in request.columns):
        raise InputValidationError("histogram column indices must be >= 0")

    if request.histogram_skip < 0:
        raise InputValidationError("histogram skip must be >= 0")

    if request.histogram_bins < 1:
        raise InputValidationError("histogram bins must be >= 1")

    if request.histogram_base not in {0, 2, 10}:
        raise InputValidationError("histogram base must be one of 0, 2, 10")

    if request.histogram_vmin is not None and request.histogram_vmax is not None:
        if request.histogram_vmin >= request.histogram_vmax:
            raise InputValidationError("histogram vmin must be smaller than vmax")
