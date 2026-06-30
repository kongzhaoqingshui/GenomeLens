"""路径兼容性辅助模块"""

# region import
from __future__ import annotations

import os
from pathlib import Path

# endregion


def _windows_short_path(path: str) -> str | None:
    """调用 Windows GetShortPathNameW 获取 8.3 短路径；失败返回 None"""

    import ctypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    GetShortPathNameW = kernel32.GetShortPathNameW
    GetShortPathNameW.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint32]
    GetShortPathNameW.restype = ctypes.c_uint32

    buf = ctypes.create_unicode_buffer(512)
    size = GetShortPathNameW(path, buf, len(buf))
    if size == 0:
        return None
    if size > len(buf):
        buf = ctypes.create_unicode_buffer(size)
        size = GetShortPathNameW(path, buf, size)
        if size == 0:
            return None
    return buf.value


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
