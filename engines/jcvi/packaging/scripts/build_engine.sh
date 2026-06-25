#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "${PROJECT_ROOT}"

# Compile optional Cython extensions in-place so PyInstaller bundles them.
python setup.py build_ext --inplace

# Build frozen executable.
python -m PyInstaller packaging/pyinstaller/jcvi_genomelens.spec --clean --noconfirm
