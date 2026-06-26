import {
  AlertCircle,
  Box,
  ChevronRight,
  FileText,
  FolderOpen,
  Image,
  Layers,
  RefreshCw,
} from "lucide-react";
import { useCallback, useMemo, useState } from "react";

import { Badge, Card, EmptyState, SectionHeader, StatCard } from "../components/ui";
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

function statusTone(state: QueryState | RunSummaryViewModel["status"]): NonNullable<React.ComponentProps<typeof Badge>["tone"]> {
  if (state === "SUCCEEDED" || state === "ready") {
    return "success";
  }
  if (state === "FAILED" || state === "error") {
    return "error";
  }
  if (state === "loading" || state === "RUNNING" || state === "PENDING") {
    return "warning";
  }
  return "default";
}

function statusLabel(state: QueryState | RunSummaryViewModel["status"], isZh: boolean): string {
  if (!isZh) {
    return String(state);
  }
  switch (state) {
    case "ready":
      return "就绪";
    case "loading":
      return "加载中";
    case "error":
      return "错误";
    case "SUCCEEDED":
      return "成功";
    case "FAILED":
      return "失败";
    case "RUNNING":
      return "运行中";
    case "PENDING":
      return "等待中";
    default:
      return String(state);
  }
}

function ResultAssetRow({
  asset,
  onOpen,
}: {
  asset: FigureAsset;
  onOpen: (path: string) => void;
}) {
  const { language } = useLanguage();
  const isZh = language === "zh-CN";
  return (
    <article className="ui-row-item flex items-center justify-between gap-4 rounded-xl border border-border bg-surface p-4">
      <div className="flex min-w-0 items-center gap-3">
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-ice-50 text-ice-600 dark:bg-ice-900/30 dark:text-ice-200"
        >
          <Image className="h-4 w-4" />
        </span>
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-text-primary">{asset.name}</p>
          <p className="mt-1 break-all text-xs text-text-tertiary">{asset.path}</p>
        </div>
      </div>
      <div className="flex shrink-0 items-center gap-2">
        <Badge tone="default">{asset.format}</Badge>
        <button
          type="button"
          className="ui-pressable inline-flex items-center gap-1 rounded-xl border border-border bg-surface px-3 py-1.5 text-xs font-medium text-text-secondary transition hover:bg-surface-raised hover:text-text-primary"
          onClick={() => onOpen(asset.path)}
        >
          <FolderOpen className="h-3.5 w-3.5" />
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
    <article className="ui-row-item flex items-center justify-between gap-4 rounded-xl border border-border bg-surface p-4">
      <div className="flex min-w-0 items-center gap-3">
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-surface text-text-tertiary"
        >
          <Box className="h-4 w-4" />
        </span>
        <div className="min-w-0">
          <p className="text-sm font-semibold text-text-primary">
            <span className="mr-2 text-text-tertiary">#{artifact.artifact_id}</span>
            {artifact.artifact_type}
          </p>
          <p className="mt-1 break-all text-xs text-text-tertiary">{artifact.path}</p>
          <p className="mt-1 text-[11px] text-text-secondary">{artifact.produced_by}</p>
        </div>
      </div>
      <div className="flex shrink-0 items-center gap-2">
        <Badge tone="default">{artifact.format ?? "unknown"}</Badge>
        <button
          type="button"
          className="ui-pressable inline-flex items-center gap-1 rounded-xl border border-border bg-surface px-3 py-1.5 text-xs font-medium text-text-secondary transition hover:bg-surface-raised hover:text-text-primary"
          onClick={() => onOpen(artifact.path)}
        >
          <FolderOpen className="h-3.5 w-3.5" />
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
    <article className="ui-row-item flex items-center justify-between gap-4 rounded-xl border border-border bg-surface p-4">
      <div className="flex min-w-0 items-center gap-3">
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-surface text-text-tertiary"
        >
          <Box className="h-4 w-4" />
        </span>
        <div className="min-w-0">
          <p className="text-sm font-semibold text-text-primary">
            <span className="mr-2 rounded-md bg-surface px-1.5 py-0.5 text-[10px] text-text-tertiary">{artifact.source}</span>
            {artifact.name}
          </p>
          <p className="mt-1 break-all text-xs text-text-tertiary">{artifact.path}</p>
        </div>
      </div>
      <div className="flex shrink-0 items-center gap-2">
        <Badge tone="default">{artifact.format || "unknown"}</Badge>
        <button
          type="button"
          className="ui-pressable inline-flex items-center gap-1 rounded-xl border border-border bg-surface px-3 py-1.5 text-xs font-medium text-text-secondary transition hover:bg-surface-raised hover:text-text-primary"
          onClick={() => onOpen(artifact.path)}
        >
          <FolderOpen className="h-3.5 w-3.5" />
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
    <Card className="overflow-hidden p-0">
      <div className="flex items-start justify-between gap-4 border-b border-border/90 bg-surface p-4">
        <div className="min-w-0">
          <p className="text-sm font-semibold text-text-primary">{child.pair_id || child.child_id}</p>
          <p className="mt-1 text-xs text-text-tertiary">
            {child.species_a_name} / {child.species_b_name}
          </p>
          {child.outdir ? <p className="mt-1 break-all text-[11px] text-text-tertiary">{child.outdir}</p> : null}
        </div>
        <Badge tone={statusTone(child.status)}>{statusLabel(child.status, isZh)}</Badge>
      </div>

      <div className="p-4">
        {figures.length > 0 ? (
          <div className="grid gap-3">
            {figures.map((path) => (
              <ResultAssetRow
                key={path}
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
          <EmptyState
            icon={Image}
            title={isZh ? "无图件" : "No figures"}
            description={isZh ? "该子运行没有返回图件。" : "This child run produced no figures."}
          />
        )}
      </div>
    </Card>
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

  const figureCount = summary?.figureAssets.length ?? 0;
  const artifactCount = artifacts.length || summary?.artifactIndex.length || 0;

  return (
    <section className="ui-page-enter grid h-screen w-full gap-0 overflow-hidden border border-border bg-surface-raised xl:grid-cols-[18rem_minmax(0,1fr)]">
      <aside className="ui-shell-sidebar flex min-h-0 flex-col border-r px-4 py-4">
        <div className="border-b border-border/90 px-2 pb-4">
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-text-tertiary">{route.label}</p>
          <h1 className="mt-2 text-lg font-semibold text-text-primary">{isZh ? "运行摘要浏览器" : "Run summary browser"}</h1>
          <p className="mt-2 text-sm leading-6 text-text-secondary">{route.description}</p>
        </div>

        <div className="mt-4 px-2">
          <label className="text-xs font-semibold uppercase tracking-[0.14em] text-text-tertiary" htmlFor="results-outdir">
            {isZh ? "输出目录" : "Output directory"}
          </label>
          <input
            id="results-outdir"
            type="text"
            value={outdir}
            placeholder={isZh ? "输入分析输出目录" : "Enter an analysis outdir"}
            className="mt-2 w-full rounded-xl border border-border bg-surface-raised px-3 py-2 text-sm text-text-primary outline-none transition placeholder:text-text-tertiary focus:border-ice-400 focus:ring-2 focus:ring-ice-100 dark:focus:ring-ice-900/50"
            onChange={(event) => setOutdir(event.target.value)}
          />
          <div className="mt-3 grid gap-2">
            <button
              type="button"
              className="ui-pressable inline-flex items-center justify-center gap-2 rounded-xl bg-ice-500 px-3 py-2 text-sm font-semibold text-white transition hover:bg-ice-400 disabled:cursor-not-allowed disabled:opacity-50"
              disabled={queryState === "loading"}
              onClick={() => void loadSummary()}
            >
              <RefreshCw className={`h-4 w-4 ${queryState === "loading" ? "animate-spin" : ""}`} />
              {queryState === "loading" ? (isZh ? "加载中..." : "Loading...") : isZh ? "加载摘要" : "Load summary"}
            </button>
            <button
              type="button"
              className="ui-pressable inline-flex items-center justify-center gap-2 rounded-xl border border-border bg-surface px-3 py-2 text-sm font-medium text-text-secondary transition hover:bg-surface-raised hover:text-text-primary disabled:cursor-not-allowed disabled:opacity-45"
              disabled={!trimmedOutdir}
              onClick={() => void handleOpenPath(trimmedOutdir)}
            >
              <FolderOpen className="h-4 w-4" />
              {isZh ? "打开输出目录" : "Open output"}
            </button>
            <button
              type="button"
              className="ui-pressable inline-flex items-center justify-center gap-2 rounded-xl border border-border bg-surface px-3 py-2 text-sm font-medium text-text-secondary transition hover:bg-surface-raised hover:text-text-primary"
              onClick={() => onNavigate("/analysis/new")}
            >
              <ChevronRight className="h-4 w-4" />
              {isZh ? "返回工作台" : "Back to workbench"}
            </button>
          </div>
        </div>

        <div className="mt-auto border-t border-border/90 px-2 pt-4">
          <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-text-tertiary">{isZh ? "概览" : "Overview"}</p>
          <div className="mt-3 grid gap-3">
            <StatCard label={isZh ? "查询" : "Query"} value={statusLabel(queryState, isZh)} tone={statusTone(queryState)} icon={RefreshCw} />
            <StatCard label={isZh ? "图件" : "Figures"} value={figureCount} tone="info" icon={Image} />
            <StatCard label={isZh ? "产物" : "Artifacts"} value={artifactCount} tone="default" icon={Box} />
          </div>
        </div>
      </aside>

      <div className="ui-surface-enter min-w-0 overflow-auto bg-surface-raised px-6 py-6">
        <div className="mx-auto max-w-5xl">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-text-tertiary">{isZh ? "结果" : "Results"}</p>
              <h2 className="mt-1 text-2xl font-semibold tracking-tight text-text-primary">{isZh ? "状态、图件与产物" : "Status, figures, and artifacts"}</h2>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-text-secondary">
                {isZh
                  ? "查看所选输出目录的运行摘要与轻量 artifact 索引。"
                  : "Inspect the run summary and the lightweight artifact index generated for the selected output directory."}
              </p>
            </div>
            <Badge tone={statusTone(summary?.status ?? queryState)} dot pulse={(summary?.status ?? queryState) === "RUNNING"}>
              {statusLabel(summary?.status ?? queryState, isZh)}
            </Badge>
          </div>

          {queryError ? (
            <div className="mt-5 flex items-start gap-3 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700 dark:border-rose-900/40 dark:bg-rose-950/20 dark:text-rose-200"
            >
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
              {queryError}
            </div>
          ) : null}
          {artifactError ? (
            <div className="mt-5 flex items-start gap-3 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-700 dark:border-amber-900/40 dark:bg-amber-950/20 dark:text-amber-200"
            >
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
              {isZh ? "产物列表暂不可用: " : "Artifact listing is unavailable: "} {artifactError}
            </div>
          ) : null}
          {openError ? (
            <div className="mt-5 flex items-start gap-3 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700 dark:border-rose-900/40 dark:bg-rose-950/20 dark:text-rose-200"
            >
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
              {openError}
            </div>
          ) : null}

          {!trimmedOutdir && queryState === "idle" ? (
            <div className="mt-6">
              <EmptyState
                icon={FolderOpen}
                title={isZh ? "输入输出目录" : "Enter an output directory"}
                description={isZh ? "输入输出目录后即可查看运行摘要与结果文件。" : "Enter an output directory to inspect a run summary and its result files."}
              />
            </div>
          ) : null}

          {summary ? (
            <div className="mt-6 grid gap-6">
              <Card>
                <SectionHeader title={isZh ? "概览" : "Overview"} />
                <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                  <div className="rounded-xl border border-border bg-bg p-4">
                    <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-text-tertiary">{isZh ? "工作流" : "Workflow"}</p>
                    <p className="mt-1 truncate text-lg font-semibold text-text-primary">{summary.workflow}</p>
                  </div>
                  <div className="rounded-xl border border-border bg-bg p-4">
                    <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-text-tertiary">{isZh ? "进度" : "Progress"}</p>
                    <p className="mt-1 text-lg font-semibold text-text-primary">{summary.progress}%</p>
                  </div>
                  <div className="rounded-xl border border-border bg-bg p-4">
                    <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-text-tertiary">{isZh ? "子运行" : "Child runs"}</p>
                    <p className="mt-1 text-lg font-semibold text-text-primary">{summary.childRunCount}</p>
                  </div>
                  <div className="rounded-xl border border-border bg-bg p-4">
                    <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-text-tertiary">{isZh ? "扩展字段" : "Extensions"}</p>
                    <p className="mt-1 text-lg font-semibold text-text-primary">{Object.keys(summary.extensions).length}</p>
                  </div>
                  <button
                    type="button"
                    className="ui-row-item flex items-center justify-between rounded-xl border border-border bg-bg p-4 text-left sm:col-span-2"
                    onClick={() => void handleOpenPath(summary.runSummaryPath)}
                  >
                    <div className="min-w-0">
                      <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-text-tertiary">{isZh ? "摘要路径" : "Summary path"}</p>
                      <p className="mt-1 truncate text-sm font-medium text-text-primary">{summary.runSummaryPath || (isZh ? "不可用" : "Unavailable")}</p>
                    </div>
                    <FileText className="h-4 w-4 shrink-0 text-text-tertiary" />
                  </button>
                  <button
                    type="button"
                    className="ui-row-item flex items-center justify-between rounded-xl border border-border bg-bg p-4 text-left sm:col-span-2 lg:col-span-1"
                    onClick={() => void handleOpenPath(summary.runLogPath)}
                  >
                    <div className="min-w-0">
                      <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-text-tertiary">{isZh ? "运行日志" : "Run log"}</p>
                      <p className="mt-1 truncate text-sm font-medium text-text-primary">{summary.runLogPath || (isZh ? "不可用" : "Unavailable")}</p>
                    </div>
                    <FileText className="h-4 w-4 shrink-0 text-text-tertiary" />
                  </button>
                </div>
              </Card>

              <Card>
                <SectionHeader
                  title={isZh ? "主要图件" : "Primary figures"}
                  subtitle={isZh ? "来自 run summary primary figure 集合的快捷入口。" : "Shortcuts from the run summary primary figure set."}
                  action={
                    <Badge tone="default">{primaryAssets.length}</Badge>
                  }
                />
                <div className="mt-4 grid gap-3">
                  {primaryAssets.length > 0 ? (
                    primaryAssets.map((asset) => (
                      <ResultAssetRow key={asset.path} asset={asset} onOpen={(path) => void handleOpenPath(path)} />
                    ))
                  ) : (
                    <EmptyState
                      icon={Image}
                      title={isZh ? "没有主要图件" : "No primary figures"}
                      description={isZh ? "当前摘要没有标记主要图件。" : "No primary figures were advertised in the summary."}
                    />
                  )}
                </div>
              </Card>

              {summary.childRuns.length > 0 ? (
                <Card>
                  <SectionHeader
                    title={isZh ? "子运行图件" : "Child run figures"}
                    subtitle={isZh ? "每个子运行对应一对物种。" : "Each child run corresponds to a species pair."}
                    action={
                      <Badge tone="default">{summary.childRuns.length}</Badge>
                    }
                  />
                  <div className="mt-4 grid gap-4">
                    {summary.childRuns.map((child) => (
                      <ChildRunRow key={child.child_id} child={child} isZh={isZh} onOpen={handleOpenPath} />
                    ))}
                  </div>
                </Card>
              ) : null}

              {Object.keys(summary.extensions).length > 0 ? (
                <Card>
                  <SectionHeader
                    title={isZh ? "扩展信息" : "Extensions"}
                    subtitle={isZh ? "后端在摘要中附加的扩展字段。" : "Extension fields attached by the backend summary."}
                    action={
                      <Badge tone="default">{Object.keys(summary.extensions).length}</Badge>
                    }
                  />
                  <div className="mt-4">
                    <details className="group">
                      <summary className="ui-pressable inline-flex cursor-pointer items-center gap-2 rounded-xl border border-border bg-surface px-3 py-2 text-sm font-medium text-text-secondary transition hover:bg-surface-raised hover:text-text-primary"
                      >
                        <Layers className="h-4 w-4" />
                        {isZh ? "查看原始扩展字段" : "View raw extension fields"}
                      </summary>
                      <pre className="ui-terminal mt-3 max-h-96 overflow-auto p-4 text-xs">
                        {JSON.stringify(summary.extensions, null, 2)}
                      </pre>
                    </details>
                  </div>
                </Card>
              ) : null}

              <Card>
                <SectionHeader
                  title={isZh ? "产物" : "Artifacts"}
                  subtitle={isZh ? "优先展示 GUI artifact 命令返回的行。" : "Artifact rows come from the GUI artifact command."}
                  action={
                    <Badge tone="default">{artifacts.length > 0 ? artifacts.length : summary.artifactIndex.length}</Badge>
                  }
                />
                <div className="mt-4 grid gap-3">
                  {artifacts.length > 0 ? (
                    artifacts.map((artifact) => (
                      <ArtifactSummaryRow key={`${artifact.source}-${artifact.path}`} artifact={artifact} onOpen={(path) => void handleOpenPath(path)} />
                    ))
                  ) : summary.artifactIndex.length > 0 ? (
                    summary.artifactIndex.map((artifact) => (
                      <ArtifactRow key={`${artifact.artifact_id}-${artifact.path}`} artifact={artifact} onOpen={(path) => void handleOpenPath(path)} />
                    ))
                  ) : (
                    <EmptyState
                      icon={Box}
                      title={isZh ? "暂无产物" : "No artifacts"}
                      description={isZh ? "当前摘要没有返回任何 artifact 记录。" : "No artifact records were returned in the current summary."}
                    />
                  )}
                </div>
              </Card>
            </div>
          ) : null}
        </div>
      </div>
    </section>
  );
}
