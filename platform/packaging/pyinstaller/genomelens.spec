# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

resource_dir = (Path(SPECPATH) / "../../resources").resolve()
datas = [(str(resource_dir), "resources")] if resource_dir.exists() else []

# WorkflowRegistry 通过 entry_points 动态发现第三方插件，内置插件虽走静态 import，
# 但为防同类动态加载遗漏，显式收集平台自身包的全部子模块作为兜底。
genomelens_hiddenimports = collect_submodules("genomelens")

a = Analysis(
    ["../../src/genomelens/cli/main.py"],
    pathex=["../../src"],
    binaries=[],
    datas=datas,
    hiddenimports=genomelens_hiddenimports,
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
    [],
    exclude_binaries=True,
    name="GenomeLens",
    console=True,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="GenomeLens",
)
