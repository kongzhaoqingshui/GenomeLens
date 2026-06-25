from pathlib import Path

import pytest

from jcvi_genomelens.manifest.models import (
    ArtifactBundleSpec,
    EngineRunManifest,
    GenomeSpec,
    PairwiseArtifacts,
    ToolchainSpec,
    WorkflowOptions,
)
from jcvi_genomelens.workflows.pairwise.artifact_reuse import (
    MissingPairwiseArtifactsError,
    ensure_pairwise_artifacts,
)


def _genome(tmp_path: Path, name: str) -> GenomeSpec:
    bed = tmp_path / f"{name}.bed"
    cds = tmp_path / f"{name}.cds"
    bed.write_text("chr1\t0\t1\tgene1\n", encoding="utf-8")
    cds.write_text(f">{name}\nATGC\n", encoding="utf-8")
    return GenomeSpec(name=name, bed=bed, cds=cds)


def test_ensure_pairwise_artifacts_uses_precomputed_files(tmp_path: Path) -> None:
    query = _genome(tmp_path, "query")
    subject = _genome(tmp_path, "subject")
    blocks = tmp_path / "query.subject.blocks"
    blocks.write_text("q1\ts1\n", encoding="utf-8")

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


def test_ensure_pairwise_artifacts_raises_when_required_file_missing(tmp_path: Path) -> None:
    # 渲染层绝不自行计算：缺必需产物时报错，而不是偷偷重跑 pairwise
    query = _genome(tmp_path, "query")
    subject = _genome(tmp_path, "subject")

    manifest = EngineRunManifest(
        workflow="graphics_synteny",
        query=query,
        subject=subject,
        toolchain=ToolchainSpec(),
        options=WorkflowOptions(),
        pairwise_artifacts=PairwiseArtifacts(blocks=tmp_path / "missing.blocks"),
    )

    with pytest.raises(MissingPairwiseArtifactsError, match="blocks"):
        ensure_pairwise_artifacts(
            manifest,
            tmp_path / "out",
            required_fields=("blocks",),
        )


def test_ensure_pairwise_artifacts_raises_when_no_artifacts_declared(tmp_path: Path) -> None:
    query = _genome(tmp_path, "query")
    subject = _genome(tmp_path, "subject")

    manifest = EngineRunManifest(
        workflow="graphics_synteny",
        query=query,
        subject=subject,
        toolchain=ToolchainSpec(),
        options=WorkflowOptions(),
    )

    with pytest.raises(MissingPairwiseArtifactsError, match="anchors"):
        ensure_pairwise_artifacts(
            manifest,
            tmp_path / "out",
            required_fields=("anchors",),
        )


def test_ensure_pairwise_artifacts_uses_bundle_contract(tmp_path: Path) -> None:
    query = _genome(tmp_path, "query")
    subject = _genome(tmp_path, "subject")
    blocks = tmp_path / "bundle.blocks"
    blocks.write_text("q1\ts1\n", encoding="utf-8")

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
