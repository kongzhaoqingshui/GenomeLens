from pathlib import Path

from jcvi_genomelens.manifest.models import (
    ArtifactBundleSpec,
    EngineRunManifest,
    GenomeSpec,
    PairwiseArtifacts,
    ToolchainSpec,
    WorkflowOptions,
)
from jcvi_genomelens.workflows.pairwise.artifact_reuse import ensure_pairwise_artifacts


def _genome(tmp_path: Path, name: str) -> GenomeSpec:
    bed = tmp_path / f"{name}.bed"
    cds = tmp_path / f"{name}.cds"
    bed.write_text("chr1\t0\t1\tgene1\n", encoding="utf-8")
    cds.write_text(f">{name}\nATGC\n", encoding="utf-8")
    return GenomeSpec(name=name, bed=bed, cds=cds)


def test_ensure_pairwise_artifacts_uses_precomputed_files(monkeypatch, tmp_path: Path) -> None:
    query = _genome(tmp_path, "query")
    subject = _genome(tmp_path, "subject")
    blocks = tmp_path / "query.subject.blocks"
    blocks.write_text("q1\ts1\n", encoding="utf-8")

    def fail_run_pairwise(*args, **kwargs):  # noqa: ANN002, ANN003
        raise AssertionError("run_pairwise should not be called")

    monkeypatch.setattr(
        "jcvi_genomelens.workflows.pairwise.artifact_reuse.run_pairwise",
        fail_run_pairwise,
    )

    manifest = EngineRunManifest(
        workflow="graphics_synteny",
        query=query,
        subject=subject,
        toolchain=ToolchainSpec(),
        options=WorkflowOptions(),
        pairwise_artifacts=PairwiseArtifacts(blocks=blocks),
    )

    commands, artifacts = ensure_pairwise_artifacts(
        manifest,
        tmp_path / "out",
        required_fields=("blocks",),
        ensure_merged_bed=True,
    )

    assert len(commands) == 1
    assert Path(str(artifacts["blocks"])) == blocks.resolve(strict=False)
    assert Path(str(artifacts["merged_bed"])).is_file()


def test_ensure_pairwise_artifacts_falls_back_when_required_file_missing(monkeypatch, tmp_path: Path) -> None:
    query = _genome(tmp_path, "query")
    subject = _genome(tmp_path, "subject")
    calls: list[str] = []

    def fake_run_pairwise(*args, **kwargs):  # noqa: ANN002, ANN003
        calls.append("run")
        return [], {"blocks": str(tmp_path / "fallback.blocks")}

    monkeypatch.setattr(
        "jcvi_genomelens.workflows.pairwise.artifact_reuse.run_pairwise",
        fake_run_pairwise,
    )

    manifest = EngineRunManifest(
        workflow="graphics_synteny",
        query=query,
        subject=subject,
        toolchain=ToolchainSpec(),
        options=WorkflowOptions(),
        pairwise_artifacts=PairwiseArtifacts(blocks=tmp_path / "missing.blocks"),
    )

    commands, artifacts = ensure_pairwise_artifacts(
        manifest,
        tmp_path / "out",
        required_fields=("blocks",),
    )

    assert calls == ["run"]
    assert commands == []
    assert artifacts["blocks"] == str(tmp_path / "fallback.blocks")


def test_ensure_pairwise_artifacts_uses_bundle_contract(monkeypatch, tmp_path: Path) -> None:
    query = _genome(tmp_path, "query")
    subject = _genome(tmp_path, "subject")
    blocks = tmp_path / "bundle.blocks"
    blocks.write_text("q1\ts1\n", encoding="utf-8")

    def fail_run_pairwise(*args, **kwargs):  # noqa: ANN002, ANN003
        raise AssertionError("run_pairwise should not be called")

    monkeypatch.setattr(
        "jcvi_genomelens.workflows.pairwise.artifact_reuse.run_pairwise",
        fail_run_pairwise,
    )

    manifest = EngineRunManifest(
        workflow="graphics_synteny",
        query=query,
        subject=subject,
        toolchain=ToolchainSpec(),
        options=WorkflowOptions(),
        artifact_bundles=[
            ArtifactBundleSpec(
                bundle_type="pairwise_core",
                artifacts={"blocks": blocks},
            )
        ],
    )

    commands, artifacts = ensure_pairwise_artifacts(
        manifest,
        tmp_path / "out",
        required_fields=("blocks",),
    )

    assert commands == []
    assert Path(str(artifacts["blocks"])) == blocks.resolve(strict=False)
