param(
  [switch]$SkipInstall,
  [switch]$SkipFrontendChecks,
  [switch]$SkipRustChecks,
  [switch]$SkipClippy,
  [switch]$TauriBuild,
  [switch]$DebugBundle
)

$ErrorActionPreference = "Stop"

$root = (Resolve-Path "$PSScriptRoot\..").Path
$gui = Join-Path $root "gui\tauri"
$cargoManifest = Join-Path $gui "src-tauri\Cargo.toml"

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
    } else {
      Invoke-GuiStep "Build GUI Tauri release bundle" {
        corepack pnpm tauri build
      }
    }
  }
} finally {
  Pop-Location
}

Write-Host ""
Write-Host "GUI build flow completed."
