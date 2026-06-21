import json
import logging
from pathlib import Path
from typing import Any, Protocol, cast

import pytest

from features import (
    catalog_ortholog_entry,
    dotplot_entry,
    karyotype_entry,
    synteny_entry,
)
from genomelens_haiant_plugin._core import PluginError, discover_mcscan_home


class FeatureEntryModule(Protocol):
    def build_runtime_command(self, params_path: str | Path) -> list[str]: ...
    def main(self, argv: list[str] | None = None) -> int: ...


def _write_params_from_sample(tmp_path: Path) -> Path:
    root = Path(__file__).resolve().parents[3]
    sample_params = root / "references" / "samples" / "haiant" / "params.json"
    payload = cast(
        dict[str, Any],
        json.loads(sample_params.read_text(encoding="utf-8")),
    )

    for item in payload["species"]:
        for key in ("bed", "cds", "gff", "genome"):
            if item.get(key):
                item[key] = str(
                    (sample_params.parent / item[key]).resolve(strict=False)
                )

    payload["output_dir"] = str(tmp_path / "output")
    payload["workflow"] = "should_be_ignored"

    params_path = tmp_path / "params.json"
    params_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return params_path


@pytest.mark.parametrize(
    ("module", "workflow", "logger_name"),
    [
        (
            cast(FeatureEntryModule, dotplot_entry),
            "graphics_dotplot",
            "gljcvi_dotplot",
        ),
        (
            cast(FeatureEntryModule, synteny_entry),
            "graphics_synteny",
            "gljcvi_synteny",
        ),
        (
            cast(FeatureEntryModule, karyotype_entry),
            "graphics_karyotype",
            "gljcvi_karyotype",
        ),
        (
            cast(FeatureEntryModule, catalog_ortholog_entry),
            "catalog_ortholog",
            "gljcvi_catalog_ortholog",
        ),
    ],
)
def test_feature_entry_builds_request_and_command(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    module: FeatureEntryModule,
    workflow: str,
    logger_name: str,
) -> None:
    params_path = _write_params_from_sample(tmp_path)
    mcscan_home = tmp_path / "gljcvimcscan"
    mcscan_home.mkdir()
    shell_path = mcscan_home / "genomelens.cmd"
    shell_path.write_text("@echo off\r\n", encoding="utf-8")
    monkeypatch.setenv("GLJCVIMCSCAN_HOME", str(mcscan_home))

    argv = module.build_runtime_command(params_path)

    assert argv[:4] == ["cmd.exe", "/c", str(shell_path), "analyze"]
    assert argv[4] == "run"
    request_path = Path(argv[5])
    assert request_path.name == "genomelens_request.json"

    request = json.loads(request_path.read_text(encoding="utf-8"))
    assert request["method"] == "mcscan"
    assert request["method_config"]["workflow"] == workflow
    assert request["output"]["directory"] == str(tmp_path / "output")
    assert request["options"]["threads"] == 2
    assert request["options"]["min_block_size"] == 1
    assert logging.getLogger(logger_name).handlers == []


def test_feature_entry_discovers_center_from_parent_tree(tmp_path: Path) -> None:
    plugins_root = tmp_path / "plugins"
    feature_root = plugins_root / "gljcvi-dotplot"
    center_root = plugins_root / "gljcvimcscan"
    feature_root.mkdir(parents=True)
    center_root.mkdir(parents=True)
    (center_root / "genomelens.cmd").write_text("@echo off\r\n", encoding="utf-8")

    assert discover_mcscan_home(feature_root) == center_root


def test_feature_entry_reports_missing_center(tmp_path: Path) -> None:
    with pytest.raises(PluginError, match="Unable to locate gljcvimcscan heavy center"):
        discover_mcscan_home(tmp_path)


@pytest.mark.parametrize(
    ("module", "label"),
    [
        (cast(FeatureEntryModule, dotplot_entry), "dotplot"),
        (cast(FeatureEntryModule, synteny_entry), "synteny"),
        (cast(FeatureEntryModule, karyotype_entry), "karyotype"),
        (
            cast(FeatureEntryModule, catalog_ortholog_entry),
            "catalog_ortholog",
        ),
    ],
)
def test_feature_entry_main_rejects_missing_params(
    capsys: pytest.CaptureFixture[str],
    module: FeatureEntryModule,
    label: str,
) -> None:
    exit_code = module.main([])

    assert exit_code == 2
    assert label in capsys.readouterr().err
