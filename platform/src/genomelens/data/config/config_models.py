"""GenomeLens shell(外壳) 的配置 dataclasses(数据类)"""

# region import
from __future__ import annotations

import warnings
from dataclasses import asdict, dataclass, field
from pathlib import Path

from genomelens.data.config.jcvi_profile import (
    AutoOptimizationDefaults,
    JcviProfileModel,
    LocalSyntenyProfileDefaults,
    PlotProfileDefaults,
    SyntenyProfileDefaults,
)
from genomelens.utils.json import _bool, _dict, _float, _int, _str, _str_list

# endregion


@dataclass
class WorkspaceConfig:
    """WorkspaceConfig(工作区配置)：runtime files(运行时文件) 的默认根目录"""

    # fmt: off
    workspace_root: str         # 工作区根目录
    temp_root: str              # 临时文件根目录
    default_output_root: str      # 默认输出根目录
    engine_profile_path: str = ""  # 可选的 JCVI engine profile 路径
    # fmt: on


@dataclass
class ToolchainConfig:
    """ToolchainConfig(工具链配置)：显式 executable(可执行文件) 覆盖项"""

    # fmt: off
    jcvi_engine_path: str = ""  # jcvi-genomelens 可执行文件路径
    blastn_path: str = ""       # BLAST+ blastn 路径
    makeblastdb_path: str = ""  # BLAST+ makeblastdb 路径
    lastal_path: str = ""       # LAST lastal 路径
    lastdb_path: str = ""       # LAST lastdb 路径
    magick_path: str = ""       # ImageMagick convert 路径
    # fmt: on


@dataclass
class RuntimeDefaults:
    """RuntimeDefaults(运行默认值)：通用运行级默认值"""

    # fmt: off
    default_threads: int = 4  # 默认并行线程数
    default_formats: list[str] = field(default_factory=lambda: ["svg"])  # 默认输出图件格式列表
    log_level: str = "INFO"   # 默认日志级别
    # fmt: on


