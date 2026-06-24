"""Typed artifact bundle contracts shared by platform planning and execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

PAIRWISE_CORE_BUNDLE_TYPE = "pairwise_core"
PAIRWISE_CORE_ARTIFACT_IDS = ("blast_table", "anchors", "simple", "blocks", "merged_bed", "layout")

if TYPE_CHECKING:
    from collections.abc import Mapping


@dataclass(frozen=True)
class ArtifactBundle:
    """Reusable artifact bundle passed between platform steps and engine workflows."""

    bundle_type: str
    artifacts: dict[str, Path] = field(default_factory=dict)

    def to_manifest_json(self) -> dict[str, object]:
        """Serialize the bundle to a manifest-compatible JSON object."""

        return {
            "bundle_type": self.bundle_type,
            "artifacts": {key: str(value) for key, value in self.artifacts.items()},
        }

    def artifact_path(self, artifact_id: str) -> Path | None:
        """Return a typed path from the bundle if present."""

        return self.artifacts.get(artifact_id)


def pairwise_core_bundle_from_paths(paths: dict[str, Path]) -> ArtifactBundle:
    """Construct the standard pairwise-core bundle from reusable artifact paths."""

    return ArtifactBundle(bundle_type=PAIRWISE_CORE_BUNDLE_TYPE, artifacts=dict(paths))


def pairwise_core_bundle_from_mapping(paths: Mapping[str, str | Path]) -> ArtifactBundle:
    """Construct a pairwise-core bundle from string/path mappings."""

    artifacts = {
        key: Path(value).expanduser().resolve(strict=False)
        for key, value in paths.items()
        if key in PAIRWISE_CORE_ARTIFACT_IDS and str(value).strip()
    }
    return pairwise_core_bundle_from_paths(artifacts)
