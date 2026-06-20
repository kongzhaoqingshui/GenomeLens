from pathlib import Path

from jcvi_genomelens import mirrored_karyotype
from jcvi_genomelens.manifest_models import EngineRunManifest, GenomeSpec, ToolchainSpec, WorkflowOptions
from jcvi_genomelens.runtime.command_runner import CommandAudit
from jcvi_genomelens.workflows import graphics_karyotype


def _write_species(tmp_path: Path, name: str, prefix: str) -> GenomeSpec:
    bed = tmp_path / f"{name}.bed"
    cds = tmp_path / f"{name}.cds"
    bed.write_text(
        "\n".join(
            [
                f"{prefix}chr1\t0\t10\t{prefix}gene1\t0\t+",
                f"{prefix}chr2\t10\t20\t{prefix}gene2\t0\t+",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    cds.write_text(f">{prefix}gene1\nATGC\n", encoding="utf-8")
    return GenomeSpec(name=name, bed=bed, cds=cds)


def _fake_karyotype_step(name: str, _func, args: list[str], *, cwd: Path | None = None) -> CommandAudit:
    figure = Path(args[args.index("-o") + 1])
    figure.write_text("synthetic figure\n", encoding="utf-8")
    return CommandAudit(name=name, argv=[name, *args], returncode=0, cwd=str(cwd or ""))


def test_mirrored_karyotype_inferrs_opposite_label_side_from_va(tmp_path: Path) -> None:
    bed = _write_species(tmp_path, "query", "q").bed
    line = f"0.65, 0.12, 0.88, 0, #2f6f73, query, bottom, {bed}"

    layout_line = mirrored_karyotype.LayoutLine(line)

    assert layout_line.label_va == "top"


def test_mirrored_karyotype_preserves_explicit_label_va(tmp_path: Path) -> None:
    bed = _write_species(tmp_path, "query", "q").bed
    line = f"0.65, 0.12, 0.88, 0, #2f6f73, query, bottom, {bed}, bottom"

    layout_line = mirrored_karyotype.LayoutLine(line)

    assert layout_line.label_va == "bottom"


def test_pairwise_karyotype_uses_mirrored_renderer_when_fix_enabled(tmp_path: Path, monkeypatch) -> None:
    query = _write_species(tmp_path, "query", "q")
    subject = _write_species(tmp_path, "subject", "s")
    simple = tmp_path / "pair.simple"
    simple.write_text("simple\n", encoding="utf-8")

    def _fake_pairwise_run(
        _manifest: EngineRunManifest,
        _outdir: str | Path,
    ) -> tuple[list[CommandAudit], dict[str, object]]:
        return [CommandAudit(name="pairwise", argv=["pairwise"], returncode=0)], {"simple": str(simple)}

    monkeypatch.setattr(graphics_karyotype, "run_pairwise", _fake_pairwise_run)
    monkeypatch.setattr(graphics_karyotype, "run_python_step", _fake_karyotype_step)

    manifest = EngineRunManifest(
        workflow="graphics_karyotype",
        toolchain=ToolchainSpec(),
        options=WorkflowOptions(
            formats=["png"],
            auto_optimization={"optimize_karyotype_labels": True},
        ),
        query=query,
        subject=subject,
    )

    commands, artifacts = graphics_karyotype.run(manifest, tmp_path / "engine")

    layout_path = Path(str(artifacts["karyotype_layout"]))
    lines = layout_path.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "# y, xstart, xend, rotation, color, label, va, bed, label_va"
    assert "0.12, 0.88" in lines[1]
    assert lines[1].endswith(", top")
    assert lines[2].endswith(", bottom")
    assert artifacts["karyotype_renderer_variant"] == "mirrored"
    assert artifacts["optimize_karyotype_labels"] is True
    assert commands[-1].name == "jcvi.graphics.karyotype"
