"""文件系统输入校验工具"""

from __future__ import annotations

from pathlib import Path

from genomelens.app.errors.exceptions import InputValidationError


def require_existing_file(path: Path, label: str) -> None:
    """要求路径指向已存在的文件"""

    if not path.is_file():
        raise InputValidationError(f"{label} does not exist or is not a file: {path}")
