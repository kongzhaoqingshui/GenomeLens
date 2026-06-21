"""Shared helpers for lightweight feature plugin entries."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from genomelens_haiant_plugin._core import (
    PluginError,
    build_analysis_request,
    build_command_for_launcher,
    close_adapter_logging,
    discover_genomelens_shell,
    discover_mcscan_home,
    load_params,
    resolve_param_path,
    setup_logging,
)


def source_plugin_root(entry_file: str | Path) -> Path:
    """Return the feature plugin root for source and frozen layouts."""

    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(entry_file).resolve().parents[2]


def write_feature_request(
    params: dict[str, object],
    base: Path,
    *,
    workflow: str,
) -> Path:
    """Write the request file consumed by the heavyweight shell."""

    output_dir = Path(resolve_param_path(base, params.get("output_dir") or "output"))
    output_dir.mkdir(parents=True, exist_ok=True)
    request = build_analysis_request(params, base, workflow=workflow)
    request_path = output_dir / "genomelens_request.json"
    request_path.write_text(
        json.dumps(request, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return request_path


def build_feature_runtime_command(
    params_path: str | Path,
    *,
    workflow: str,
    plugin_root: Path,
    logger_name: str,
) -> list[str]:
    """Translate feature params into a ``gljcvimcscan`` shell invocation."""

    params, base = load_params(params_path)
    output_dir = Path(resolve_param_path(base, params.get("output_dir") or "output"))
    logger = setup_logging(output_dir, logger_name=logger_name)
    logger.info("Loaded params.json: %s", params_path)

    mcscan_home = discover_mcscan_home(plugin_root)
    launcher = discover_genomelens_shell(mcscan_home)
    request_path = write_feature_request(params, base, workflow=workflow)
    argv = build_command_for_launcher(launcher, request_path)
    logger.info("Dispatching gljcvimcscan shell: %s", argv)
    return argv


def build_runtime_command(
    params_path: str | Path,
    *,
    workflow: str,
    plugin_root: Path,
    logger_name: str,
) -> list[str]:
    """Build the shell argv and release log handles."""

    try:
        return build_feature_runtime_command(
            params_path,
            workflow=workflow,
            plugin_root=plugin_root,
            logger_name=logger_name,
        )
    finally:
        close_adapter_logging(logger_name)


def run_runtime(argv: list[str]) -> int:
    completed = subprocess.run(argv, shell=False, check=False)
    return int(completed.returncode)


def main(
    argv: list[str] | None,
    *,
    workflow: str,
    plugin_root: Path,
    logger_name: str,
    error_prefix: str,
) -> int:
    """Common CLI entry for lightweight feature plugins."""

    args = sys.argv[1:] if argv is None else argv
    try:
        if len(args) != 1:
            raise PluginError("Expected one params.json path")
        command = build_runtime_command(
            args[0],
            workflow=workflow,
            plugin_root=plugin_root,
            logger_name=logger_name,
        )
        return run_runtime(command)
    except PluginError as exc:
        print(f"{error_prefix}: {exc}", file=sys.stderr)
        return 2
