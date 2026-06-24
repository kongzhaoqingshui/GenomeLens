"""平台执行请求的输入预处理入口"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from genomelens.analysis.planning.models import SyntenyExecutionRequest
from genomelens.contracts.species import GenomeInputSpec, PreparedGenomeInputSpec
from genomelens.preprocessing.annotation import preprocess_one, write_preprocessing_summary

if TYPE_CHECKING:
    from genomelens.data.workspace.output_layout import OutputLayout


def prepare_inputs(
    set_state: Callable[[Any], None],
    request: SyntenyExecutionRequest,
    layout: OutputLayout,
    *,
    preprocessing_state: Any | None = None,
) -> tuple[PreparedGenomeInputSpec, PreparedGenomeInputSpec, list[dict[str, object]]]:
    """预处理 raw 输入或返回已准备好的 BED/CDS 输入"""

    def prepare_one(species: GenomeInputSpec) -> tuple[PreparedGenomeInputSpec, dict[str, object] | None]:
        if species.prepared:
            return species.prepared, None

        raw = species.raw
        if raw is None:
            raise RuntimeError(f"{species.name} input was expected but missing")

        result = preprocess_one(species.name, raw.gff, raw.genome, layout.prepared)
        return PreparedGenomeInputSpec(result.bed, result.cds), result.summary

    if preprocessing_state is not None and (request.query.raw or request.subject.raw):
        set_state(preprocessing_state)

    query, query_summary = prepare_one(request.query)
    subject, subject_summary = prepare_one(request.subject)

    summaries = [summary for summary in [query_summary, subject_summary] if summary is not None]
    if summaries:
        write_preprocessing_summary(layout.preprocessing_summary, summaries)

    return query, subject, summaries
