import {
  AlertCircle,
  Clock,
  FolderOpen,
  Layers,
  Plus,
  RefreshCw,
  Rocket,
  Search,
} from "lucide-react";
import { useCallback, useMemo, useState } from "react";

import { Badge, Card, EmptyState, SectionHeader, StatCard } from "../components/ui";
import { useLanguage } from "../i18n/useLanguage";
import type { ProjectSummary } from "../models";
import type { AppRoute } from "../routes/routes";
import { createProject, listProjects } from "../services/workbench";

interface ProjectsPageProps {
  route: AppRoute;
  onNavigate: (path: string) => void;
}

type QueryState = "idle" | "loading" | "ready" | "error";

function formatError(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

function formatTimestamp(value?: string, isZh = false): string {
  if (!value) {
    return isZh ? "不可用" : "Unavailable";
  }

  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString();
}

function dedupeProjects(projects: ProjectSummary[]): ProjectSummary[] {
  const seen = new Set<string>();
  return projects.filter((project) => {
    const key = project.path || project.name;
    if (seen.has(key)) {
      return false;
    }
    seen.add(key);
    return true;
  });
}

function stateTone(state: QueryState): NonNullable<React.ComponentProps<typeof Badge>["tone"]> {
  switch (state) {
    case "ready":
      return "success";
    case "error":
      return "error";
    case "loading":
      return "warning";
    default:
      return "default";
  }
}

function ProjectCard({
  project,
  isZh,
}: {
  project: ProjectSummary;
  isZh: boolean;
}) {
  return (
    <Card className="group relative overflow-hidden p-0">
      <div className="flex items-start gap-4 p-5">
        <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-ice-50 text-ice-600 transition group-hover:scale-105 dark:bg-ice-900/30 dark:text-ice-200"
        >
          <Layers className="h-5 w-5" />
        </span>
        <div className="min-w-0 flex-1">
          <p className="truncate text-base font-semibold text-text-primary">{project.name}</p>
          <p className="mt-1 break-all text-xs leading-5 text-text-tertiary">{project.path}</p>
          <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
            <div className="rounded-lg border border-border bg-surface p-2">
              <p className="text-text-tertiary">{isZh ? "更新" : "Updated"}</p>
              <p className="mt-0.5 font-medium text-text-primary">{formatTimestamp(project.updatedAt, isZh)}</p>
            </div>
            <div className="rounded-lg border border-border bg-surface p-2">
              <p className="text-text-tertiary">{isZh ? "创建" : "Created"}</p>
              <p className="mt-0.5 font-medium text-text-primary">{formatTimestamp(project.createdAt, isZh)}</p>
            </div>          </div>
        </div>
      </div>
      <div className="border-t border-border/90 bg-surface px-5 py-3">
        <div className="flex items-center justify-between gap-3 text-xs">
          <div className="min-w-0">
            <p className="truncate text-text-tertiary">
              {isZh ? "配置" : "Config"}: {project.configPath ?? (isZh ? "不可用" : "Unavailable")}
            </p>
            <p className="mt-0.5 truncate text-text-tertiary">
              JCVI: {project.jcviConfigPath ?? (isZh ? "不可用" : "Unavailable")}
            </p>
          </div>
          <div className="shrink-0 text-right">
            <p className="text-text-tertiary">{isZh ? "上次运行" : "Last run"}</p>
            <p className="mt-0.5 font-medium text-text-primary">{formatTimestamp(project.lastRunAt, isZh)}</p>
          </div>
        </div>
      </div>
    </Card>
  );
}

export default function ProjectsPage({ route, onNavigate }: ProjectsPageProps) {
  const { language } = useLanguage();
  const isZh = language === "zh-CN";
  const [workspace, setWorkspace] = useState("");
  const [projectName, setProjectName] = useState("");
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [queryState, setQueryState] = useState<QueryState>("idle");
  const [queryError, setQueryError] = useState<string | null>(null);
  const [createState, setCreateState] = useState<QueryState>("idle");
  const [createError, setCreateError] = useState<string | null>(null);

  const trimmedWorkspace = workspace.trim();
  const trimmedProjectName = projectName.trim();

  const refreshProjects = useCallback(async () => {
    if (!trimmedWorkspace) {
      setProjects([]);
      setQueryError(null);
      setQueryState("idle");
      return;
    }

    setQueryState("loading");
    setQueryError(null);
    try {
      const nextProjects = await listProjects({ workspace: trimmedWorkspace });
      setProjects(dedupeProjects(nextProjects));
      setCreateError(null);
      setQueryState("ready");
    } catch (error: unknown) {
      setProjects([]);
      setQueryError(formatError(error));
      setQueryState("error");
    }
  }, [trimmedWorkspace]);

  const handleCreateProject = useCallback(async () => {
    if (!trimmedWorkspace || !trimmedProjectName) {
      return;
    }

    setCreateState("loading");
    setCreateError(null);
    try {
      const createdProject = await createProject({
        workspace: trimmedWorkspace,
        name: trimmedProjectName,
      });
      setProjects((current) => dedupeProjects([createdProject, ...current]));
      setProjectName("");
      setQueryError(null);
      setCreateState("ready");
      setQueryState("ready");
    } catch (error: unknown) {
      setCreateError(formatError(error));
      setCreateState("error");
    }
  }, [trimmedProjectName, trimmedWorkspace]);

  const helperText = useMemo(() => {
    if (!trimmedWorkspace) {
      return isZh ? "输入工作区路径后即可加载或创建项目。" : "Enter a workspace path to load or create projects.";
    }
    if (queryState === "loading") {
      return isZh ? "正在从所选工作区读取项目。" : "Loading projects from the selected workspace.";
    }
    if (queryState === "error") {
      return isZh ? "读取项目时发生错误，请检查 workspace 路径和后端命令状态。" : "The backend project command returned an error. Check the workspace path and backend state.";
    }
    if (projects.length === 0) {
      return isZh ? "当前工作区里还没有发现项目元数据。" : "No project metadata found yet in this workspace.";
    }
    return isZh ? `当前工作区已加载 ${projects.length} 个项目。` : `${projects.length} project${projects.length === 1 ? "" : "s"} loaded from the current workspace.`;
  }, [isZh, projects.length, queryState, trimmedWorkspace]);

  return (
    <section className="ui-page-enter grid h-screen w-full gap-0 overflow-hidden border border-border bg-surface-raised xl:grid-cols-[18rem_minmax(0,1fr)]">
      <aside className="ui-shell-sidebar flex min-h-0 flex-col border-r px-4 py-4">
        <div className="border-b border-border/90 px-2 pb-4">
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-text-tertiary">{route.label}</p>
          <h1 className="mt-2 text-lg font-semibold text-text-primary">{isZh ? "工作区项目" : "Workspace projects"}</h1>
          <p className="mt-2 text-sm leading-6 text-text-secondary">{route.description}</p>
        </div>

        <div className="mt-4 px-2">
          <label className="text-xs font-semibold uppercase tracking-[0.14em] text-text-tertiary" htmlFor="projects-workspace">
            {isZh ? "工作区路径" : "Workspace path"}
          </label>
          <div className="relative mt-2">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-tertiary" />
            <input
              id="projects-workspace"
              type="text"
              value={workspace}
              placeholder={isZh ? "输入工作区目录" : "Enter a workspace directory"}
              className="w-full rounded-xl border border-border bg-surface-raised py-2 pl-9 pr-3 text-sm text-text-primary outline-none transition placeholder:text-text-tertiary focus:border-ice-400 focus:ring-2 focus:ring-ice-100 dark:focus:ring-ice-900/50"
              onChange={(event) => setWorkspace(event.target.value)}
            />
          </div>
          <div className="mt-3 grid gap-2">
            <button
              type="button"
              className="ui-pressable inline-flex items-center justify-center gap-2 rounded-xl bg-ice-500 px-3 py-2 text-sm font-semibold text-white transition hover:bg-ice-400 disabled:cursor-not-allowed disabled:opacity-50"
              disabled={queryState === "loading"}
              onClick={() => void refreshProjects()}
            >
              <RefreshCw className={`h-4 w-4 ${queryState === "loading" ? "animate-spin" : ""}`} />
              {queryState === "loading" ? (isZh ? "刷新中..." : "Refreshing...") : isZh ? "刷新项目" : "Refresh projects"}
            </button>
            <button
              type="button"
              className="ui-pressable inline-flex items-center justify-center gap-2 rounded-xl border border-border bg-surface px-3 py-2 text-sm font-medium text-text-secondary transition hover:bg-surface-raised hover:text-text-primary"
              onClick={() => onNavigate("/analysis/new")}
            >
              <Rocket className="h-4 w-4" />
              {isZh ? "打开工作台" : "Open workbench"}
            </button>
          </div>
        </div>

        <div className="mt-auto border-t border-border/90 px-2 pt-4">
          <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-text-tertiary">{isZh ? "概览" : "Overview"}</p>
          <div className="mt-3 grid gap-3">
            <StatCard label={isZh ? "查询" : "Query"} value={queryState} tone={stateTone(queryState)} icon={RefreshCw} />
            <StatCard label={isZh ? "项目" : "Projects"} value={projects.length} tone="info" icon={Layers} />
            <StatCard label={isZh ? "工作区" : "Workspace"} value={trimmedWorkspace ? basename(trimmedWorkspace) : (isZh ? "未设置" : "Not set")} tone="default" icon={FolderOpen} />
          </div>
        </div>
      </aside>

      <div className="ui-surface-enter min-h-0 overflow-auto bg-surface-raised px-6 py-6">
        <div className="mx-auto max-w-5xl">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-text-tertiary">{isZh ? "项目" : "Projects"}</p>
              <h2 className="mt-1 text-2xl font-semibold tracking-tight text-text-primary">{isZh ? "项目列表与创建" : "Project list and creation"}</h2>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-text-secondary">{helperText}</p>
            </div>
            <Badge tone={stateTone(queryState)} dot pulse={queryState === "loading"}>
              {queryState === "loading" ? (isZh ? "加载中" : "Loading") : queryState === "ready" ? (isZh ? "就绪" : "Ready") : isZh ? "等待" : "Idle"}
            </Badge>
          </div>

          {queryError ? (
            <div className="mt-5 flex items-start gap-3 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700 dark:border-rose-900/40 dark:bg-rose-950/20 dark:text-rose-200"
            >
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
              {queryError}
            </div>
          ) : null}
          {createError ? (
            <div className="mt-5 flex items-start gap-3 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700 dark:border-rose-900/40 dark:bg-rose-950/20 dark:text-rose-200"
            >
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
              {createError}
            </div>
          ) : null}

          <Card className="mt-6">
            <SectionHeader title={isZh ? "创建项目" : "Create project"} subtitle={isZh ? "使用当前工作区路径和项目名称创建新的元数据。" : "Use the current workspace path and a project name to create new metadata."} />
            <div className="mt-4 grid gap-3 lg:grid-cols-[minmax(0,1fr)_auto]">
              <div className="relative">
                <Plus className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-tertiary" />
                <input
                  type="text"
                  value={projectName}
                  placeholder={isZh ? "输入项目名称" : "Enter a project name"}
                  className="w-full rounded-xl border border-border bg-surface-raised py-2 pl-9 pr-3 text-sm text-text-primary outline-none transition placeholder:text-text-tertiary focus:border-ice-400 focus:ring-2 focus:ring-ice-100 dark:focus:ring-ice-900/50"
                  onChange={(event) => setProjectName(event.target.value)}
                />
              </div>
              <button
                type="button"
                className="ui-pressable inline-flex items-center justify-center gap-2 rounded-xl bg-ice-500 px-4 py-2 text-sm font-semibold text-white transition hover:bg-ice-400 disabled:cursor-not-allowed disabled:opacity-45"
                disabled={!trimmedWorkspace || !trimmedProjectName || createState === "loading"}
                onClick={() => void handleCreateProject()}
              >
                <Plus className="h-4 w-4" />
                {createState === "loading" ? (isZh ? "创建中..." : "Creating...") : isZh ? "创建项目" : "Create project"}
              </button>
            </div>
          </Card>

          <Card className="mt-6">
            <SectionHeader
              title={isZh ? "可用项目" : "Available projects"}
              subtitle={isZh ? "扫描所选工作区中的 `.genomelens/project.json` 元数据。" : "Scan the selected workspace for `.genomelens/project.json` metadata."}
              action={
                <Badge tone="default">
                  <Clock className="mr-1 h-3 w-3" />
                  {projects.length}
                </Badge>
              }
            />

            <div className="mt-4">
              {!trimmedWorkspace && queryState === "idle" ? (
                <EmptyState
                  icon={FolderOpen}
                  title={isZh ? "输入工作区路径" : "Enter a workspace path"}
                  description={isZh ? "先在左侧输入工作区路径，再刷新读取项目元数据。" : "Enter a workspace path on the left, then refresh to query project metadata."}
                />
              ) : null}

              {trimmedWorkspace && queryState === "loading" ? (
                <EmptyState
                  icon={RefreshCw}
                  title={isZh ? "正在加载项目..." : "Loading projects..."}
                  description={isZh ? "请稍候，正在读取项目元数据。" : "Please wait while project metadata is being read."}
                />
              ) : null}

              {trimmedWorkspace && queryState !== "loading" && projects.length === 0 && !queryError ? (
                <EmptyState
                  icon={Search}
                  title={isZh ? "当前工作区暂未返回任何项目。" : "No projects were returned for this workspace yet."}
                  description={isZh ? "尝试创建一个新项目，或检查路径是否正确。" : "Try creating a new project, or check that the path is correct."}
                />
              ) : null}

              {projects.length > 0 ? (
                <div className="ui-stagger-list grid gap-4 sm:grid-cols-2">
                  {projects.map((project) => (
                    <ProjectCard key={`${project.path}-${project.name}`} project={project} isZh={isZh} />
                  ))}
                </div>
              ) : null}
            </div>
          </Card>
        </div>
      </div>
    </section>
  );
}

function basename(path: string): string {
  const parts = path.split(/[\\/]/);
  return parts.length > 0 ? parts[parts.length - 1] : path;
}
