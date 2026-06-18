"""GenomeLens 分析请求层

把外部输入（JSON、CLI 参数）规范化成统一的 `AnalysisRequest` 模型。
"""

# region import
from genomelens.analysis.requests.loader import load_analysis_request, write_analysis_request
from genomelens.analysis.requests.models import (
    AnalysisConfigRef,
    AnalysisInput,
    AnalysisOptions,
    AnalysisOutput,
    AnalysisRequest,
    AnalysisSpeciesInput,
    McscanMethodConfig,
)
from genomelens.analysis.requests.normalizer import (
    discover_species_from_directory,
    mcscan_auto_request_from_cli,
    mcscan_template_request,
    normalize_analysis_request,
    read_request_config,
)
from genomelens.analysis.requests.schema import ANALYSIS_REQUEST_JSON_SCHEMA

# endregion

__all__ = [
    "AnalysisConfigRef",
    "AnalysisInput",
    "AnalysisOptions",
    "AnalysisOutput",
    "AnalysisRequest",
    "AnalysisSpeciesInput",
    "McscanMethodConfig",
    "ANALYSIS_REQUEST_JSON_SCHEMA",
    "load_analysis_request",
    "write_analysis_request",
    "discover_species_from_directory",
    "read_request_config",
    "mcscan_auto_request_from_cli",
    "normalize_analysis_request",
    "mcscan_template_request",
]
