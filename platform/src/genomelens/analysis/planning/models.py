"""Platform execution plan and internal request models"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from genomelens.artifacts.bundles import ArtifactBundle
from genomelens.contracts.species import AnalysisTaskSpec, GenomeInputSpec

StepKind = Literal[
    "pairwise_synteny",
    "global_karyotype",
    "multi_local_synteny",
    "graphics_histogram",
    "graphics_heatmap",
]


@dataclass(frozen=True)
class StepInputRef:
    """Reference to an upstream step artifact"""

    step_id: str
    artifact_id: str

    def to_json(self) -> dict[str, object]:
        return {"step_id": self.step_id, "artifact_id": self.artifact_id}


@dataclass(frozen=True)
class StepOutputRef:
    """Declaration of an expected step artifact"""

    artifact_id: str
    artifact_type: str
    required: bool = False

    def to_json(self) -> dict[str, object]:
        return {
            "artifact_id": self.artifact_id,
            "artifact_type": self.artifact_type,
            "required": self.required,
        }


@dataclass(frozen=True)
class PairwiseArtifactInputs:
    """Reusable pairwise-core artifacts"""

    blast_table: Path | None = None
    anchors: Path | None = None
    simple: Path | None = None
    blocks: Path | None = None
    merged_bed: Path | None = None
    layout: Path | None = None

    def to_manifest_json(self) -> dict[str, str]:
        return {key: str(value) for key, value in self.to_path_dict().items()}

    def to_path_dict(self) -> dict[str, Path]:
        data: dict[str, Path] = {}
        for key in ("blast_table", "anchors", "simple", "blocks", "merged_bed", "layout"):
            value = getattr(self, key)
            if value is not None:
                data[key] = value
        return data

    @classmethod
    def from_mapping(cls, data: Mapping[str, str | Path]) -> PairwiseArtifactInputs:
        values = {
            key: Path(value).expanduser().resolve(strict=False)
            for key, value in data.items()
            if key in {"blast_table", "anchors", "simple", "blocks", "merged_bed", "layout"} and str(value).strip()
        }
        return cls(**values)

    @property
    def has_any(self) -> bool:
        return any(getattr(self, key) is not None for key in ("blast_table", "anchors", "simple", "blocks"))


@dataclass(frozen=True)
class SyntenyExecutionRequest:
    """Internal request for synteny and MCscan-style workflows"""

    reference: GenomeInputSpec
    target: GenomeInputSpec
    outdir: Path
    additional_species: list[GenomeInputSpec] = field(default_factory=list)
    threads: int = 4
    min_block_size: int = 5
    formats: list[str] = field(default_factory=lambda: ["svg"])
    engine_path: str = ""
    engine_workflow: str = "graphics_synteny"
    blastn_path: str = ""
    makeblastdb_path: str = ""
    lastal_path: str = ""
    lastdb_path: str = ""
    layout_path: str = ""
    seqids_path: str = ""
    allow_simplified_fallback: bool = False
    force: bool = False
    precomputed_artifacts: PairwiseArtifactInputs | None = None
    artifact_bundles: list[ArtifactBundle] = field(default_factory=list)
    input_ports: dict[str, object] = field(default_factory=dict)
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
    log_level: str = "INFO"
    verbose: bool = False
    auto_optimization: dict[str, bool] = field(default_factory=dict)
    console_log: bool = False
    use_native_local_synteny_renderer: bool = False

    @property
    def species(self) -> list[GenomeInputSpec]:
        return [self.reference, self.target, *self.additional_species]

    @property
    def query(self) -> GenomeInputSpec:
        return self.reference

    @property
    def subject(self) -> GenomeInputSpec:
        return self.target

    @property
    def jcvi_engine(self) -> str:
        return self.engine_path

    @property
    def jcvi_workflow(self) -> str:
        return self.engine_workflow

    @property
    def jcvi_layout(self) -> str:
        return self.layout_path

    @property
    def jcvi_seqids(self) -> str:
        return self.seqids_path

    @property
    def task_id(self) -> str:
        names = "__".join(species.name for species in self.species)
        return f"{names}__{self.engine_workflow}"

    @property
    def task_spec(self) -> AnalysisTaskSpec:
        return AnalysisTaskSpec(
            task_id=self.task_id,
            task_type="pairwise_synteny" if len(self.species) == 2 else "multi_species_synteny",
            workflow=self.engine_workflow,
            species=self.species,
        )


@dataclass(frozen=True)
class HeatmapExecutionRequest:
    """Internal request for heatmap rendering"""

    matrix: Path
    outdir: Path
    formats: list[str] = field(default_factory=lambda: ["svg"])
    engine_path: str = ""
    figsize: str = ""
    dpi: int = 300
    cmap: str = ""
    groups: bool = False
    rowgroups: Path | None = None
    horizontalbar: bool = False
    force: bool = False
    log_level: str = "INFO"

    @property
    def workflow(self) -> str:
        return "graphics_heatmap"

    @property
    def jcvi_engine(self) -> str:
        return self.engine_path

    @property
    def task_id(self) -> str:
        return f"{self.matrix.stem}__{self.workflow}"

    @property
    def task_spec(self) -> AnalysisTaskSpec:
        return AnalysisTaskSpec(task_id=self.task_id, task_type="plot_heatmap", workflow=self.workflow, species=[])


@dataclass(frozen=True)
class HistogramExecutionRequest:
    """Internal request for histogram rendering"""

    inputs: list[Path]
    outdir: Path
    columns: list[int] = field(default_factory=lambda: [0])
    formats: list[str] = field(default_factory=lambda: ["svg"])
    engine_path: str = ""
    force: bool = False
    histogram_skip: int = 0
    histogram_bins: int = 20
    histogram_vmin: float | None = 0.0
    histogram_vmax: float | None = None
    histogram_xlabel: str = "value"
    histogram_title: str = ""
    histogram_base: int = 0
    histogram_facet: bool = False
    histogram_fill: str = "white"
    dpi: int = 300
    log_level: str = "INFO"
    verbose: bool = False
    console_log: bool = False

    @property
    def workflow(self) -> str:
        return "graphics_histogram"

    @property
    def jcvi_engine(self) -> str:
        return self.engine_path

    @property
    def task_id(self) -> str:
        stems = "__".join(path.stem for path in self.inputs)
        suffix = "cols_" + "_".join(str(item) for item in self.columns)
        return f"{stems}__{suffix}__{self.workflow}"

    @property
    def task_spec(self) -> AnalysisTaskSpec:
        return AnalysisTaskSpec(task_id=self.task_id, task_type="plot_histogram", workflow=self.workflow, species=[])


@dataclass(frozen=True)
class ExecutionStep:
    """A typed node inside an execution DAG"""

    step_id: str
    kind: StepKind
    payload: object
    depends_on: list[str] = field(default_factory=list)
    inputs: list[StepInputRef] = field(default_factory=list)
    outputs: list[StepOutputRef] = field(default_factory=list)


@dataclass(frozen=True)
class ExecutionPlan:
    """Expanded execution DAG derived from a workflow request"""

    plan_id: str
    workflow_id: str
    outdir: Path
    force: bool = False
    steps: list[ExecutionStep] = field(default_factory=list)
    reference_name: str | None = None
    target_names: list[str] = field(default_factory=list)
    optimizer_profile_id: str = ""
    shared_runtime_profile_id: str = ""
    shared_runtime_step_kinds: list[StepKind] = field(default_factory=list)
