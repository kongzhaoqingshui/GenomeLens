$ErrorActionPreference = "Stop"
$root = (Resolve-Path "$PSScriptRoot\..").Path

# 从平台版本源读取版本号，避免硬编码
$version = (python -c "import sys; sys.path.insert(0, '$root\\platform\\src'); from genomelens._version import __version__; print(__version__)")
if (-not $version) { throw "Cannot read __version__ from platform/src/genomelens/_version.py" }
& (Join-Path $root "engines\jcvi\packaging\scripts\build_engine.ps1")
& (Join-Path $root "platform\packaging\scripts\build_windows.ps1")

$runtime = Join-Path $root "platform\dist\GenomeLens"
$resources = Join-Path $runtime "resources\toolchain"
$engineExe = Join-Path $root "engines\jcvi\dist\jcvi-genomelens.exe"
$engineCurrent = Join-Path $root "toolchains\jcvi-genomelens\current"
New-Item -ItemType Directory -Force -Path "$resources\jcvi-genomelens\bin", "$resources\blast", "$resources\imagemagick", $engineCurrent | Out-Null
Copy-Item $engineExe "$engineCurrent\jcvi-genomelens.exe" -Force
Copy-Item $engineExe "$resources\jcvi-genomelens\bin\jcvi-genomelens.exe" -Force
robocopy "$root\toolchains\blast\current" "$resources\blast" /E | Out-Null
if ($LASTEXITCODE -gt 7) { exit $LASTEXITCODE }
robocopy "$root\toolchains\imagemagick\current" "$resources\imagemagick" /E | Out-Null
if ($LASTEXITCODE -gt 7) { exit $LASTEXITCODE }

$app = Join-Path $root "app"
$coreStage = Join-Path $root ".build\GenomeLens-$version-windows-core"
$bundleStage = Join-Path $root ".build\GenomeLens-$version-windows-with-toolchains"
$engineStage = Join-Path $root ".build\GenomeLens-toolchain-jcvi-genomelens-0.1.0-windows"
foreach ($p in @($coreStage, $bundleStage, $engineStage)) {
  if (Test-Path $p) { Remove-Item -LiteralPath $p -Recurse -Force }
  New-Item -ItemType Directory -Force -Path $p | Out-Null
}
robocopy $runtime $bundleStage /E | Out-Null
if ($LASTEXITCODE -gt 7) { exit $LASTEXITCODE }
robocopy $runtime $coreStage /E /XD resources | Out-Null
if ($LASTEXITCODE -gt 7) { exit $LASTEXITCODE }
New-Item -ItemType Directory -Force -Path "$engineStage\bin" | Out-Null
Copy-Item $engineExe "$engineStage\bin\jcvi-genomelens.exe" -Force

foreach ($zip in @(
  "GenomeLens-$version-windows-core.zip",
  "GenomeLens-$version-windows-with-toolchains.zip",
  "GenomeLens-toolchain-jcvi-genomelens-0.1.0-windows.zip"
)) {
  $target = Join-Path $app $zip
  if (Test-Path $target) { Remove-Item -LiteralPath $target -Force }
}
Compress-Archive -Path "$coreStage\*" -DestinationPath (Join-Path $app "GenomeLens-$version-windows-core.zip")
Compress-Archive -Path "$bundleStage\*" -DestinationPath (Join-Path $app "GenomeLens-$version-windows-with-toolchains.zip")
Compress-Archive -Path "$engineStage\*" -DestinationPath (Join-Path $app "GenomeLens-toolchain-jcvi-genomelens-0.1.0-windows.zip")
Write-Host "Split packages written to $app"
