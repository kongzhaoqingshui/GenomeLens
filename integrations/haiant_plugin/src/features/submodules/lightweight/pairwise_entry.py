"""HAIant 轻量功能入口：``jcvi.pairwise``"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import cast

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from genomelens_haiant_plugin._core import (
    PluginError,
    _parse_formats,
    build_submodule_runtime_command,
    close_adapter_logging,
    coerce_submodule_params,
    load_params,
    resolve_genomelens_exe,
    resolve_param_path,
    setup_adapter_logging,
)

LOGGER_NAME = "gljcvi_pairwise"
ERROR_PREFIX = "GenomeLens pairwise synteny foundation plugin error"
SUB_MODULE_ID = "jcvi.pairwise"

# 子模块可调参数（param_id, 类型），作为 ``parameters`` 写入 ``SubmoduleRequest``
DECLARED_PARAMS = [
    ("align_soft", "str"),
    ("dbtype", "str"),
    ("emit_ortholog", "bool"),
    ("cscore", "float"),
    ("dist", "int"),
    ("iter", "int"),
    ("min_block_size", "int"),
    ("threads", "int"),
]


def build_runtime_command(params_path: str | Path) -> list[str]:
    """构建 GenomeLens ``analyze run submodule_request.json`` 命令"""

    params, base = load_params(params_path)
    output_dir = Path(resolve_param_path(base, params.get("output_dir") or "output"))
    logger = setup_adapter_logging(output_dir, logger_name=LOGGER_NAME)
    logger.info("Loaded params.json: %s", params_path)

    try:
        genomelens_exe = resolve_genomelens_exe(params, base)
        input_dir = resolve_param_path(
            base, params.get("input_dir"), required=True, must_exist=True
        )
        formats_value = params.get("formats")
        argv = build_submodule_runtime_command(
            genomelens_exe,
            module_id=SUB_MODULE_ID,
            inputs={"species_pair": input_dir},
            parameters=coerce_submodule_params(params, base, DECLARED_PARAMS),
            output_dir=output_dir,
            formats=_parse_formats(formats_value),
            threads=cast(int | None, params.get("threads")),
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
    """运行双物种共线性基础分析入口"""

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
