"""Shared helpers for lightweight feature plugin entries."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from genomelens_haiant_plugin._core import (
    PluginError,
    build_analysis_request,
    build_analyze_run_command,
    close_adapter_logging,
    load_params,
    resolve_genomelens_exe,
    resolve_param_path,
    setup_adapter_logging,
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
    """Write the request file consumed by the external GenomeLens executable."""

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
    logger_name: str,
    params: dict[str, object] | None = None,
    base: Path | None = None,
) -> list[str]:
    """Translate feature params into a GenomeLens ``analyze run`` invocation."""

    if params is None or base is None:
        params, base = load_params(params_path)
    else:
        base = Path(base)
    output_dir = Path(resolve_param_path(base, params.get("output_dir") or "output"))
    logger = setup_adapter_logging(output_dir, logger_name=logger_name)
    logger.info("Loaded params.json: %s", params_path)

    genomelens_exe = resolve_genomelens_exe(params, base)
    request_path = write_feature_request(params, base, workflow=workflow)
    argv = build_analyze_run_command(genomelens_exe, request_path)
    logger.info("Dispatching GenomeLens: %s", argv)
    return argv


def build_runtime_command(
    params_path: str | Path,
    *,
    workflow: str,
    logger_name: str,
    params: dict[str, object] | None = None,
    base: Path | None = None,
) -> list[str]:
    """Build the shell argv and release log handles."""

    try:
        return build_feature_runtime_command(
            params_path,
            workflow=workflow,
            logger_name=logger_name,
            params=params,
            base=base,
        )
    finally:
        close_adapter_logging(logger_name)


def run_runtime(argv: list[str]) -> int:
    """运行外部命令并返回退出码"""

    completed = subprocess.run(argv, shell=False, check=False)
    return int(completed.returncode)


def main(
    argv: list[str] | None,
    *,
    workflow: str,
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
            logger_name=logger_name,
        )
        return run_runtime(command)
    except PluginError as exc:
        print(f"{error_prefix}: {exc}", file=sys.stderr)
        return 2
