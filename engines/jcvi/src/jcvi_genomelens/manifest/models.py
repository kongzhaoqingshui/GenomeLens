"""Validated JCVI engine manifest dataclasses"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class GenomeSpec:
    """Prepared BED/CDS inputs for a species"""

    name: str
    bed: Path
    cds: Path


@dataclass(frozen=True)
class ToolchainSpec:
    """Resolved executable paths for the engine runtime"""

    blastn: Path | None = None
    makeblastdb: Path | None = None
    lastal: Path | None = None
    lastdb: Path | None = None


@dataclass(frozen=True)
class PairwiseArtifacts:
    """Reusable pairwise-core artifacts"""

    blast_table: Path | None = None
    anchors: Path | None = None
    simple: Path | None = None
    blocks: Path | None = None
    merged_bed: Path | None = None
    layout: Path | None = None


@dataclass(frozen=True)
class ArtifactBundleSpec:
    """Generic reusable artifact bundle loaded from manifest inputs"""

    bundle_type: str
    artifacts: dict[str, Path] = field(default_factory=dict)

    def artifact_path(self, artifact_id: str) -> Path | None:
        return self.artifacts.get(artifact_id)


@dataclass(frozen=True)
class WorkflowOptions:
    """Resolved workflow options passed from the platform manifest"""

    threads: int = 4
    min_block_size: int = 5
    formats: list[str] = field(default_factory=lambda: ["svg"])
    layout: Path | None = None
    seqids: Path | None = None
    allow_simplified_fallback: bool = False
    align_soft: str = "blast"
    dbtype: str = "nucl"
    cscore: float = 0.7
    dist: int = 20
    iter: int = 1
    target_gene_ids: list[str] = field(default_factory=list)
    up: int = 20
    down: int = 20
    split_targets: bool = False
    label_targets: bool = False
    glyphstyle: str = ""
    glyphcolor: str = ""
    shadestyle: str = ""
    figsize: str = ""
    dpi: int = 300
    cmap: str = ""
    groups: bool = False
    rowgroups: Path | None = None
    horizontalbar: bool = False
    log_level: str = "INFO"
    verbose: bool = False
    auto_optimization: dict[str, bool] = field(default_factory=dict)
    use_native_local_synteny_renderer: bool = False
    histogram_inputs: list[Path] = field(default_factory=list)
    histogram_columns: list[int] = field(default_factory=lambda: [0])
    histogram_skip: int = 0
    histogram_bins: int = 20
    histogram_vmin: float | None = 0.0
    histogram_vmax: float | None = None
    histogram_xlabel: str = "value"
    histogram_title: str = ""
    histogram_base: int = 0
    histogram_facet: bool = False
    histogram_fill: str = "white"


@dataclass(frozen=True)
class EngineTrack:
    """One species track in a multi-species graphic workflow"""

    name: str
    bed: Path


@dataclass(frozen=True)
class EngineEdge:
    """Track-to-track connection consumed by global karyotype workflows"""

    i: int
    j: int
    simple: Path


@dataclass(frozen=True)
class EngineRunManifest:
    """Validated engine manifest"""

    workflow: str
    toolchain: ToolchainSpec
    options: WorkflowOptions
    query: GenomeSpec | None = None
    subject: GenomeSpec | None = None
    schema_version: int = 3
    task: dict[str, object] = field(default_factory=dict)
    species: list[dict[str, object]] = field(default_factory=list)
    expected_outputs: list[str] = field(default_factory=list)
    meta: dict[str, object] = field(default_factory=dict)
    tracks: list[EngineTrack] = field(default_factory=list)
    edges: list[EngineEdge] = field(default_factory=list)
    artifact_bundles: list[ArtifactBundleSpec] = field(default_factory=list)
    pairwise_artifacts: PairwiseArtifacts | None = None
    blocks: Path | None = None
    bed: Path | None = None
    matrix: Path | None = None
