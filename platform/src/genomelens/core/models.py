"""shell(外壳) 侧分析请求的核心 dataclasses(数据类)"""

# region import
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

# endregion


@dataclass(frozen=True)
class RawAnnotationInputSpec:
    """RawAnnotationInputSpec(原始注释输入)：GFF/GTF 加 genome FASTA(基因组序列)"""

    # fmt: off
    gff: Path     # GFF/GTF 注释文件路径
    genome: Path  # 基因组 FASTA 序列路径
    # fmt: on


@dataclass(frozen=True)
class PreparedGenomeInputSpec:
    """PreparedGenomeInputSpec(标准输入)：BED 加 CDS FASTA"""

    # fmt: off
    bed: Path  # BED 格式注释文件路径
    cds: Path  # CDS FASTA 序列路径
    # fmt: on


@dataclass(frozen=True)
class GenomeInputSpec:
    """GenomeInputSpec(基因组输入)：比较中的一个具名物种侧"""

    # fmt: off
    name: str  # 物种公开名称（用于图件、报告与配对标识）
    prepared: PreparedGenomeInputSpec | None = None  # 已预处理的标准输入
    raw: RawAnnotationInputSpec | None = None        # 原始注释输入，与 prepared 互斥

    @property
    # fmt: on

    def mode(self) -> str:
        """返回公开输入模式名称"""

        # prepared/raw 是当前两种互斥入口，mode 属性负责把内部状态折叠成稳定字符串
        if self.prepared:
            return "bed_cds"
        if self.raw:
            return "gff_genome"
        return "unknown"


@dataclass(frozen=True)
class AnalysisTaskSpec:
    """AnalysisTaskSpec(分析任务规格)：面向平台核心的稳定任务描述"""

    # fmt: off
    task_id: str    # 跨层稳定的任务标识（通常由物种名与 workflow 拼接）
    task_type: str  # 面向顶层摘要的任务类型（如 pairwise_synteny）
    workflow: str   # 底层 engine workflow 名称
    species: list[GenomeInputSpec]    # 当前任务涉及的物种列表
    source: str = "genomelens-shell"  # 任务来源标识，用于区分 CLI/GUI/插件
    # fmt: on

    def to_manifest_json(self) -> dict[str, object]:
        """转成 engine manifest(引擎清单) 可直接写入的公开字段"""

        # task manifest 只保留跨层稳定字段，避免把 shell 内部对象结构泄漏到 engine 协议
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "workflow": self.workflow,
            "source": self.source,
        }


@dataclass(frozen=True)
class ArtifactRecord:
    """ArtifactRecord(产物记录)：供报告、GUI 和后续评分模块统一读取"""

    # fmt: off
    artifact_id: str       # 产物在报告与 GUI 中的唯一键
    artifact_type: str     # 产物类型（figure/table/log 等）
    path: str              # 产物文件路径
    produced_by: str       # 产生该产物的 workflow 或子模块
    format: str = ""       # 文件格式后缀（如 svg、tsv）
    preview: bool = False  # 是否推荐在 GUI 中预览
    input_refs: list[str] = field(default_factory=list)        # 上游输入产物引用
    metadata: dict[str, object] = field(default_factory=dict)  # 产物额外元数据
    # fmt: on

    def to_json(self) -> dict[str, object]:
        """转成稳定 JSON(结构化数据)"""

        return {
            "artifact_id": self.artifact_id,
            "artifact_type": self.artifact_type,
            "path": self.path,
            "produced_by": self.produced_by,
            "format": self.format,
            "preview": self.preview,
            "input_refs": self.input_refs,
            "metadata": self.metadata,
        }
