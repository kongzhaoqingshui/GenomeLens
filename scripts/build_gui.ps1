param(
  [switch]$SkipInstall,
  [switch]$SkipFrontendChecks,
  [switch]$SkipRustChecks,
  [switch]$SkipClippy,
  [switch]$TauriBuild,
  [switch]$DebugBundle,
  [string]$OutputDir
)

$ErrorActionPreference = "Stop"

$root = (Resolve-Path "$PSScriptRoot\..").Path
$gui = Join-Path $root "gui\tauri"
$cargoManifest = Join-Path $gui "src-tauri\Cargo.toml"
$defaultAppOutput = Join-Path $root "app\JCVI-meow-gui"

if (-not (Test-Path $gui)) {
  throw "GUI workspace not found: $gui"
}

function Invoke-GuiStep {
  param(
    [Parameter(Mandatory = $true)][string]$Name,
    [Parameter(Mandatory = $true)][scriptblock]$Script
  )

  Write-Host ""
  Write-Host "==> $Name"
  & $Script
}

function Resolve-GuiOutputDir {
  if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    return $defaultAppOutput
  }

  if ([System.IO.Path]::IsPathRooted($OutputDir)) {
    return $OutputDir
  }

  return (Join-Path $root $OutputDir)
}

function Publish-GuiApp {
  param(
    [Parameter(Mandatory = $true)][string]$Profile
  )

  $targetDir = Join-Path $gui "src-tauri\target\$Profile"
  $sourceExe = Join-Path $targetDir "genomelens-gui.exe"
  if (-not (Test-Path $sourceExe)) {
    throw "Tauri executable was not found after build: $sourceExe"
  }

  $appOutput = Resolve-GuiOutputDir
  if (Test-Path $appOutput) {
    Remove-Item -LiteralPath $appOutput -Recurse -Force
  }

  New-Item -ItemType Directory -Path $appOutput | Out-Null
  Copy-Item -LiteralPath $sourceExe -Destination (Join-Path $appOutput "JCVI-meow.exe") -Force

  $bundleSource = Join-Path $targetDir "bundle"
  if (Test-Path $bundleSource) {
    $bundleOutput = Join-Path $appOutput "bundle"
    New-Item -ItemType Directory -Path $bundleOutput | Out-Null
    Get-ChildItem -Path $bundleSource -Recurse -File | ForEach-Object {
      $relative = [System.IO.Path]::GetRelativePath($bundleSource, $_.FullName)
      $destination = Join-Path $bundleOutput $relative
      $destinationParent = Split-Path -Parent $destination
      if (-not (Test-Path $destinationParent)) {
        New-Item -ItemType Directory -Path $destinationParent | Out-Null
      }
      Copy-Item -LiteralPath $_.FullName -Destination $destination -Force
    }
  }

  $manifest = [ordered]@{
    product = "JCVI meow"
    profile = $Profile
    executable = "JCVI-meow.exe"
    sourceExecutable = $sourceExe
    builtAt = (Get-Date).ToString("o")
  }
  $manifest | ConvertTo-Json | Set-Content -Path (Join-Path $appOutput "build-manifest.json") -Encoding UTF8

  Write-Host "Published GUI app to $appOutput"
}

Push-Location $gui
try {
  Invoke-GuiStep "Check Corepack pnpm" {
    corepack pnpm --version
  }

  if (-not $SkipInstall) {
    Invoke-GuiStep "Install GUI dependencies" {
      corepack pnpm install --frozen-lockfile
    }
  }

  if (-not $SkipFrontendChecks) {
    Invoke-GuiStep "Lint GUI frontend" {
      corepack pnpm run lint
    }
    Invoke-GuiStep "Typecheck GUI frontend" {
      corepack pnpm typecheck
    }
    Invoke-GuiStep "Test GUI frontend" {
      corepack pnpm test
    }
    Invoke-GuiStep "Build GUI web assets" {
      corepack pnpm build:web
    }
  }

  if (-not $SkipRustChecks) {
    if (-not (Get-Command cargo -ErrorAction SilentlyContinue)) {
      throw "cargo was not found on PATH. Install Rust before running GUI Rust checks."
    }

    Invoke-GuiStep "Check GUI Tauri crate" {
      cargo check --manifest-path $cargoManifest
    }

    if (-not $SkipClippy) {
      Invoke-GuiStep "Lint GUI Tauri crate" {
        cargo clippy --manifest-path $cargoManifest -- -D warnings
      }
    }
  }

  if ($TauriBuild) {
    if ($DebugBundle) {
      Invoke-GuiStep "Build GUI Tauri debug bundle" {
        corepack pnpm tauri build --debug
      }
      Invoke-GuiStep "Publish GUI debug app to app directory" {
        Publish-GuiApp -Profile "debug"
      }
    } else {
      Invoke-GuiStep "Build GUI Tauri release bundle" {
        corepack pnpm tauri build
      }
      Invoke-GuiStep "Publish GUI release app to app directory" {
        Publish-GuiApp -Profile "release"
      }
    }
  }
} finally {
  Pop-Location
}

Write-Host ""
Write-Host "GUI build flow completed."
