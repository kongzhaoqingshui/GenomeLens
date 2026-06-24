"""运行摘要数据模型"""

# region import
from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar

from genomelens.utils.json import (
    _any_list,
    _dict,
    _dict_list,
    _float,
    _int,
    _str,
    _str_dict,
    _str_list,
)

# endregion


@dataclass(frozen=True)
class ChildRunRecord:
    """ChildRunRecord(子任务记录)：复合工作流中的单个执行步骤结果"""

    # fmt: off
    pair_id: str         # 子任务唯一标识（如 query__subject）
    species_a_name: str  # 配对中的第一物种名称
    species_b_name: str  # 配对中的第二物种名称
    status: str          # 该配对子任务的执行状态
    outdir: str          # 配对子任务的输出目录
    run_summary_path: str = ""     # 子任务 run_summary.json 路径
    engine_summary_path: str = ""  # 引擎返回的 summary 路径
    blast_table: str = ""          # BLAST 比对表路径
    anchors_path: str = ""         # 共线性锚点文件路径
    simple_path: str = ""          # 简化共线性边文件路径
    blocks_path: str = ""          # 共线性 blocks 文件路径
    query_bed: str = ""            # query 物种 BED 路径
    subject_bed: str = ""          # subject 物种 BED 路径
    final_figures: list[str] = field(default_factory=list)  # 该配对产出的图件路径列表
    error: dict[str, str] | None = None  # 失败时的错误类型与消息
    # fmt: on

    def to_json(self) -> dict[str, object]:
        """转为 JSON object(JSON 对象)"""

        data: dict[str, object] = {
            "child_id": self.pair_id,
            "pair_id": self.pair_id,
            "species_a_name": self.species_a_name,
            "species_b_name": self.species_b_name,
            "status": self.status,
            "outdir": self.outdir,
        }
        # pairwise 子任务的产物多少取决于工作流，因此按需序列化更利于阅读。
        if self.run_summary_path:
            data["run_summary_path"] = self.run_summary_path
        if self.engine_summary_path:
            data["engine_summary_path"] = self.engine_summary_path
        if self.blast_table:
            data["blast_table"] = self.blast_table
        if self.anchors_path:
            data["anchors_path"] = self.anchors_path
        if self.simple_path:
            data["simple_path"] = self.simple_path
        if self.blocks_path:
            data["blocks_path"] = self.blocks_path
        if self.query_bed:
            data["query_bed"] = self.query_bed
        if self.subject_bed:
            data["subject_bed"] = self.subject_bed
        if self.final_figures:
            data["final_figures"] = list(self.final_figures)
        if self.error is not None:
            data["error"] = dict(self.error)
        return data

    @classmethod
    def from_json(cls, data: dict[str, object]) -> ChildRunRecord:
        """从 JSON object(JSON 对象) 读取"""

        error = data.get("error")
        return cls(
            pair_id=_str(data.get("child_id") or data.get("pair_id")),
            species_a_name=_str(data.get("species_a_name")),
            species_b_name=_str(data.get("species_b_name")),
            status=_str(data.get("status")),
            outdir=_str(data.get("outdir")),
            run_summary_path=_str(data.get("run_summary_path")),
            engine_summary_path=_str(data.get("engine_summary_path")),
            blast_table=_str(data.get("blast_table")),
            anchors_path=_str(data.get("anchors_path")),
            simple_path=_str(data.get("simple_path")),
            blocks_path=_str(data.get("blocks_path")),
            query_bed=_str(data.get("query_bed")),
            subject_bed=_str(data.get("subject_bed")),
            final_figures=_str_list(data.get("final_figures")),
            error=_str_dict(error) if isinstance(error, dict) else None,
        )


@dataclass(frozen=True)
class UiBlock:
    """UiBlock(UI 块)：供 GUI/工作台读取的渲染契约"""

    # fmt: off
    state: str       # 工作流状态（SUCCEEDED/FAILED/RUNNING 等）
    progress: float  # 0~1 的进度值，供进度条渲染
    primary_figures: list[str]  # 需要优先展示的主要图件路径
    summary_path: str           # run_summary.json 路径
    log_path: str               # 运行日志路径
    # fmt: on

    def to_json(self) -> dict[str, object]:
        """转为 JSON object(JSON 对象)"""

        return {
            "state": self.state,
            "progress": self.progress,
            "primary_figures": list(self.primary_figures),
            "summary_path": self.summary_path,
            "log_path": self.log_path,
        }

    @classmethod
    def from_json(cls, data: dict[str, object]) -> UiBlock:
        """从 JSON object(JSON 对象) 读取"""

        return cls(
            state=_str(data.get("state")),
            progress=_float(data.get("progress"), default=0.0),
            primary_figures=_str_list(data.get("primary_figures")),
            summary_path=_str(data.get("summary_path")),
            log_path=_str(data.get("log_path")),
        )


