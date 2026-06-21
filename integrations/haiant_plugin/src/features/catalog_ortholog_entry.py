"""Lightweight HAIant feature entry for ``catalog_ortholog``."""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from features._shared import build_runtime_command as shared_build_runtime_command
from features._shared import main as run_feature_main
from features._shared import source_plugin_root

WORKFLOW = "catalog_ortholog"
LOGGER_NAME = "gljcvi_catalog_ortholog"


def plugin_root() -> Path:
    """Return the catalog_ortholog plugin root."""

    return source_plugin_root(__file__)


def build_runtime_command(params_path: str | Path) -> list[str]:
    """Build the GenomeLens analyze run command for catalog_ortholog."""

    return shared_build_runtime_command(
        params_path,
        workflow=WORKFLOW,
        plugin_root=plugin_root(),
        logger_name=LOGGER_NAME,
    )


def main(argv: list[str] | None = None) -> int:
    """Run the catalog_ortholog feature entry."""

    return run_feature_main(
        argv,
        workflow=WORKFLOW,
        plugin_root=plugin_root(),
        logger_name=LOGGER_NAME,
        error_prefix="GenomeLens catalog_ortholog feature plugin error",
    )


if __name__ == "__main__":
    raise SystemExit(main())
