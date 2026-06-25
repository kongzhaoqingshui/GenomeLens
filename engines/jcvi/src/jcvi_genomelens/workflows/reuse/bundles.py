"""JCVI workflow 共享产物包(bundle)辅助函数"""

from __future__ import annotations

from jcvi_genomelens.manifest.models import ArtifactBundleSpec, EngineRunManifest, PairwiseArtifacts

PAIRWISE_CORE_BUNDLE_TYPE = "pairwise_core"
PAIRWISE_CORE_ARTIFACT_IDS = ("blast_table", "anchors", "simple", "blocks", "merged_bed", "layout")


def find_bundle(bundles: list[ArtifactBundleSpec], bundle_type: str) -> ArtifactBundleSpec | None:
    """返回首个匹配指定类型的 bundle"""

    return next((bundle for bundle in bundles if bundle.bundle_type == bundle_type), None)


def pairwise_artifacts_from_bundles(bundles: list[ArtifactBundleSpec]) -> PairwiseArtifacts | None:
    """从通用 bundle 列表解析 pairwise 产物"""

    bundle = find_bundle(bundles, PAIRWISE_CORE_BUNDLE_TYPE)
    if bundle is None:
        return None

    artifacts = PairwiseArtifacts(
        blast_table=bundle.artifact_path("blast_table"),
        anchors=bundle.artifact_path("anchors"),
        simple=bundle.artifact_path("simple"),
        blocks=bundle.artifact_path("blocks"),
        merged_bed=bundle.artifact_path("merged_bed"),
        layout=bundle.artifact_path("layout"),
    )
    if not any(getattr(artifacts, key) is not None for key in PAIRWISE_CORE_ARTIFACT_IDS):
        return None
    return artifacts


def pairwise_artifacts_from_manifest(manifest: EngineRunManifest) -> PairwiseArtifacts | None:
    """从 legacy 或 bundle 输入中解析 pairwise 产物"""

    return manifest.pairwise_artifacts or pairwise_artifacts_from_bundles(manifest.artifact_bundles)


def pairwise_core_bundle_from_artifacts(artifacts: PairwiseArtifacts) -> ArtifactBundleSpec:
    """将 legacy pairwise 产物转换为通用 bundle 规格"""

    return ArtifactBundleSpec(
        bundle_type=PAIRWISE_CORE_BUNDLE_TYPE,
        artifacts={key: value for key in PAIRWISE_CORE_ARTIFACT_IDS if (value := getattr(artifacts, key)) is not None},
    )
