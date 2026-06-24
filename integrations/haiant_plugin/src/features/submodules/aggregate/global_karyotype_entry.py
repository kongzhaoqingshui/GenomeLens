"""Aggregate HAIant feature entry for ``jcvi.graphics_karyotype_global``."""

from __future__ import annotations

import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from genomelens_haiant_plugin._core import (
    PluginError,
    build_analyze_submodule_command,
    close_adapter_logging,
    coerce_submodule_params,
    load_params,
    resolve_genomelens_exe,
    resolve_param_path,
    setup_adapter_logging,
)

LOGGER_NAME = "gljcvi_global_karyotype"
ERROR_PREFIX = "GenomeLens global karyotype feature plugin error"
SUB_MODULE_ID = "jcvi.graphics_karyotype_global"

# 子模块可调参数（param_id, 类型），随 ``--params`` 转发给 ``analyze submodule``。
DECLARED_PARAMS = [
    ("figsize", "str"),
    ("dpi", "int"),
]


def _parse_json_list(value: object, label: str) -> list[object]:
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError as exc:
            raise PluginError(f"{label} must be a JSON list") from exc
        if not isinstance(parsed, list):
            raise PluginError(f"{label} must be a JSON list")
        return parsed
    raise PluginError(f"{label} must be a list")


def build_runtime_command(params_path: str | Path) -> list[str]:
    """Build the GenomeLens ``analyze submodule`` command for the global karyotype submodule."""

    params, base = load_params(params_path)
    output_dir = Path(resolve_param_path(base, params.get("output_dir") or "output"))
    logger = setup_adapter_logging(output_dir, logger_name=LOGGER_NAME)
    logger.info("Loaded params.json: %s", params_path)

    try:
        genomelens_exe = resolve_genomelens_exe(params, base)
        tracks = _parse_json_list(params.get("tracks"), "tracks")
        edges = _parse_json_list(params.get("edges"), "edges")
        if not tracks:
            raise PluginError("tracks must be a non-empty list")
        if not edges:
            raise PluginError("edges must be a non-empty list")

        formats_value = params.get("formats")
        argv = build_analyze_submodule_command(
            genomelens_exe,
            module_id=SUB_MODULE_ID,
            input_ports={"tracks": tracks, "edges": edges},
            output_dir=output_dir,
            params=coerce_submodule_params(params, base, DECLARED_PARAMS),
            formats=[item.strip() for item in formats_value.split(",") if item.strip()]
            if isinstance(formats_value, str)
            else None,
            force=True,
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
    """Run the global karyotype feature entry."""

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
