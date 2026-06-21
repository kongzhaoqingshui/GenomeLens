"""Legacy HAIant plugin entry backed by the shared package core."""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
from pathlib import Path

from genomelens_haiant_plugin._core import (
    PluginError,
    build_analysis_request,
    build_command_for_launcher,
    close_adapter_logging,
    discover_genomelens_shell,
    load_params,
    parse_bool,
    resolve_param_path,
    setup_logging,
)

LOGGER_NAME = "genomelens_haiant_plugin"
SUPPORTED_WORKFLOWS = {"graphics_synteny"}


def plugin_root() -> Path:
    """Return the plugin root for source and frozen layouts."""

    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def runtime_executable() -> Path:
    """Locate the packaged legacy GenomeLens runtime executable."""

    env = os.environ.get("GENOMELENS_PLUGIN_RUNTIME", "").strip()
    if env:
        return Path(env).expanduser().resolve(strict=False)

    runtime_root = plugin_root() / "runtime" / "GenomeLens"
    for candidate in (
        runtime_root / "GenomeLens-runtime.exe",
        runtime_root / "GenomeLens.exe",
    ):
        if candidate.is_file():
            return candidate
    return runtime_root / "GenomeLens-runtime.exe"


def runtime_launcher() -> Path:
    """Prefer the platform shell and fall back to the raw executable."""

    runtime_root = plugin_root() / "runtime" / "GenomeLens"
    try:
        return discover_genomelens_shell(runtime_root)
    except PluginError:
        return runtime_executable()


def _workflow(params: dict[str, object]) -> str:
    workflow = str(params.get("workflow") or "graphics_synteny").strip()
    if workflow not in SUPPORTED_WORKFLOWS:
        allowed = ", ".join(sorted(SUPPORTED_WORKFLOWS))
        raise PluginError(
            f"Unsupported HAIant workflow: {workflow}. Supported workflow: {allowed}"
        )
    return workflow


def write_runtime_request(params: dict[str, object], base: Path) -> Path:
    """Write the stable analysis request consumed by the runtime shell."""

    output_dir = Path(resolve_param_path(base, params.get("output_dir") or "output"))
    output_dir.mkdir(parents=True, exist_ok=True)
    request = build_analysis_request(params, base, workflow=_workflow(params))
    request_path = output_dir / "genomelens_request.json"
    request_path.write_text(
        json.dumps(request, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return request_path


def setup_adapter_logging(base: Path, output_dir_value: object) -> logging.Logger:
    """Configure adapter logging under ``output_dir/run.log``."""

    output_dir = Path(resolve_param_path(base, output_dir_value or "output"))
    return setup_logging(output_dir, logger_name=LOGGER_NAME)


def _build_runtime_command(params_path: str | Path) -> list[str]:
    params, base = load_params(params_path)
    logger = setup_adapter_logging(base, params.get("output_dir"))
    logger.info("Loaded params.json: %s", params_path)

    launcher = runtime_launcher()
    if not launcher.is_file():
        raise PluginError(f"GenomeLens runtime executable not found: {launcher}")

    request_path = write_runtime_request(params, base)
    argv = build_command_for_launcher(launcher, request_path)
    logger.info("Dispatching GenomeLens runtime: %s", argv)
    return argv


def build_runtime_command(params_path: str | Path) -> list[str]:
    """Build the runtime argv and release adapter log handles."""

    try:
        return _build_runtime_command(params_path)
    finally:
        close_adapter_logging(LOGGER_NAME)


def run_runtime(argv: list[str]) -> int:
    completed = subprocess.run(argv, shell=False, check=False)
    return int(completed.returncode)


def main(argv: list[str] | None = None) -> int:
    """Run the legacy plugin in no-arg or ``params.json`` mode."""

    args = sys.argv[1:] if argv is None else argv
    try:
        launcher = runtime_launcher()
        if not args:
            if not launcher.is_file():
                raise PluginError(f"GenomeLens runtime executable not found: {launcher}")
            return run_runtime(build_command_for_launcher(launcher))
        if len(args) != 1:
            raise PluginError("Expected zero arguments or one params.json path")
        return run_runtime(build_runtime_command(args[0]))
    except PluginError as exc:
        print(f"GenomeLens HAIant plugin error: {exc}", file=sys.stderr)
        return 2


__all__ = [
    "PluginError",
    "build_runtime_command",
    "close_adapter_logging",
    "load_params",
    "main",
    "parse_bool",
    "plugin_root",
    "resolve_param_path",
    "run_runtime",
    "runtime_executable",
    "runtime_launcher",
    "setup_adapter_logging",
    "write_runtime_request",
]
