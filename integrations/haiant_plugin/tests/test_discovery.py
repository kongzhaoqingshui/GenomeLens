from pathlib import Path

import pytest

from genomelens_haiant_plugin import (
    GLJCVIMCSCAN_HOME_ENV,
    PluginError,
    discover_mcscan_home,
    genomelens_shell_path,
)


def _write_shell(home: Path) -> Path:
    shell = home / "genomelens.cmd"
    shell.write_text("@echo off\r\n", encoding="utf-8")
    return shell


def test_discover_mcscan_home_uses_env_var(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    center = tmp_path / "gljcvimcscan"
    center.mkdir()
    _write_shell(center)
    monkeypatch.setenv(GLJCVIMCSCAN_HOME_ENV, str(center))

    resolved = discover_mcscan_home()

    assert resolved == center
    assert genomelens_shell_path(resolved) == center / "genomelens.cmd"


def test_discover_mcscan_home_searches_parent_sibling(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv(GLJCVIMCSCAN_HOME_ENV, raising=False)
    plugins_root = tmp_path / "plugins"
    child = plugins_root / "gljcvi-dotplot"
    child.mkdir(parents=True)
    center = plugins_root / "gljcvimcscan"
    center.mkdir()
    _write_shell(center)

    resolved = discover_mcscan_home(child)

    assert resolved == center


def test_discover_mcscan_home_reports_clear_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv(GLJCVIMCSCAN_HOME_ENV, raising=False)

    with pytest.raises(PluginError, match="Unable to locate gljcvimcscan heavy center"):
        discover_mcscan_home(tmp_path)
