"""读取和写入 GenomeLens configuration JSON(配置 JSON)"""

# region import
from __future__ import annotations

import json
import os
from pathlib import Path

from genomelens.app.errors.exceptions import WorkspaceError
from genomelens.data.config.config_models import (
    ConfigModel,
    WorkspaceConfig,
    default_workspace_root,
    normalize_path_string,
)
from genomelens.data.config.jcvi_profile import JcviProfileModel
from genomelens.data.config.platform_config import PlatformConfigModel
from genomelens.utils.json import _dict, _int, _str

# endregion


DEFAULT_CONFIG_NAME = "genomelens.config.json"
DEFAULT_JCVI_CONFIG_NAME = "jcvi.config.json"


def default_config(workspace: str | Path | None = None) -> ConfigModel:
    """为工作区构建默认配置模型"""

    root = normalize_path_string(workspace or default_workspace_root())
    jcvi_path = normalize_path_string(Path(root) / DEFAULT_JCVI_CONFIG_NAME)
    return ConfigModel(
        workspace=WorkspaceConfig(
            workspace_root=root,
            temp_root=normalize_path_string(Path(root) / "temp"),
            default_output_root=normalize_path_string(Path(root) / "results"),
            engine_profile_path=jcvi_path,
        )
    )


def default_config_path(workspace: str | Path | None = None) -> Path:
    """返回工作区的默认平台配置路径"""

    root = Path(normalize_path_string(workspace or default_workspace_root()))
    return root / DEFAULT_CONFIG_NAME


def default_jcvi_config_path(workspace: str | Path | None = None) -> Path:
    """返回工作区的默认 engine profile 路径"""

    root = Path(normalize_path_string(workspace or default_workspace_root()))
    return root / DEFAULT_JCVI_CONFIG_NAME


def _write_json_file(payload: dict[str, object], path: str | Path, *, force: bool = False) -> Path:
    target = Path(path).expanduser().resolve(strict=False)
    if target.exists() and not force:
        raise WorkspaceError(f"配置已经存在：{target}")

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return target


def write_platform_config(config: PlatformConfigModel, path: str | Path, *, force: bool = False) -> Path:
    """写出平台配置文件"""

    return _write_json_file(config.to_json_dict(), path, force=force)


def write_engine_profile(profile: JcviProfileModel, path: str | Path, *, force: bool = False) -> Path:
    """写出 engine profile 文件"""

    return _write_json_file(profile.to_json_dict(), path, force=force)


def write_split_config(
    config: ConfigModel,
    config_path: str | Path,
    jcvi_config_path: str | Path,
    *,
    force: bool = False,
) -> tuple[Path, Path]:
    """写出工具主配置和 engine profile 两个文件（兼容旧签名）"""

    jcvi_path = Path(jcvi_config_path).expanduser().resolve(strict=False)

    # 主配置里会回写 engine profile 的最终路径，保证后续只读主配置时也能找到子配置
    config.workspace.engine_profile_path = normalize_path_string(jcvi_path)
    main_path = _write_json_file(config.to_project_json_dict(), config_path, force=force)
    written_jcvi = _write_json_file(config.to_jcvi_json_dict(), jcvi_path, force=force)
    return main_path, written_jcvi


def _read_json_object(path: str | Path, label: str) -> dict[str, object]:
    source = Path(path).expanduser().resolve(strict=False)
    data = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise WorkspaceError(f"{label} 必须是 JSON object(对象)：{source}")
    return data


def _resolve_engine_profile_path(
    source: Path,
    *,
    explicit: str | Path | None = None,
    configured: str | Path | None = None,
) -> Path | None:
    """解析 engine profile 路径：显式 > 主配置中的路径 > 环境变量"""

    raw = _str(explicit) or _str(configured) or os.environ.get("GENOMELENS_ENGINE_PROFILE", "")
    if not raw.strip():
        return None

    jcvi_source = Path(raw).expanduser()
    if not jcvi_source.is_absolute():
        jcvi_source = source.parent / jcvi_source
    jcvi_source = jcvi_source.resolve(strict=False)
    if not jcvi_source.is_file():
        raise WorkspaceError(f"engine profile 不存在：{jcvi_source}")
    return jcvi_source


