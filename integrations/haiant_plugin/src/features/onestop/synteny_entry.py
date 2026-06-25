"""Lightweight HAIant feature entry for the integrated ``analyze workflow synteny`` flow.

This entry builds a V3 ``WorkflowRequest`` JSON from the HAIant ``params.json`` and
invokes the external GenomeLens executable with:

    <genomelens_exe> analyze run <output_dir>/workflow_request.json

The ``synteny`` one-stop workflow auto-routes to pairwise / multi-species /
reference-vs-targets based on species count and target genes.
"""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from genomelens_haiant_plugin._core import (
    PluginError,
    build_workflow_runtime_command,
    close_adapter_logging,
    compress_output_intermediates,
    load_params,
    resolve_genomelens_exe,
    resolve_param_path,
    setup_adapter_logging,
)

LOGGER_NAME = "gljcvi_synteny"


def build_runtime_command(params_path: str | Path) -> list[str]:
    """Build the ``analyze run workflow_request.json`` command from HAIant params."""

    params, base = load_params(params_path)
    output_dir = Path(resolve_param_path(base, params.get("output_dir") or "output"))
    logger = setup_adapter_logging(output_dir, logger_name=LOGGER_NAME)
    logger.info("Loaded params.json: %s", params_path)

    try:
        genomelens_exe = resolve_genomelens_exe(params, base)
        output_dir = resolve_param_path(base, params.get("output_dir") or "output")
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        argv = build_workflow_runtime_command(genomelens_exe, params, base, output_dir)
        logger.info("Dispatching GenomeLens: %s", argv)
        return argv
    finally:
        close_adapter_logging(LOGGER_NAME)


def run_runtime(argv: list[str]) -> int:
    """Run a prepared command and return its exit code."""

    import subprocess

    completed = subprocess.run(argv, shell=False, check=False)
    return int(completed.returncode)


def main(argv: list[str] | None = None) -> int:
    """Run the ``analyze workflow synteny`` feature entry."""

    args = sys.argv[1:] if argv is None else argv
    try:
        if len(args) != 1:
            raise PluginError("Expected one params.json path")
        params, base = load_params(args[0])
        command = build_runtime_command(args[0])
        exit_code = run_runtime(command)
        output_dir = Path(
            resolve_param_path(base, params.get("output_dir") or "output")
        )
        if exit_code == 0:
            compress_output_intermediates(output_dir)
        return exit_code
    except PluginError as exc:
        print(f"GenomeLens synteny workflow plugin error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
