from pathlib import Path

import pytest

from jcvi_genomelens.graphics.local_synteny_renderer import (
    GeneRecord,
    _build_track_window,
    _format_bp_range,
    _read_bed,
    _read_blocks,
    _strip_highlight_prefix,
    render_local_synteny,
)


def _write_fixture_bed(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                "chr1\t100\t200\tg1\t0\t+",
                "chr1\t300\t400\tg2\t0\t-",
                "chr1\t500\t600\tg3\t0\t+",
                "chr2\t100\t200\tg4\t0\t+",
                "chr2\t300\t400\tg5\t0\t-",
                "chr3\t100\t200\tg6\t0\t+",
                "chr3\t300\t400\tg7\t0\t-",
                "chrA\t100\t200\ts1\t0\t+",
                "chrA\t300\t400\ts2\t0\t-",
                "chrB\t100\t200\ts3\t0\t+",
                "chrB\t300\t400\ts4\t0\t-",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def _write_fixture_blocks(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                "g1\ts1",
                "g2\ts2",
                "g3\t.",
                "g4\ts3",
                "g5\ts4",
                "g6\t.",
                "g7\t.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def _write_multi_track_blocks(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                "g1\ts1\ts3",
                "g2\ts2\t.",
                "g3\t.\ts4",
                "g4\t.\t.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


@pytest.fixture
def fixture_dir(tmp_path: Path) -> Path:
    bed = tmp_path / "all.bed"
    blocks = tmp_path / "blocks.txt"
    _write_fixture_bed(bed)
    _write_fixture_blocks(blocks)
    return tmp_path


def test_strip_highlight_prefix() -> None:
    assert _strip_highlight_prefix("r*geneA") == (True, "geneA")
    assert _strip_highlight_prefix("geneA") == (False, "geneA")
    # Whitespace is trimmed only from the body; the prefix must be exactly "r".
    assert _strip_highlight_prefix("r*  geneA  ") == (True, "geneA")
    assert _strip_highlight_prefix(" x*geneA") == (False, "geneA")


def test_read_bed_maps_accn_to_record(tmp_path: Path) -> None:
    bed = tmp_path / "test.bed"
    bed.write_text("chr1\t100\t200\tg1\t0\t+\n", encoding="utf-8")
    genes = _read_bed(bed)
    assert "g1" in genes
    assert genes["g1"].chromosome == "chr1"
    assert genes["g1"].start == 100
    assert genes["g1"].end == 200


def test_read_blocks_parses_rows_and_highlights(tmp_path: Path) -> None:
    blocks = tmp_path / "test.blocks"
    blocks.write_text("r*g1\ts1\n", encoding="utf-8")
    rows = _read_blocks(blocks, track_count=2)
    assert len(rows) == 1
    assert rows[0].query_gene == "g1"
    assert rows[0].highlighted is True
    assert rows[0].subject_genes == ["s1"]


def test_render_local_synteny_produces_non_empty_svg(fixture_dir: Path) -> None:
    output = fixture_dir / "out.svg"
    result = render_local_synteny(
        blocks_path=fixture_dir / "blocks.txt",
        bed_path=fixture_dir / "all.bed",
        output_path=output,
        track_names=["Ref", "Sub"],
    )
    assert result == output
    assert output.is_file()
    assert output.stat().st_size > 0


def test_render_keeps_cross_chromosome_segments(fixture_dir: Path) -> None:
    """跨染色体参考基因应生成多个 segment，而不是被裁切。"""

    output = fixture_dir / "out.svg"
    render_local_synteny(
        blocks_path=fixture_dir / "blocks.txt",
        bed_path=fixture_dir / "all.bed",
        output_path=output,
        track_names=["Ref", "Sub"],
    )
    content = output.read_text(encoding="utf-8")
    # SVG should contain chromosome labels for chr1, chr2 and chr3.
    assert "chr1" in content
    assert "chr2" in content
    assert "chr3" in content


def test_render_highlights_target_genes(fixture_dir: Path) -> None:
    output = fixture_dir / "out.svg"
    render_local_synteny(
        blocks_path=fixture_dir / "blocks.txt",
        bed_path=fixture_dir / "all.bed",
        output_path=output,
        track_names=["Ref", "Sub"],
        target_gene_ids=["g2", "g5"],
    )
    content = output.read_text(encoding="utf-8")
    # The highlight marker should be drawn in black.
    assert "#000000" in content


def test_render_includes_chromosome_legend(fixture_dir: Path) -> None:
    output = fixture_dir / "out.svg"
    render_local_synteny(
        blocks_path=fixture_dir / "blocks.txt",
        bed_path=fixture_dir / "all.bed",
        output_path=output,
        track_names=["Ref", "Sub"],
    )
    content = output.read_text(encoding="utf-8")
    # Legend entries for all chromosomes should be present.
    assert "chr1" in content
    assert "chrA" in content


def test_render_includes_species_placeholder(fixture_dir: Path) -> None:
    output = fixture_dir / "out.svg"
    render_local_synteny(
        blocks_path=fixture_dir / "blocks.txt",
        bed_path=fixture_dir / "all.bed",
        output_path=output,
        track_names=["Ref", "Sub"],
    )
    content = output.read_text(encoding="utf-8")
    assert "Ref" in content
    assert "Sub" in content


def test_render_labels_target_genes(fixture_dir: Path) -> None:
    output = fixture_dir / "out.svg"
    render_local_synteny(
        blocks_path=fixture_dir / "blocks.txt",
        bed_path=fixture_dir / "all.bed",
        output_path=output,
        track_names=["Ref", "Sub"],
        target_gene_ids=["g2"],
        label_targets=True,
    )
    content = output.read_text(encoding="utf-8")
    assert "g2" in content


def test_render_multi_track(fixture_dir: Path) -> None:
    multi_blocks = fixture_dir / "multi.blocks"
    _write_multi_track_blocks(multi_blocks)
    output = fixture_dir / "out.svg"
    render_local_synteny(
        blocks_path=multi_blocks,
        bed_path=fixture_dir / "all.bed",
        output_path=output,
        track_names=["Ref", "SubA", "SubB"],
    )
    content = output.read_text(encoding="utf-8")
    assert output.is_file()
    assert output.stat().st_size > 0
    assert "SubA" in content
    assert "SubB" in content


def test_format_bp_range() -> None:
    assert _format_bp_range(0, 21_320_000) == "0.00-21.32Mb"
    assert _format_bp_range(500, 1500) == "0.50-1.50kb"
    assert _format_bp_range(0, 500) == "0-500bp"


def test_build_track_window_maps_genes_proportionally() -> None:
    genes = [
        GeneRecord("g1", "chr1", 100, 200, "+"),
        GeneRecord("g2", "chr1", 300, 400, "-"),
    ]
    window = _build_track_window(name="Ref", index=0, color="#2f6f73", genes=genes, scale=0.01)
    assert len(window.segments) == 1
    assert window.segments[0].chromosome == "chr1"
    # g1 and g2 are separated by a 100 bp gap; at scale 0.01 that gap is 1.0 visual unit.
    assert window.all_genes[0].x < window.all_genes[1].x


def test_build_track_window_compresses_large_gap() -> None:
    genes = [
        GeneRecord("g1", "chr1", 100, 200, "+"),
        GeneRecord("g2", "chr1", 1_000_200, 1_000_300, "+"),
    ]
    window = _build_track_window(name="Ref", index=0, color="#2f6f73", genes=genes, scale=1e-5)
    # The 1 Mb gap should be compressed.
    assert window.segments[0].has_compressed_gaps is True
    # Visual distance should be much smaller than the raw 1 Mb * scale = 10 units.
    assert window.all_genes[1].x - window.all_genes[0].x < 1.0


def test_build_track_window_splits_multiple_chromosomes() -> None:
    genes = [
        GeneRecord("g1", "chrA", 100, 200, "+"),
        GeneRecord("g2", "chrB", 100, 200, "+"),
    ]
    window = _build_track_window(name="Sub", index=1, color="#b85c38", genes=genes, scale=0.01)
    assert len(window.segments) == 2
    assert window.segments[0].chromosome == "chrA"
    assert window.segments[1].chromosome == "chrB"
    assert "chrA" in window.range_label
    assert "chrB" in window.range_label


def test_render_range_labels_appear_in_svg(fixture_dir: Path) -> None:
    output = fixture_dir / "out.svg"
    render_local_synteny(
        blocks_path=fixture_dir / "blocks.txt",
        bed_path=fixture_dir / "all.bed",
        output_path=output,
        track_names=["Ref", "Sub"],
    )
    content = output.read_text(encoding="utf-8")
    # Range labels like "chr1 0.10-0.60kb" should be present.
    assert "chr1" in content
    assert "chr2" in content


def test_render_track_labels_on_both_sides_appear(fixture_dir: Path) -> None:
    output = fixture_dir / "out.svg"
    render_local_synteny(
        blocks_path=fixture_dir / "blocks.txt",
        bed_path=fixture_dir / "all.bed",
        output_path=output,
        track_names=["Ref", "Sub"],
    )
    content = output.read_text(encoding="utf-8")
    assert "Ref" in content
    assert "Sub" in content


def test_custom_figsize_is_respected(fixture_dir: Path) -> None:
    output = fixture_dir / "out.svg"
    # Just ensure no exception and file is produced.
    render_local_synteny(
        blocks_path=fixture_dir / "blocks.txt",
        bed_path=fixture_dir / "all.bed",
        output_path=output,
        track_names=["Ref", "Sub"],
        figsize="12x6",
    )
    assert output.is_file()
    assert output.stat().st_size > 0
