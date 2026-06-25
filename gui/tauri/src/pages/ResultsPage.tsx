import { useCallback, useMemo, useState } from "react";

import { useLanguage } from "../i18n/useLanguage";
import type { ArtifactRecord, ArtifactSummary, ChildRunRecord, FigureAsset, RunSummaryViewModel } from "../models";
import type { AppRoute } from "../routes/routes";
import { listArtifacts, openPath, readSummaryView } from "../services/workbench";

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
    return "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-200";
  }
  if (state === "FAILED" || state === "error") {
    return "bg-rose-50 text-rose-700 dark:bg-rose-950/30 dark:text-rose-200";
  }
  if (state === "loading" || state === "RUNNING" || state === "PENDING") {
    return "bg-amber-50 text-amber-700 dark:bg-amber-950/30 dark:text-amber-200";
  }
  return "bg-surface text-text-secondary";
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
  const { language } = useLanguage();
  const isZh = language === "zh-CN";
  return (
    <article className="ui-row-item grid gap-3 px-6 py-4 lg:grid-cols-[8rem_minmax(0,1fr)_auto]">
      <div className="text-sm text-text-tertiary">{label}</div>
      <div className="min-w-0">
        <p className="truncate text-sm font-medium text-text-primary">{asset.name}</p>
        <p className="mt-1 break-all text-sm text-text-secondary">{asset.path}</p>
      </div>
      <div className="flex items-center gap-2">
        <span className="rounded-full bg-surface px-2.5 py-1 text-[11px] font-semibold uppercase text-text-secondary">{asset.format}</span>
        <button
          type="button"
          className="ui-pressable rounded-lg border border-border bg-surface px-3 py-1.5 text-xs font-medium text-text-secondary transition hover:bg-surface-raised hover:text-text-primary"
          onClick={() => onOpen(asset.path)}
        >
          {isZh ? "打开" : "Open"}
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
  const { language } = useLanguage();
  const isZh = language === "zh-CN";
  return (
    <article className="ui-row-item grid gap-3 px-6 py-4 lg:grid-cols-[10rem_minmax(0,1fr)_auto]">
      <div className="grid gap-1 text-sm">
        <span className="font-medium text-text-primary">{artifact.artifact_type}</span>
        <span className="text-text-tertiary">{artifact.artifact_id}</span>
      </div>
      <div className="min-w-0">
        <p className="break-all text-sm text-text-secondary">{artifact.path}</p>
        <p className="mt-1 text-xs text-text-tertiary">{artifact.produced_by}</p>
      </div>
      <div className="flex items-center gap-2">
        <span className="rounded-full bg-surface px-2.5 py-1 text-[11px] font-semibold uppercase text-text-secondary">
          {artifact.format ?? "unknown"}
        </span>
        <button
          type="button"
          className="ui-pressable rounded-lg border border-border bg-surface px-3 py-1.5 text-xs font-medium text-text-secondary transition hover:bg-surface-raised hover:text-text-primary"
          onClick={() => onOpen(artifact.path)}
        >
          {isZh ? "打开" : "Open"}
        </button>
      </div>
    </article>
  );
}

function ArtifactSummaryRow({
  artifact,
  onOpen,
}: {
  artifact: ArtifactSummary;
  onOpen: (path: string) => void;
}) {
  const { language } = useLanguage();
  const isZh = language === "zh-CN";
  return (
    <article className="ui-row-item grid gap-3 px-6 py-4 lg:grid-cols-[10rem_minmax(0,1fr)_auto]">
      <div className="grid gap-1 text-sm">
        <span className="font-medium text-text-primary">{artifact.name}</span>
        <span className="text-text-tertiary">{artifact.source}</span>
      </div>
      <div className="min-w-0">
        <p className="break-all text-sm text-text-secondary">{artifact.path}</p>
        <p className="mt-1 text-xs text-text-tertiary">
          {artifact.preview ? (isZh ? "可预览结果" : "Preview-ready result") : isZh ? "运行输出产物" : "Run output artifact"}
        </p>
      </div>
      <div className="flex items-center gap-2">
        <span className="rounded-full bg-surface px-2.5 py-1 text-[11px] font-semibold uppercase text-text-secondary">
          {artifact.format || "unknown"}
        </span>
        <button
          type="button"
          className="ui-pressable rounded-lg border border-border bg-surface px-3 py-1.5 text-xs font-medium text-text-secondary transition hover:bg-surface-raised hover:text-text-primary"
          onClick={() => onOpen(artifact.path)}
        >
          {isZh ? "打开" : "Open"}
        </button>
      </div>
    </article>
  );
}

