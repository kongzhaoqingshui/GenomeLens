#!/usr/bin/env python
"""Compile optional Cython extensions for the jcvi-genomelens engine.

This script is invoked by the packaging scripts (build_engine.ps1 / build_engine.sh)
before PyInstaller runs. It does NOT run during ``pip install -e .``; the engine
remains installable as a pure Python package even without a C compiler.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from Cython.Build import cythonize
from setuptools import Extension, setup


def _extra_compile_args() -> list[str]:
    if sys.platform == "win32":
        return ["/O2"]
    return ["-O3"]


def main() -> int:
    project_root = Path(__file__).resolve().parents[2]
    src_root = project_root / "src"

    extensions = [
        Extension(
            "jcvi.assembly.chic",
            [str(src_root / "jcvi/assembly/chic.pyx")],
            include_dirs=[np.get_include()],
            extra_compile_args=_extra_compile_args(),
        ),
        Extension(
            "jcvi.formats.cblast",
            [str(src_root / "jcvi/formats/cblast.pyx")],
            extra_compile_args=_extra_compile_args(),
        ),
    ]

    setup(
        ext_modules=cythonize(extensions, language_level="3"),
        script_args=["build_ext", "--inplace"],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
