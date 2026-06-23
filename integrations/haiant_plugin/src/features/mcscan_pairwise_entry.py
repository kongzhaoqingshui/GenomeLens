"""Lightweight HAIant feature entry for ``jcvi.mcscan_pairwise``."""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from genomelens_haiant_plugin._core import (
    PluginError,
    build_analyze_run_command,
    close_adapter_logging,
    load_params,
    resolve_genomelens_exe,
    resolve_param_path,
    setup_adapter_logging,
    write_submodule_request,
)

LOGGER_NAME = "gljcvi_mcscan_pairwise"
ERROR_PREFIX = "GenomeLens MCscan pairwise feature plugin error"
SUB_MODULE_ID = "jcvi.mcscan_pairwise"


def build_runtime_command(params_path: str | Path) -> list[str]:
    """Build the GenomeLens ``analyze run`` command for the MCscan pairwise submodule."""

    params, base = load_params(params_path)
    output_dir = Path(resolve_param_path(base, params.get("output_dir") or "output"))
    logger = setup_adapter_logging(output_dir, logger_name=LOGGER_NAME)
    logger.info("Loaded params.json: %s", params_path)

    try:
        genomelens_exe = resolve_genomelens_exe(params, base)
        input_dir = resolve_param_path(
            base, params.get("input_dir"), required=True, must_exist=True
        )
        request_path = write_submodule_request(
            params,
            base,
            sub_module_id=SUB_MODULE_ID,
            port_bindings={"species_pair": input_dir},
        )
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
    """Run the MCscan pairwise feature entry."""

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
