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
