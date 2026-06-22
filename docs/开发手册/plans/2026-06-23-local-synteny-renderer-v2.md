# Local Synteny Renderer V2

Date: 2026-06-23
Branch: codex/local-synteny-renderer-v2-main
Complexity: High

## Scope

Rewrite the native local synteny renderer into a chromosome-aware renderer for
local comparative genomics figures. The renderer must handle `.blocks` rows
where a species column crosses chromosomes, where long anchor-free intervals
would otherwise stretch the panel, and where each track may contain one or more
chromosome segments.

## Modules

- `engines/jcvi/src/jcvi_genomelens/graphics/local_synteny_renderer.py`
- `engines/jcvi/src/jcvi_genomelens/workflows/local_synteny.py`
- `engines/jcvi/src/jcvi_genomelens/workflows/local_synteny_multi.py`
- `platform/src/genomelens/app/controller/runners/local_synteny_aggregate.py`
- Renderer and aggregate tests under `engines/jcvi/tests` and `platform/tests`

## Architecture

- Scene builder: parse `.blocks` and merged BED into block rows, genes, targets,
  and track names without assuming a single chromosome per species.
- Layout solver: split each track into `(species, chromosome)` segments, compress
  long intra-chromosome gaps, assign segment lanes, and build adjacent-track
  links only (`0-1`, `1-2`, not `0-2`).
- Matplotlib renderer: draw chromosome bars, crisp gene ticks, compact terminal
  break markers, chromosome/range labels, JCVI-style interval ribbons, and a
  bottom target-gene colour legend.

## Acceptance Criteria

- `Iin.Chr`-style cross-chromosome blocks render as separate `Iin5` and `Iin2`
  chromosome segments.
- Long anchor-free gaps are represented with break markers and `...`.
- Multi-track links are adjacent-track links; missing middle values do not create
  cross-track shortcuts.
- Tracks are rendered at true relative local-window lengths and centered on the
  shared canvas axis.
- Target chromosome segments are automatically reversed when anchor order
  descends relative to the reference, with descending range labels such as
  `18.33-7.50Mb`.
- Synteny links are JCVI-style interval ribbons based on gene widths, with
  inversion ribbons drawn by reversed endpoints.
- Very short chromosome segments include up to 20 same-chromosome flanking genes
  on each side and show compact terminal break marks when the BED context
  continues.
- Special short truncated segments use a distinct warning edge/text colour to
  show that readability-preserving expansion has relaxed strict visual scale.
- Target/highlight genes are represented by coloured ribbons and a bottom legend,
  not by star markers.
- Chromosome labels are unboxed compact text, truncation is shown with integrated
  terminal break marks, and dense gene ticks remain crisp without translucent
  block overlays.
- Upper chromosome labels sit close to the track, roughly matching the range
  label spacing, and use a subtle semi-transparent white cushion rather than a
  framed box.
- Existing `render_local_synteny(...)` call signature remains stable.
- `use_native_local_synteny_renderer=true` uses V2, while `false` keeps the JCVI
  fallback path.
- Multi-species aggregate preserves all usable subject hits instead of keeping
  only the first subject gene from a row.

## Verification

- Unit tests for renderer segment splitting, gap compression, scoped IDs,
  missing values, and adjacent-only links.
- Unit tests for centered true-length tracks, flanking context expansion,
  chromosome label placement rules, interval ribbon endpoints, target legends,
  and raster DPI handling.
- Visual regression checks ensure the old chromosome label frame colour and
  pair-cloud background are not emitted.
- Unit tests for multi-species aggregate multi-hit preservation.
- Engine integration tests for native local synteny multi rendering.
- Manual visual inspection against `app/gljcvi-auto` intermediate data.

## Debt And Follow-Up

- Publication mode can later add curated colored gene-family paths, photos,
  explicit phenotype labels, and custom legend blocks like the reference paper
  figure.
- The current V2 focuses on robust comparative-genomics layout and compact
  local synteny readability.
