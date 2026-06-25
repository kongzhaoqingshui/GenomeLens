"""GenomeLens 平台级配置数据模型"""

# region import
from __future__ import annotations

from dataclasses import asdict, dataclass, field

from genomelens.data.config.config_models import (
    RuntimeDefaults,
    ToolchainConfig,
    WorkspaceConfig,
    normalize_optional_path,
    normalize_path_string,
)
from genomelens.utils.json import _dict, _int, _str, _str_list

# endregion


@dataclass
class PlatformConfigModel:
    """PlatformConfigModel(平台配置)：环境与平台级默认值

    V3 将任务身份、参考物种、目标基因、输入路径等分析语义从平台配置中移除，
    仅保留 workspace、toolchain、runtime 与指向 engine profile 的链接。
    """

    # fmt: off
    schema_version: int = 3
    workspace: WorkspaceConfig = field(default_factory=lambda: WorkspaceConfig(workspace_root=""))
    toolchain: ToolchainConfig = field(default_factory=ToolchainConfig)
    runtime: RuntimeDefaults = field(default_factory=RuntimeDefaults)
    # fmt: on

    def to_json_dict(self) -> dict[str, object]:
        """序列化为平台配置文件"""

        return {
            "schema_version": self.schema_version,
            "workspace_root": self.workspace.workspace_root,
            "temp_root": self.workspace.temp_root,
            "default_output_root": self.workspace.default_output_root,
            "engine_profile_path": self.workspace.engine_profile_path,
            "log_level": self.runtime.log_level,
            "toolchain": {
                "jcvi_engine_path": self.toolchain.jcvi_engine_path,
                "blastn_path": self.toolchain.blastn_path,
                "makeblastdb_path": self.toolchain.makeblastdb_path,
                "lastal_path": self.toolchain.lastal_path,
                "lastdb_path": self.toolchain.lastdb_path,
                "magick_path": self.toolchain.magick_path,
            },
            "runtime": {
                "threads": self.runtime.default_threads,
                "formats": self.runtime.default_formats,
            },
        }

    @classmethod
    def from_json_dict(cls, data: dict[str, object]) -> PlatformConfigModel:
        """从平台配置 JSON 反序列化"""

        workspace_root = _str(data.get("workspace_root"))
        workspace = WorkspaceConfig(
            workspace_root=normalize_path_string(workspace_root) if workspace_root else "",
            temp_root=normalize_path_string(_str(data.get("temp_root"), default="")) or "",
            default_output_root=normalize_path_string(_str(data.get("default_output_root"), default="")) or "",
            engine_profile_path=normalize_optional_path(data.get("engine_profile_path")),
        )

        toolchain_raw = _dict(data.get("toolchain"))
        toolchain = ToolchainConfig(
            jcvi_engine_path=normalize_optional_path(toolchain_raw.get("jcvi_engine_path")),
            blastn_path=normalize_optional_path(toolchain_raw.get("blastn_path")),
            makeblastdb_path=normalize_optional_path(toolchain_raw.get("makeblastdb_path")),
            lastal_path=normalize_optional_path(toolchain_raw.get("lastal_path")),
            lastdb_path=normalize_optional_path(toolchain_raw.get("lastdb_path")),
            magick_path=normalize_optional_path(toolchain_raw.get("magick_path")),
        )

        runtime_raw = _dict(data.get("runtime"))
        runtime = RuntimeDefaults(
            default_threads=_int(runtime_raw.get("threads"), default=4),
            default_formats=_str_list(runtime_raw.get("formats"), default=["svg"]),
            log_level=_str(data.get("log_level"), default="INFO"),
        )

        return cls(
            schema_version=_int(data.get("schema_version"), default=3),
            workspace=workspace,
            toolchain=toolchain,
            runtime=runtime,
        )

    def as_nested_dict(self) -> dict[str, object]:
        """返回供内部调试使用的嵌套 dict(字典)"""

        return asdict(self)


__all__ = [
    "PlatformConfigModel",
]