def read_platform_config(path: str | Path) -> PlatformConfigModel:
    """读取平台配置文件"""

    data = _read_json_object(path, "平台配置")
    return PlatformConfigModel.from_json_dict(data)


def read_engine_profile(path: str | Path) -> JcviProfileModel:
    """读取 engine profile 文件

    兼容 schema_version 2 旧文件：自动按字段映射迁移到 V3 profile。
    """

    data = _read_json_object(path, "engine profile")
    version = _int(data.get("schema_version"), default=3)
    if version < 3:
        return ConfigModel._migrate_v2_profile(data)
    return JcviProfileModel.from_json_dict(data)


def read_config(path: str | Path, *, jcvi_config_path: str | Path | None = None) -> ConfigModel:
    """读取 config JSON(配置 JSON)，并按需合并 engine profile

    兼容 schema_version 2 旧文件：自动迁移到 V3 模型并发出警告。
    schema_version 3 主配置需通过 jcvi_config_path 参数、环境变量或主配置中的
    engine_profile_path 字段关联 engine profile。
    """

    source = Path(path).expanduser().resolve(strict=False)
    data = _read_json_object(source, "配置")
    version = _int(data.get("schema_version"), default=3)

    if version < 3:
        jcvi_path = _resolve_engine_profile_path(
            source,
            explicit=jcvi_config_path,
            configured=_str(data.get("engine_profile_path") or data.get("jcvi_config_path")),
        )
        if jcvi_path is not None:
            jcvi_data = _read_json_object(jcvi_path, "engine profile")
            for key in ("toolchain", "runtime", "mcscan", "local_synteny"):
                jcvi_section = _dict(jcvi_data.get(key))
                if not jcvi_section:
                    continue
                merged = dict(_dict(data.get(key)))
                merged.update(jcvi_section)
                data[key] = merged
            data["engine_profile_path"] = str(jcvi_path)
        return ConfigModel.from_json_dict(data)

    profile: JcviProfileModel | None = None
    profile_path = _resolve_engine_profile_path(
        source,
        explicit=jcvi_config_path,
        configured=_str(data.get("engine_profile_path") or data.get("jcvi_config_path")),
    )
    if profile_path is not None:
        profile = read_engine_profile(profile_path)

    return ConfigModel.from_json_dict(data, profile=profile)


def read_optional_config(
    path: str | Path | None = None,
    *,
    jcvi_config_path: str | Path | None = None,
) -> ConfigModel | None:
    """读取显式 config(配置)，或读取 `GENOMELENS_CONFIG` 指向的配置"""

    raw = _str(path) or os.environ.get("GENOMELENS_CONFIG", "")
    if not raw:
        raw_jcvi = _str(jcvi_config_path) or os.environ.get("GENOMELENS_ENGINE_PROFILE", "")
        if raw_jcvi:
            # 只有 engine profile 时，基于默认主配置补齐工作区字段，避免调用方手写兜底逻辑
            config = default_config()
            source = Path(raw_jcvi).expanduser().resolve(strict=False)
            if not source.is_file():
                raise WorkspaceError(f"engine profile 不存在：{source}")
            config.profile = read_engine_profile(source)
            return config
        return None
    source = Path(raw).expanduser().resolve(strict=False)
    if not source.is_file():
        raise WorkspaceError(f"配置不存在：{source}")
    return read_config(source, jcvi_config_path=jcvi_config_path)


# 兼容旧环境变量名
if "GENOMELENS_JCVI_CONFIG" in os.environ and "GENOMELENS_ENGINE_PROFILE" not in os.environ:
    os.environ["GENOMELENS_ENGINE_PROFILE"] = os.environ["GENOMELENS_JCVI_CONFIG"]


__all__ = [
    "DEFAULT_CONFIG_NAME",
    "DEFAULT_JCVI_CONFIG_NAME",
    "default_config",
    "default_config_path",
    "default_jcvi_config_path",
    "read_config",
    "read_engine_profile",
    "read_optional_config",
    "read_platform_config",
    "write_engine_profile",
    "write_platform_config",
    "write_split_config",
]
