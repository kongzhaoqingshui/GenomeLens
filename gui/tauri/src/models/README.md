# GUI data contract notes

This directory contains the Phase 0 TypeScript draft for the GUI business/data-flow layer.

## Scope

- `check-report.ts` mirrors the structured `genomelens check -j` payload and provides simple environment display helpers.
- `analysis-request.ts` mirrors `platform/src/genomelens/analysis/request_models.py`.
- `analysis-request-draft.ts` provides GUI-local camelCase draft types plus request mapping helpers for forms/stores.
- `project.ts` and `run-session.ts` define the GUI-owned Tauri command payloads for project listing, analysis runs, log snapshots, and event flow.
- `run-summary.ts` mirrors the stable top-level fields in `platform/src/genomelens/core/summary_models.py`.
- `run-summary-view.ts` provides GUI-local result parsing helpers centered on `run_summary.json` and `artifact_index`.
- `validation.ts` is a field-level validation draft for the task creation form.

## Suggestions for A and the core maintainer

1. Keep GUI requests aligned with `AnalysisRequest` schema version `1`.
2. Expose `analyze template mcscan` and `analyze schema` through Tauri commands before the task wizard is wired.
3. Treat `method_config` as method-specific payload. The GUI should not move JCVI fields into generic options.
4. Prefer reading `run_summary.json` and `artifact_index` for result pages instead of scraping stdout.
5. Confirm whether GUI should validate target gene existence client-side by reading reference BED, or leave that to platform validation.
6. Keep direct command payloads in platform `snake_case`; map to GUI-local `camelCase` draft/view models only at the frontend boundary.

## Known schema question

`AnalysisOptions` in Python already includes `log_level`, `verbose`, and `console_log`, while the current JSON schema document only lists
`preset`, `threads`, and `min_block_size`. The GUI types include the Python fields so the task form can round-trip platform requests.

