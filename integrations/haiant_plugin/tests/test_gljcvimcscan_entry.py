import json
from pathlib import Path
from typing import cast

import pytest

import gljcvimcscan_entry
from genomelens_haiant_plugin import GLJCVIMCSCAN_HOME_ENV


def _write_shell(home: Path) -> Path:
    shell = home / "genomelens.cmd"
    shell.write_text("@echo off\r\n", encoding="utf-8")
    return shell


def _write_params(root: Path) -> Path:
    query_bed = root / "query.bed"
    query_cds = root / "query.cds"
    subject_bed = root / "subject.bed"
    subject_cds = root / "subject.cds"
    query_bed.write_text(
        "chr1\t1\t10\tqgene1\nchr1\t20\t30\tqgene2\n", encoding="utf-8"
    )
    query_cds.write_text(">qgene1\nATG\n>qgene2\nATG\n", encoding="utf-8")
    subject_bed.write_text("chr1\t1\t10\tsgene1\n", encoding="utf-8")
    subject_cds.write_text(">sgene1\nATG\n", encoding="utf-8")
    params = {
        "input_mode": "bed_cds",
        "species": [
            {"name": "query", "bed": "query.bed", "cds": "query.cds"},
            {"name": "subject", "bed": "subject.bed", "cds": "subject.cds"},
        ],
        "output_dir": "output",
        "target_gene_ids": "qgene2",
        "reference": "query",
        "up": 1,
        "down": 1,
        "formats": "png",
    }
    params_path = root / "params.json"
    params_path.write_text(json.dumps(params, ensure_ascii=False), encoding="utf-8")
    return params_path


def test_build_center_command_writes_local_synteny_request(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    center = tmp_path / "gljcvimcscan"
    center.mkdir()
    shell = _write_shell(center)
    monkeypatch.setenv(GLJCVIMCSCAN_HOME_ENV, str(center))
    params_path = _write_params(tmp_path)

    argv = gljcvimcscan_entry.build_center_command(params_path)

    assert argv[:3] == ["cmd.exe", "/c", str(shell)]
    assert argv[3:5] == ["analyze", "run"]
    request = json.loads(
        (tmp_path / "output" / "genomelens_request.json").read_text(encoding="utf-8")
    )
    assert request["method_config"]["workflow"] == "local_synteny"
    assert request["method_config"]["target_gene_ids"] == ["qgene2"]
    assert request["input"]["reference_index"] == 0


def test_main_forwards_exit_code(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    center = tmp_path / "gljcvimcscan"
    center.mkdir()
    _write_shell(center)
    monkeypatch.setenv(GLJCVIMCSCAN_HOME_ENV, str(center))
    params_path = _write_params(tmp_path)
    captured: dict[str, object] = {}

    def fake_run(argv: list[str]) -> int:
        captured["argv"] = argv
        return 7

    monkeypatch.setattr(gljcvimcscan_entry, "run_process", fake_run)

    code = gljcvimcscan_entry.main([str(params_path)])

    assert code == 7
    argv = cast(list[str], captured["argv"])
    assert argv[3:5] == ["analyze", "run"]


def test_main_rejects_missing_args(capsys: pytest.CaptureFixture[str]) -> None:
    code = gljcvimcscan_entry.main([])

    assert code == 2
    assert "Expected exactly one params.json path" in capsys.readouterr().err
