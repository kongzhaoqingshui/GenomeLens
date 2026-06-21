import json
import logging
from pathlib import Path
from typing import Any, Protocol, cast

import pytest

from features import (
    auto_entry,
    catalog_ortholog_entry,
    dotplot_entry,
    karyotype_entry,
    local_synteny_entry,
    synteny_entry,
)


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

    genomelens_exe = tmp_path / "GenomeLens.cmd"
    genomelens_exe.write_text("@echo off\r\n", encoding="utf-8")

    sample_input_dir = (sample_params.parent / payload.get("input_dir", "../shell/bed_cds_minimal")).resolve()
    payload["genomelens_exe"] = str(genomelens_exe)
    payload["input_dir"] = str(sample_input_dir)
    payload["output_dir"] = str(tmp_path / "output")
    payload["target_gene_ids"] = "qgene1"

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
        (
            cast(FeatureEntryModule, local_synteny_entry),
            "local_synteny",
            "gljcvi_local_synteny",
        ),
        (
            cast(FeatureEntryModule, auto_entry),
            "graphics_synteny",
            "gljcvi_auto",
        ),
    ],
)
def test_feature_entry_builds_request_and_command(
    tmp_path: Path,
    module: FeatureEntryModule,
    workflow: str,
    logger_name: str,
) -> None:
    params_path = _write_params_from_sample(tmp_path)

    argv = module.build_runtime_command(params_path)

    assert argv[:4] == ["cmd.exe", "/c", str(tmp_path / "GenomeLens.cmd"), "analyze"]
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
        (
            cast(FeatureEntryModule, local_synteny_entry),
            "local synteny",
        ),
        (
            cast(FeatureEntryModule, auto_entry),
            "MCscan auto workflow",
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
