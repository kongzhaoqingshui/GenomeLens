"""Build validated JCVI engine manifest payloads."""

from __future__ import annotations

from pathlib import Path
from typing import cast

from genomelens._version import __version__
from genomelens.analysis.planning.models import (
    HeatmapExecutionRequest,
    HistogramExecutionRequest,
    SyntenyExecutionRequest,
)
from genomelens.artifacts.bundles import ArtifactBundle
from genomelens.contracts.species import GenomeInputSpec, PreparedGenomeInputSpec
from genomelens.engines.jcvi.command_mapping import normalize_workflow
from genomelens.engines.jcvi.path_patch import absolute_path


def _species_manifest_entry(
    species: GenomeInputSpec,
    role: str,
    prepared: PreparedGenomeInputSpec,
) -> dict[str, object]:
    return {
        "name": species.name,
        "role": role,
        "input_mode": species.mode,
        "bed": absolute_path(prepared.bed),
        "cds": absolute_path(prepared.cds),
    }


def _pairwise_artifact_manifest(artifacts: dict[str, str]) -> dict[str, str]:
    return {key: absolute_path(value) for key, value in artifacts.items() if str(value).strip()}


def _artifact_bundle_manifest(bundle: ArtifactBundle) -> dict[str, object]:
    return {
        "bundle_type": bundle.bundle_type,
        "artifacts": {key: absolute_path(value) for key, value in bundle.artifacts.items()},
    }


