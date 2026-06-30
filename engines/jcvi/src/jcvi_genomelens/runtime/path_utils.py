"""路径兼容性辅助模块"""

# region import
from __future__ import annotations

import os
from pathlib import Path

# endregion


def ensure_dir(path: str | Path) -> Path:
    """创建并返回目录路径"""

    target = Path(path).expanduser().resolve(strict=False)
    # engine workflow 常把 outdir/path 当作“存在即可”的契约，这里集中兜底
    target.mkdir(parents=True, exist_ok=True)
    return target


def _windows_short_path(path: str) -> str | None:
    """通过 cmd 的 %~sI 获取 8.3 短路径；失败返回 None"""

    import subprocess

    result = subprocess.run(
        ["cmd", "/c", "for", "%I", "in", f'("{path}")', "do", "@echo", "%~sI"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=False,
    )
    if result.returncode != 0:
        return None
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    return lines[0] if lines else None


def short_path(path: str | Path) -> str:
    """返回适用于 ANSI argv 的短路径（Windows 8.3），非 Windows 下返回原路径。

    BLAST+ 等历史可执行文件在 Windows 上仍使用 ``main`` 入口，命令行参数会被
    C 运行时按当前代码页转为 ANSI，导致中文路径损坏。本函数先把路径转成 8.3
    短名，再传给这类外部程序，从而绕开编码问题。
    """

    target = Path(path).expanduser().resolve(strict=False)
    if os.name != "nt":
        return str(target)

    short = _windows_short_path(str(target))
    if short:
        return short

    # 目标尚未存在（如输出前缀）：向上找到最近存在的祖先，用其短路径拼接剩余部分。
    existing = target
    tail: list[str] = []
    while not existing.exists() and existing.parent != existing:
        tail.append(existing.name)
        existing = existing.parent
    if not existing.exists():
        return str(target)

    short_parent = _windows_short_path(str(existing))
    if not short_parent:
        return str(target)

    result = Path(short_parent)
    for part in reversed(tail):
        result = result / part
    return str(result)
