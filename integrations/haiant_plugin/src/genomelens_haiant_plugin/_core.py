"""Shared helpers for HAIant plugin entries."""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import zipfile
from dataclasses import asdict
from pathlib import Path
from typing import Mapping, Sequence, cast


LOGGER_NAME = "genomelens_haiant_plugin"
GENOMELENS_EXE_ENV = "GENOMELENS_EXE"


class PluginError(Exception):
    """Raised when a HAIant entry cannot build a valid GenomeLens request."""


def resource_path(*parts: str | Path) -> Path:
    """Return a path inside the plugin root for source and frozen layouts."""

    if getattr(sys, "frozen", False):
        frozen_root = getattr(sys, "_MEIPASS", "")
        base = (
            Path(frozen_root) if frozen_root else Path(sys.executable).resolve().parent
        )
    else:
        base = Path(__file__).resolve().parents[2]
    return base.joinpath(*(str(part) for part in parts))


def load_params(path: str | Path) -> tuple[dict[str, object], Path]:
    """Load a params.json file and return its payload with the base directory."""

    source = Path(path).expanduser().resolve(strict=False)
    if not source.is_file():
        raise PluginError(f"params.json not found: {source}")
    try:
        payload = json.loads(source.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise PluginError(f"Invalid JSON: {source}") from exc
    if not isinstance(payload, dict):
        raise PluginError("params.json must contain a JSON object")
    return payload, source.parent


def resolve_param_path(
    base: Path,
    value: object,
    *,
    required: bool = False,
    must_exist: bool = False,
) -> str:
    """Resolve a path-like parameter relative to the params.json directory."""

    if value is None or str(value).strip() == "":
        if required:
            raise PluginError("Required path field is empty")
        return ""
    raw = Path(str(value))
    resolved = raw if raw.is_absolute() else base / raw
    resolved = resolved.expanduser().resolve(strict=False)
    if must_exist and not resolved.exists():
        raise PluginError(f"Path does not exist: {resolved}")
    return str(resolved)


def parse_bool(value: object) -> bool:
    """Parse user-facing boolean forms from HAIant params."""

    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    text = str(value).strip().lower()
    if text in {"true", "1", "yes", "on"}:
        return True
    if text in {"false", "0", "no", "off", ""}:
        return False
    raise PluginError(f"Invalid boolean value: {value}")


def _split_csv(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [item.strip() for item in str(value or "").split(",") if item.strip()]


def _optional_path(base: Path, value: object) -> str:
    return resolve_param_path(base, value, must_exist=bool(str(value or "").strip()))


def _int_value(
    value: object, *, default: int, label: str, minimum: int | None = None
) -> int:
    if value is None or str(value).strip() == "":
        resolved = default
    else:
        try:
            resolved = int(str(value).strip())
        except (TypeError, ValueError) as exc:
            raise PluginError(f"{label} must be an integer") from exc
    if minimum is not None and resolved < minimum:
        raise PluginError(f"{label} must be >= {minimum}")
    return resolved


def _float_value(value: object, *, default: float, label: str) -> float:
    if value is None or str(value).strip() == "":
        return default
    try:
        return float(str(value).strip())
    except (TypeError, ValueError) as exc:
        raise PluginError(f"{label} must be a number") from exc


def _reference_index(
    params: Mapping[str, object], species: Sequence[Mapping[str, object]]
) -> int:
    value = params.get("reference")
    if value is None or str(value).strip() == "":
        return 0
    text = str(value).strip()
    if text.isdigit():
        index = int(text) - 1
    else:
        names = [str(item.get("name") or "") for item in species]
        if text not in names:
            raise PluginError(f"Reference species not found: {text}")
        index = names.index(text)
    if not 0 <= index < len(species):
        raise PluginError(f"Reference index out of range: {value}")
    return index


def _target_gene_ids(params: Mapping[str, object]) -> list[str]:
    raw = params.get("target_gene_ids")
    if raw is None or str(raw).strip() == "":
        raw = params.get("target_genes")
    return _split_csv(raw)


def _auto_optimization(params: Mapping[str, object]) -> dict[str, bool]:
    payload = params.get("auto_optimization")
    nested = payload if isinstance(payload, dict) else {}
    return {
        "optimize_figsize": parse_bool(
            nested.get("optimize_figsize", params.get("optimize_figsize", False))
        ),
        "rewrite_layout_links": parse_bool(
            nested.get(
                "rewrite_layout_links", params.get("rewrite_layout_links", False)
            )
        ),
        "optimize_karyotype_labels": parse_bool(
            nested.get(
                "optimize_karyotype_labels",
                params.get("optimize_karyotype_labels", False),
            )
        ),
    }


def _discover_species_from_input_dir(
    base: Path, input_dir: object
) -> list[dict[str, object]]:
    """Mirror the platform auto-directory species discovery."""

    from genomelens.analysis.requests.normalization.input_resolver import (
        discover_species_from_directory,
    )

    resolved = Path(resolve_param_path(base, input_dir, required=True, must_exist=True))
    discovered = discover_species_from_directory(resolved)
    return [asdict(item) for item in discovered]


def build_species_from_params(
    params: Mapping[str, object],
    base: Path,
    mode: str | None = None,
) -> list[dict[str, object]]:
    """Build the WorkflowRequest species list from HAIant params.

    Supports explicit ``species`` list or auto-discovery from ``input_dir``.
    """

    species_payload = params.get("species")
    input_dir = params.get("input_dir")
    if isinstance(species_payload, list) and species_payload:
        resolved_mode = (mode or str(params.get("input_mode") or "bed_cds")).strip()
        species: list[dict[str, object]] = []
        for index, item in enumerate(species_payload, start=1):
            if not isinstance(item, dict):
                raise PluginError(f"species[{index}] must be an object")
            name = str(item.get("name") or f"species{index}")
            if resolved_mode == "bed_cds":
                species.append(
                    {
                        "name": name,
                        "input_mode": "bed_cds",
                        "bed": resolve_param_path(
                            base, item.get("bed"), required=True, must_exist=True
                        ),
                        "cds": resolve_param_path(
                            base, item.get("cds"), required=True, must_exist=True
                        ),
                    }
                )
                continue
            if resolved_mode == "gff_genome":
                species.append(
                    {
                        "name": name,
                        "input_mode": "gff_genome",
                        "gff": resolve_param_path(
                            base, item.get("gff"), required=True, must_exist=True
                        ),
                        "genome": resolve_param_path(
                            base, item.get("genome"), required=True, must_exist=True
                        ),
                    }
                )
                continue
            raise PluginError(f"Unsupported input_mode: {resolved_mode}")
        if len(species) < 2:
            raise PluginError("At least two species entries are required")
        return species

    if input_dir:
        return _discover_species_from_input_dir(base, input_dir)

    raise PluginError("Either input_dir or species must be provided")


def _workflow_id_from_engine_workflow(engine_workflow: str) -> str:
    """Map a JCVI engine workflow to the public WorkflowRequest workflow_id."""

    if engine_workflow == "graphics_histogram":
        return "graphics_histogram"
    if engine_workflow == "graphics_heatmap":
        return "graphics_heatmap"
    if engine_workflow == "local_synteny":
        return "local_synteny"
    return "synteny"


def _common_parameter_groups(
    params: Mapping[str, object],
    *,
    engine_workflow: str,
    target_gene_ids: list[str],
) -> dict[str, object]:
    """Build the typed WorkflowRequest parameter groups from HAIant params."""

    return {
        "synteny": {
            "align_soft": str(params.get("align_soft") or "blast"),
            "dbtype": str(params.get("dbtype") or "nucl"),
            "cscore": _float_value(params.get("cscore"), default=0.7, label="cscore"),
            "dist": _int_value(params.get("dist"), default=20, label="dist", minimum=1),
            "iter": _int_value(params.get("iter"), default=1, label="iter", minimum=1),
            "allow_simplified_fallback": parse_bool(
                params.get("allow_simplified_fallback", False)
            ),
        },
        "local_synteny": {
            "target_gene_ids": target_gene_ids,
            "up": _int_value(params.get("up"), default=20, label="up", minimum=0),
            "down": _int_value(params.get("down"), default=20, label="down", minimum=0),
            "split_targets": parse_bool(params.get("split_targets", False)),
            "label_targets": parse_bool(params.get("label_targets", False)),
            "use_native_renderer": parse_bool(
                params.get("use_native_local_synteny_renderer", False)
            ),
        },
        "plot": {
            "glyphstyle": str(params.get("glyphstyle") or ""),
            "glyphcolor": str(params.get("glyphcolor") or ""),
            "shadestyle": str(params.get("shadestyle") or ""),
            "figsize": str(params.get("figsize") or ""),
            "dpi": _int_value(params.get("dpi"), default=300, label="dpi", minimum=1),
            "auto_optimization": _auto_optimization(params),
        },
        "histogram": {},
        "heatmap": {},
        "extras": {"engine_workflow": engine_workflow},
    }


def _common_runtime(params: Mapping[str, object], base: Path) -> dict[str, object]:
    """Build the WorkflowRequest runtime block."""

    return {
        "project_config": _optional_path(base, params.get("config")),
        "engine_config": _optional_path(base, params.get("jcvi_config")),
        "jcvi_engine": _optional_path(base, params.get("jcvi_engine")),
        "blastn": _optional_path(base, params.get("blastn")),
        "makeblastdb": _optional_path(base, params.get("makeblastdb")),
        "threads": _int_value(
            params.get("threads"), default=4, label="threads", minimum=1
        ),
        "min_block_size": _int_value(
            params.get("min_block_size"),
            default=5,
            label="min_block_size",
            minimum=1,
        ),
        "log_level": str(params.get("log_level") or "INFO"),
        "verbose": parse_bool(params.get("verbose", False)),
        "console_log": parse_bool(params.get("console_log", False)),
    }


def build_workflow_request(
    params: Mapping[str, object],
    base: Path,
    *,
    workflow: str | None = None,
) -> dict[str, object]:
    """Translate HAIant params into a stable GenomeLens WorkflowRequest v2 payload."""

    engine_workflow = str(
        workflow or params.get("workflow") or "graphics_synteny"
    ).strip()
    workflow_id = _workflow_id_from_engine_workflow(engine_workflow)

    mode = str(params.get("input_mode") or "bed_cds").strip()
    species = (
        []
        if workflow_id in {"graphics_histogram", "graphics_heatmap"}
        else build_species_from_params(params, base, mode)
    )
    output_dir = Path(resolve_param_path(base, params.get("output_dir") or "output"))
    target_gene_ids = _target_gene_ids(params)
    if workflow_id == "local_synteny" and not target_gene_ids:
        raise PluginError(
            "local_synteny workflow requires target_gene_ids or target_genes"
        )

    inputs: dict[str, object] = {}
    if params.get("input_dir"):
        inputs["directory"] = resolve_param_path(base, params.get("input_dir"))

    return {
        "schema_version": 2,
        "kind": "workflow_request",
        "workflow_id": workflow_id,
        "species": species,
        "reference_index": _reference_index(params, species) if species else 0,
        "inputs": inputs,
        "parameters": _common_parameter_groups(
            params,
            engine_workflow=engine_workflow,
            target_gene_ids=target_gene_ids,
        ),
        "output": {
            "directory": str(output_dir),
            "force": parse_bool(params.get("force", True)),
            "formats": _parse_formats(params.get("formats")),
        },
        "runtime": _common_runtime(params, base),
    }


def build_histogram_workflow_request(
    params: Mapping[str, object],
    base: Path,
    *,
    input_files: Sequence[str],
) -> dict[str, object]:
    """Build a WorkflowRequest v2 payload for the histogram feature."""

    output_dir = Path(resolve_param_path(base, params.get("output_dir") or "output"))
    parameters = _common_parameter_groups(
        params,
        engine_workflow="graphics_histogram",
        target_gene_ids=[],
    )
    columns = params.get("histogram_columns")
    if isinstance(columns, list):
        parsed_columns = [int(str(column)) for column in columns]
    else:
        parsed_columns = [
            int(item.strip()) for item in str(columns or "0").split(",") if item.strip()
        ]
    parameters["histogram"] = {
        "inputs": list(input_files),
        "columns": parsed_columns or [0],
        "bins": _int_value(
            params.get("histogram_bins"),
            default=20,
            label="histogram_bins",
            minimum=1,
        ),
        "xlabel": str(params.get("histogram_xlabel") or "value"),
        "title": str(params.get("histogram_title") or ""),
        "fill": str(params.get("histogram_fill") or "white"),
    }
    return {
        "schema_version": 2,
        "kind": "workflow_request",
        "workflow_id": "graphics_histogram",
        "species": [],
        "reference_index": 0,
        "inputs": {},
        "parameters": parameters,
        "output": {
            "directory": str(output_dir),
            "force": parse_bool(params.get("force", True)),
            "formats": _parse_formats(params.get("formats")),
        },
        "runtime": _common_runtime(params, base),
    }


def build_heatmap_workflow_request(
    params: Mapping[str, object],
    base: Path,
    *,
    matrix_path: str,
) -> dict[str, object]:
    """Build a WorkflowRequest v2 payload for the heatmap feature."""

    output_dir = Path(resolve_param_path(base, params.get("output_dir") or "output"))
    parameters = _common_parameter_groups(
        params,
        engine_workflow="graphics_heatmap",
        target_gene_ids=[],
    )
    parameters["heatmap"] = {
        "matrix": matrix_path,
        "rowgroups": _optional_path(base, params.get("rowgroups")),
        "cmap": str(params.get("cmap") or ""),
        "groups": parse_bool(params.get("groups", False)),
        "horizontalbar": parse_bool(params.get("horizontalbar", False)),
    }
    return {
        "schema_version": 2,
        "kind": "workflow_request",
        "workflow_id": "graphics_heatmap",
        "species": [],
        "reference_index": 0,
        "inputs": {},
        "parameters": parameters,
        "output": {
            "directory": str(output_dir),
            "force": parse_bool(params.get("force", True)),
            "formats": _parse_formats(params.get("formats")),
        },
        "runtime": _common_runtime(params, base),
    }


def write_workflow_request(
    params: Mapping[str, object],
    base: Path,
    *,
    workflow: str | None = None,
) -> Path:
    """Write genomelens_request.json for a plugin entry."""

    request = build_workflow_request(
        params,
        base,
        workflow=workflow,
    )
    output = cast(dict[str, object], request["output"])
    output_dir = Path(str(output["directory"]))
    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / "genomelens_request.json"
    target.write_text(
        json.dumps(request, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return target


def write_request_payload(
    params: Mapping[str, object],
    base: Path,
    request: dict[str, object],
) -> Path:
    """Write a prepared WorkflowRequest payload under the configured output directory."""

    output_dir = Path(resolve_param_path(base, params.get("output_dir") or "output"))
    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / "genomelens_request.json"
    target.write_text(
        json.dumps(request, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return target


def setup_adapter_logging(
    output_dir: str | Path, *, logger_name: str = LOGGER_NAME
) -> logging.Logger:
    """Set up adapter logging under output_dir/run.log."""

    destination = Path(output_dir).expanduser().resolve(strict=False)
    destination.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    close_logging(logger_name=logger_name)
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    file_handler = logging.FileHandler(
        destination / "run.log", encoding="utf-8", mode="a"
    )
    file_handler.setFormatter(formatter)
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    return logger


def close_logging(*, logger_name: str = LOGGER_NAME) -> None:
    """Flush and close adapter log handlers."""

    logger = logging.getLogger(logger_name)
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        try:
            handler.flush()
        finally:
            handler.close()


def close_adapter_logging(logger_name: str = LOGGER_NAME) -> None:
    """Flush and close adapter log handlers."""

    close_logging(logger_name=logger_name)


def resolve_genomelens_exe(params: Mapping[str, object], base: Path) -> Path:
    """Locate the external GenomeLens executable from params or environment."""

    raw = str(
        params.get("GenomeLens_Path")
        or params.get("genomelens_exe")
        or os.environ.get(GENOMELENS_EXE_ENV, "")
    ).strip()
    if not raw:
        raise PluginError(
            "GenomeLens_Path is required: set it in params.json (GenomeLens_Path or genomelens_exe) "
            "or via GENOMELENS_EXE environment variable"
        )
    path = Path(raw)
    if not path.is_absolute():
        path = (base / path).expanduser().resolve(strict=False)
    else:
        path = path.expanduser().resolve(strict=False)
    if not path.is_file():
        raise PluginError(f"GenomeLens executable not found: {path}")
    return path


def build_analyze_run_command(
    genomelens_exe: str | Path, request_path: Path
) -> list[str]:
    """Build the unified ``<GenomeLens.exe> analyze run <request>`` argv."""

    exe = Path(genomelens_exe)
    args = ["analyze", "run", str(request_path)]
    if exe.suffix.lower() in {".cmd", ".bat"}:
        return ["cmd.exe", "/c", str(exe), *args]
    return [str(exe), *args]


def build_analyze_submodule_command(
    genomelens_exe: str | Path,
    *,
    module_id: str,
    input_ports: Mapping[str, object],
    output_dir: str | Path,
    input_dir: str | Path = "",
    params: Mapping[str, object] | None = None,
    formats: Sequence[str] | None = None,
    threads: int | None = None,
    min_block_size: int | None = None,
    force: bool = True,
) -> list[str]:
    """Build the ``<GenomeLens.exe> analyze submodule ...`` argv."""

    exe = Path(genomelens_exe)
    args = [
        "analyze",
        "submodule",
        module_id,
        "--input-ports",
        json.dumps(dict(input_ports), ensure_ascii=False),
        "--output-dir",
        str(output_dir),
    ]
    if str(input_dir).strip():
        args.extend(["--input-dir", str(input_dir)])
    if params:
        args.extend(["--params", json.dumps(dict(params), ensure_ascii=False)])
    if formats:
        args.extend(["--formats", ",".join(str(item) for item in formats)])
    if threads is not None:
        args.extend(["--threads", str(threads)])
    if min_block_size is not None:
        args.extend(["--min-block-size", str(min_block_size)])
    if force:
        args.append("--force")
    if exe.suffix.lower() in {".cmd", ".bat"}:
        return ["cmd.exe", "/c", str(exe), *args]
    return [str(exe), *args]


def _parse_formats(value: object) -> list[str]:
    """Return the selected output format as a single-item list (default svg).

    The UI exposes ``formats`` as a single-select (``customer_selector``), so
    only the first selected value is honored.  Lists are accepted defensively
    for backward compatibility, but multi-format output is intentionally not
    supported by the auto plugin.
    """

    if isinstance(value, list):
        text = str(value[0]).strip() if value else ""
    else:
        text = str(value or "").strip().split(",")[0].strip()
    return [text] if text else ["svg"]


def build_auto_jcvi_config(
    params: Mapping[str, object],
    base: Path,
    output_dir: str | Path,
) -> Path:
    """Dynamically build ``jcvi.config.json`` for the ``analyze workflow synteny`` flow.

    The config is derived from the HAIant ``params.json`` and the species auto-discovered
    from ``input_dir``.  No per-species request files are generated.
    """

    resolved_output = Path(output_dir).expanduser().resolve(strict=False)
    resolved_output.mkdir(parents=True, exist_ok=True)

    input_dir = resolve_param_path(
        base, params.get("input_dir"), required=True, must_exist=True
    )
    species = _discover_species_from_input_dir(base, input_dir)
    reference_index = _reference_index(params, species)
    reference_name = str(species[reference_index].get("name") or "")

    target_gene_ids = _target_gene_ids(params)
    workflow = "local_synteny" if target_gene_ids else "graphics_synteny"

    optimize_auto = parse_bool(params.get("optimize_auto", False))

    jcvi_config: dict[str, object] = {
        "schema_version": 2,
        "toolchain": {
            "jcvi_engine_path": "",
            "blastn_path": "",
            "makeblastdb_path": "",
            "lastal_path": "",
            "lastdb_path": "",
            "magick_path": "",
        },
        "runtime": {
            "threads": _int_value(
                params.get("threads"), default=4, label="threads", minimum=1
            ),
            "formats": _parse_formats(params.get("formats")),
        },
        "mcscan": {
            "workflow": workflow,
            "min_block_size": _int_value(
                params.get("min_block_size"),
                default=1,
                label="min_block_size",
                minimum=1,
            ),
            "align_soft": str(params.get("align_soft") or "blast"),
            "dbtype": str(params.get("dbtype") or "nucl"),
            "cscore": _float_value(params.get("cscore"), default=0.7, label="cscore"),
            "dist": _int_value(params.get("dist"), default=20, label="dist", minimum=1),
            "iter": _int_value(params.get("iter"), default=1, label="iter", minimum=1),
            "reference": reference_name,
        },
        "local_synteny": {
            "target_gene_ids": target_gene_ids,
            "up": _int_value(params.get("up"), default=20, label="up", minimum=0),
            "down": _int_value(params.get("down"), default=20, label="down", minimum=0),
            "split_targets": parse_bool(params.get("split_targets", False)),
            "label_targets": parse_bool(params.get("label_targets", False)),
            "glyphstyle": str(params.get("glyphstyle") or ""),
            "glyphcolor": str(params.get("glyphcolor") or ""),
            "shadestyle": str(params.get("shadestyle") or ""),
            "figsize": str(params.get("figsize") or ""),
            "dpi": _int_value(params.get("dpi"), default=300, label="dpi", minimum=1),
            "auto_optimization": {
                "optimize_figsize": optimize_auto,
                "rewrite_layout_links": optimize_auto,
                "optimize_karyotype_labels": optimize_auto,
            },
            "use_native_local_synteny_renderer": parse_bool(
                params.get("use_native_local_synteny_renderer", False)
            ),
        },
    }

    target = resolved_output / "jcvi.config.json"
    target.write_text(
        json.dumps(jcvi_config, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return target


def build_mcscan_jcvi_command(
    genomelens_exe: str | Path,
    input_dir: str | Path,
    output_dir: str | Path,
    jcvi_config_path: str | Path,
    *,
    workflow_id: str = "synteny",
) -> list[str]:
    """Build the ``<GenomeLens.exe> analyze workflow <workflow_id> <in> <out> --jcvi-config ...`` argv."""

    exe = Path(genomelens_exe)
    args = [
        "analyze",
        "workflow",
        workflow_id,
        str(input_dir),
        str(output_dir),
        "--jcvi-config",
        str(jcvi_config_path),
        "--force",
    ]
    if exe.suffix.lower() in {".cmd", ".bat"}:
        return ["cmd.exe", "/c", str(exe), *args]
    return [str(exe), *args]


def compress_output_intermediates(
    output_dir: str | Path,
    *,
    archive_name: str = "intermediates.zip",
    marker_name: str = "intermediates.zip.deletable",
    preserve: set[str] | None = None,
) -> Path | None:
    """Package everything except ``results`` into a zip and mark it as deletable.

    The ``results`` directory is left untouched.  After archiving, the original
    intermediate files and directories are removed so the output root only keeps
    ``results``, the archive, and a ``.deletable`` marker.
    """

    root = Path(output_dir).expanduser().resolve(strict=False)
    if not root.is_dir():
        return None

    kept = preserve or set()
    kept = {*kept, "results", archive_name, marker_name}

    items = [path for path in root.iterdir() if path.name not in kept]
    if not items:
        return None

    archive_path = root / archive_name
    marker_path = root / marker_name

    logger = logging.getLogger(LOGGER_NAME)
    logger.info("Compressing intermediate files to %s", archive_path)

    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in items:
            if path.is_file():
                zf.write(path, path.name)
            elif path.is_dir():
                for child in path.rglob("*"):
                    arcname = str(child.relative_to(root)).replace("\\", "/")
                    zf.write(child, arcname)

    for path in items:
        if path.is_file():
            path.unlink()
        elif path.is_dir():
            _rm_tree(path)

    marker_path.write_text(
        "This archive contains intermediate files that can be safely deleted.\n",
        encoding="utf-8",
    )
    logger.info("Marked intermediates as deletable: %s", archive_path)
    return archive_path


def _rm_tree(path: Path) -> None:
    """Recursively remove a directory tree."""

    for child in path.iterdir():
        if child.is_dir():
            _rm_tree(child)
        else:
            child.unlink()
    path.rmdir()


def run_process(argv: Sequence[str]) -> int:
    """Run a prepared command and return its exit code."""

    completed = subprocess.run(list(argv), shell=False, check=False)
    return int(completed.returncode)
