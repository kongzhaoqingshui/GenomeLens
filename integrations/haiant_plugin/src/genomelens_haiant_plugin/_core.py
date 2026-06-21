"""Shared helpers for the legacy and lightweight HAIant plugin entries."""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path
from typing import Final

DEFAULT_FORMATS: Final[tuple[str, ...]] = ("png",)
LOGGER_NAME: Final[str] = "genomelens_haiant_plugin"
PATH_METHOD_KEYS: Final[set[str]] = {
    "jcvi_engine",
    "blastn",
    "makeblastdb",
    "jcvi_layout",
    "jcvi_seqids",
}
FLOAT_METHOD_KEYS: Final[set[str]] = {"cscore"}
INT_METHOD_KEYS: Final[set[str]] = {"dist", "iter", "up", "down", "dpi"}
METHOD_OPTION_KEYS: Final[tuple[str, ...]] = (
    "jcvi_engine",
    "blastn",
    "makeblastdb",
    "jcvi_layout",
    "jcvi_seqids",
    "align_soft",
    "dbtype",
    "cscore",
    "dist",
    "iter",
    "up",
    "down",
    "glyphstyle",
    "glyphcolor",
    "shadestyle",
    "figsize",
    "dpi",
)
METHOD_FLAG_KEYS: Final[tuple[str, ...]] = (
    "allow_simplified_fallback",
    "split_targets",
    "label_targets",
    "optimize_figsize",
    "rewrite_layout_links",
    "fix_karyotype_label_overlap",
    "trim_cross_chromosome_blocks",
)
LOCAL_PARAM_ALIASES: Final[dict[str, str]] = {
    "target_genes": "target_gene_ids",
}


class PluginError(Exception):
    """Expected adapter failure surfaced to the plugin process."""


def load_params(path: str | Path) -> tuple[dict[str, object], Path]:
    """Load ``params.json`` and return its payload with the parent directory."""

    source = Path(path).expanduser().resolve(strict=False)
    if not source.is_file():
        raise PluginError(f"params.json not found: {source}")

    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise PluginError(f"Invalid JSON: {source}") from exc

    if not isinstance(payload, dict):
        raise PluginError("params.json must contain a JSON object")

    return payload, source.parent


def parse_bool(value: object) -> bool:
    """Parse permissive platform booleans."""

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


def resolve_param_path(
    base: Path,
    value: object,
    *,
    required: bool = False,
    must_exist: bool = False,
    fallback_bases: tuple[Path, ...] = (),
) -> str:
    """Resolve a path-like parameter against ``params.json`` and fallbacks."""

    if value is None or str(value).strip() == "":
        if required:
            raise PluginError("Required path field is empty")
        return ""

    raw = Path(str(value))
    if raw.is_absolute():
        candidates = [raw]
    else:
        candidates = [base / raw, *[fallback / raw for fallback in fallback_bases]]
    resolved = [candidate.expanduser().resolve(strict=False) for candidate in candidates]

    if must_exist:
        for candidate in resolved:
            if candidate.exists():
                return str(candidate)
        joined = ", ".join(str(candidate) for candidate in resolved)
        raise PluginError(f"Path does not exist: {joined}")

    return str(resolved[0])


def _formats(value: object) -> list[str]:
    if isinstance(value, list):
        items = [str(item).strip() for item in value]
    else:
        default_value = ",".join(DEFAULT_FORMATS)
        items = [item.strip() for item in str(value or default_value).split(",")]
    return [item for item in items if item] or list(DEFAULT_FORMATS)


def _as_int(value: object, default: int) -> int:
    if value in {None, ""}:
        return default
    return int(str(value))


def _as_float(value: object) -> float:
    return float(str(value))


def build_species_from_params(
    params: dict[str, object],
    base: Path,
    mode: str,
) -> list[dict[str, object]]:
    """Convert ``species[]`` from HAIant params into analysis request entries."""

    species_payload = params.get("species")
    if not isinstance(species_payload, list) or not species_payload:
        raise PluginError("species must contain at least two entries")

    species: list[dict[str, object]] = []
    for index, item in enumerate(species_payload, start=1):
        if not isinstance(item, dict):
            raise PluginError(f"species[{index}] must be an object")

        name = str(item.get("name") or f"species{index}")
        if mode == "bed_cds":
            species.append(
                {
                    "name": name,
                    "input_mode": "bed_cds",
                    "bed": resolve_param_path(
                        base,
                        item.get("bed"),
                        required=True,
                        must_exist=True,
                    ),
                    "cds": resolve_param_path(
                        base,
                        item.get("cds"),
                        required=True,
                        must_exist=True,
                    ),
                }
            )
            continue

        if mode == "gff_genome":
            species.append(
                {
                    "name": name,
                    "input_mode": "gff_genome",
                    "gff": resolve_param_path(
                        base,
                        item.get("gff"),
                        required=True,
                        must_exist=True,
                    ),
                    "genome": resolve_param_path(
                        base,
                        item.get("genome"),
                        required=True,
                        must_exist=True,
                    ),
                }
            )
            continue

        raise PluginError(f"Unsupported input_mode: {mode}")

    if len(species) < 2:
        raise PluginError("At least two species entries are required")

    return species


