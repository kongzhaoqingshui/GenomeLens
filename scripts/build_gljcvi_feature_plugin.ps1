param(
  [Parameter(Mandatory = $true)]
  [ValidateSet(
    "dotplot",
    "synteny",
    "karyotype",
    "catalog_ortholog",
    "local_synteny",
    "synteny_figure",
    "histogram",
    "heatmap",
    "mcscan_pairwise",
    "global_karyotype",
    "multi_local_synteny"
  )]
  [string]$Feature
)

$ErrorActionPreference = "Stop"

$root = (Resolve-Path "$PSScriptRoot\..").Path
$srcRoot = Join-Path $root "integrations\haiant_plugin\src"
$samplesRoot = Join-Path $root "references\samples\shell\bed_cds_minimal"

# 平台只承认两类能力：一站式工作流（onestop，analyze workflow）与可编排子模块（submodules，analyze submodule）。
$featureMap = @{
  # 一站式工作流插件（analyze workflow synteny）
  synteny = @{
    Package = "gljcvi-synteny"
    Entry = "features\onestop\synteny_entry.py"
    Category = "onestop"
  }
  # 可编排子模块插件（analyze submodule <module_id>）
  mcscan_pairwise = @{
    Package = "gljcvi-mcscan-pairwise"
    Entry = "features\submodules\mcscan_pairwise_entry.py"
    Category = "submodules"
  }
  catalog_ortholog = @{
    Package = "gljcvi-catalog-ortholog"
    Entry = "features\submodules\catalog_ortholog_entry.py"
    Category = "submodules"
  }
  dotplot = @{
    Package = "gljcvi-dotplot"
    Entry = "features\submodules\dotplot_entry.py"
    Category = "submodules"
  }
  synteny_figure = @{
    Package = "gljcvi-synteny-figure"
    Entry = "features\submodules\synteny_figure_entry.py"
    Category = "submodules"
  }
  karyotype = @{
    Package = "gljcvi-karyotype"
    Entry = "features\submodules\karyotype_entry.py"
    Category = "submodules"
  }
  local_synteny = @{
    Package = "gljcvi-local-synteny"
    Entry = "features\submodules\local_synteny_entry.py"
    Category = "submodules"
  }
  histogram = @{
    Package = "gljcvi-histogram"
    Entry = "features\submodules\histogram_entry.py"
    Category = "submodules"
  }
  heatmap = @{
    Package = "gljcvi-heatmap"
    Entry = "features\submodules\heatmap_entry.py"
    Category = "submodules"
  }
  global_karyotype = @{
    Package = "gljcvi-global-karyotype"
    Entry = "features\submodules\global_karyotype_entry.py"
    Category = "submodules"
  }
  multi_local_synteny = @{
    Package = "gljcvi-multi-local-synteny"
    Entry = "features\submodules\multi_local_synteny_entry.py"
    Category = "submodules"
  }
}

$featureMeta = $featureMap[$Feature]
$packageName = $featureMeta.Package
$entryPath = Join-Path $srcRoot $featureMeta.Entry
$category = $featureMeta.Category
$assetsRoot = Join-Path $root "integrations\haiant_plugin\assets\$category\$Feature"

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
$outputFolder = Join-Path $root "app\$category"
$zipPath = Join-Path $outputFolder "$packageName.zip"

foreach ($path in @($distRoot, $workRoot, $specRoot, $stageRoot)) {
  if (Test-Path $path) {
    Remove-Item -LiteralPath $path -Recurse -Force
  }
}

New-Item -ItemType Directory -Force -Path $distRoot | Out-Null
New-Item -ItemType Directory -Force -Path $workRoot | Out-Null
New-Item -ItemType Directory -Force -Path $specRoot | Out-Null
New-Item -ItemType Directory -Force -Path $stageRoot | Out-Null
New-Item -ItemType Directory -Force -Path $outputFolder | Out-Null

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

# 只有使用 species_pair 端口的插件才复制示例物种输入；histogram/heatmap/global_karyotype/multi_local_synteny 保持 input 空目录
$speciesInputFeatures = @(
  "synteny",
  "mcscan_pairwise",
  "catalog_ortholog",
  "dotplot",
  "synteny_figure",
  "karyotype",
  "local_synteny"
)
if ($speciesInputFeatures -contains $Feature) {
  Copy-Item (Join-Path $samplesRoot "query.bed") (Join-Path $inputDir "query.bed") -Force
  Copy-Item (Join-Path $samplesRoot "query.cds") (Join-Path $inputDir "query.cds") -Force
  Copy-Item (Join-Path $samplesRoot "subject.bed") (Join-Path $inputDir "subject.bed") -Force
  Copy-Item (Join-Path $samplesRoot "subject.cds") (Join-Path $inputDir "subject.cds") -Force
}

if (Test-Path $zipPath) {
  Remove-Item -LiteralPath $zipPath -Force
}
Compress-Archive -Path (Join-Path $stageRoot "*") -DestinationPath $zipPath

Write-Host "Wrote $zipPath"
