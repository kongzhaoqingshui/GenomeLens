"""Shared toolchain resolution helpers for runners and diagnostics."""

# region import
from __future__ import annotations

from genomelens.app.errors import messages
from genomelens.app.errors.exceptions import ToolchainError
from genomelens.data.config.config_models import ConfigModel
from genomelens.toolchain.runtime.platform_names import (
    blastn_candidates,
    lastal_candidates,
    lastdb_candidates,
    makeblastdb_candidates,
)
from genomelens.toolchain.runtime.resource_locator import (
    LocatedResource,
    locate_engine,
    locate_tool,
)
from genomelens.toolchain.runtime.toolchain_installer import install_toolchain

# endregion


def resolve_jcvi_engine(
    *,
    explicit: str = "",
    config: ConfigModel | None = None,
) -> LocatedResource:
    """定位 JCVI 引擎，优先使用显式路径或配置中的路径。"""

    return locate_engine(explicit=explicit, config=config)


def resolve_blast_toolchain(
    *,
    blastn_explicit: str = "",
    makeblastdb_explicit: str = "",
    blastn_config: str = "",
    makeblastdb_config: str = "",
    auto_install: bool = True,
) -> tuple[LocatedResource, LocatedResource, list[dict[str, object]]]:
    """定位 BLAST+ 工具链，缺失时可选自动安装。

    返回 (blastn, makeblastdb, install_attempts)。
    """

    installs: list[dict[str, object]] = []
    blastn = locate_tool(
        "blast",
        explicit=blastn_explicit,
        config_value=blastn_config,
        packaged_names=blastn_candidates(),
    )
    makeblastdb = locate_tool(
        "blast",
        explicit=makeblastdb_explicit,
        config_value=makeblastdb_config,
        packaged_names=makeblastdb_candidates(),
    )

    if auto_install and (not blastn.ok or not makeblastdb.ok):
        install_result = install_toolchain("blast")
        installs.append(
            {
                "name": install_result.name,
                "status": install_result.status,
                "path": install_result.path,
                "message": install_result.message,
            }
        )
        blastn = locate_tool(
            "blast",
            explicit=blastn_explicit,
            config_value=blastn_config,
            packaged_names=blastn_candidates(),
        )
        makeblastdb = locate_tool(
            "blast",
            explicit=makeblastdb_explicit,
            config_value=makeblastdb_config,
            packaged_names=makeblastdb_candidates(),
        )

    return blastn, makeblastdb, installs


def resolve_last_toolchain(
    *,
    lastal_explicit: str = "",
    lastdb_explicit: str = "",
) -> tuple[str, str]:
    """定位 LAST 比对工具链，返回 (lastal_path, lastdb_path)。"""

    lastal = locate_tool("last", explicit=lastal_explicit, packaged_names=lastal_candidates())
    lastdb = locate_tool("last", explicit=lastdb_explicit, packaged_names=lastdb_candidates())

    if not lastal.ok or not lastdb.ok:
        raise ToolchainError(
            messages.TOOLCHAIN_LAST_NOT_FOUND,
        )

    return lastal.path, lastdb.path


def resolve_pairwise_toolchain(
    *,
    jcvi_engine: str = "",
    blastn_path: str = "",
    makeblastdb_path: str = "",
    lastal_path: str = "",
    lastdb_path: str = "",
    align_soft: str = "blast",
    config: ConfigModel | None = None,
) -> tuple[LocatedResource, LocatedResource, LocatedResource, str, str]:
    """定位 pairwise MCscan 所需的引擎与 BLAST/LAST 工具链。

    返回 (engine, blastn, makeblastdb, lastal_path, lastdb_path)。
    """

    engine = resolve_jcvi_engine(explicit=jcvi_engine, config=config)
    blastn, makeblastdb, _installs = resolve_blast_toolchain(
        blastn_explicit=blastn_path,
        makeblastdb_explicit=makeblastdb_path,
        auto_install=True,
    )

    resolved_lastal_path = ""
    resolved_lastdb_path = ""
    if align_soft == "last":
        resolved_lastal_path, resolved_lastdb_path = resolve_last_toolchain(
            lastal_explicit=lastal_path,
            lastdb_explicit=lastdb_path,
        )

    if not engine.ok:
        raise ToolchainError(
            messages.TOOLCHAIN_ENGINE_NOT_FOUND.format(message=engine.message),
        )
    if not blastn.ok:
        raise ToolchainError(
            messages.TOOLCHAIN_GENERIC_NOT_FOUND.format(message=blastn.message),
        )
    if not makeblastdb.ok:
        raise ToolchainError(
            messages.TOOLCHAIN_GENERIC_NOT_FOUND.format(message=makeblastdb.message),
        )

    return engine, blastn, makeblastdb, resolved_lastal_path, resolved_lastdb_path


def resolve_imagemagick(
    *,
    explicit: str = "",
    config_value: str = "",
) -> LocatedResource:
    """定位 ImageMagick 可执行文件。"""

    from genomelens.toolchain.runtime.platform_names import magick_candidates

    return locate_tool(
        "imagemagick",
        explicit=explicit,
        config_value=config_value,
        packaged_names=magick_candidates(),
    )
