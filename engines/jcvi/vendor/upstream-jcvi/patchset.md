# GenomeLens Patchset

This file tracks **direct local modifications** applied to the vendored upstream tree at `engines/jcvi/src/jcvi/`.

It does **not** list:

- normal GenomeLens engine wrapper code under `engines/jcvi/src/jcvi_genomelens/`
- pure upstream sync changes that arrived when upgrading from one JCVI version to another

## Current base

- Upstream JCVI version: `1.6.6`
- Patchset name: `windows-genomelens`
- Initial vendored import checkpoint: `60915aa1`
- Latest recorded upstream sync checkpoint: `126ab6c5`

## Direct local patches relative to upstream JCVI 1.6.6

### 1. Version metadata pin

- File: `engines/jcvi/src/jcvi/_version.py`
- Purpose: keep a stable vendored version string for packaged GenomeLens builds and probe output
- Local behavior: expose `__version__ = "1.6.6"`

### 2. Windows shell/runtime compatibility

- File: `engines/jcvi/src/jcvi/apps/base.py`
- Local changes:
  - guard `signal.SIGPIPE` access on Windows
  - let `which()` resolve `.exe` candidates when the caller passes bare executable names
  - avoid forcing `/bin/bash` as the execution shell on Windows paths

### 3. Tree dependency fallback

- File: `engines/jcvi/src/jcvi/graphics/tree.py`
- Local change:
  - prefer `ete4` when available
  - fall back to `ete3` for the current Windows GenomeLens runtime

## Recording rule

Whenever a future commit edits any file under `engines/jcvi/src/jcvi/`, append a new entry here with:

- file path
- reason
- behavior change
- commit id in the GenomeLens repository
