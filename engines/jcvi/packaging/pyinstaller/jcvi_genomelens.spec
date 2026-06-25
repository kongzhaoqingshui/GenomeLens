# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_all, collect_submodules

ortools_datas, ortools_binaries, ortools_hiddenimports = collect_all("ortools")

# 工作流分发器（workflows/dispatcher.py）通过 import_module(字符串) 从 _WORKFLOW_REGISTRY
# 动态加载各 runner（workflows.graphics.* / workflows.pairwise.* / workflows.local_synteny.*）。
# PyInstaller 静态分析看不到这些动态导入，必须显式收集整个包的全部子模块，
# 否则打包产物会缺失这些工作流模块（ModuleNotFoundError: jcvi_genomelens.workflows.graphics）。
jcvi_genomelens_hiddenimports = collect_submodules("jcvi_genomelens")

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
    hiddenimports=[*ortools_hiddenimports, *matplotlib_backends, *jcvi_genomelens_hiddenimports],
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
