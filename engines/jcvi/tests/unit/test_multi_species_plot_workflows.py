from pathlib import Path

from jcvi_genomelens.manifest_models import EngineEdge, EngineRunManifest, EngineTrack, ToolchainSpec, WorkflowOptions
from jcvi_genomelens.runtime.command_runner import CommandAudit
from jcvi_genomelens.workflows import graphics_karyotype_global, local_synteny_multi


def _write_bed(path: Path, *, prefix: str) -> Path:
    path.write_text(
        "\n".join(
            [
                f"{prefix}chr1\t0\t10\t{prefix}gene1\t0\t+",
                f"{prefix}chr2\t10\t20\t{prefix}gene2\t0\t+",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def _fake_synteny_step(name: str, _func, args: list[str], *, cwd: Path | None = None) -> CommandAudit:
    output_prefix = Path(args[-1])
    fmt = args[args.index("--format") + 1]
    figure = Path(f"{output_prefix}.{fmt}")
    figure.write_text("synthetic figure\n", encoding="utf-8")
    return CommandAudit(name=name, argv=[name, *args], returncode=0, cwd=str(cwd or ""))


def _fake_karyotype_step(name: str, _func, args: list[str], *, cwd: Path | None = None) -> CommandAudit:
    figure = Path(args[args.index("-o") + 1])
    figure.write_text("synthetic figure\n", encoding="utf-8")
    return CommandAudit(name=name, argv=[name, *args], returncode=0, cwd=str(cwd or ""))


def test_local_synteny_multi_rewrites_default_layout_and_optimizes_figsize(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(local_synteny_multi, "run_python_step", _fake_synteny_step)

    blocks = tmp_path / "local.blocks"
    blocks.write_text("\n".join(f"qgene{i}\tsgene{i}\ttgene{i}" for i in range(24)) + "\n", encoding="utf-8")
    bed = tmp_path / "local.bed"
    bed.write_text("chr1\t0\t10\tqgene1\t0\t+\n", encoding="utf-8")
    manifest = EngineRunManifest(
        workflow="local_synteny_multi",
        toolchain=ToolchainSpec(),
        options=WorkflowOptions(
            formats=["png"],
            optimize_figsize=True,
            rewrite_layout_links=True,
            target_gene_ids=["qgene2"],
        ),
        tracks=[
            EngineTrack("query", bed),
            EngineTrack("subject", bed),
            EngineTrack("third", bed),
        ],
        blocks=blocks,
        bed=bed,
    )

    commands, artifacts = local_synteny_multi.run(manifest, tmp_path / "engine")

    layout_path = Path(str(artifacts["multi_species_local_layout"]))
    layout_text = layout_path.read_text(encoding="utf-8")
    assert "e, 0, 1, #c8c8c8" in layout_text
    assert "e, 1, 2, #c8c8c8" in layout_text
    assert "e, 0, 2, #c8c8c8" not in layout_text
    assert artifacts["rewritten_layout_edges"] == 2
    assert artifacts["optimized_figsize"] == "8x7"
    assert "--figsize" in commands[0].argv
    assert commands[0].argv[commands[0].argv.index("--figsize") + 1] == "8x7"


def test_local_synteny_multi_keeps_explicit_figsize(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(local_synteny_multi, "run_python_step", _fake_synteny_step)

    blocks = tmp_path / "local.blocks"
    blocks.write_text("qgene1\tsgene1\ttgene1\n", encoding="utf-8")
    bed = tmp_path / "local.bed"
    bed.write_text("chr1\t0\t10\tqgene1\t0\t+\n", encoding="utf-8")
    manifest = EngineRunManifest(
        workflow="local_synteny_multi",
        toolchain=ToolchainSpec(),
        options=WorkflowOptions(
            formats=["png"],
            figsize="13x8",
            optimize_figsize=True,
            rewrite_layout_links=True,
            target_gene_ids=["qgene1"],
        ),
        tracks=[
            EngineTrack("query", bed),
            EngineTrack("subject", bed),
            EngineTrack("third", bed),
        ],
        blocks=blocks,
        bed=bed,
    )

    commands, artifacts = local_synteny_multi.run(manifest, tmp_path / "engine")

    assert "optimized_figsize" not in artifacts
    assert "--figsize" in commands[0].argv
    assert commands[0].argv[commands[0].argv.index("--figsize") + 1] == "13x8"


def test_global_karyotype_reorders_tracks_without_faking_edge_semantics(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(graphics_karyotype_global, "run_python_step", _fake_karyotype_step)

    query_bed = _write_bed(tmp_path / "query.bed", prefix="q")
    subject_bed = _write_bed(tmp_path / "subject.bed", prefix="s")
    third_bed = _write_bed(tmp_path / "third.bed", prefix="t")
    simple_a = tmp_path / "query_subject.simple"
    simple_b = tmp_path / "query_third.simple"
    simple_a.write_text("simple-a\n", encoding="utf-8")
    simple_b.write_text("simple-b\n", encoding="utf-8")
    manifest = EngineRunManifest(
        workflow="graphics_karyotype_global",
        toolchain=ToolchainSpec(),
        options=WorkflowOptions(
            formats=["png"],
            optimize_figsize=True,
            rewrite_layout_links=True,
        ),
        tracks=[
            EngineTrack("query", query_bed),
            EngineTrack("subject", subject_bed),
            EngineTrack("third", third_bed),
        ],
        edges=[
            EngineEdge(0, 1, simple_a),
            EngineEdge(0, 2, simple_b),
        ],
    )

    commands, artifacts = graphics_karyotype_global.run(manifest, tmp_path / "engine")

    layout_path = Path(str(artifacts["global_karyotype_layout"]))
    layout_text = layout_path.read_text(encoding="utf-8")
    assert artifacts["rewritten_track_order"] == ["subject", "query", "third"]
    assert artifacts["rewritten_layout_edges"] == 2
    assert f"e, 0, 1, {simple_a}" in layout_text
    assert f"e, 1, 2, {simple_b}" in layout_text
    assert f"e, 0, 2, {simple_b}" not in layout_text
    assert artifacts["optimized_figsize"] == "10x9"
    assert "--figsize" in commands[0].argv
    assert commands[0].argv[commands[0].argv.index("--figsize") + 1] == "10x9"
