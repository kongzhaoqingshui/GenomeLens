"""MCscan 方法专属的 RunSummary 扩展字段"""

# region import
from __future__ import annotations

from dataclasses import dataclass, field

from genomelens.core.json_utils import _optional_int
from genomelens.core.summary_models import PairwiseJobSummary

# endregion


@dataclass(frozen=True)
class McscanSummaryExtension:
    """McscanSummaryExtension：承载 RunSummary 中所有 JCVI/MCscan 专属字段

    这些字段不再直接挂在 `RunSummary` 上，而是通过 `method_data` 注入，
    使顶层摘要保持方法无关，同时通过 `to_dict()` 扁平展开保持 JSON 兼容。
    """

    # fmt: off
    # 引擎元数据
    jcvi_backend: str = ""           # 引擎后端标识
    jcvi_workflow: str = ""          # 实际运行的 JCVI workflow 名称
    jcvi_engine_path: str = ""       # 引擎可执行文件路径
    jcvi_distribution: str = ""      # 引擎分发方式（source/wheel 等）
    jcvi_engine_version: str = ""    # 引擎版本
    jcvi_upstream_version: str = ""  # 上游 JCVI 版本
    jcvi_patchset: str = ""          # 当前 patchset 标识
    jcvi_runtime_mode: str = ""      # 引擎运行模式（core/accelerated）
    jcvi_loaded_extensions: list[str] = field(default_factory=list)   # 已加载扩展
    jcvi_missing_extensions: list[str] = field(default_factory=list)  # 缺失扩展

    # 通用产物字段
    engine_summary_path: str = ""  # 引擎 summary JSON 路径
    blast_table: str = ""          # BLAST 比对表路径
    anchors_path: str = ""         # 共线性锚点文件路径
    simple_path: str = ""          # 简化共线性边文件路径
    blocks_path: str = ""          # 共线性 blocks 文件路径
    query_bed: str = ""            # query 物种 BED 路径
    subject_bed: str = ""          # subject 物种 BED 路径
    preprocess_summaries: list[dict[str, object]] = field(default_factory=list)  # 预处理摘要列表
    preprocessing_summary_path: str = ""  # 预处理汇总文件路径
    simplified_fallback: bool = False     # 是否使用了简化回退路径

    # pairwise 特有字段
    species_a_name: str | None = None        # 第一物种名称
    species_b_name: str | None = None        # 第二物种名称
    species_a_input_mode: str | None = None  # 第一物种输入模式
    species_b_input_mode: str | None = None  # 第二物种输入模式
    species_a_bed: str | None = None         # 第一物种 BED 路径
    species_b_bed: str | None = None         # 第二物种 BED 路径

    # multi-species / reference-vs-targets 特有字段
    species_count: int | None = None     # 物种总数
    pairing_strategy: str | None = None  # 配对策略（all_vs_all_pairwise/reference_vs_targets）
    pairwise_jobs: list[PairwiseJobSummary] | None = None  # 各 pairwise 子任务摘要
    pairwise_job_count: int | None = None    # 子任务数量（序列化时自动计算）
    global_figures: list[str] | None = None  # 全局多物种图件路径
    multi_species_local_figures: list[str] | None = None  # 多物种局部共线性图件路径
    reference_name: str | None = None  # reference_vs_targets 中的参考物种名

    # 原生多物种标记；当前 MCscan 只走 pairwise 聚合，因此默认 False
    native_multi_species: bool = False  # 是否由引擎原生支持多物种
    native_edges: list[dict[str, object]] | None = None  # 原生多物种边数据
    native_layout: dict[str, object] | None = None       # 原生多物种布局数据
    # fmt: on

    def to_dict(self) -> dict[str, object]:
        """转成可合并进 RunSummary.method_data 的字典"""

        data: dict[str, object] = {}

        engine_meta_keys = (
            "jcvi_backend",
            "jcvi_workflow",
            "jcvi_engine_path",
            "jcvi_distribution",
            "jcvi_engine_version",
            "jcvi_upstream_version",
            "jcvi_patchset",
            "jcvi_runtime_mode",
        )
        has_engine_meta = any(getattr(self, key) for key in engine_meta_keys)

        # 引擎元数据：只在有值时输出，避免空字符串污染 summary
        for key in engine_meta_keys:
            value = getattr(self, key)
            if value:
                data[key] = value

        # extension 状态和 runtime 元数据一起出现，读取方更容易当成一组处理
        if has_engine_meta:
            data["jcvi_loaded_extensions"] = list(self.jcvi_loaded_extensions)
            data["jcvi_missing_extensions"] = list(self.jcvi_missing_extensions)
            data["simplified_fallback"] = self.simplified_fallback
        # 通用产物字段
        for key in (
            "engine_summary_path",
            "blast_table",
            "anchors_path",
            "simple_path",
            "blocks_path",
            "query_bed",
            "subject_bed",
            "preprocessing_summary_path",
        ):
            value = getattr(self, key)
            if value:
                data[key] = value

        if self.preprocess_summaries:
            data["preprocess_summaries"] = list(self.preprocess_summaries)
        if self.simplified_fallback:
            data["simplified_fallback"] = self.simplified_fallback

        # pairwise 特有
        for key in (
            "species_a_name",
            "species_b_name",
            "species_a_input_mode",
            "species_b_input_mode",
            "species_a_bed",
            "species_b_bed",
        ):
            value = getattr(self, key)
            if value is not None:
                data[key] = value

        # multi / reference-vs-targets 特有
        if self.species_count is not None:
            data["species_count"] = self.species_count
        if self.pairing_strategy is not None:
            data["pairing_strategy"] = self.pairing_strategy
        if self.pairwise_jobs is not None:
            data["pairwise_jobs"] = [job.to_json() for job in self.pairwise_jobs]
            data["pairwise_job_count"] = len(self.pairwise_jobs)
        if self.global_figures is not None:
            data["global_figures"] = list(self.global_figures)
        if self.multi_species_local_figures is not None:
            data["multi_species_local_figures"] = list(self.multi_species_local_figures)
        if self.reference_name is not None:
            data["reference_name"] = self.reference_name

        # 原生多物种扩展字段；当前 MCscan 默认 False，为后续引擎预留
        data["native_multi_species"] = self.native_multi_species
        if self.native_edges is not None:
            data["native_edges"] = list(self.native_edges)
        if self.native_layout is not None:
            data["native_layout"] = dict(self.native_layout)

        return data

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> McscanSummaryExtension:
        """从 RunSummary.method_data 的原始字典还原"""

        raw_jobs = data.get("pairwise_jobs")
        pairwise_jobs: list[PairwiseJobSummary] | None = None
        if isinstance(raw_jobs, list):
            pairwise_jobs = [PairwiseJobSummary.from_json(item) for item in raw_jobs if isinstance(item, dict)]

        def _str_list(value: object) -> list[str]:
            if isinstance(value, list):
                return [str(item) for item in value]
            return []

        def _dict_list(value: object) -> list[dict[str, object]]:
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
            return []

        def _dict(value: object) -> dict[str, object]:
            if isinstance(value, dict):
                return value
            return {}

        return cls(
            jcvi_backend=str(data.get("jcvi_backend") or ""),
            jcvi_workflow=str(data.get("jcvi_workflow") or ""),
            jcvi_engine_path=str(data.get("jcvi_engine_path") or ""),
            jcvi_distribution=str(data.get("jcvi_distribution") or ""),
            jcvi_engine_version=str(data.get("jcvi_engine_version") or ""),
            jcvi_upstream_version=str(data.get("jcvi_upstream_version") or ""),
            jcvi_patchset=str(data.get("jcvi_patchset") or ""),
            jcvi_runtime_mode=str(data.get("jcvi_runtime_mode") or ""),
            jcvi_loaded_extensions=_str_list(data.get("jcvi_loaded_extensions")),
            jcvi_missing_extensions=_str_list(data.get("jcvi_missing_extensions")),
            engine_summary_path=str(data.get("engine_summary_path") or ""),
            blast_table=str(data.get("blast_table") or ""),
            anchors_path=str(data.get("anchors_path") or ""),
            simple_path=str(data.get("simple_path") or ""),
            blocks_path=str(data.get("blocks_path") or ""),
            query_bed=str(data.get("query_bed") or ""),
            subject_bed=str(data.get("subject_bed") or ""),
            preprocess_summaries=_dict_list(data.get("preprocess_summaries")),
            preprocessing_summary_path=str(data.get("preprocessing_summary_path") or ""),
            simplified_fallback=bool(data.get("simplified_fallback")),
            species_a_name=str(data["species_a_name"]) if "species_a_name" in data else None,
            species_b_name=str(data["species_b_name"]) if "species_b_name" in data else None,
            species_a_input_mode=str(data["species_a_input_mode"]) if "species_a_input_mode" in data else None,
            species_b_input_mode=str(data["species_b_input_mode"]) if "species_b_input_mode" in data else None,
            species_a_bed=str(data["species_a_bed"]) if "species_a_bed" in data else None,
            species_b_bed=str(data["species_b_bed"]) if "species_b_bed" in data else None,
            species_count=_optional_int(data.get("species_count")),
            pairing_strategy=str(data["pairing_strategy"]) if "pairing_strategy" in data else None,
            pairwise_jobs=pairwise_jobs,
            global_figures=_str_list(data.get("global_figures")),
            multi_species_local_figures=_str_list(data.get("multi_species_local_figures")),
            reference_name=str(data["reference_name"]) if "reference_name" in data else None,
            native_multi_species=bool(data.get("native_multi_species", False)),
            native_edges=_dict_list(data.get("native_edges")),
            native_layout=_dict(data.get("native_layout")),
        )


__all__ = ["McscanSummaryExtension"]
