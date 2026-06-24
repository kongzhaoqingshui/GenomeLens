"""Lightweight HAIant feature entry for ``jcvi.graphics_histogram``."""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from genomelens_haiant_plugin._core import (
    PluginError,
    build_analyze_run_command,
    build_histogram_workflow_request,
    close_adapter_logging,
    load_params,
    resolve_genomelens_exe,
    resolve_param_path,
    setup_adapter_logging,
    write_request_payload,
)

LOGGER_NAME = "gljcvi_histogram"
ERROR_PREFIX = "GenomeLens histogram feature plugin error"


def build_runtime_command(params_path: str | Path) -> list[str]:
    """Build the GenomeLens ``analyze run`` command for the histogram workflow."""

    params, base = load_params(params_path)
    output_dir = Path(resolve_param_path(base, params.get("output_dir") or "output"))
    logger = setup_adapter_logging(output_dir, logger_name=LOGGER_NAME)
    logger.info("Loaded params.json: %s", params_path)

    try:
        genomelens_exe = resolve_genomelens_exe(params, base)
        raw_files = params.get("input_files")
        if isinstance(raw_files, str):
            raw_files = [item.strip() for item in raw_files.split(",") if item.strip()]
        if not isinstance(raw_files, list) or not raw_files:
            raise PluginError("input_files must be a non-empty list of file paths")
        numeric_files = [
            resolve_param_path(base, path, required=True, must_exist=True)
            for path in raw_files
        ]

        request = build_histogram_workflow_request(
            params,
            base,
            input_files=numeric_files,
        )
        request_path = write_request_payload(params, base, request)
        argv = build_analyze_run_command(genomelens_exe, request_path)
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
    """Run the histogram feature entry."""

    args = sys.argv[1:] if argv is None else argv
    try:
        if len(args) != 1:
            raise PluginError("Expected one params.json path")
        command = build_runtime_command(args[0])
        return run_runtime(command)
    except PluginError as exc:
        print(f"{ERROR_PREFIX}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
