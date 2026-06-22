import { useCallback, useMemo, useState } from "react";

import type { ArtifactRecord, FigureAsset, RunSummaryViewModel } from "../models";
import type { AppRoute } from "../routes/routes";
import { openPath, readSummaryView } from "../services/workbench";

interface ResultsPageProps {
  route: AppRoute;
  onNavigate: (path: string) => void;
}

type QueryState = "idle" | "loading" | "ready" | "error";

function formatError(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

function statusClass(state: QueryState | RunSummaryViewModel["status"]) {
  if (state === "SUCCEEDED" || state === "ready") {
    return "bg-emerald-50 text-emerald-700";
  }
  if (state === "FAILED" || state === "error") {
    return "bg-rose-50 text-rose-700";
  }
  if (state === "loading" || state === "RUNNING" || state === "PENDING") {
    return "bg-amber-50 text-amber-700";
  }
  return "bg-slate-100 text-slate-600";
}

function ResultAssetRow({
  label,
  asset,
  onOpen,
}: {
  label: string;
  asset: FigureAsset;
  onOpen: (path: string) => void;
}) {
  return (
    <article className="grid gap-3 px-6 py-4 lg:grid-cols-[8rem_minmax(0,1fr)_auto]">
      <div className="text-sm text-slate-400">{label}</div>
      <div className="min-w-0">
        <p className="truncate text-sm font-medium text-slate-900">{asset.name}</p>
        <p className="mt-1 break-all text-sm text-slate-500">{asset.path}</p>
      </div>
      <div className="flex items-center gap-2">
        <span className="rounded-full bg-slate-100 px-2.5 py-1 text-[11px] font-semibold uppercase text-slate-600">
          {asset.format}
        </span>
        <button
          type="button"
          className="rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-medium text-slate-700 transition hover:bg-slate-50"
          onClick={() => onOpen(asset.path)}
        >
          Open
        </button>
      </div>
    </article>
  );
}

function ArtifactRow({
  artifact,
  onOpen,
}: {
  artifact: ArtifactRecord;
  onOpen: (path: string) => void;
}) {
  return (
    <article className="grid gap-3 px-6 py-4 lg:grid-cols-[10rem_minmax(0,1fr)_auto]">
      <div className="grid gap-1 text-sm">
        <span className="font-medium text-slate-900">{artifact.artifact_type}</span>
        <span className="text-slate-400">{artifact.artifact_id}</span>
      </div>
      <div className="min-w-0">
        <p className="break-all text-sm text-slate-500">{artifact.path}</p>
        <p className="mt-1 text-xs text-slate-400">{artifact.produced_by}</p>
      </div>
      <div className="flex items-center gap-2">
        <span className="rounded-full bg-slate-100 px-2.5 py-1 text-[11px] font-semibold uppercase text-slate-600">
          {artifact.format ?? "unknown"}
        </span>
        <button
          type="button"
          className="rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-medium text-slate-700 transition hover:bg-slate-50"
          onClick={() => onOpen(artifact.path)}
        >
          Open
        </button>
      </div>
    </article>
  );
}

export default function ResultsPage({ route, onNavigate }: ResultsPageProps) {
  const [outdir, setOutdir] = useState("");
  const [queryState, setQueryState] = useState<QueryState>("idle");
  const [summary, setSummary] = useState<RunSummaryViewModel | null>(null);
  const [queryError, setQueryError] = useState<string | null>(null);
  const [openError, setOpenError] = useState<string | null>(null);

  const trimmedOutdir = outdir.trim();

  const loadSummary = useCallback(async () => {
    if (!trimmedOutdir) {
      setSummary(null);
      setQueryState("idle");
      setQueryError(null);
      return;
    }

    setQueryState("loading");
    setQueryError(null);
    try {
      const nextSummary = await readSummaryView({ outdir: trimmedOutdir });
      setSummary(nextSummary);
      setQueryState("ready");
    } catch (error: unknown) {
      setSummary(null);
      setQueryError(formatError(error));
      setQueryState("error");
    }
  }, [trimmedOutdir]);

  const handleOpenPath = useCallback(async (path: string) => {
    setOpenError(null);
    try {
      await openPath({ path });
    } catch (error: unknown) {
      setOpenError(formatError(error));
    }
  }, []);

  const primaryAssets = useMemo(() => {
    if (!summary) {
      return [];
    }

    const primarySet = new Set(summary.primaryFigurePaths);
    return summary.figureAssets.filter((asset) => primarySet.has(asset.path));
  }, [summary]);

  return (
    <section className="grid w-full gap-0 overflow-hidden border border-slate-200 bg-white xl:grid-cols-[17rem_minmax(0,1fr)]">
      <aside className="border-r border-slate-200/80 bg-[#f6f8f9]">
        <div className="border-b border-slate-200/80 px-5 py-5">
          <p className="text-xs font-medium uppercase tracking-[0.18em] text-slate-400">{route.label}</p>
          <h1 className="mt-2 text-lg font-semibold text-slate-900">Run summary browser</h1>
          <p className="mt-2 text-sm leading-6 text-slate-500">{route.description}</p>
        </div>

        <div className="px-5 py-4">
          <label className="text-xs font-medium uppercase tracking-[0.18em] text-slate-400" htmlFor="results-outdir">
            Output directory
          </label>
          <input
            id="results-outdir"
            type="text"
            value={outdir}
            placeholder="Enter an analysis outdir"
            className="mt-3 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-ice-400 focus:ring-2 focus:ring-ice-100"
            onChange={(event) => setOutdir(event.target.value)}
          />
          <div className="mt-3 grid gap-2">
            <button
              type="button"
              className="rounded-lg bg-slate-900 px-3 py-2 text-sm font-semibold text-white transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:bg-slate-300"
              disabled={queryState === "loading"}
              onClick={() => void loadSummary()}
            >
              {queryState === "loading" ? "Loading..." : "Load summary"}
            </button>
            <button
              type="button"
              className="rounded-lg border border-slate-200 px-3 py-2 text-sm font-medium text-slate-600 transition hover:bg-white hover:text-slate-900 disabled:cursor-not-allowed disabled:text-slate-400"
              disabled={!trimmedOutdir}
              onClick={() => void handleOpenPath(trimmedOutdir)}
            >
              Open output
            </button>
            <button
              type="button"
              className="rounded-lg border border-slate-200 px-3 py-2 text-sm font-medium text-slate-600 transition hover:bg-white hover:text-slate-900"
              onClick={() => onNavigate("/analysis/new")}
            >
              Back to workbench
            </button>
          </div>
        </div>

        <div className="border-t border-slate-200/80 px-5 py-4">
          <div className="text-[11px] font-medium uppercase tracking-[0.18em] text-slate-400">State</div>
          <div className="mt-3 divide-y divide-slate-200/80 border-y border-slate-200/80">
            <div className="flex items-center justify-between py-3 text-sm">
              <span className="text-slate-400">Query</span>
              <span className="font-medium capitalize text-slate-900">{queryState}</span>
            </div>
            <div className="flex items-center justify-between py-3 text-sm">
              <span className="text-slate-400">Figures</span>
              <span className="font-medium text-slate-900">{summary?.figureAssets.length ?? 0}</span>
            </div>
            <div className="flex items-center justify-between py-3 text-sm">
              <span className="text-slate-400">Artifacts</span>
              <span className="font-medium text-slate-900">{summary?.artifactIndex.length ?? 0}</span>
            </div>
          </div>
        </div>
      </aside>

      <div className="min-w-0 bg-white">
        <div className="border-b border-slate-200/80 px-6 py-5">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-xs font-medium uppercase tracking-[0.18em] text-slate-400">Results</p>
              <h2 className="mt-1 text-lg font-semibold text-slate-900">Status, figures, and artifacts</h2>
              <p className="mt-2 text-sm leading-6 text-slate-500">
                This page reads `readSummaryView()` now and can later absorb additional artifact commands without changing the layout.
              </p>
            </div>
            <span
              className={`rounded-full px-3 py-1 text-[11px] font-semibold uppercase ${statusClass(
                summary?.status ?? queryState,
              )}`}
            >
              {summary?.status ?? queryState}
            </span>
          </div>
        </div>

        {queryError ? <div className="border-b border-slate-200/80 bg-rose-50 px-6 py-4 text-sm text-rose-700">{queryError}</div> : null}
        {openError ? <div className="border-b border-slate-200/80 bg-rose-50 px-6 py-4 text-sm text-rose-700">{openError}</div> : null}

        {!trimmedOutdir && queryState === "idle" ? (
          <div className="border-b border-slate-200/80 px-6 py-10 text-sm text-slate-500">
            Enter an output directory to inspect a run summary and its result files.
          </div>
        ) : null}

        {summary ? (
          <>
            <section>
              <div className="px-6 py-4">
                <h3 className="text-sm font-semibold text-slate-900">Overview</h3>
              </div>
              <div className="divide-y divide-slate-200/80 border-y border-slate-200/80">
                <div className="grid grid-cols-[12rem_minmax(0,1fr)] gap-4 px-6 py-4 text-sm">
                  <span className="text-slate-400">Workflow</span>
                  <span className="font-medium text-slate-900">{summary.workflow}</span>
                </div>
                <div className="grid grid-cols-[12rem_minmax(0,1fr)] gap-4 px-6 py-4 text-sm">
                  <span className="text-slate-400">Method</span>
                  <span className="font-medium text-slate-900">{summary.method || "Unavailable"}</span>
                </div>
                <div className="grid grid-cols-[12rem_minmax(0,1fr)] gap-4 px-6 py-4 text-sm">
                  <span className="text-slate-400">Progress</span>
                  <span className="font-medium text-slate-900">{summary.progress}%</span>
                </div>
                <div className="grid grid-cols-[12rem_minmax(0,1fr)] gap-4 px-6 py-4 text-sm">
                  <span className="text-slate-400">Summary path</span>
                  <button
                    type="button"
                    className="truncate text-left font-medium text-ice-700 transition hover:text-ice-900"
                    onClick={() => void handleOpenPath(summary.runSummaryPath)}
                  >
                    {summary.runSummaryPath || "Unavailable"}
                  </button>
                </div>
                <div className="grid grid-cols-[12rem_minmax(0,1fr)] gap-4 px-6 py-4 text-sm">
                  <span className="text-slate-400">Run log</span>
                  <button
                    type="button"
                    className="truncate text-left font-medium text-ice-700 transition hover:text-ice-900"
                    onClick={() => void handleOpenPath(summary.runLogPath)}
                  >
                    {summary.runLogPath || "Unavailable"}
                  </button>
                </div>
              </div>
            </section>

            <section>
              <div className="px-6 py-4">
                <h3 className="text-sm font-semibold text-slate-900">Primary figures</h3>
                <p className="mt-1 text-sm text-slate-500">Current lightweight results are driven by summary figures until dedicated artifact listing lands.</p>
              </div>

              {primaryAssets.length > 0 ? (
                <div className="divide-y divide-slate-200/80 border-y border-slate-200/80">
                  {primaryAssets.map((asset) => (
                    <ResultAssetRow key={asset.path} label={asset.source} asset={asset} onOpen={(path) => void handleOpenPath(path)} />
                  ))}
                </div>
              ) : (
                <div className="border-y border-slate-200/80 px-6 py-8 text-sm text-slate-500">No primary figures were advertised in the summary.</div>
              )}
            </section>

            <section>
              <div className="px-6 py-4">
                <h3 className="text-sm font-semibold text-slate-900">Artifacts</h3>
                <p className="mt-1 text-sm text-slate-500">Artifact rows currently come from `artifact_index` in the summary payload.</p>
              </div>

              {summary.artifactIndex.length > 0 ? (
                <div className="divide-y divide-slate-200/80 border-y border-slate-200/80">
                  {summary.artifactIndex.map((artifact) => (
                    <ArtifactRow key={`${artifact.artifact_id}-${artifact.path}`} artifact={artifact} onOpen={(path) => void handleOpenPath(path)} />
                  ))}
                </div>
              ) : (
                <div className="border-y border-slate-200/80 px-6 py-8 text-sm text-slate-500">No artifact records were returned in the current summary.</div>
              )}
            </section>
          </>
        ) : null}
      </div>
    </section>
  );
}
