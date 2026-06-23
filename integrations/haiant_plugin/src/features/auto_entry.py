"""Lightweight HAIant feature entry for the ``analyze workflow`` auto flow.

This entry does **not** write a ``genomelens_request.json``.  Instead it dynamically
builds a ``jcvi.config.json`` from the HAIant ``params.json`` and directly invokes the
external GenomeLens executable with:

    <genomelens_exe> analyze workflow <workflow_id> <input_dir> <output_dir> --jcvi-config <jcvi.config.json>
"""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from genomelens_haiant_plugin._core import (
    PluginError,
    _target_gene_ids,
    build_auto_jcvi_config,
    build_mcscan_jcvi_command,
    close_adapter_logging,
    compress_output_intermediates,
    load_params,
    resolve_genomelens_exe,
    resolve_param_path,
    setup_adapter_logging,
)

LOGGER_NAME = "gljcvi_auto"


def plugin_root() -> Path:
    """Return the auto workflow plugin root."""

    from features._shared import source_plugin_root

    return source_plugin_root(__file__)


def build_runtime_command(params_path: str | Path) -> list[str]:
    """Build the ``analyze workflow`` auto command from HAIant params."""

    params, base = load_params(params_path)
    output_dir = Path(resolve_param_path(base, params.get("output_dir") or "output"))
    logger = setup_adapter_logging(output_dir, logger_name=LOGGER_NAME)
    logger.info("Loaded params.json: %s", params_path)

    try:
        genomelens_exe = resolve_genomelens_exe(params, base)
        input_dir = resolve_param_path(
            base, params.get("input_dir"), required=True, must_exist=True
        )
        output_dir = resolve_param_path(base, params.get("output_dir") or "output")
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        jcvi_config_path = build_auto_jcvi_config(params, base, output_dir)
        workflow_id = (
            "reference_vs_targets" if _target_gene_ids(params) else "pairwise_synteny"
        )
        argv = build_mcscan_jcvi_command(
            genomelens_exe,
            input_dir,
            output_dir,
            jcvi_config_path,
            workflow_id=workflow_id,
        )
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
    """Run the ``analyze workflow`` auto workflow entry."""

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
        print(f"GenomeLens MCscan auto workflow plugin error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
