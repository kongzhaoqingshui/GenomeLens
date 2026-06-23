"""Lightweight HAIant feature entry for ``graphics_synteny``."""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from features._entry_template import make_feature_entry

WORKFLOW = "graphics_synteny"
LOGGER_NAME = "gljcvi_synteny"
ERROR_PREFIX = "GenomeLens synteny feature plugin error"

_entry = make_feature_entry(WORKFLOW, LOGGER_NAME, ERROR_PREFIX)
build_runtime_command = _entry.build_runtime_command
main = _entry.main

if __name__ == "__main__":
    raise SystemExit(main())
