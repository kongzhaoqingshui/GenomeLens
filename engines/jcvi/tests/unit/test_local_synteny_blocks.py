from pathlib import Path

import pytest

from jcvi_genomelens.workflows.local_synteny.single import _extract_local_blocks


def test_single_unsplit_target_marks_gene_red(tmp_path: Path) -> None:
    blocks = tmp_path / "blocks.txt"
    blocks.write_text("qgene2\tsgene2\n", encoding="utf-8")

    local_blocks, covered = _extract_local_blocks(
        blocks,
        ["qgene1", "qgene2", "qgene3"],
        {"qgene1": 0, "qgene2": 1, "qgene3": 2},
        ["qgene2"],
        up=1,
        down=1,
        split_targets=False,
        query_label="query",
        subject_label="subject",
    )

    assert local_blocks == {"qgene2": ["r*qgene2\tsgene2"]}
    assert covered == {"qgene1", "qgene2", "qgene3"}


def test_window_keeps_non_target_rows_unmarked(tmp_path: Path) -> None:
    blocks = tmp_path / "blocks.txt"
    blocks.write_text("qgene1\tsgene1\nqgene2\tsgene2\nqgene3\tsgene3\n", encoding="utf-8")

    local_blocks, _ = _extract_local_blocks(
        blocks,
        ["qgene1", "qgene2", "qgene3"],
        {"qgene1": 0, "qgene2": 1, "qgene3": 2},
        ["qgene2"],
        up=1,
        down=1,
        split_targets=False,
        query_label="query",
        subject_label="subject",
    )

    assert local_blocks == {"qgene2": ["qgene1\tsgene1", "r*qgene2\tsgene2", "qgene3\tsgene3"]}


def test_unsplit_distant_targets_exclude_genes_between_windows(tmp_path: Path) -> None:
    """两个相距很远的目标只保留各自 ±窗口，不纳入它们之间的无关基因

    旧实现用 [min_start, max_end] 包络合并，会把两窗口之间的所有基因都拉进来，
    在真实数据上撑出上千行。现改为取窗口并集，远距离目标各自独立。
    """

    order = [f"q{i}" for i in range(11)]
    index = {gene: i for i, gene in enumerate(order)}
    blocks = tmp_path / "blocks.txt"
    blocks.write_text("\n".join(f"q{i}\ts{i}" for i in range(11)) + "\n", encoding="utf-8")

    local_blocks, covered = _extract_local_blocks(
        blocks,
        order,
        index,
        ["q1", "q9"],
        up=1,
        down=1,
        split_targets=False,
        query_label="query",
        subject_label="subject",
    )

    # 仅 q0..q2（q1 窗口）与 q8..q10（q9 窗口）；q3..q7 不应出现
    assert local_blocks == {
        "merged": [
            "q0\ts0",
            "r*q1\ts1",
            "q2\ts2",
            "q8\ts8",
            "r*q9\ts9",
            "q10\ts10",
        ]
    }
    assert covered == {"q0", "q1", "q2", "q8", "q9", "q10"}


def test_unsplit_overlapping_targets_merge_into_one_window(tmp_path: Path) -> None:
    """相邻/重叠的目标窗口仍合并为一个连续区间，行为与并集一致"""

    order = [f"q{i}" for i in range(6)]
    index = {gene: i for i, gene in enumerate(order)}
    blocks = tmp_path / "blocks.txt"
    blocks.write_text("\n".join(f"q{i}\ts{i}" for i in range(6)) + "\n", encoding="utf-8")

    local_blocks, covered = _extract_local_blocks(
        blocks,
        order,
        index,
        ["q2", "q3"],
        up=1,
        down=1,
        split_targets=False,
        query_label="query",
        subject_label="subject",
    )

    # q2 窗口 [1,3] 与 q3 窗口 [2,4] 重叠，合并为 [1,4]
    assert local_blocks == {
        "merged": [
            "q1\ts1",
            "r*q2\ts2",
            "r*q3\ts3",
            "q4\ts4",
        ]
    }
    assert covered == {"q1", "q2", "q3", "q4"}


def test_single_unsplit_target_error_names_gene_not_merged(tmp_path: Path) -> None:
    blocks = tmp_path / "blocks.txt"
    blocks.write_text("qgene2\t.\n", encoding="utf-8")

    with pytest.raises(ValueError) as excinfo:
        _extract_local_blocks(
            blocks,
            ["qgene1", "qgene2", "qgene3"],
            {"qgene1": 0, "qgene2": 1, "qgene3": 2},
            ["qgene2"],
            up=1,
            down=1,
            split_targets=False,
            query_label="query",
            subject_label="subject",
        )

    message = str(excinfo.value)
    assert "qgene2" in message
    assert "merged" not in message
