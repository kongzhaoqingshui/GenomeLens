# GUI data contract notes

This directory contains the Phase 0 TypeScript draft for the GUI business/data-flow layer.

> Current platform protocol note: platform requests have moved to `WorkflowRequest v2` and summaries to `RunSummary v3`.
> The files in this directory still contain `AnalysisRequest v1` drafts from the first GUI spike and should be treated as migration targets, not as the current protocol contract.

## Scope

- `check-report.ts` mirrors the structured `genomelens check -j` payload and provides simple environment display helpers.
- `analysis-request.ts` currently mirrors the old request draft and should be replaced by a `workflow-request.ts` model.
- `analysis-request-draft.ts` currently provides old GUI-local draft helpers and should be replaced by `WorkflowRequestDraft` mapping helpers.
- `artifact.ts` defines GUI-owned Tauri payloads for listing run artifacts from `run_summary.json`.
- `jcvi-meow.ts` provides GUI-owned startup warmup state, capability entry view models, and workflow preset helpers for the JCVI shell experience.
- `project.ts` and `run-session.ts` define the GUI-owned Tauri command payloads for project listing, analysis runs, log snapshots, and event flow.
- `request-preview.ts` defines the GUI-owned Tauri payloads for importing and previewing a local request JSON file; it should summarize `workflow_id` for V2 requests.
- `run-summary.ts` should mirror the stable top-level fields in `platform/src/genomelens/core/summary_models.py`, including `artifact_index`, `child_runs`, and `extensions`.
- `run-summary-view.ts` provides GUI-local result parsing helpers centered on `run_summary.json` and `artifact_index`.
- `validation.ts` is a field-level validation draft for the task creation form.

## Suggestions for A and the core maintainer

1. Keep GUI requests aligned with `WorkflowRequest` schema version `2`.
2. Expose `analyze template <workflow>` and `analyze schema` through Tauri commands before the task wizard is wired.
3. Treat `parameters.*` as workflow-specific payloads. The GUI should not rebuild platform workflow planning logic.
4. Prefer reading `run_summary.json` and `artifact_index` for result pages instead of scraping stdout.
5. Confirm whether GUI should validate target gene existence client-side by reading reference BED, or leave that to platform validation.
6. Keep direct command payloads in platform `snake_case`; map to GUI-local `camelCase` draft/view models only at the frontend boundary.

## Migration focus

Replace the old `AnalysisRequest` draft stack with:

1. `WorkflowRequest` platform JSON types.
2. `WorkflowRequestDraft` GUI-local form state.
3. Explicit `toWorkflowRequest()` / `fromWorkflowRequest()` adapters.
4. `RunSummary v3` result view models based on `artifact_index`, `child_runs`, and `extensions`.