function basename(path: string): string {
  const parts = path.split(/[\\/]/);
  return parts.length > 0 ? parts[parts.length - 1] : path;
}

function inferFormat(path: string, fallback = "unknown"): string {
  const name = basename(path);
  const dotIndex = name.lastIndexOf(".");
  if (dotIndex < 0 || dotIndex === name.length - 1) {
    return fallback;
  }
  return name.slice(dotIndex + 1).toLowerCase();
}

function ChildRunRow({
  child,
  isZh,
  onOpen,
}: {
  child: ChildRunRecord;
  isZh: boolean;
  onOpen: (path: string) => void;
}) {
  const figures = child.final_figures ?? [];
  return (
    <article className="ui-row-item px-6 py-4">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="text-sm font-semibold text-text-primary">{child.pair_id || child.child_id}</p>
          <p className="mt-1 text-xs text-text-tertiary">
            {child.species_a_name} / {child.species_b_name}
          </p>
          {child.outdir ? (
            <p className="mt-1 break-all text-xs text-text-tertiary">{child.outdir}</p>
          ) : null}
        </div>
        <span className={`rounded-full px-3 py-1 text-[11px] font-semibold uppercase ${statusClass(child.status)}`}>
          {child.status}
        </span>
      </div>

      {figures.length > 0 ? (
        <div className="mt-4 divide-y divide-border/90 border-y border-border/90">
          {figures.map((path) => (
            <ResultAssetRow
              key={path}
              label="figure"
              asset={{
                path,
                name: basename(path),
                format: inferFormat(path),
                source: "child_runs",
                preview: true,
              }}
              onOpen={onOpen}
            />
          ))}
        </div>
      ) : (
        <p className="mt-3 text-sm text-text-secondary">{isZh ? "该子运行没有返回图件。" : "This child run produced no figures."}</p>
      )}
    </article>
  );
}

