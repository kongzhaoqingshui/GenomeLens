$ErrorActionPreference = "Stop"

$scriptRoot = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
if (-not $scriptRoot) {
  $scriptRoot = (Resolve-Path (Join-Path (Get-Location) "scripts")).Path
}
$root = [System.IO.Path]::GetFullPath((Join-Path $scriptRoot ".."))

$versionFile = Join-Path $root "platform\src\genomelens\_version.py"
$versionMatch = Select-String -LiteralPath $versionFile -Pattern '^__version__\s*=\s*"([^"]+)"' | Select-Object -First 1
$version = if ($versionMatch) { $versionMatch.Matches[0].Groups[1].Value } else { "" }
if (-not $version) {
  throw "Cannot read __version__ from platform/src/genomelens/_version.py"
}

& "$root\engines\jcvi\packaging\scripts\build_engine.ps1"
& "$root\platform\packaging\scripts\build_windows.ps1"

$runtime = Join-Path $root "platform\dist\GenomeLens"
$resources = Join-Path $runtime "resources\toolchain"
$engineExe = Join-Path $root "engines\jcvi\dist\jcvi-genomelens.exe"
$engineCurrent = Join-Path $root "toolchains\jcvi-genomelens\current"

New-Item -ItemType Directory -Force -Path `
  (Join-Path $resources "jcvi-genomelens\bin"), `
  (Join-Path $resources "blast"), `
  (Join-Path $resources "imagemagick"), `
  $engineCurrent | Out-Null

Copy-Item $engineExe (Join-Path $engineCurrent "jcvi-genomelens.exe") -Force
Copy-Item $engineExe (Join-Path $resources "jcvi-genomelens\bin\jcvi-genomelens.exe") -Force

robocopy (Join-Path $root "toolchains\blast\current") (Join-Path $resources "blast") /E | Out-Null
if ($LASTEXITCODE -gt 7) { exit $LASTEXITCODE }

$imagemagick = Join-Path $root "toolchains\imagemagick\current"
if (Test-Path $imagemagick) {
  robocopy $imagemagick (Join-Path $resources "imagemagick") /E | Out-Null
  if ($LASTEXITCODE -gt 7) { exit $LASTEXITCODE }
} else {
  Write-Host "Optional ImageMagick toolchain not found; skipping resources\toolchain\imagemagick"
}

$app = Join-Path $root "app"
New-Item -ItemType Directory -Force -Path $app | Out-Null

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

New-Item -ItemType Directory -Force -Path (Join-Path $engineStage "bin") | Out-Null
Copy-Item $engineExe (Join-Path $engineStage "bin\jcvi-genomelens.exe") -Force

foreach ($zip in @(
  "GenomeLens-$version-windows-core.zip",
  "GenomeLens-$version-windows-with-toolchains.zip",
  "GenomeLens-toolchain-jcvi-genomelens-0.1.0-windows.zip"
)) {
  $target = Join-Path $app $zip
  if (Test-Path $target) { Remove-Item -LiteralPath $target -Force }
}

Compress-Archive -Path (Join-Path $coreStage "*") -DestinationPath (Join-Path $app "GenomeLens-$version-windows-core.zip")
Compress-Archive -Path (Join-Path $bundleStage "*") -DestinationPath (Join-Path $app "GenomeLens-$version-windows-with-toolchains.zip")
Compress-Archive -Path (Join-Path $engineStage "*") -DestinationPath (Join-Path $app "GenomeLens-toolchain-jcvi-genomelens-0.1.0-windows.zip")

Write-Host "Split packages written to $app"
