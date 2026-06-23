"""Factory for lightweight HAIant feature plugin entries.

Each feature entry (dotplot, synteny, karyotype, local synteny, catalog ortholog)
shares the same shape: translate a HAIant ``params.json`` into a GenomeLens
``analyze run`` invocation and forward the exit code.  This module generates the
boilerplate so individual entries only declare their workflow, logger name and
error prefix.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from features._shared import build_runtime_command as _build_runtime_command
from features._shared import main as _main


def make_feature_entry(
    workflow: str,
    logger_name: str,
    error_prefix: str,
) -> SimpleNamespace:
    """Generate ``build_runtime_command`` and ``main`` for a feature entry."""

    def build_runtime_command(params_path: str | Path) -> list[str]:
        """Build the GenomeLens ``analyze run`` command for this feature."""

        return _build_runtime_command(
            params_path,
            workflow=workflow,
            logger_name=logger_name,
        )

    def main(argv: list[str] | None = None) -> int:
        """Run the feature entry."""

        return _main(
            argv,
            workflow=workflow,
            logger_name=logger_name,
            error_prefix=error_prefix,
        )

    return SimpleNamespace(
        build_runtime_command=build_runtime_command,
        main=main,
    )
