#!/usr/bin/env python
"""Build Cython extensions for the jcvi-genomelens engine.

These extensions are optional at runtime (the engine falls back to pure-Python
implementations when they are missing), but they significantly speed up the
pairwise / HIC workflows. This setup.py is used by the packaging scripts to
compile them in-place before PyInstaller bundles the engine.
"""

from Cython.Build import build_ext
from setuptools import Extension, setup
import numpy as np


def _get_extra_compile_args():
    """Return optimization flags appropriate for the host compiler."""

    import sys

    if sys.platform == "win32":
        return ["/O2"]
    return ["-O3"]


_compile_args = _get_extra_compile_args()

ext_modules = [
    Extension(
        "jcvi.assembly.chic",
        ["src/jcvi/assembly/chic.pyx"],
        include_dirs=[np.get_include()],
        extra_compile_args=_compile_args,
    ),
    Extension(
        "jcvi.formats.cblast",
        ["src/jcvi/formats/cblast.pyx"],
        extra_compile_args=_compile_args,
    ),
]

setup(
    ext_modules=ext_modules,
    cmdclass={"build_ext": build_ext},
)
