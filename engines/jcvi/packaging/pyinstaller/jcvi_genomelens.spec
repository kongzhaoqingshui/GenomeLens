# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_all

ortools_datas, ortools_binaries, ortools_hiddenimports = collect_all("ortools")

matplotlib_backends = [
    # Vector formats
    "matplotlib.backends.backend_svg",
    "matplotlib.backends.backend_pdf",
    "matplotlib.backends.backend_ps",
    "matplotlib.backends.backend_pgf",
    # Raster formats (png/jpg/...); Agg is required by savefig even when PIL writes jpg
    "matplotlib.backends.backend_agg",
    # Pillow is needed for non-png raster output such as jpg
    "PIL",
    "PIL._imagingtk",
    "PIL._tkinter_finder",
    "PIL.JpegImagePlugin",
    "PIL.PngImagePlugin",
    "PIL.TiffImagePlugin",
]

a = Analysis(
    ["../../src/jcvi_genomelens/cli.py"],
    pathex=["../../src"],
    binaries=ortools_binaries,
    datas=[("../../src/jcvi", "jcvi"), *ortools_datas],
    hiddenimports=[*ortools_hiddenimports, *matplotlib_backends],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="jcvi-genomelens",
    console=True,
)
