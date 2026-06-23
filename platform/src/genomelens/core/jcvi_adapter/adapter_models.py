"""JCVI 引擎适配器边界数据模型

本模块只保留与 engine 进程直接交互的边界对象：
- probe 结果
- engine run 结果

执行层内部模型（如 McscanExecutionRequest）已迁移到
`genomelens.analysis.execution_models`，不应再出现在这里。
"""

# region import
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

# endregion


@dataclass(frozen=True)
class JcviProbeResult:
    """JcviProbeResult：probe 命令返回的引擎能力摘要"""

    # fmt: off
    status: str                 # 探测状态（ok / error）
    engine_version: str         # 引擎版本
    jcvi_upstream_version: str  # 上游 JCVI 版本
    patchset: str               # 当前 patchset 标识
    distribution: str = ""      # 引擎分发方式（source/wheel 等）
    runtime_mode: str = ""      # 运行模式（core/accelerated 等）
    loaded_extensions: list[str] = field(default_factory=list)   # 已加载扩展
    missing_extensions: list[str] = field(default_factory=list)  # 缺失扩展
    error: object = None        # 失败时的异常或错误对象
    # fmt: on

    @classmethod
    def from_json(cls, data: dict[str, object]) -> JcviProbeResult:
        """从 probe JSON 构建结果对象"""

        def _str_list(key: str) -> list[str]:
            raw = data.get(key)
            if isinstance(raw, list):
                return [str(item) for item in raw if item is not None]
            return []

        return cls(
            status=str(data.get("status", "error")),
            engine_version=str(data.get("engine_version", "")),
            jcvi_upstream_version=str(data.get("jcvi_upstream_version", "")),
            patchset=str(data.get("patchset", "")),
            distribution=str(data.get("distribution", "")),
            runtime_mode=str(data.get("runtime_mode", "")),
            loaded_extensions=_str_list("loaded_extensions"),
            missing_extensions=_str_list("missing_extensions"),
            error=data.get("error"),
        )


@dataclass(frozen=True)
class JcviRunResult:
    """JcviRunResult：解析后的 engine summary(引擎摘要) 字段"""

    # fmt: off
    status: str                 # 引擎执行状态
    summary_path: Path          # 引擎 summary JSON 路径
    engine_version: str         # 引擎版本
    jcvi_upstream_version: str  # 上游 JCVI 版本
    patchset: str               # 当前 patchset 标识
    artifacts: dict[str, object]  # 引擎返回的产物字典
    distribution: str = ""        # 引擎分发方式（source/wheel 等）
    runtime_mode: str = ""        # 运行模式（core/accelerated 等）
    loaded_extensions: list[str] = field(default_factory=list)             # 已加载的扩展列表
    missing_extensions: list[str] = field(default_factory=list)            # 缺失的扩展列表
    task: dict[str, object] = field(default_factory=dict)                  # 引擎回写的 task 元数据
    species: list[dict[str, object]] = field(default_factory=list)         # 引擎回写的物种信息
    artifact_index: list[dict[str, object]] = field(default_factory=list)  # 引擎产物索引
    error: object = None  # 失败时的异常或错误对象
    # fmt: on
