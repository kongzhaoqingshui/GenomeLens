"""Lightweight HAIant feature entry for ``catalog_ortholog``."""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from features._entry_template import make_feature_entry

WORKFLOW = "catalog_ortholog"
LOGGER_NAME = "gljcvi_catalog_ortholog"
ERROR_PREFIX = "GenomeLens catalog_ortholog feature plugin error"

_entry = make_feature_entry(WORKFLOW, LOGGER_NAME, ERROR_PREFIX)
build_runtime_command = _entry.build_runtime_command
main = _entry.main

if __name__ == "__main__":
    raise SystemExit(main())
