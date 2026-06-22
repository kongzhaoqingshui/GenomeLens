from pathlib import Path

import pytest

from jcvi_genomelens.graphics.local_synteny_renderer import (
    GeneRecord,
    MappedGene,
    PositionedGene,
    _build_track_window,
    _compute_layout,
    _effective_dpi,
    _format_bp_range,
    _label_positions_for_segments,
    _layout_visual_audit,
    _read_bed,
    _read_blocks,
    _ribbon_endpoint_pairs,
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
    # Target genes are shown in the bottom colour legend, not as star markers.
    assert "g2" in content
    assert "g5" in content
    assert "#000000" not in content


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


def test_compute_layout_links_only_adjacent_tracks(fixture_dir: Path) -> None:
    multi_blocks = fixture_dir / "multi.blocks"
    _write_multi_track_blocks(multi_blocks)

    layout = _compute_layout(multi_blocks, fixture_dir / "all.bed", ["Ref", "SubA", "SubB"], [])
    links = {(link.left_track, link.right_track, link.left_gene, link.right_gene) for link in layout.links}

    assert links == {
        (0, 1, "g1", "s1"),
        (1, 2, "s1", "s3"),
        (0, 1, "g2", "s2"),
    }
    assert (0, 2, "g1", "s3") not in links


def test_format_bp_range() -> None:
    assert _format_bp_range(0, 21_320_000) == "0.00-21.32Mb"
    assert _format_bp_range(18_330_000, 7_500_000) == "18.33-7.50Mb"
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


def test_compute_layout_splits_subject_cross_chromosome_segments(fixture_dir: Path) -> None:
    layout = _compute_layout(
        fixture_dir / "blocks.txt",
        fixture_dir / "all.bed",
        ["Ref", "Sub"],
        [],
    )

    subject = layout.tracks[1]
    assert [segment.chromosome for segment in subject.segments] == ["chrA", "chrB"]
    assert {link.right_gene for link in layout.links} == {"s1", "s2", "s3", "s4"}


def test_compute_layout_maps_reference_by_bed_coordinates(tmp_path: Path) -> None:
    bed = tmp_path / "all.bed"
    bed.write_text(
        "\n".join(
            [
                "qchr\t0\t10\tq1\t0\t+",
                "qchr\t20\t30\tq2\t0\t+",
                "qchr\t1000\t1010\tq3\t0\t+",
                "schr\t0\t10\ts1\t0\t+",
                "schr\t20\t30\ts2\t0\t+",
                "schr\t40\t50\ts3\t0\t+",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    blocks = tmp_path / "blocks.txt"
    blocks.write_text("q1\ts1\nq2\ts2\nq3\ts3\n", encoding="utf-8")

    layout = _compute_layout(blocks, bed, ["Ref", "Sub"], [])

    xs = [mapped.x for mapped in layout.tracks[0].all_genes]
    first_gap = xs[1] - xs[0]
    second_gap = xs[2] - xs[1]
    assert second_gap > first_gap * 20


def test_compute_layout_scales_subject_chromosome_segments_by_bed_span(tmp_path: Path) -> None:
    bed = tmp_path / "all.bed"
    bed.write_text(
        "\n".join(
            [
                "qchr\t0\t10\tq1\t0\t+",
                "qchr\t1000\t1010\tq2\t0\t+",
                "short\t0\t10\ts1\t0\t+",
                "long\t0\t1000\ts2\t0\t+",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    blocks = tmp_path / "blocks.txt"
    blocks.write_text("q1\ts1\nq2\ts2\n", encoding="utf-8")

    layout = _compute_layout(blocks, bed, ["Ref", "Sub"], [])

    widths = {segment.chromosome: segment.visual_end - segment.visual_start for segment in layout.tracks[1].segments}
    assert widths["long"] > widths["short"] * 5


def test_compute_layout_scales_track_lengths_across_species_by_bed_span(tmp_path: Path) -> None:
    bed = tmp_path / "all.bed"
    bed.write_text(
        "\n".join(
            [
                "qchr\t0\t10\tq1\t0\t+",
                "qchr\t1000\t1010\tq2\t0\t+",
                "schr\t0\t10\ts1\t0\t+",
                "schr\t100\t110\ts2\t0\t+",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    blocks = tmp_path / "blocks.txt"
    blocks.write_text("q1\ts1\nq2\ts2\n", encoding="utf-8")

    layout = _compute_layout(blocks, bed, ["Ref", "Sub"], [])

    reference_width = layout.tracks[0].segments[0].visual_end - layout.tracks[0].segments[0].visual_start
    subject_width = layout.tracks[1].segments[0].visual_end - layout.tracks[1].segments[0].visual_start
    assert subject_width < reference_width * 0.35


def test_compute_layout_centers_tracks_after_scaling(tmp_path: Path) -> None:
    bed = tmp_path / "all.bed"
    bed.write_text(
        "\n".join(
            [
                "qchr\t0\t10\tq1\t0\t+",
                "qchr\t1000\t1010\tq2\t0\t+",
                "schr\t0\t10\ts1\t0\t+",
                "schr\t100\t110\ts2\t0\t+",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    blocks = tmp_path / "blocks.txt"
    blocks.write_text("q1\ts1\nq2\ts2\n", encoding="utf-8")

    layout = _compute_layout(blocks, bed, ["Ref", "Sub"], [])
    audit = _layout_visual_audit(layout)
    centers = [track["center"] for track in audit["tracks"]]

    assert centers == pytest.approx([0.48, 0.48], abs=1e-6)


def test_compressed_background_gaps_do_not_expand_track_length(tmp_path: Path) -> None:
    bed = tmp_path / "all.bed"
    subject_genes = [f"schr\t{i * 10000}\t{i * 10000 + 20}\ts{i}\t0\t+" for i in range(80)]
    bed.write_text(
        "\n".join(
            [
                "qchr\t0\t20\tq1\t0\t+",
                "qchr\t2000000\t2000020\tq2\t0\t+",
                *subject_genes,
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    blocks = tmp_path / "blocks.txt"
    blocks.write_text("q1\ts0\nq2\ts79\n", encoding="utf-8")

    layout = _compute_layout(blocks, bed, ["Ref", "Sub"], [])

    reference_width = layout.tracks[0].segments[0].visual_end - layout.tracks[0].segments[0].visual_start
    subject_width = layout.tracks[1].segments[0].visual_end - layout.tracks[1].segments[0].visual_start
    assert subject_width < reference_width * 0.50


def test_short_segment_expands_to_flanking_context_and_marks_truncation(tmp_path: Path) -> None:
    bed = tmp_path / "all.bed"
    subject_genes = [f"schr\t{i * 100}\t{i * 100 + 20}\ts{i}\t0\t+" for i in range(60)]
    bed.write_text(
        "\n".join(
            [
                "qchr\t0\t20\tq1\t0\t+",
                *subject_genes,
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    blocks = tmp_path / "blocks.txt"
    blocks.write_text("q1\ts30\n", encoding="utf-8")

    layout = _compute_layout(blocks, bed, ["Ref", "Sub"], [])
    segment = layout.tracks[1].segments[0]

    assert len(segment.genes) >= 41
    assert segment.left_truncated is True
    assert segment.right_truncated is True


def test_target_segment_reverses_when_anchor_order_is_descending(tmp_path: Path) -> None:
    bed = tmp_path / "all.bed"
    bed.write_text(
        "\n".join(
            [
                "qchr\t0\t20\tq1\t0\t+",
                "qchr\t1000\t1020\tq2\t0\t+",
                "schr\t0\t20\ts2\t0\t+",
                "schr\t1000\t1020\ts1\t0\t+",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    blocks = tmp_path / "blocks.txt"
    blocks.write_text("q1\ts1\nq2\ts2\n", encoding="utf-8")

    layout = _compute_layout(blocks, bed, ["Ref", "Sub"], [])
    segment = layout.tracks[1].segments[0]
    positions = {mapped.gene.accn: mapped for mapped in segment.genes}

    assert segment.reversed is True
    assert segment.start_bp > segment.end_bp
    assert _format_bp_range(segment.start_bp, segment.end_bp) == "1.02-0.00kb"
    assert positions["s1"].x < positions["s2"].x
    assert positions["s1"].display_strand == "-"


def test_target_track_segments_follow_leftmost_orientation(tmp_path: Path) -> None:
    bed = tmp_path / "all.bed"
    bed.write_text(
        "\n".join(
            [
                "qchr\t0\t20\tq1\t0\t+",
                "qchr\t100\t120\tq2\t0\t+",
                "qchr\t1000\t1020\tq3\t0\t+",
                "qchr\t1100\t1120\tq4\t0\t+",
                "schrA\t0\t20\ts1\t0\t+",
                "schrA\t100\t120\ts2\t0\t+",
                "schrB\t0\t20\ts4\t0\t+",
                "schrB\t100\t120\ts3\t0\t+",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    blocks = tmp_path / "blocks.txt"
    blocks.write_text("q1\ts1\nq2\ts2\nq3\ts3\nq4\ts4\n", encoding="utf-8")

    layout = _compute_layout(blocks, bed, ["Ref", "Sub"], [])
    subject = layout.tracks[1]

    assert len(subject.segments) == 2
    assert [segment.reversed for segment in subject.segments] == [False, False]
    assert all(segment.start_bp < segment.end_bp for segment in subject.segments)


def test_compute_layout_keeps_multiple_chromosomes_on_one_row(tmp_path: Path) -> None:
    bed = tmp_path / "all.bed"
    bed_lines = [f"qchr\t{i * 10}\t{i * 10 + 5}\tq{i}\t0\t+" for i in range(24)]
    bed_lines.extend(f"schr{i}\t0\t10\ts{i}\t0\t+" for i in range(24))
    bed.write_text("\n".join(bed_lines) + "\n", encoding="utf-8")
    blocks = tmp_path / "blocks.txt"
    blocks.write_text("\n".join(f"q{i}\ts{i}" for i in range(24)) + "\n", encoding="utf-8")

    layout = _compute_layout(blocks, bed, ["Ref", "Sub"], [])

    subject = layout.tracks[1]
    assert len(subject.segments) == 24
    assert subject.lane_count == 1
    assert {segment.lane for segment in subject.segments} == {0}
    ordered_segments = subject.segments
    for left, right in zip(ordered_segments, ordered_segments[1:], strict=False):
        assert left.visual_end <= right.visual_start


def test_compute_layout_marks_long_anchor_free_gap(tmp_path: Path) -> None:
    bed = tmp_path / "all.bed"
    bed.write_text(
        "\n".join(
            [
                "qchr\t0\t10\tq1\t0\t+",
                "qchr\t10\t20\tq2\t0\t+",
                "schr\t0\t10\ts1\t0\t+",
                "schr\t2000000\t2000010\ts2\t0\t+",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    blocks = tmp_path / "blocks.txt"
    blocks.write_text("q1\ts1\nq2\ts2\n", encoding="utf-8")

    layout = _compute_layout(blocks, bed, ["Ref", "Sub"], [])

    segment = layout.tracks[1].segments[0]
    assert segment.has_compressed_gaps is True
    assert segment.gap_markers
    assert segment.visual_end - segment.visual_start < 0.25


def test_compute_layout_handles_scoped_ids_and_missing_values(tmp_path: Path) -> None:
    bed = tmp_path / "all.bed"
    bed.write_text(
        "\n".join(
            [
                "qchr\t0\t10\tquery__q1\t0\t+",
                "qchr\t10\t20\tquery__q2\t0\t+",
                "schr\t0\t10\tsubject__s1\t0\t+",
                "tchr\t0\t10\tthird__t1\t0\t+",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    blocks = tmp_path / "blocks.txt"
    blocks.write_text("r*query__q1\tsubject__s1\t.\nquery__q2\t.\tthird__t1\n", encoding="utf-8")

    layout = _compute_layout(blocks, bed, ["query", "subject", "third"], ["query__q1"])

    assert "query__q1" in layout.target_gene_ids
    assert [segment.chromosome for segment in layout.tracks[1].segments] == ["schr"]
    assert [segment.chromosome for segment in layout.tracks[2].segments] == ["tchr"]
    assert {(link.left_gene, link.right_gene) for link in layout.links} == {
        ("query__q1", "subject__s1"),
    }


def test_chromosome_label_positions_follow_segment_count_rules(fixture_dir: Path) -> None:
    layout = _compute_layout(
        fixture_dir / "blocks.txt",
        fixture_dir / "all.bed",
        ["Ref", "Sub"],
        [],
    )

    two_segment_track = layout.tracks[1]
    two_positions = _label_positions_for_segments(two_segment_track, set())
    assert two_positions[0][0] < two_segment_track.segments[0].visual_start
    assert two_positions[1][0] > two_segment_track.segments[1].visual_end

    three_segment_track = layout.tracks[0]
    three_positions = _label_positions_for_segments(three_segment_track, set())
    assert all(position[1] > three_segment_track.y for position in three_positions.values())


def test_ribbon_endpoint_pairs_reverse_inversions() -> None:
    left = PositionedGene(MappedGene(GeneRecord("a", "chr", 0, 100, "+"), x=0.20, width=0.04), y=0.8)
    right_forward = PositionedGene(MappedGene(GeneRecord("b", "chr", 0, 100, "+"), x=0.30, width=0.04), y=0.6)
    right_reverse = PositionedGene(MappedGene(GeneRecord("c", "chr", 0, 100, "-"), x=0.30, width=0.04), y=0.6)

    _left_a, _left_b, right_a, right_b = _ribbon_endpoint_pairs(left, right_forward)
    _inv_left_a, _inv_left_b, inv_right_a, inv_right_b = _ribbon_endpoint_pairs(left, right_reverse)

    assert right_a[0] < right_b[0]
    assert inv_right_a[0] > inv_right_b[0]


def test_render_uses_target_legend_and_no_pair_cloud(fixture_dir: Path) -> None:
    output = fixture_dir / "out.svg"
    render_local_synteny(
        blocks_path=fixture_dir / "blocks.txt",
        bed_path=fixture_dir / "all.bed",
        output_path=output,
        track_names=["Ref", "Sub"],
        target_gene_ids=["g2"],
    )

    content = output.read_text(encoding="utf-8")
    assert "g2" in content
    assert "#b8b8b8" not in content
    assert "#fff8dc" not in content


def test_effective_dpi_doubles_default_raster_quality() -> None:
    assert _effective_dpi(300, "png") == 900
    assert _effective_dpi(900, "png") == 900
    assert _effective_dpi(300, "svg") == 300
