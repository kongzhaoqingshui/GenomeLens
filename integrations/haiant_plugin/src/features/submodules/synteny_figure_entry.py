"""Lightweight HAIant feature entry for ``jcvi.graphics_synteny``."""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

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

LOGGER_NAME = "gljcvi_synteny_figure"
ERROR_PREFIX = "GenomeLens synteny figure feature plugin error"
SUB_MODULE_ID = "jcvi.graphics_synteny"

# 子模块可调参数（param_id, 类型），随 ``--params`` 转发给 ``analyze submodule``。
DECLARED_PARAMS = [
    ("glyphstyle", "str"),
    ("glyphcolor", "str"),
    ("shadestyle", "str"),
    ("figsize", "str"),
    ("dpi", "int"),
]


def build_runtime_command(params_path: str | Path) -> list[str]:
    """Build the GenomeLens ``analyze submodule`` command for the synteny figure module."""

    params, base = load_params(params_path)
    output_dir = Path(resolve_param_path(base, params.get("output_dir") or "output"))
    logger = setup_adapter_logging(output_dir, logger_name=LOGGER_NAME)
    logger.info("Loaded params.json: %s", params_path)

    try:
        genomelens_exe = resolve_genomelens_exe(params, base)
        input_dir = resolve_param_path(
            base, params.get("input_dir"), required=True, must_exist=True
        )
        blocks = params.get("blocks")
        if not blocks:
            raise PluginError(
                "blocks is required (a .blocks file from MCscan pairwise)"
            )
        blocks_path = resolve_param_path(base, blocks, required=True, must_exist=True)

        input_ports: dict[str, object] = {
            "species_pair": input_dir,
            "blocks": blocks_path,
        }
        layout = params.get("layout")
        if layout:
            input_ports["layout"] = resolve_param_path(
                base, layout, required=True, must_exist=True
            )

        formats_value = params.get("formats")
        argv = build_analyze_submodule_command(
            genomelens_exe,
            module_id=SUB_MODULE_ID,
            input_ports=input_ports,
            output_dir=output_dir,
            input_dir=input_dir,
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
    """Run the synteny figure feature entry."""

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