def _reference_index(
    params: dict[str, object],
    species: list[dict[str, object]],
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


def _method_value(params: dict[str, object], key: str) -> object:
    alias = LOCAL_PARAM_ALIASES.get(key)
    if alias and params.get(alias) not in {None, ""}:
        return params.get(alias)
    return params.get(key)


def _build_method_config(
    params: dict[str, object],
    base: Path,
    *,
    workflow: str,
) -> dict[str, object]:
    method_config: dict[str, object] = {"workflow": workflow}

    for key in METHOD_OPTION_KEYS:
        value = _method_value(params, key)
        if value in {None, ""}:
            continue

        if key in PATH_METHOD_KEYS:
            method_config[key] = resolve_param_path(base, value, must_exist=True)
        elif key in FLOAT_METHOD_KEYS:
            method_config[key] = _as_float(value)
        elif key in INT_METHOD_KEYS:
            method_config[key] = _as_int(value, 0)
        else:
            method_config[key] = value

    for key in METHOD_FLAG_KEYS:
        if key in params:
            method_config[key] = parse_bool(params.get(key))

    target_genes = _method_value(params, "target_genes")
    if target_genes not in {None, ""}:
        if isinstance(target_genes, list):
            method_config["target_gene_ids"] = [
                str(item).strip() for item in target_genes if str(item).strip()
            ]
        else:
            method_config["target_gene_ids"] = [
                item.strip() for item in str(target_genes).split(",") if item.strip()
            ]

    return method_config


def build_analysis_request(
    params: dict[str, object],
    base: Path,
    *,
    workflow: str,
) -> dict[str, object]:
    """Translate HAIant params into a stable GenomeLens analysis request."""

    mode = str(params.get("input_mode") or "bed_cds")
    output_dir = Path(resolve_param_path(base, params.get("output_dir") or "output"))
    output_dir.mkdir(parents=True, exist_ok=True)
    species = build_species_from_params(params, base, mode)

    return {
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
            "formats": _formats(params.get("formats")),
        },
        "config": {
            "project_config": resolve_param_path(
                base,
                params.get("config"),
                must_exist=bool(params.get("config")),
            ),
            "method_config": resolve_param_path(
                base,
                params.get("jcvi_config"),
                must_exist=bool(params.get("jcvi_config")),
            ),
        },
        "options": {
            "preset": str(params.get("preset") or "auto"),
            "threads": _as_int(params.get("threads"), 4),
            "min_block_size": _as_int(params.get("min_block_size"), 5),
        },
        "method_config": _build_method_config(params, base, workflow=workflow),
    }


def setup_logging(
    output_dir: str | Path,
    *,
    logger_name: str = LOGGER_NAME,
) -> logging.Logger:
    """Write adapter logs to ``output_dir/run.log``."""

    destination = Path(output_dir).expanduser().resolve(strict=False)
    destination.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    close_adapter_logging(logger_name)

    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    file_handler = logging.FileHandler(
        destination / "run.log",
        encoding="utf-8",
        mode="a",
    )
    file_handler.setFormatter(formatter)
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    return logger


def close_adapter_logging(logger_name: str = LOGGER_NAME) -> None:
    """Flush and close logging handlers for the given adapter logger."""

    logger = logging.getLogger(logger_name)
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        try:
            handler.flush()
        finally:
            handler.close()


def resource_path(relative_path: str) -> str:
    """Resolve a bundled resource path, respecting ``sys._MEIPASS``."""

    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
    return str((root / relative_path).resolve(strict=False))


def discover_mcscan_home(plugin_root: Path) -> Path:
    """Locate the heavyweight ``gljcvimcscan`` plugin home."""

    env = os.environ.get("GLJCVIMCSCAN_HOME", "").strip()
    if env:
        candidate = Path(env).expanduser().resolve(strict=False)
        if candidate.is_dir():
            return candidate
        raise PluginError(f"GLJCVIMCSCAN_HOME is not a directory: {candidate}")

    current = plugin_root.expanduser().resolve(strict=False)
    if current.name.lower() == "gljcvimcscan" and current.is_dir():
        return current

    while True:
        candidate = current / "gljcvimcscan"
        if candidate.is_dir():
            return candidate
        if current.parent == current:
            break
        current = current.parent

    raise PluginError(
        "gljcvimcscan center not found. Install the gljcvimcscan plugin "
        "or set GLJCVIMCSCAN_HOME."
    )


def discover_genomelens_shell(home: Path) -> Path:
    """Locate the platform shell under the heavyweight plugin home."""

    for name in ("genomelens.cmd", "genomelens.exe", "genomelens.bat", "genomelens"):
        candidate = home / name
        if candidate.is_file():
            return candidate
    raise PluginError(f"genomelens shell not found under: {home}")


def build_command_for_launcher(
    launcher: Path,
    request_path: Path | None = None,
) -> list[str]:
    """Build a transparent launcher argv for shells and executables."""

    args = ["analyze", "run", str(request_path)] if request_path is not None else []
    if launcher.suffix.lower() in {".cmd", ".bat"}:
        return ["cmd.exe", "/c", str(launcher), *args]
    return [str(launcher), *args]
