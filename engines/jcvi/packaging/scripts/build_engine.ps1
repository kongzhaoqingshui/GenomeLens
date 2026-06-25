param(
  [string]$ProjectRoot = (Resolve-Path "$PSScriptRoot\..\..").Path
)

$ErrorActionPreference = "Stop"
Push-Location $ProjectRoot

# Compile optional Cython extensions in-place so PyInstaller bundles them.
# The engine can still run in "core" mode without them, but the packaged
# build should include the accelerated extensions.
python setup.py build_ext --inplace
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -m PyInstaller packaging\pyinstaller\jcvi_genomelens.spec --clean --noconfirm
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Pop-Location