export default function ResultsPage({ route, onNavigate }: ResultsPageProps) {
  const { language } = useLanguage();
  const isZh = language === "zh-CN";
  const [outdir, setOutdir] = useState("");
  const [queryState, setQueryState] = useState<QueryState>("idle");
  const [summary, setSummary] = useState<RunSummaryViewModel | null>(null);
  const [artifacts, setArtifacts] = useState<ArtifactSummary[]>([]);
  const [artifactError, setArtifactError] = useState<string | null>(null);
  const [queryError, setQueryError] = useState<string | null>(null);
  const [openError, setOpenError] = useState<string | null>(null);

  const trimmedOutdir = outdir.trim();

  const loadSummary = useCallback(async () => {
    if (!trimmedOutdir) {
      setSummary(null);
      setArtifacts([]);
      setArtifactError(null);
      setQueryState("idle");
      setQueryError(null);
      return;
    }

    setQueryState("loading");
    setQueryError(null);
    setArtifactError(null);
    try {
      const [nextSummary, nextArtifacts] = await Promise.all([
        readSummaryView({ outdir: trimmedOutdir }),
        listArtifacts({ outdir: trimmedOutdir }).catch((error: unknown) => {
          setArtifactError(formatError(error));
          return [] as ArtifactSummary[];
        }),
      ]);
      setSummary(nextSummary);
      setArtifacts(nextArtifacts);
      setQueryState("ready");
    } catch (error: unknown) {
      setSummary(null);
      setArtifacts([]);
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
    <section className="ui-page-enter grid w-full gap-0 overflow-hidden border border-border bg-surface-raised xl:grid-cols-[17rem_minmax(0,1fr)]">
      <aside className="ui-shell-sidebar border-r">
        <div className="border-b border-border/90 px-5 py-5">
          <p className="text-xs font-medium uppercase tracking-[0.16em] text-text-tertiary">{route.label}</p>
          <h1 className="mt-2 text-lg font-semibold text-text-primary">{isZh ? "运行摘要浏览器" : "Run summary browser"}</h1>
          <p className="mt-2 text-sm leading-6 text-text-secondary">{route.description}</p>
        </div>

        <div className="px-5 py-4">
          <label className="text-xs font-medium uppercase tracking-[0.16em] text-text-tertiary" htmlFor="results-outdir">
            {isZh ? "输出目录" : "Output directory"}
          </label>
          <input
            id="results-outdir"
            type="text"
            value={outdir}
            placeholder={isZh ? "输入分析输出目录" : "Enter an analysis outdir"}
            className="mt-3 w-full rounded-lg border border-border bg-surface-raised px-3 py-2 text-sm text-text-primary outline-none transition placeholder:text-text-tertiary focus:border-ice-400 focus:ring-2 focus:ring-ice-100 dark:focus:ring-ice-900/50"
            onChange={(event) => setOutdir(event.target.value)}
          />
          <div className="mt-3 grid gap-2">
            <button
              type="button"
              className="ui-pressable rounded-lg bg-ice-500 px-3 py-2 text-sm font-semibold text-white transition hover:bg-ice-400 disabled:cursor-not-allowed disabled:opacity-50"
              disabled={queryState === "loading"}
              onClick={() => void loadSummary()}
            >
              {queryState === "loading" ? (isZh ? "加载中..." : "Loading...") : isZh ? "加载摘要" : "Load summary"}
            </button>
            <button
              type="button"
              className="ui-pressable rounded-lg border border-border bg-surface px-3 py-2 text-sm font-medium text-text-secondary transition hover:bg-surface-raised hover:text-text-primary disabled:cursor-not-allowed disabled:opacity-45"
              disabled={!trimmedOutdir}
              onClick={() => void handleOpenPath(trimmedOutdir)}
            >
              {isZh ? "打开输出目录" : "Open output"}
            </button>
            <button
              type="button"
              className="ui-pressable rounded-lg border border-border bg-surface px-3 py-2 text-sm font-medium text-text-secondary transition hover:bg-surface-raised hover:text-text-primary"
              onClick={() => onNavigate("/analysis/new")}
            >
              {isZh ? "返回工作台" : "Back to workbench"}
            </button>
          </div>
        </div>

        <div className="border-t border-border/90 px-5 py-4">
          <div className="text-[11px] font-medium uppercase tracking-[0.16em] text-text-tertiary">{isZh ? "状态" : "State"}</div>
          <div className="mt-3 divide-y divide-border/90 border-y border-border/90">
            <div className="flex items-center justify-between py-3 text-sm">
              <span className="text-text-tertiary">{isZh ? "查询" : "Query"}</span>
              <span className={`rounded-full px-3 py-1 text-[11px] font-semibold uppercase ${statusClass(queryState)}`}>{queryState}</span>
            </div>
            <div className="flex items-center justify-between py-3 text-sm">
              <span className="text-text-tertiary">{isZh ? "图件" : "Figures"}</span>
              <span className="font-medium text-text-primary">{summary?.figureAssets.length ?? 0}</span>
            </div>
            <div className="flex items-center justify-between py-3 text-sm">
              <span className="text-text-tertiary">{isZh ? "产物" : "Artifacts"}</span>
              <span className="font-medium text-text-primary">{artifacts.length || summary?.artifactIndex.length || 0}</span>
            </div>
          </div>
        </div>
      </aside>

      <div className="ui-surface-enter min-w-0 bg-surface-raised">
        <div className="border-b border-border/90 px-6 py-5">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-xs font-medium uppercase tracking-[0.16em] text-text-tertiary">{isZh ? "结果" : "Results"}</p>
              <h2 className="mt-1 text-lg font-semibold text-text-primary">{isZh ? "状态、图件与产物" : "Status, figures, and artifacts"}</h2>
              <p className="mt-2 text-sm leading-6 text-text-secondary">
                {isZh
                  ? "查看所选输出目录的运行摘要与轻量 artifact 索引。"
                  : "Inspect the run summary and the lightweight artifact index generated for the selected output directory."}
              </p>
            </div>
            <span className={`rounded-full px-3 py-1 text-[11px] font-semibold uppercase ${statusClass(summary?.status ?? queryState)}`}>
              {summary?.status ?? queryState}
            </span>
          </div>
        </div>

        {queryError ? <div className="border-b border-border/90 bg-rose-50 px-6 py-4 text-sm text-rose-700 dark:bg-rose-950/30 dark:text-rose-200">{queryError}</div> : null}
        {artifactError ? (
          <div className="border-b border-border/90 bg-amber-50 px-6 py-4 text-sm text-amber-700 dark:bg-amber-950/30 dark:text-amber-200">
            {isZh ? "产物列表暂不可用: " : "Artifact listing is unavailable: "} {artifactError}
          </div>
        ) : null}
        {openError ? <div className="border-b border-border/90 bg-rose-50 px-6 py-4 text-sm text-rose-700 dark:bg-rose-950/30 dark:text-rose-200">{openError}</div> : null}

        {!trimmedOutdir && queryState === "idle" ? (
          <div className="border-b border-border/90 px-6 py-10 text-sm text-text-secondary">
            {isZh ? "输入输出目录后即可查看运行摘要与结果文件。" : "Enter an output directory to inspect a run summary and its result files."}
          </div>
        ) : null}

        {summary ? (
          <>
            <section>
              <div className="px-6 py-4">
                <h3 className="text-sm font-semibold text-text-primary">{isZh ? "概览" : "Overview"}</h3>
              </div>
              <div className="divide-y divide-border/90 border-y border-border/90">
                <div className="grid grid-cols-[12rem_minmax(0,1fr)] gap-4 px-6 py-4 text-sm">
                  <span className="text-text-tertiary">{isZh ? "工作流" : "Workflow"}</span>
                  <span className="font-medium text-text-primary">{summary.workflow}</span>
                </div>
                <div className="grid grid-cols-[12rem_minmax(0,1fr)] gap-4 px-6 py-4 text-sm">
                  <span className="text-text-tertiary">{isZh ? "进度" : "Progress"}</span>
                  <span className="font-medium text-text-primary">{summary.progress}%</span>
                </div>
                <div className="grid grid-cols-[12rem_minmax(0,1fr)] gap-4 px-6 py-4 text-sm">
                  <span className="text-text-tertiary">{isZh ? "摘要路径" : "Summary path"}</span>
                  <button
                    type="button"
                    className="ui-pressable truncate text-left font-medium text-ice-700 transition hover:text-ice-900 dark:text-ice-300 dark:hover:text-ice-100"
                    onClick={() => void handleOpenPath(summary.runSummaryPath)}
                  >
                    {summary.runSummaryPath || (isZh ? "不可用" : "Unavailable")}
                  </button>
                </div>
                <div className="grid grid-cols-[12rem_minmax(0,1fr)] gap-4 px-6 py-4 text-sm">
                  <span className="text-text-tertiary">{isZh ? "运行日志" : "Run log"}</span>
                  <button
                    type="button"
                    className="ui-pressable truncate text-left font-medium text-ice-700 transition hover:text-ice-900 dark:text-ice-300 dark:hover:text-ice-100"
                    onClick={() => void handleOpenPath(summary.runLogPath)}
                  >
                    {summary.runLogPath || (isZh ? "不可用" : "Unavailable")}
                  </button>
                </div>
                <div className="grid grid-cols-[12rem_minmax(0,1fr)] gap-4 px-6 py-4 text-sm">
                  <span className="text-text-tertiary">{isZh ? "子运行" : "Child runs"}</span>
                  <span className="font-medium text-text-primary">{summary.childRunCount}</span>
                </div>
                <div className="grid grid-cols-[12rem_minmax(0,1fr)] gap-4 px-6 py-4 text-sm">
                  <span className="text-text-tertiary">{isZh ? "扩展字段" : "Extensions"}</span>
                  <span className="font-medium text-text-primary">{Object.keys(summary.extensions).length}</span>
                </div>
              </div>
            </section>

            <section>
              <div className="px-6 py-4">
                <h3 className="text-sm font-semibold text-text-primary">{isZh ? "主要图件" : "Primary figures"}</h3>
                <p className="mt-1 text-sm text-text-secondary">
                  {isZh ? "图件快捷入口来自 run summary 里的 primary figure 集合。" : "Figure shortcuts come from the run summary primary figure set."}
                </p>
              </div>

              {primaryAssets.length > 0 ? (
                <div className="divide-y divide-border/90 border-y border-border/90">
                  {primaryAssets.map((asset) => (
                    <ResultAssetRow key={asset.path} label={asset.source} asset={asset} onOpen={(path) => void handleOpenPath(path)} />
                  ))}
                </div>
              ) : (
                <div className="border-y border-border/90 px-6 py-8 text-sm text-text-secondary">
                  {isZh ? "当前摘要没有标记主要图件。" : "No primary figures were advertised in the summary."}
                </div>
              )}
            </section>

            {summary.childRuns.length > 0 ? (
              <section>
                <div className="px-6 py-4">
                  <h3 className="text-sm font-semibold text-text-primary">{isZh ? "子运行图件" : "Child run figures"}</h3>
                  <p className="mt-1 text-sm text-text-secondary">
                    {isZh
                      ? "每个子运行对应一对物种，下方列出其生成的图件。"
                      : "Each child run corresponds to a species pair; its generated figures are listed below."}
                  </p>
                </div>
                <div className="divide-y divide-border/90 border-y border-border/90">
                  {summary.childRuns.map((child) => (
                    <ChildRunRow key={child.child_id} child={child} isZh={isZh} onOpen={handleOpenPath} />
                  ))}
                </div>
              </section>
            ) : null}

            {Object.keys(summary.extensions).length > 0 ? (
              <section>
                <div className="px-6 py-4">
                  <h3 className="text-sm font-semibold text-text-primary">{isZh ? "扩展信息" : "Extensions"}</h3>
                  <p className="mt-1 text-sm text-text-secondary">
                    {isZh
                      ? "后端在摘要中附加的扩展字段，可展开查看原始内容。"
                      : "Extension fields attached by the backend summary; expand to inspect raw values."}
                  </p>
                </div>
                <div className="border-y border-border/90 px-6 py-4">
                  <details className="group">
                    <summary className="cursor-pointer text-sm font-medium text-text-secondary transition hover:text-text-primary">
                      {isZh ? "查看原始扩展字段" : "View raw extension fields"}
                    </summary>
                    <pre className="mt-3 max-h-96 overflow-auto rounded-lg border border-border bg-surface p-4 text-xs text-text-secondary">
                      {JSON.stringify(summary.extensions, null, 2)}
                    </pre>
                  </details>
                </div>
              </section>
            ) : null}

            <section>
              <div className="px-6 py-4">
                <h3 className="text-sm font-semibold text-text-primary">{isZh ? "产物" : "Artifacts"}</h3>
                <p className="mt-1 text-sm text-text-secondary">
                  {isZh ? "优先展示 GUI artifact 命令返回的行；若命令未返回，再回退到 summary 里的 artifact 记录。" : "Artifact rows come from the GUI artifact command, with summary records as fallback context."}
                </p>
              </div>

              {artifacts.length > 0 ? (
                <div className="divide-y divide-border/90 border-y border-border/90">
                  {artifacts.map((artifact) => (
                    <ArtifactSummaryRow key={`${artifact.source}-${artifact.path}`} artifact={artifact} onOpen={(path) => void handleOpenPath(path)} />
                  ))}
                </div>
              ) : summary.artifactIndex.length > 0 ? (
                <div className="divide-y divide-border/90 border-y border-border/90">
                  {summary.artifactIndex.map((artifact) => (
                    <ArtifactRow key={`${artifact.artifact_id}-${artifact.path}`} artifact={artifact} onOpen={(path) => void handleOpenPath(path)} />
                  ))}
                </div>
              ) : (
                <div className="border-y border-border/90 px-6 py-8 text-sm text-text-secondary">
                  {isZh ? "当前摘要没有返回任何 artifact 记录。" : "No artifact records were returned in the current summary."}
                </div>
              )}
            </section>
          </>
        ) : null}
      </div>
    </section>
  );
}
