"""Shared helpers for HAIant plugin entries."""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Collection, Mapping, Sequence, cast


LOGGER_NAME = "genomelens_haiant_plugin"
PLUGIN_RUNTIME_ENV = "GENOMELENS_PLUGIN_RUNTIME"
GLJCVIMCSCAN_HOME_ENV = "GLJCVIMCSCAN_HOME"
GENOMELENS_EXE_ENV = "GENOMELENS_EXE"
SUPPORTED_WORKFLOWS = {"graphics_synteny"}
_GENOMELENS_SHELL_CANDIDATES = ("genomelens.cmd", "genomelens.exe", "genomelens")
_LEGACY_RUNTIME_CANDIDATE = "GenomeLens-runtime.exe"


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


def plugin_root() -> Path:
    """Return the plugin root directory."""

    return resource_path()


def runtime_executable() -> Path:
    """Locate the bundled legacy GenomeLens runtime executable."""

    env = os.environ.get(PLUGIN_RUNTIME_ENV, "").strip()
    if env:
        return Path(env).expanduser().resolve(strict=False)
    return plugin_root() / "runtime" / "GenomeLens" / _LEGACY_RUNTIME_CANDIDATE


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
        "trim_cross_chromosome_blocks": parse_bool(
            nested.get(
                "trim_cross_chromosome_blocks",
                params.get("trim_cross_chromosome_blocks", False),
            )
        ),
    }


def _histogram_columns(value: object) -> list[int]:
    raw = _split_csv(value)
    if not raw:
        return [0]
    columns: list[int] = []
    for item in raw:
        try:
            columns.append(int(item))
        except ValueError as exc:
            raise PluginError(f"Invalid histogram column: {item}") from exc
    return columns


def _optional_float(value: object) -> float | None:
    if value is None or str(value).strip() == "":
        return None
    try:
        return float(str(value).strip())
    except (TypeError, ValueError) as exc:
        raise PluginError(f"Invalid numeric value: {value}") from exc


