"""HAIant 一站式共线性功能入口

该入口从 HAIant ``params.json`` 构建 V3 ``WorkflowRequest`` JSON，
并调用外部 GenomeLens 可执行文件：

    <genomelens_exe> analyze run <output_dir>/workflow_request.json

``synteny`` 一站式工作流根据物种数量与目标基因自动路由到
pairwise / 多物种 / 参考种对目标种 模式
"""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from genomelens_haiant_plugin._core import (
    PluginError,
    build_workflow_runtime_command,
    close_adapter_logging,
    compress_output_intermediates,
    load_params,
    resolve_genomelens_exe,
    resolve_param_path,
    setup_adapter_logging,
)

LOGGER_NAME = "gljcvi_synteny"


def build_runtime_command(params_path: str | Path) -> list[str]:
    """从 HAIant params 构建 ``analyze run workflow_request.json`` 命令"""

    params, base = load_params(params_path)
    output_dir = Path(resolve_param_path(base, params.get("output_dir") or "output"))
    logger = setup_adapter_logging(output_dir, logger_name=LOGGER_NAME)
    logger.info("Loaded params.json: %s", params_path)

    try:
        genomelens_exe = resolve_genomelens_exe(params, base)
        output_dir = resolve_param_path(base, params.get("output_dir") or "output")
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        argv = build_workflow_runtime_command(genomelens_exe, params, base, output_dir)
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
    """运行一站式 ``synteny`` 工作流插件入口"""

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
        print(f"GenomeLens synteny workflow plugin error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
