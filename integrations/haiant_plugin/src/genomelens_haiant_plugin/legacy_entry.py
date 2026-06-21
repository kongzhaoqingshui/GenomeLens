"""PyInstaller entry for the legacy monolithic HAIant plugin."""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from genomelens_haiant_plugin import main


if __name__ == "__main__":
    raise SystemExit(main())
