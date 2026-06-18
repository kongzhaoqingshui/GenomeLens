# GUI Phase 0 demo data

This directory contains the minimal local data used by the GUI Phase 0 business/data-flow work.

## Data Set

`bed-cds-minimal/input/` contains three small BED+CDS species:

- `query`: reference species used by pairwise and local synteny demos
- `subject`: first target species
- `third`: second target species used by the multi-species all-vs-all demo

The sequences are intentionally tiny and deterministic. `query` and `subject` mirror the repository shell fixture, while
`third` uses matching CDS sequences with distinct gene IDs so GUI parsing can exercise multi-species output without
large files.

## Request Examples

`requests/` contains three `AnalysisRequest` JSON files:

- `pairwise-mcscan.json`: two-species `graphics_synteny`
- `multi-species-all-vs-all.json`: three-species all-vs-all pairwise aggregation
- `local-synteny.json`: two-species local synteny centered on `qgene2`

Run from the repository root:

```powershell
conda activate genomelens
genomelens analyze run gui/demo-data/requests/pairwise-mcscan.json -j
genomelens analyze run gui/demo-data/requests/multi-species-all-vs-all.json -j
genomelens analyze run gui/demo-data/requests/local-synteny.json -j
```

Outputs are written under `gui/demo-data/runs/`, which is ignored by Git.

