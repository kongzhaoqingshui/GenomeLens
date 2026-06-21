"""Lightweight HAIant feature entry for the ``analyze mcscan jcvi`` auto workflow."""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from features._shared import build_runtime_command as shared_build_runtime_command
from features._shared import main as run_feature_main
from features._shared import source_plugin_root

WORKFLOW = "graphics_synteny"
LOGGER_NAME = "gljcvi_auto"


def plugin_root() -> Path:
    """Return the auto workflow plugin root."""

    return source_plugin_root(__file__)


def build_runtime_command(params_path: str | Path) -> list[str]:
    """Build the GenomeLens analyze run command for the auto workflow."""

    return shared_build_runtime_command(
        params_path,
        workflow=WORKFLOW,
        plugin_root=plugin_root(),
        logger_name=LOGGER_NAME,
    )


def main(argv: list[str] | None = None) -> int:
    """Run the ``analyze mcscan jcvi`` auto workflow entry."""

    return run_feature_main(
        argv,
        workflow=WORKFLOW,
        plugin_root=plugin_root(),
        logger_name=LOGGER_NAME,
        error_prefix="GenomeLens MCscan auto workflow plugin error",
    )


if __name__ == "__main__":
    raise SystemExit(main())
