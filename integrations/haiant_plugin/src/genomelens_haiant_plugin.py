"""Compatibility shim for the legacy HAIant plugin executable."""

from __future__ import annotations

from genomelens_haiant_plugin import main


if __name__ == "__main__":
    raise SystemExit(main())
