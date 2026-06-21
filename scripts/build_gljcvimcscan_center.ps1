$ErrorActionPreference = "Stop"
$root = (Resolve-Path "$PSScriptRoot\..").Path
$pluginName = "gljcvimcscan-1.0.0"
$stage = Join-Path $root ".build\$pluginName"
$zip = Join-Path $root "app\$pluginName.zip"
$entryBuild = Join-Path $root "integrations\haiant_plugin\build\gljcvimcscan"
$entryDist = Join-Path $root "integrations\haiant_plugin\dist\gljcvimcscan"
$entryScript = Join-Path $root "integrations\haiant_plugin\src\gljcvimcscan_entry.py"
$entryExe = Join-Path $entryDist "main.exe"
$platformDist = Join-Path $root "platform\dist\GenomeLens"

if (-not (Test-Path $platformDist)) {
  throw "Platform bundle not found at $platformDist. Build scripts/build_split_packages.ps1 first."
}
if (-not (Test-Path (Join-Path $platformDist "genomelens.cmd")) -and -not (Test-Path (Join-Path $platformDist "genomelens.exe"))) {
  throw "Platform shell not found in $platformDist. Ensure the split package build produced genomelens.cmd or genomelens.exe."
}

foreach ($path in @($stage, $entryBuild, $entryDist)) {
  if (Test-Path $path) { Remove-Item -LiteralPath $path -Recurse -Force }
}

python -m PyInstaller --onefile --name main $entryScript --distpath $entryDist --workpath $entryBuild --specpath $entryBuild --clean
if (-not (Test-Path $entryExe)) {
  throw "gljcvimcscan entry executable not found: $entryExe"
}

New-Item -ItemType Directory -Force -Path $stage | Out-Null
robocopy $platformDist $stage /E | Out-Null
if ($LASTEXITCODE -gt 7) { exit $LASTEXITCODE }

Copy-Item $entryExe (Join-Path $stage "main.exe") -Force
Copy-Item "$root\integrations\haiant_plugin\assets\gljcvimcscan\config.json" (Join-Path $stage "config.json") -Force
Copy-Item "$root\integrations\haiant_plugin\assets\gljcvimcscan\params.json" (Join-Path $stage "params.json") -Force
Copy-Item "$root\integrations\haiant_plugin\assets\gljcvimcscan\README.md" (Join-Path $stage "README.md") -Force
Copy-Item "$root\integrations\haiant_plugin\PARAMETER_MAPPING.md" (Join-Path $stage "PARAMETER_MAPPING.md") -Force
Copy-Item "$root\integrations\haiant_plugin\ARCHITECTURE.md" (Join-Path $stage "ARCHITECTURE.md") -Force

New-Item -ItemType Directory -Force -Path (Join-Path $stage "input") | Out-Null
Copy-Item "$root\references\samples\shell\bed_cds_minimal\query.bed" (Join-Path $stage "input\query.bed") -Force
Copy-Item "$root\references\samples\shell\bed_cds_minimal\query.cds" (Join-Path $stage "input\query.cds") -Force
Copy-Item "$root\references\samples\shell\bed_cds_minimal\subject.bed" (Join-Path $stage "input\subject.bed") -Force
Copy-Item "$root\references\samples\shell\bed_cds_minimal\subject.cds" (Join-Path $stage "input\subject.cds") -Force
New-Item -ItemType Directory -Force -Path (Join-Path $stage "output") | Out-Null

if (Test-Path $zip) { Remove-Item -LiteralPath $zip -Force }
Compress-Archive -Path "$stage\*" -DestinationPath $zip
Write-Host "Wrote $zip"
