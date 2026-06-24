"""Artifact contract models shared by CLI, GUI and integrations."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ArtifactRecord:
    """ArtifactRecord(产物记录)：供报告、GUI 和后续评分模块统一读取"""

    # fmt: off
    artifact_id: str       # 产物在报告与 GUI 中的唯一键
    artifact_type: str     # 产物类型（figure/table/log 等）
    path: str              # 产物文件路径
    produced_by: str       # 产生该产物的 workflow 或子模块
    owner_task: str = ""    # 拥有该产物的任务 ID
    format: str = ""       # 文件格式后缀（如 svg、tsv）
    preview: bool = False  # 是否推荐在 GUI 中预览
    input_refs: list[str] = field(default_factory=list)        # 上游输入产物引用
    provenance: dict[str, object] = field(default_factory=dict) # 产物来源追踪
    metadata: dict[str, object] = field(default_factory=dict)  # 产物额外元数据
    # fmt: on

    def to_json(self) -> dict[str, object]:
        """转成稳定 JSON(结构化数据)"""

        return {
            "artifact_id": self.artifact_id,
            "artifact_type": self.artifact_type,
            "path": self.path,
            "produced_by": self.produced_by,
            "owner_task": self.owner_task,
            "format": self.format,
            "preview": self.preview,
            "input_refs": self.input_refs,
            "provenance": self.provenance,
            "metadata": self.metadata,
        }