def _discover_species_from_input_dir(base: Path, input_dir: object) -> list[dict[str, object]]:
    """Mirror the ``analyze mcscan jcvi`` auto-directory species discovery."""

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
    """Build the AnalysisRequest species list from HAIant params.

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


def build_analysis_request(
    params: Mapping[str, object],
    base: Path,
    *,
    workflow: str | None = None,
    supported_workflows: Collection[str] | None = None,
) -> dict[str, object]:
    """Translate HAIant params into a stable GenomeLens AnalysisRequest payload."""

    resolved_workflow = str(
        workflow or params.get("workflow") or "graphics_synteny"
    ).strip()
    if supported_workflows is not None and resolved_workflow not in supported_workflows:
        allowed = ", ".join(sorted(supported_workflows))
        raise PluginError(
            f"Unsupported HAIant workflow: {resolved_workflow}. Supported workflow: {allowed}"
        )

    mode = str(params.get("input_mode") or "bed_cds").strip()
    species = build_species_from_params(params, base, mode)
    output_dir = Path(resolve_param_path(base, params.get("output_dir") or "output"))
    target_gene_ids = _target_gene_ids(params)
    if resolved_workflow == "local_synteny" and not target_gene_ids:
        raise PluginError(
            "local_synteny workflow requires target_gene_ids or target_genes"
        )

    request: dict[str, object] = {
        "schema_version": 1,
        "kind": "analysis_request",
        "method": "mcscan",
        "input": {
            "mode": mode,
            "directory": "",
            "species": species,
            "reference_index": _reference_index(params, species),
        },
        "output": {
            "directory": str(output_dir),
            "force": parse_bool(params.get("force", True)),
            "formats": _split_csv(params.get("formats") or "png") or ["png"],
        },
        "config": {
            "project_config": _optional_path(base, params.get("config")),
            "method_config": _optional_path(base, params.get("jcvi_config")),
        },
        "options": {
            "preset": str(params.get("preset") or "auto"),
            "threads": _int_value(
                params.get("threads"), default=4, label="threads", minimum=1
            ),
            "min_block_size": _int_value(
                params.get("min_block_size"),
                default=5,
                label="min_block_size",
                minimum=1,
            ),
        },
        "method_config": {
            "workflow": resolved_workflow,
            "jcvi_engine": _optional_path(base, params.get("jcvi_engine")),
            "blastn": _optional_path(base, params.get("blastn")),
            "makeblastdb": _optional_path(base, params.get("makeblastdb")),
            "jcvi_layout": _optional_path(base, params.get("jcvi_layout")),
            "jcvi_seqids": _optional_path(base, params.get("jcvi_seqids")),
            "allow_simplified_fallback": parse_bool(
                params.get("allow_simplified_fallback", False)
            ),
            "align_soft": str(params.get("align_soft") or "blast"),
            "dbtype": str(params.get("dbtype") or "nucl"),
            "cscore": _float_value(params.get("cscore"), default=0.7, label="cscore"),
            "dist": _int_value(params.get("dist"), default=20, label="dist", minimum=1),
            "iter": _int_value(params.get("iter"), default=1, label="iter", minimum=1),
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
            "auto_optimization": _auto_optimization(params),
            "histogram_inputs": _split_csv(params.get("histogram_inputs")),
            "histogram_columns": _histogram_columns(params.get("histogram_columns")),
            "histogram_skip": _int_value(
                params.get("histogram_skip"), default=0, label="histogram_skip", minimum=0
            ),
            "histogram_bins": _int_value(
                params.get("histogram_bins"), default=20, label="histogram_bins", minimum=1
            ),
            "histogram_vmin": _optional_float(params.get("histogram_vmin")),
            "histogram_vmax": _optional_float(params.get("histogram_vmax")),
            "histogram_xlabel": str(params.get("histogram_xlabel") or "value"),
            "histogram_title": str(params.get("histogram_title") or ""),
            "histogram_base": _int_value(
                params.get("histogram_base"), default=0, label="histogram_base", minimum=0
            ),
            "histogram_facet": parse_bool(params.get("histogram_facet", False)),
            "histogram_fill": str(params.get("histogram_fill") or "white"),
        },
    }
    return request


def write_analysis_request(
    params: Mapping[str, object],
    base: Path,
    *,
    workflow: str | None = None,
    supported_workflows: Collection[str] | None = None,
) -> Path:
    """Write genomelens_request.json for a plugin entry."""

    request = build_analysis_request(
        params,
        base,
        workflow=workflow,
        supported_workflows=supported_workflows,
    )
    output = cast(dict[str, object], request["output"])
    output_dir = Path(str(output["directory"]))
    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / "genomelens_request.json"
    target.write_text(
        json.dumps(request, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return target


def write_runtime_request(params: Mapping[str, object], base: Path) -> Path:
    """Write the legacy graphics_synteny request for the single-package plugin."""

    return write_analysis_request(params, base, supported_workflows=SUPPORTED_WORKFLOWS)


def setup_logging(
    base: Path, output_dir_value: object, *, logger_name: str = LOGGER_NAME
) -> logging.Logger:
    """Set up adapter logging under output_dir/run.log."""

    output_dir = Path(resolve_param_path(base, output_dir_value or "output"))
    return setup_adapter_logging(output_dir, logger_name=logger_name)


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


def _has_genomelens_shell(home: Path) -> bool:
    return any(
        (home / candidate).is_file() for candidate in _GENOMELENS_SHELL_CANDIDATES
    )


def genomelens_shell_path(home: str | Path) -> Path:
    """Return the platform-level genomelens shell inside a gljcvimcscan home."""

    base = Path(home).expanduser().resolve(strict=False)
    for candidate in _GENOMELENS_SHELL_CANDIDATES:
        path = base / candidate
        if path.is_file():
            return path
    raise PluginError(f"genomelens shell not found in gljcvimcscan home: {base}")


# Backward-compatible alias used by lightweight feature entries.
discover_genomelens_shell = genomelens_shell_path


def discover_mcscan_home(start: str | Path | None = None) -> Path:
    """Locate the gljcvimcscan heavy center via env var or upward directory search."""

    env = os.environ.get(GLJCVIMCSCAN_HOME_ENV, "").strip()
    if env:
        candidate = Path(env).expanduser().resolve(strict=False)
        if not candidate.is_dir() or not _has_genomelens_shell(candidate):
            raise PluginError(
                f"{GLJCVIMCSCAN_HOME_ENV} does not point to a valid gljcvimcscan home: {candidate}"
            )
        return candidate

    origin = (
        Path(start).expanduser().resolve(strict=False)
        if start is not None
        else resource_path()
    )
    current = origin if origin.is_dir() else origin.parent
    for directory in (current, *current.parents):
        if directory.name.lower() == "gljcvimcscan" and _has_genomelens_shell(
            directory
        ):
            return directory
        sibling = directory / "gljcvimcscan"
        if _has_genomelens_shell(sibling):
            return sibling.resolve(strict=False)

    raise PluginError(
        "Unable to locate gljcvimcscan heavy center. Install gljcvimcscan or set GLJCVIMCSCAN_HOME."
    )


def resolve_genomelens_exe(params: Mapping[str, object], base: Path) -> Path:
    """Locate the external GenomeLens executable from params or environment."""

    raw = str(params.get("genomelens_exe") or os.environ.get(GENOMELENS_EXE_ENV, "")).strip()
    if not raw:
        raise PluginError(
            "genomelens_exe is required: set it in params.json or via GENOMELENS_EXE environment variable"
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


def build_command_for_launcher(
    launcher: Path,
    request_path: Path | None = None,
) -> list[str]:
    """Build a transparent launcher argv for shells and executables."""

    args = ["analyze", "run", str(request_path)] if request_path is not None else []
    if launcher.suffix.lower() in {".cmd", ".bat"}:
        return ["cmd.exe", "/c", str(launcher), *args]
    return [str(launcher), *args]


def run_process(argv: Sequence[str]) -> int:
    """Run a prepared command and return its exit code."""

    completed = subprocess.run(list(argv), shell=False, check=False)
    return int(completed.returncode)


def _build_runtime_command(params_path: str | Path) -> list[str]:
    params, base = load_params(params_path)
    logger = setup_logging(base, params.get("output_dir"))
    logger.info("Loaded params.json: %s", params_path)
    runtime = runtime_executable()
    if not runtime.is_file():
        raise PluginError(f"GenomeLens runtime executable not found: {runtime}")
    request_path = write_analysis_request(
        params, base, supported_workflows=SUPPORTED_WORKFLOWS
    )
    argv = [str(runtime), "analyze", "run", str(request_path)]
    logger.info("Dispatching GenomeLens runtime: %s", argv)
    return argv


def build_runtime_command(params_path: str | Path) -> list[str]:
    """Build the legacy lightweight plugin runtime argv."""

    try:
        return _build_runtime_command(params_path)
    finally:
        close_logging()


def main(argv: list[str] | None = None) -> int:
    """Legacy single-package HAIant plugin entry."""

    if argv is None:
        argv = sys.argv[1:]
    try:
        runtime = runtime_executable()
        if not argv:
            if not runtime.is_file():
                raise PluginError(f"GenomeLens runtime executable not found: {runtime}")
            return run_process([str(runtime)])
        if len(argv) != 1:
            raise PluginError("Expected zero arguments or one params.json path")
        return run_process(build_runtime_command(argv[0]))
    except PluginError as exc:
        print(f"GenomeLens HAIant plugin error: {exc}", file=sys.stderr)
        return 2