@dataclass(frozen=True)
class ScoringBlock:
    """ScoringBlock(评分块)：未来 ML Scoring Layer 接入前的占位结构"""

    # fmt: off
    status: str = "not_run"  # 评分执行状态
    scores: list[object] = field(default_factory=list)   # 各维度评分结果
    ranking: list[object] = field(default_factory=list)  # 排序后的推荐列表
    message: str = "机器学习评分模块尚未接入当前工作流。"  # 面向用户的评分说明
    artifact_path: str = ""  # 评分产物文件路径
    model_version: str = ""  # 评分模型版本
    # fmt: on

    def to_json(self) -> dict[str, object]:
        """转为 JSON object(JSON 对象)"""

        return {
            "status": self.status,
            "scores": list(self.scores),
            "ranking": list(self.ranking),
            "message": self.message,
            "artifact_path": self.artifact_path,
            "model_version": self.model_version,
        }

    @classmethod
    def from_json(cls, data: dict[str, object]) -> ScoringBlock:
        """从 JSON object(JSON 对象) 读取"""

        return cls(
            status=_str(data.get("status"), default="not_run"),
            scores=_any_list(data.get("scores")),
            ranking=_any_list(data.get("ranking")),
            message=_str(data.get("message")),
            artifact_path=_str(data.get("artifact_path")),
            model_version=_str(data.get("model_version")),
        )


@dataclass(frozen=True)
class RunSummary:
    """RunSummary(运行摘要)：方法无关的顶层摘要壳

    方法专属字段全部下沉到 `extensions`，由具体方法扩展（如 McscanSummaryExtension）
    负责填充。schema v3 不再把扩展字段扁平展开，方便 artifact、GUI 和 Agent 稳定读取。
    """

    # fmt: off
    status: str                       # 整个分析任务的顶层状态
    schema_version: int               # 摘要 JSON schema 版本
    workflow: str                     # 实际运行的工作流/方法标识
    task: dict[str, object]           # 任务元数据（task_id、task_type 等）
    species: list[dict[str, object]]  # 参与分析的物种角色与名称列表
    final_figures: list[str]          # 最终产出的所有图件路径
    artifact_index: list[dict[str, object]]  # 结构化产物索引
    logs: dict[str, str]   # 各类日志文件路径
    ui: UiBlock            # 供 GUI 渲染的状态块
    scoring: ScoringBlock  # 评分结果块
    method: str = ""       # 方法名（如 mcscan）
    extensions: dict[str, object] = field(default_factory=dict)  # 方法专属扩展字段
    child_runs: list[ChildRunRecord] = field(default_factory=list)  # 复合任务子任务记录
    analysis_request_path: str = ""  # 实际执行的 WorkflowRequest 快照路径

    _KNOWN_TOP_KEYS: ClassVar[set[str]] = {
        "status",
        "schema_version",
        "workflow",
        "task",
        "species",
        "final_figures",
        "artifact_index",
        "logs",
        "ui",
        "scoring",
        "method",
        "extensions",
        "child_runs",
        "analysis_request_path",
    }
    # fmt: on

    def to_json(self) -> dict[str, object]:
        """转为 JSON object(JSON 对象)"""

        data: dict[str, object] = {
            "status": self.status,
            "schema_version": self.schema_version,
            "workflow": self.workflow,
            "task": dict(self.task),
            "species": list(self.species),
            "final_figures": list(self.final_figures),
            "artifact_index": list(self.artifact_index),
            "logs": dict(self.logs),
            "ui": self.ui.to_json(),
            "scoring": self.scoring.to_json(),
        }
        if self.method:
            data["method"] = self.method
        data["extensions"] = dict(self.extensions)
        if self.child_runs:
            data["child_runs"] = [item.to_json() for item in self.child_runs]
        if self.analysis_request_path:
            data["analysis_request_path"] = self.analysis_request_path
        return data

    @classmethod
    def from_json(cls, data: dict[str, object]) -> RunSummary:
        """从 JSON object(JSON 对象) 读取"""

        extensions = _dict(data.get("extensions"))
        child_runs = [ChildRunRecord.from_json(item) for item in _dict_list(data.get("child_runs"))]
        return cls(
            status=_str(data.get("status")),
            schema_version=_int(data.get("schema_version"), default=3),
            workflow=_str(data.get("workflow")),
            task=_dict(data.get("task")),
            species=_dict_list(data.get("species")),
            final_figures=_str_list(data.get("final_figures")),
            artifact_index=_dict_list(data.get("artifact_index")),
            logs=_str_dict(data.get("logs")),
            ui=UiBlock.from_json(_dict(data.get("ui"))),
            scoring=ScoringBlock.from_json(_dict(data.get("scoring"))),
            method=_str(data.get("method")),
            extensions=extensions,
            child_runs=child_runs,
            analysis_request_path=_str(data.get("analysis_request_path")),
        )
