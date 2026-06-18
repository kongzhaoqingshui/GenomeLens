# GUI data contract notes

This directory contains the Phase 0 TypeScript draft for the GUI business/data-flow layer.

## Scope

- `analysis-request.ts` mirrors `platform/src/genomelens/analysis/request_models.py`.
- `run-summary.ts` mirrors the stable top-level fields in `platform/src/genomelens/core/summary_models.py`.
- `validation.ts` is a field-level validation draft for the task creation form.

## Suggestions for A and the core maintainer

1. Keep GUI requests aligned with `AnalysisRequest` schema version `1`.
2. Expose `analyze template mcscan` and `analyze schema` through Tauri commands before the task wizard is wired.
3. Treat `method_config` as method-specific payload. The GUI should not move JCVI fields into generic options.
4. Prefer reading `run_summary.json` and `artifact_index` for result pages instead of scraping stdout.
5. Confirm whether GUI should validate target gene existence client-side by reading reference BED, or leave that to platform validation.

## Known schema question

`AnalysisOptions` in Python already includes `log_level`, `verbose`, and `console_log`, while the current JSON schema document only lists
`preset`, `threads`, and `min_block_size`. The GUI types include the Python fields so the task form can round-trip platform requests.

