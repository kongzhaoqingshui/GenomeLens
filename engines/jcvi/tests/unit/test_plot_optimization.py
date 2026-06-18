from pathlib import Path

from jcvi_genomelens.manifest_models import WorkflowOptions
from jcvi_genomelens.workflows.plot_optimization import (
    prepare_synteny_plot_inputs,
    rewrite_layout_links,
    suggest_figsize,
    trim_cross_chromosome_blocks,
)


def test_rewrite_layout_links_turns_star_edges_into_chain(tmp_path: Path) -> None:
    layout = tmp_path / "layout.csv"
    layout.write_text(
        "\n".join(
            [
                "# x, y, rotation, ha, va, color, ratio, label",
                "0.50, 0.80, 0, center, top, red, 1, A",
                "0.50, 0.50, 0, center, top, blue, 1, B",
                "0.50, 0.20, 0, center, top, green, 1, C",
                "e, 0, 2, #ccc",
                "e, 0, 1, #999",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    rewritten, changed = rewrite_layout_links(layout, tmp_path / "layout.rewritten.csv")

    assert changed == 2
    assert "e, 0, 1, #999" in rewritten.read_text(encoding="utf-8")
    assert "e, 1, 2, #ccc" in rewritten.read_text(encoding="utf-8")
    assert "e, 0, 2, #ccc" not in rewritten.read_text(encoding="utf-8")


def test_trim_cross_chromosome_blocks_drops_mismatched_rows(tmp_path: Path) -> None:
    bed = tmp_path / "all.bed"
    bed.write_text(
        "\n".join(
            [
                "chr1\t0\t10\tq1\t0\t+",
                "chr1\t10\t20\ts1\t0\t+",
                "chr2\t0\t10\ts2\t0\t+",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    blocks = tmp_path / "blocks.txt"
    blocks.write_text("q1\ts1\nq1\ts2\n", encoding="utf-8")

    trimmed, count = trim_cross_chromosome_blocks(blocks, bed, tmp_path / "blocks.trimmed.txt")

    assert count == 1
    assert trimmed.read_text(encoding="utf-8") == "q1\ts1\n"


def test_suggest_figsize_uses_tracks_and_block_rows(tmp_path: Path) -> None:
    layout = tmp_path / "layout.csv"
    layout.write_text(
        "\n".join(
            [
                "0.50, 0.80, 0, center, top, red, 1, A",
                "0.50, 0.50, 0, center, top, blue, 1, B",
                "0.50, 0.20, 0, center, top, green, 1, C",
                "e, 0, 2, #ccc",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    blocks = tmp_path / "blocks.txt"
    blocks.write_text("\n".join(f"q{i}\ts{i}" for i in range(50)) + "\n", encoding="utf-8")

    assert suggest_figsize(blocks, layout) == "10x7"


def test_prepare_synteny_plot_inputs_defaults_to_original_files(tmp_path: Path) -> None:
    blocks = tmp_path / "blocks.txt"
    bed = tmp_path / "all.bed"
    layout = tmp_path / "layout.csv"
    blocks.write_text("q1\ts1\n", encoding="utf-8")
    bed.write_text("chr1\t0\t10\tq1\t0\t+\nchr1\t10\t20\ts1\t0\t+\n", encoding="utf-8")
    layout.write_text("0.5, 0.8, 0, center, top, red, 1, A\n", encoding="utf-8")

    inputs = prepare_synteny_plot_inputs(
        blocks=blocks,
        bed=bed,
        layout=layout,
        root=tmp_path,
        stem="plot",
        options=WorkflowOptions(),
    )

    assert inputs.blocks == blocks
    assert inputs.layout == layout
    assert inputs.figsize == ""
    assert inputs.artifacts == {}


def test_prepare_synteny_plot_inputs_applies_independent_switches(tmp_path: Path) -> None:
    bed = tmp_path / "all.bed"
    bed.write_text(
        "chr1\t0\t10\tq1\t0\t+\nchr2\t10\t20\ts1\t0\t+\nchr1\t20\t30\ts2\t0\t+\n",
        encoding="utf-8",
    )
    blocks = tmp_path / "blocks.txt"
    blocks.write_text("q1\ts1\nq1\ts2\n", encoding="utf-8")
    layout = tmp_path / "layout.csv"
    layout.write_text(
        "0.5, 0.8, 0, center, top, red, 1, A\n0.5, 0.5, 0, center, top, blue, 1, B\n"
        "0.5, 0.2, 0, center, top, green, 1, C\ne, 0, 1\ne, 0, 2\n",
        encoding="utf-8",
    )

    inputs = prepare_synteny_plot_inputs(
        blocks=blocks,
        bed=bed,
        layout=layout,
        root=tmp_path,
        stem="plot",
        options=WorkflowOptions(
            optimize_figsize=True,
            rewrite_layout_links=True,
            trim_cross_chromosome_blocks=True,
        ),
    )

    assert inputs.blocks.name == "plot.trimmed.blocks"
    assert inputs.layout.name == "plot.rewritten.layout"
    assert inputs.figsize == "8x7"
    assert inputs.artifacts["trimmed_cross_chromosome_block_rows"] == 1
    assert inputs.artifacts["rewritten_layout_edges"] == 2


def test_prepare_synteny_plot_inputs_falls_back_when_trimmed_blocks_are_empty(tmp_path: Path) -> None:
    bed = tmp_path / "all.bed"
    bed.write_text(
        "chr1\t0\t10\tq1\t0\t+\nchr2\t10\t20\ts1\t0\t+\n",
        encoding="utf-8",
    )
    blocks = tmp_path / "blocks.txt"
    blocks.write_text("q1\ts1\n", encoding="utf-8")
    layout = tmp_path / "layout.csv"
    layout.write_text("0.5, 0.8, 0, center, top, red, 1, A\n", encoding="utf-8")

    inputs = prepare_synteny_plot_inputs(
        blocks=blocks,
        bed=bed,
        layout=layout,
        root=tmp_path,
        stem="plot",
        options=WorkflowOptions(trim_cross_chromosome_blocks=True),
    )

    assert inputs.blocks == blocks
    assert inputs.artifacts["trimmed_cross_chromosome_block_rows"] == 1
    assert inputs.artifacts["trimmed_blocks_fallback"] == "original_blocks"