class JcviManifestBuilder:
    """Convert platform execution requests into engine manifest v3 payloads."""

    def build_pairwise_manifest(
        self,
        request: SyntenyExecutionRequest,
        *,
        query: PreparedGenomeInputSpec,
        subject: PreparedGenomeInputSpec,
        blastn_path: str,
        makeblastdb_path: str,
        lastal_path: str = "",
        lastdb_path: str = "",
    ) -> dict[str, object]:
        workflow = normalize_workflow(request.engine_workflow)
        task = request.task_spec
        toolchain: dict[str, object] = {
            "blastn": absolute_path(blastn_path),
            "makeblastdb": absolute_path(makeblastdb_path),
        }
        if request.align_soft == "last":
            toolchain["lastal"] = absolute_path(lastal_path)
            toolchain["lastdb"] = absolute_path(lastdb_path)

        inputs: dict[str, object] = {
            "species": [
                _species_manifest_entry(request.reference, "reference", query),
                _species_manifest_entry(request.target, "target", subject),
            ],
        }
        if request.artifact_bundles:
            inputs["artifact_bundles"] = [_artifact_bundle_manifest(bundle) for bundle in request.artifact_bundles]
        if request.precomputed_artifacts is not None:
            inputs["pairwise_artifacts"] = _pairwise_artifact_manifest(request.precomputed_artifacts.to_manifest_json())

        return {
            "schema_version": 3,
            "workflow": workflow,
            "task": {**task.to_manifest_json(), "workflow": workflow},
            "inputs": inputs,
            "species": [
                _species_manifest_entry(request.reference, "reference", query),
                _species_manifest_entry(request.target, "target", subject),
            ],
            "toolchain": toolchain,
            "parameters": self._synteny_parameters(request),
            "expected_outputs": ["blast_table", "anchors", "simple", "blocks", "figures"],
            "meta": {
                "source": "genomelens-platform",
                "shell_version": __version__,
                "platform_protocol": "task_manifest_v3",
                "species_model": "species_array",
            },
        }

    def build_histogram_manifest(self, request: HistogramExecutionRequest) -> dict[str, object]:
        workflow = normalize_workflow(request.workflow)
        return {
            "schema_version": 3,
            "workflow": workflow,
            "task": {**request.task_spec.to_manifest_json(), "workflow": workflow},
            "inputs": {"histogram_files": [absolute_path(item) for item in request.inputs]},
            "species": [],
            "toolchain": {},
            "parameters": {
                "formats": request.formats,
                "dpi": request.dpi,
                "log_level": request.log_level,
                "verbose": request.verbose,
                "histogram_columns": list(request.columns),
                "histogram_skip": request.histogram_skip,
                "histogram_bins": request.histogram_bins,
                "histogram_vmin": request.histogram_vmin,
                "histogram_vmax": request.histogram_vmax,
                "histogram_xlabel": request.histogram_xlabel,
                "histogram_title": request.histogram_title,
                "histogram_base": request.histogram_base,
                "histogram_facet": request.histogram_facet,
                "histogram_fill": request.histogram_fill,
            },
            "expected_outputs": ["figures"],
            "meta": {
                "source": "genomelens-platform",
                "shell_version": __version__,
                "platform_protocol": "task_manifest_v3",
                "input_model": "numeric_files",
            },
        }

    def build_heatmap_manifest(self, request: HeatmapExecutionRequest) -> dict[str, object]:
        parameters: dict[str, object] = {
            "formats": list(request.formats),
            "figsize": request.figsize,
            "dpi": request.dpi,
            "cmap": request.cmap,
            "groups": request.groups,
            "horizontalbar": request.horizontalbar,
            "log_level": request.log_level,
        }
        if request.rowgroups is not None:
            parameters["rowgroups"] = absolute_path(request.rowgroups)

        return {
            "schema_version": 3,
            "workflow": "graphics_heatmap",
            "task": {
                "task_id": request.task_id,
                "task_type": "plot_heatmap",
                "workflow": "graphics_heatmap",
            },
            "inputs": {"matrix": absolute_path(request.matrix)},
            "species": [],
            "toolchain": {},
            "parameters": parameters,
            "expected_outputs": ["figures", "heatmap_figures"],
            "meta": {
                "source": "genomelens-platform",
                "shell_version": __version__,
                "platform_protocol": "task_manifest_v3",
                "input_model": "matrix_csv",
            },
        }

    def build_global_karyotype_manifest(
        self,
        *,
        tracks: list[dict[str, str]],
        edges: list[dict[str, object]],
        blastn_path: str,
        makeblastdb_path: str,
        formats: list[str],
        figsize: str = "",
        dpi: int = 300,
        auto_optimization: dict[str, bool] | None = None,
        log_level: str = "INFO",
        task: dict[str, object] | None = None,
        species: list[dict[str, object]] | None = None,
    ) -> dict[str, object]:
        return {
            "schema_version": 3,
            "workflow": "graphics_karyotype_global",
            "task": task or {"workflow": "graphics_karyotype_global", "task_type": "global_synteny"},
            "inputs": {
                "tracks": [{"name": str(track["name"]), "bed": absolute_path(track["bed"])} for track in tracks],
                "edges": [
                    {
                        "i": int(cast(int, edge["i"])),
                        "j": int(cast(int, edge["j"])),
                        "simple": absolute_path(str(edge["simple"])),
                    }
                    for edge in edges
                ],
            },
            "species": species or [],
            "toolchain": {
                "blastn": absolute_path(blastn_path),
                "makeblastdb": absolute_path(makeblastdb_path),
            },
            "parameters": {
                "formats": formats,
                "figsize": figsize,
                "dpi": dpi,
                "log_level": log_level,
                "auto_optimization": dict(auto_optimization or {}),
            },
            "expected_outputs": ["global_karyotype_figures"],
            "meta": {
                "source": "genomelens-platform",
                "shell_version": __version__,
                "platform_protocol": "task_manifest_v3",
                "species_model": "multi_species_tracks",
            },
        }

    def build_multi_local_synteny_manifest(
        self,
        *,
        tracks: list[dict[str, str]],
        blocks: str | Path,
        bed: str | Path,
        formats: list[str],
        target_gene_ids: list[str],
        label_targets: bool,
        glyphstyle: str,
        glyphcolor: str,
        shadestyle: str,
        figsize: str,
        dpi: int,
        auto_optimization: dict[str, bool] | None = None,
        use_native_local_synteny_renderer: bool = False,
        task: dict[str, object] | None = None,
        species: list[dict[str, object]] | None = None,
    ) -> dict[str, object]:
        return {
            "schema_version": 3,
            "workflow": "local_synteny_multi",
            "task": task or {"workflow": "local_synteny_multi", "task_type": "multi_species_local_synteny"},
            "inputs": {
                "tracks": [{"name": str(track["name"]), "bed": absolute_path(track["bed"])} for track in tracks],
                "blocks": absolute_path(blocks),
                "bed": absolute_path(bed),
            },
            "species": species or [],
            "toolchain": {},
            "parameters": {
                "formats": formats,
                "target_gene_ids": list(target_gene_ids),
                "label_targets": label_targets,
                "glyphstyle": glyphstyle,
                "glyphcolor": glyphcolor,
                "shadestyle": shadestyle,
                "figsize": figsize,
                "dpi": dpi,
                "auto_optimization": dict(auto_optimization or {}),
                "use_native_local_synteny_renderer": use_native_local_synteny_renderer,
            },
            "expected_outputs": ["multi_species_local_figures"],
            "meta": {
                "source": "genomelens-platform",
                "shell_version": __version__,
                "platform_protocol": "task_manifest_v3",
                "species_model": "multi_species_local_tracks",
            },
        }

    @staticmethod
    def _synteny_parameters(request: SyntenyExecutionRequest) -> dict[str, object]:
        return {
            "threads": request.threads,
            "min_block_size": request.min_block_size,
            "formats": request.formats,
            "layout": absolute_path(request.layout_path),
            "seqids": absolute_path(request.seqids_path),
            "allow_simplified_fallback": request.allow_simplified_fallback,
            "align_soft": request.align_soft,
            "dbtype": request.dbtype,
            "cscore": request.cscore,
            "dist": request.dist,
            "iter": request.iter,
            "target_gene_ids": list(request.target_gene_ids),
            "up": request.up,
            "down": request.down,
            "split_targets": request.split_targets,
            "label_targets": request.label_targets,
            "glyphstyle": request.glyphstyle,
            "glyphcolor": request.glyphcolor,
            "shadestyle": request.shadestyle,
            "figsize": request.figsize,
            "dpi": request.dpi,
            "log_level": request.log_level,
            "verbose": request.verbose,
            "auto_optimization": dict(request.auto_optimization),
            "use_native_local_synteny_renderer": request.use_native_local_synteny_renderer,
        }