@dataclass
class ConfigModel:
    """ConfigModel(总配置)：V3 兼容聚合对象

    V3 在模型层拆分为 PlatformConfigModel（平台级）与 JcviProfileModel（引擎默认值）。
    ConfigModel 继续作为内部兼容入口，把 workspace/toolchain/runtime 与 profile 聚合在一起，
    方便 CLI 与请求组装器一次性读取。
    """

    # fmt: off
    workspace: WorkspaceConfig
    toolchain: ToolchainConfig = field(default_factory=ToolchainConfig)
    runtime: RuntimeDefaults = field(default_factory=RuntimeDefaults)
    profile: JcviProfileModel = field(default_factory=JcviProfileModel)
    schema_version: int = 3  # 配置 JSON schema 版本
    # fmt: on

    def to_project_json_dict(self) -> dict[str, object]:
        """序列化为工具主配置文件"""

        return {
            "schema_version": self.schema_version,
            "workspace_root": self.workspace.workspace_root,
            "temp_root": self.workspace.temp_root,
            "default_output_root": self.workspace.default_output_root,
            "log_level": self.runtime.log_level,
            "engine_profile_path": self.workspace.engine_profile_path,
        }

    def to_jcvi_json_dict(self) -> dict[str, object]:
        """序列化为 JCVI engine profile 配置文件"""

        return self.profile.to_json_dict()

    @classmethod
    def from_json_dict(cls, data: dict[str, object], *, profile: JcviProfileModel | None = None) -> ConfigModel:
        """从当前配置 JSON 协议反序列化

        - schema_version 2：旧版单文件，按字段映射拆分为 platform + profile，并发出迁移警告。
        - schema_version 3：主配置 JSON，profile 需通过外部 engine profile 文件提供；
          若 data 中带有 "profile" 字段则直接解析（测试场景）。
        """

        version = _int(data.get("schema_version"), default=3)
        workspace_root = _str(data.get("workspace_root"), default=default_workspace_root())
        workspace = WorkspaceConfig(
            workspace_root=normalize_path_string(workspace_root),
            temp_root=normalize_path_string(_str(data.get("temp_root"), default=str(Path(workspace_root) / "temp"))),
            default_output_root=normalize_path_string(
                _str(data.get("default_output_root"), default=str(Path(workspace_root) / "results"))
            ),
            engine_profile_path=normalize_optional_path(
                data.get("engine_profile_path") or data.get("jcvi_config_path")
            ),
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

        parsed_profile = profile if profile is not None else cls._profile_from_json_dict(data, version)

        return cls(
            workspace=workspace,
            toolchain=toolchain,
            runtime=runtime,
            profile=parsed_profile,
            schema_version=version,
        )

    @classmethod
    def _profile_from_json_dict(cls, data: dict[str, object], version: int) -> JcviProfileModel:
        """从 data 解析 profile；schema_version 2 时做字段迁移"""

        if version < 3:
            warnings.warn(
                "schema_version 2 的配置文件已弃用，建议迁移到 V3 平台配置 + engine profile",
                DeprecationWarning,
                stacklevel=3,
            )
            return cls._migrate_v2_profile(data)

        embedded_profile = _dict(data.get("profile"))
        if embedded_profile:
            return JcviProfileModel.from_json_dict(embedded_profile)

        # 主配置中仅含平台字段，profile 由调用方通过 engine_profile_path 额外读取后设置
        return JcviProfileModel()

    @classmethod
    def _migrate_v2_profile(cls, data: dict[str, object]) -> JcviProfileModel:
        """把 schema_version 2 的 mcscan / local_synteny 分组迁移到 JcviProfileModel"""

        mcscan_raw = _dict(data.get("mcscan"))
        local_raw = _dict(data.get("local_synteny"))
        auto_opt_raw = _dict(local_raw.get("auto_optimization"))

        synteny = SyntenyProfileDefaults(
            align_soft=_str(mcscan_raw.get("align_soft"), default="blast"),
            dbtype=_str(mcscan_raw.get("dbtype"), default="nucl"),
            cscore=_float(mcscan_raw.get("cscore"), default=0.7),
            dist=_int(mcscan_raw.get("dist"), default=20),
            iter=_int(mcscan_raw.get("iter"), default=1),
            min_block_size=_int(mcscan_raw.get("min_block_size"), default=5),
        )

        local_synteny = LocalSyntenyProfileDefaults(
            up=_int(local_raw.get("up"), default=20),
            down=_int(local_raw.get("down"), default=20),
            split_targets=_bool(local_raw.get("split_targets"), default=False),
            label_targets=_bool(local_raw.get("label_targets"), default=False),
            use_native_local_synteny_renderer=_bool(local_raw.get("use_native_local_synteny_renderer"), default=False),
        )

        auto_optimization = AutoOptimizationDefaults(
            optimize_figsize=_bool(auto_opt_raw.get("optimize_figsize"), default=False),
            rewrite_layout_links=_bool(auto_opt_raw.get("rewrite_layout_links"), default=False),
            optimize_karyotype_labels=_bool(auto_opt_raw.get("optimize_karyotype_labels"), default=False),
        )
        plot = PlotProfileDefaults(
            glyphstyle=_str(local_raw.get("glyphstyle")),
            glyphcolor=_str(local_raw.get("glyphcolor")),
            shadestyle=_str(local_raw.get("shadestyle")),
            figsize=_str(local_raw.get("figsize")),
            dpi=_int(local_raw.get("dpi"), default=300),
            auto_optimization=auto_optimization,
        )

        return JcviProfileModel(
            schema_version=3,
            synteny=synteny,
            local_synteny=local_synteny,
            plot=plot,
        )

    def as_nested_dict(self) -> dict[str, object]:
        """返回供内部调试使用的嵌套 dict(字典)"""

        return asdict(self)


def default_workspace_root() -> str:
    """返回默认用户工作区根目录"""

    return normalize_path_string(Path.home() / "GenomeLensWork")


def normalize_path_string(path: str | Path) -> str:
    """规范化路径，不要求目标已经存在"""

    return str(Path(path).expanduser().resolve(strict=False))


def normalize_optional_path(value: object) -> str:
    """规范化可选路径字段，同时保留空字符串"""

    if value is None or str(value).strip() == "":
        return ""

    # 只有真正配置了路径时才做绝对化，空串语义要原样保留。
    return normalize_path_string(str(value))


__all__ = [
    "ConfigModel",
    "RuntimeDefaults",
    "ToolchainConfig",
    "WorkspaceConfig",
    "default_workspace_root",
    "normalize_optional_path",
    "normalize_path_string",
]
