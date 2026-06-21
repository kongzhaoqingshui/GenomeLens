$ErrorActionPreference = "Stop"
$scriptRoot = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
if (-not $scriptRoot) { $scriptRoot = (Resolve-Path (Join-Path (Get-Location) "scripts")).Path }
$root = [System.IO.Path]::GetFullPath((Join-Path $scriptRoot ".."))
$pluginName = "GenomeLens-HAIant-plugin-1.0.0.post1"
$stage = Join-Path $root ".build\$pluginName"
$zip = Join-Path $root "app\$pluginName.zip"
New-Item -ItemType Directory -Force -Path (Join-Path $root "app") | Out-Null
if (Test-Path $stage) { Remove-Item -LiteralPath $stage -Recurse -Force }
New-Item -ItemType Directory -Force -Path $stage | Out-Null
if (-not (Test-Path "$root\integrations\haiant_plugin\dist\GenomeLens.exe")) {
  throw "Plugin entry exe not found. Build integrations/haiant_plugin first."
}
Copy-Item "$root\integrations\haiant_plugin\dist\GenomeLens.exe" "$stage\GenomeLens.exe" -Force
Copy-Item "$root\integrations\haiant_plugin\dist\GenomeLens.exe" "$stage\main.exe" -Force
Copy-Item "$root\integrations\haiant_plugin\assets\config.json" "$stage\config.json"
Copy-Item "$root\integrations\haiant_plugin\assets\params.json" "$stage\params.json"
Copy-Item "$root\integrations\haiant_plugin\assets\README.md" "$stage\README.md"
Copy-Item "$root\integrations\haiant_plugin\PARAMETER_MAPPING.md" "$stage\PARAMETER_MAPPING.md"
New-Item -ItemType Directory -Force -Path "$stage\input" | Out-Null
Copy-Item "$root\references\samples\shell\bed_cds_minimal\query.bed" "$stage\input\query.bed" -Force
Copy-Item "$root\references\samples\shell\bed_cds_minimal\query.cds" "$stage\input\query.cds" -Force
Copy-Item "$root\references\samples\shell\bed_cds_minimal\subject.bed" "$stage\input\subject.bed" -Force
Copy-Item "$root\references\samples\shell\bed_cds_minimal\subject.cds" "$stage\input\subject.cds" -Force
New-Item -ItemType Directory -Force -Path "$stage\output" | Out-Null
Set-Content -LiteralPath "$stage\output\.gitkeep" -Value "" -Encoding UTF8
New-Item -ItemType Directory -Force -Path "$stage\runtime\GenomeLens" | Out-Null
if (Test-Path "$root\platform\dist\GenomeLens") {
  Copy-Item "$root\platform\dist\GenomeLens\*" "$stage\runtime\GenomeLens" -Recurse -Force
}
$toolchainStage = Join-Path $stage "runtime\GenomeLens\resources\toolchain"
$blastSource = "$root\toolchains\blast\current"
$blastTarget = Join-Path $toolchainStage "blast"
$engineSource = "$root\toolchains\jcvi-genomelens\current\jcvi-genomelens.exe"
$engineTarget = Join-Path $toolchainStage "jcvi-genomelens\bin"
if (-not (Test-Path $blastSource)) {
  throw "BLAST toolchain not found: $blastSource"
}
if (-not (Test-Path $engineSource)) {
  throw "JCVI engine executable not found: $engineSource"
}
New-Item -ItemType Directory -Force -Path $blastTarget, $engineTarget | Out-Null
Copy-Item "$blastSource\*" $blastTarget -Recurse -Force
Copy-Item $engineSource "$engineTarget\jcvi-genomelens.exe" -Force
$imagemagickSource = "$root\toolchains\imagemagick\current"
if (Test-Path $imagemagickSource) {
  $imagemagickTarget = Join-Path $toolchainStage "imagemagick"
  New-Item -ItemType Directory -Force -Path $imagemagickTarget | Out-Null
  Copy-Item "$imagemagickSource\*" $imagemagickTarget -Recurse -Force
}
if (Test-Path $zip) { Remove-Item -LiteralPath $zip -Force }
Compress-Archive -Path "$stage\*" -DestinationPath $zip
Write-Host "Wrote $zip"
