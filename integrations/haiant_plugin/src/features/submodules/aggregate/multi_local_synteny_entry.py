"""HAIant 聚合功能入口：``jcvi.local_synteny_multi``"""

from __future__ import annotations

import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from genomelens_haiant_plugin._core import (
    PluginError,
    _parse_formats,
    _split_csv,
    build_submodule_runtime_command,
    close_adapter_logging,
    coerce_submodule_params,
    load_params,
    resolve_genomelens_exe,
    resolve_param_path,
    setup_adapter_logging,
)

LOGGER_NAME = "gljcvi_multi_local_synteny"
ERROR_PREFIX = "GenomeLens multi-species local synteny feature plugin error"
SUB_MODULE_ID = "jcvi.local_synteny_multi"

# 子模块可调参数（param_id, 类型），作为 ``parameters`` 写入 ``SubmoduleRequest``
DECLARED_PARAMS = [
    ("up", "int"),
    ("down", "int"),
    ("split_targets", "bool"),
    ("label_targets", "bool"),
    ("use_native_local_synteny_renderer", "bool"),
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
    """构建 GenomeLens ``analyze run submodule_request.json`` 命令"""

    params, base = load_params(params_path)
    output_dir = Path(resolve_param_path(base, params.get("output_dir") or "output"))
    logger = setup_adapter_logging(output_dir, logger_name=LOGGER_NAME)
    logger.info("Loaded params.json: %s", params_path)

    try:
        genomelens_exe = resolve_genomelens_exe(params, base)
        tracks = _parse_json_list(params.get("tracks"), "tracks")
        blocks = params.get("blocks")
        bed = params.get("bed")
        target_genes = params.get("target_genes") or params.get("target_gene_ids")
        if not tracks:
            raise PluginError("tracks must be a non-empty list")
        if not blocks:
            raise PluginError("blocks is required")
        if not bed:
            raise PluginError("bed is required")
        if not target_genes:
            raise PluginError("target_genes or target_gene_ids is required")

        blocks_path = resolve_param_path(base, blocks, required=True, must_exist=True)
        bed_path = resolve_param_path(base, bed, required=True, must_exist=True)
        target_gene_ids = _split_csv(target_genes)
        if not target_gene_ids:
            raise PluginError("target_genes must contain at least one gene ID")

        formats_value = params.get("formats")
        argv = build_submodule_runtime_command(
            genomelens_exe,
            module_id=SUB_MODULE_ID,
            inputs={
                "tracks": tracks,
                "blocks": blocks_path,
                "bed": bed_path,
                "target_genes": target_gene_ids,
            },
            parameters=coerce_submodule_params(params, base, DECLARED_PARAMS),
            output_dir=output_dir,
            formats=_parse_formats(formats_value),
            force=True,
        )
        logger.info("Dispatching GenomeLens: %s", argv)
        return argv
    finally:
        close_adapter_logging(LOGGER_NAME)


def run_runtime(argv: list[str]) -> int:
    """运行已准备好的命令并返回退出码"""

    import subprocess

    completed = subprocess.run(argv, shell=False, check=False)
    return int(completed.returncode)


def main(argv: list[str] | None = None) -> int:
    """运行多物种局部共线性(multi-species local synteny)功能入口"""

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
