"""共享 workflow(工作流) 辅助模块"""

# region import
from __future__ import annotations

from pathlib import Path

from jcvi_genomelens.runtime.command_runner import CommandAudit

# endregion


def _assert_ok(command: CommandAudit) -> None:
    """校验 command 执行成功，失败时抛出 RuntimeError"""

    if command.returncode != 0:
        raise RuntimeError(command.stderr or command.stdout or f"{command.name} failed")


def build_figure_options(
    options: object,
    fmt: str,
    figsize: str = "",
) -> list[str]:
    """把 manifest 图件参数转成 JCVI ``graphics.synteny`` 命令行参数。

    ``options`` 可以是 ``WorkflowOptions`` 模型或任何提供 ``figsize``、``dpi``、
    ``glyphstyle``、``glyphcolor``、``shadestyle`` 属性的对象。
    """

    args: list[str] = []
    effective_figsize = figsize or getattr(options, "figsize", None) or ""
    if effective_figsize:
        args.extend(["--figsize", str(effective_figsize)])
    dpi = getattr(options, "dpi", None)
    if dpi:
        args.extend(["--dpi", str(dpi)])
    args.extend(["--format", fmt, "--notex"])
    glyphstyle = getattr(options, "glyphstyle", None)
    if glyphstyle:
        args.extend(["--glyphstyle", str(glyphstyle)])
    glyphcolor = getattr(options, "glyphcolor", None)
    if glyphcolor:
        args.extend(["--glyphcolor", str(glyphcolor)])
    shadestyle = getattr(options, "shadestyle", None)
    if shadestyle:
        args.extend(["--shadestyle", str(shadestyle)])
    return args


def read_bed_names(path: Path) -> list[str]:
    """从类 BED 文件读取 gene names(基因名称)"""

    names: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) >= 4:
            # 第 4 列是 BED name，GenomeLens/JCVI 都把它当作基因主键。
            names.append(parts[3])
    return names
