"""GenomeLens platform-wide constants.

Constants that cross module boundaries (timeouts, default paths) live here so
that runners, adapters, and CLI commands do not hard-code the same magic numbers.
"""

from __future__ import annotations

from pathlib import Path

PROBE_TIMEOUT_SECONDS = 120
"""Timeout for ``jcvi-genomelens probe`` calls."""

ENGINE_RUN_TIMEOUT_SECONDS = 3600
"""Timeout for a full ``jcvi-genomelens run`` engine invocation."""

DEFAULT_WORKSPACE_PATH = Path.home() / "GenomeLensWork"
"""Default root for temporary/cache workspaces used by the CLI."""
