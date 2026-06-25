import json
from pathlib import Path

import pytest

from genomelens.data.config.config_models import WorkspaceConfig
from genomelens.data.config.config_store import (
    default_config,
    default_jcvi_config_path,
    read_config,
    read_engine_profile,
    read_platform_config,
    write_engine_profile,
    write_platform_config,
    write_split_config,
)
from genomelens.data.config.jcvi_profile import (
    JcviProfileModel,
    LocalSyntenyProfileDefaults,
    SyntenyProfileDefaults,
)
from genomelens.data.config.platform_config import PlatformConfigModel, RuntimeDefaults


def test_default_config_has_schema_version_three() -> None:
    config = default_config("/tmp/work")

    assert config.schema_version == 3
    assert config.profile.synteny.min_block_size == 5
    assert config.profile.local_synteny.up == 20
    assert config.profile.plot.dpi == 300


def test_split_config_roundtrip(tmp_path: Path) -> None:
    config = default_config(tmp_path / "work")
    main_path = tmp_path / "work" / "genomelens.config.json"
    jcvi_path = default_jcvi_config_path(tmp_path / "work")

    written_main, written_jcvi = write_split_config(config, main_path, jcvi_path)
    loaded = read_config(written_main)

    assert written_main == main_path.resolve(strict=False)
    assert written_jcvi == jcvi_path.resolve(strict=False)
    assert loaded.workspace.engine_profile_path == str(written_jcvi)
    assert loaded.schema_version == 3

    # runtime 仅保留通用运行级字段
    assert loaded.runtime.default_threads == 4
    assert loaded.runtime.default_formats == ["svg"]
    assert loaded.runtime.log_level == "INFO"

    # profile 分组
    assert loaded.profile.synteny.min_block_size == 5
    assert loaded.profile.synteny.align_soft == "blast"
    assert loaded.profile.local_synteny.up == 20
    assert loaded.profile.local_synteny.down == 20
    assert loaded.profile.plot.dpi == 300
    assert loaded.profile.plot.auto_optimization.optimize_figsize is False

    assert loaded.toolchain.lastal_path == ""
    assert loaded.toolchain.lastdb_path == ""

    # engine profile 文件为 V3 结构
    jcvi_text = jcvi_path.read_text(encoding="utf-8")
    assert '"schema_version": 3' in jcvi_text
    assert '"synteny"' in jcvi_text
    assert '"local_synteny"' in jcvi_text
    assert '"plot"' in jcvi_text
    assert '"min_block_size"' in jcvi_text
    assert '"auto_optimization"' in jcvi_text


def test_v2_config_migrates_to_v3_profile(tmp_path: Path) -> None:
    jcvi_path = tmp_path / "jcvi.config.json"
    jcvi_path.write_text(
        json.dumps(
            {
                "schema_version": 2,
                "toolchain": {
                    "blastn_path": "C:\\Tools\\blast\\bin\\blastn.exe",
                },
                "runtime": {
                    "threads": 8,
                },
                "mcscan": {
                    "cscore": 0.9,
                },
                "local_synteny": {
                    "up": 15,
                    "dpi": 200,
                    "auto_optimization": {
                        "optimize_figsize": True,
                        "rewrite_layout_links": True,
                        "optimize_karyotype_labels": True,
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    main_path = tmp_path / "genomelens.config.json"
    main_path.write_text(
        json.dumps(
            {
                "schema_version": 2,
                "workspace_root": str(tmp_path / "work"),
                "jcvi_config_path": str(jcvi_path),
                "log_level": "INFO",
            }
        ),
        encoding="utf-8",
    )
    with pytest.warns(DeprecationWarning, match="schema_version 2"):
        loaded = read_config(main_path)
    assert loaded.toolchain.blastn_path == str(Path("C:\\Tools\\blast\\bin\\blastn.exe").resolve())
    assert loaded.runtime.default_threads == 8
    assert loaded.profile.synteny.cscore == 0.9
    assert loaded.profile.local_synteny.up == 15
    assert loaded.profile.plot.dpi == 200
    assert loaded.profile.plot.auto_optimization.optimize_figsize is True
    assert loaded.profile.plot.auto_optimization.rewrite_layout_links is True
    assert loaded.profile.plot.auto_optimization.optimize_karyotype_labels is True


def test_platform_config_roundtrip(tmp_path: Path) -> None:
    platform = PlatformConfigModel(
        workspace=WorkspaceConfig(
            workspace_root=str(tmp_path / "work"),
            temp_root=str(tmp_path / "work" / "temp"),
            default_output_root=str(tmp_path / "work" / "results"),
            engine_profile_path=str(tmp_path / "profile.json"),
        ),
        runtime=RuntimeDefaults(default_threads=8, default_formats=["png"], log_level="DEBUG"),
    )
    path = tmp_path / "platform.json"
    write_platform_config(platform, path)

    loaded = read_platform_config(path)

    assert loaded.workspace.engine_profile_path == str(tmp_path / "profile.json")
    assert loaded.runtime.default_threads == 8
    assert loaded.runtime.default_formats == ["png"]


def test_engine_profile_roundtrip(tmp_path: Path) -> None:
    profile = JcviProfileModel(
        synteny=SyntenyProfileDefaults(min_block_size=12, cscore=0.8),
        local_synteny=LocalSyntenyProfileDefaults(up=10),
    )
    path = tmp_path / "profile.json"
    write_engine_profile(profile, path)

    loaded = read_engine_profile(path)

    assert loaded.synteny.min_block_size == 12
    assert loaded.synteny.cscore == 0.8
    assert loaded.local_synteny.up == 10
    assert loaded.local_synteny.down == 20
