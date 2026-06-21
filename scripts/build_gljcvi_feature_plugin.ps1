param(
  [Parameter(Mandatory = $true)]
  [ValidateSet("dotplot", "synteny", "karyotype", "catalog_ortholog", "local_synteny")]
  [string]$Feature
)

$ErrorActionPreference = "Stop"

$root = (Resolve-Path "$PSScriptRoot\..").Path
$srcRoot = Join-Path $root "integrations\haiant_plugin\src"
$assetsRoot = Join-Path $root "integrations\haiant_plugin\assets\features\$Feature"
$samplesRoot = Join-Path $root "references\samples\shell\bed_cds_minimal"

$featureMap = @{
  dotplot = @{
    Package = "gljcvi-dotplot"
    Entry = "features\dotplot_entry.py"
  }
  synteny = @{
    Package = "gljcvi-synteny"
    Entry = "features\synteny_entry.py"
  }
  karyotype = @{
    Package = "gljcvi-karyotype"
    Entry = "features\karyotype_entry.py"
  }
  catalog_ortholog = @{
    Package = "gljcvi-catalog-ortholog"
    Entry = "features\catalog_ortholog_entry.py"
  }
  local_synteny = @{
    Package = "gljcvi-local-synteny"
    Entry = "features\local_synteny_entry.py"
  }
}

$featureMeta = $featureMap[$Feature]
$packageName = $featureMeta.Package
$entryPath = Join-Path $srcRoot $featureMeta.Entry

if (-not (Test-Path $entryPath)) {
  throw "Feature entry not found: $entryPath"
}
if (-not (Test-Path $assetsRoot)) {
  throw "Feature assets not found: $assetsRoot"
}

$pyiRoot = Join-Path $root ".build\pyinstaller\$Feature"
$distRoot = Join-Path $pyiRoot "dist"
$workRoot = Join-Path $pyiRoot "work"
$specRoot = Join-Path $pyiRoot "spec"
$stageRoot = Join-Path $root ".build\$packageName"
$zipPath = Join-Path $root "app\$packageName.zip"

foreach ($path in @($distRoot, $workRoot, $specRoot, $stageRoot)) {
  if (Test-Path $path) {
    Remove-Item -LiteralPath $path -Recurse -Force
  }
}

New-Item -ItemType Directory -Force -Path $distRoot | Out-Null
New-Item -ItemType Directory -Force -Path $workRoot | Out-Null
New-Item -ItemType Directory -Force -Path $specRoot | Out-Null
New-Item -ItemType Directory -Force -Path $stageRoot | Out-Null

$pyinstallerArgs = @(
  "--noconfirm",
  "--clean",
  "--onefile",
  "--name",
  "main",
  "--distpath",
  $distRoot,
  "--workpath",
  $workRoot,
  "--specpath",
  $specRoot,
  "--paths",
  $srcRoot,
  $entryPath
)

& pyinstaller @pyinstallerArgs
if ($LASTEXITCODE -ne 0) {
  throw "PyInstaller build failed for feature '$Feature'."
}

$exePath = Join-Path $distRoot "main.exe"
if (-not (Test-Path $exePath)) {
  throw "Expected PyInstaller output not found: $exePath"
}

Copy-Item $exePath (Join-Path $stageRoot "main.exe") -Force
Copy-Item (Join-Path $assetsRoot "config.json") (Join-Path $stageRoot "config.json") -Force
Copy-Item (Join-Path $assetsRoot "params.json") (Join-Path $stageRoot "params.json") -Force
Copy-Item (Join-Path $assetsRoot "README.md") (Join-Path $stageRoot "README.md") -Force
Copy-Item (Join-Path $root "integrations\haiant_plugin\PARAMETER_MAPPING.md") (Join-Path $stageRoot "PARAMETER_MAPPING.md") -Force

$inputDir = Join-Path $stageRoot "input"
$outputDir = Join-Path $stageRoot "output"
New-Item -ItemType Directory -Force -Path $inputDir | Out-Null
New-Item -ItemType Directory -Force -Path $outputDir | Out-Null

Copy-Item (Join-Path $samplesRoot "query.bed") (Join-Path $inputDir "query.bed") -Force
Copy-Item (Join-Path $samplesRoot "query.cds") (Join-Path $inputDir "query.cds") -Force
Copy-Item (Join-Path $samplesRoot "subject.bed") (Join-Path $inputDir "subject.bed") -Force
Copy-Item (Join-Path $samplesRoot "subject.cds") (Join-Path $inputDir "subject.cds") -Force

if (Test-Path $zipPath) {
  Remove-Item -LiteralPath $zipPath -Force
}
Compress-Archive -Path (Join-Path $stageRoot "*") -DestinationPath $zipPath

Write-Host "Wrote $zipPath"
