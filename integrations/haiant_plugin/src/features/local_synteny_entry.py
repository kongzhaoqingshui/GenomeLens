"""Lightweight HAIant feature entry for ``local_synteny``."""

from __future__ import annotations

import sys
from dataclasses import asdict
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from features._shared import build_runtime_command as shared_build_runtime_command
from features._shared import load_params
from features._shared import main as run_feature_main
from features._shared import resolve_param_path
from features._shared import source_plugin_root

WORKFLOW = "local_synteny"
LOGGER_NAME = "gljcvi_local_synteny"


def plugin_root() -> Path:
    """Return the local synteny plugin root."""

    return source_plugin_root(__file__)


def _expand_input_dir(params: dict[str, object], base: Path) -> dict[str, object]:
    """Mirror the ``analyze mcscan jcvi`` auto-directory flow.

    If ``species`` is absent but ``input_dir`` is given, discover paired
    species files from that directory just like the CLI auto flow.
    """

    if params.get("species"):
        return params
    raw_input_dir = params.get("input_dir")
    if not raw_input_dir:
        return params

    from genomelens.analysis.requests.normalization.input_resolver import (
        discover_species_from_directory,
    )

    input_dir = resolve_param_path(base, raw_input_dir, required=True, must_exist=True)
    discovered = discover_species_from_directory(input_dir)
    expanded = dict(params)
    expanded["species"] = [asdict(item) for item in discovered]
    # ``input_dir`` is only a HAIant convenience; the request itself uses species[].
    expanded.pop("input_dir", None)
    return expanded


def build_runtime_command(params_path: str | Path) -> list[str]:
    """Build the heavyweight shell command for local synteny."""

    params, base = load_params(params_path)
    params = _expand_input_dir(params, base)
    return shared_build_runtime_command(
        params,
        workflow=WORKFLOW,
        plugin_root=plugin_root(),
        logger_name=LOGGER_NAME,
    )


def main(argv: list[str] | None = None) -> int:
    """Run the local synteny feature entry."""

    return run_feature_main(
        argv,
        workflow=WORKFLOW,
        plugin_root=plugin_root(),
        logger_name=LOGGER_NAME,
        error_prefix="GenomeLens local synteny feature plugin error",
    )


if __name__ == "__main__":
    raise SystemExit(main())
