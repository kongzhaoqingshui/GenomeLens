import { useCallback, useMemo, useState } from "react";

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

function queryTone(queryState: QueryState) {
  switch (queryState) {
    case "ready":
      return "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-200";
    case "error":
      return "bg-rose-50 text-rose-700 dark:bg-rose-950/30 dark:text-rose-200";
    case "loading":
      return "bg-amber-50 text-amber-700 dark:bg-amber-950/30 dark:text-amber-200";
    default:
      return "bg-surface text-text-secondary";
  }
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
    <section className="ui-page-enter grid w-full gap-0 overflow-hidden border border-border bg-surface-raised xl:grid-cols-[17rem_minmax(0,1fr)]">
      <aside className="ui-shell-sidebar border-r">
        <div className="border-b border-border/90 px-5 py-5">
          <p className="text-xs font-medium uppercase tracking-[0.16em] text-text-tertiary">{route.label}</p>
          <h1 className="mt-2 text-lg font-semibold text-text-primary">{isZh ? "工作区项目" : "Workspace projects"}</h1>
          <p className="mt-2 text-sm leading-6 text-text-secondary">{route.description}</p>
        </div>

        <div className="px-5 py-4">
          <label className="text-xs font-medium uppercase tracking-[0.16em] text-text-tertiary" htmlFor="projects-workspace">
            {isZh ? "工作区路径" : "Workspace path"}
          </label>
          <input
            id="projects-workspace"
            type="text"
            value={workspace}
            placeholder={isZh ? "输入工作区目录" : "Enter a workspace directory"}
            className="mt-3 w-full rounded-lg border border-border bg-surface-raised px-3 py-2 text-sm text-text-primary outline-none transition placeholder:text-text-tertiary focus:border-ice-400 focus:ring-2 focus:ring-ice-100 dark:focus:ring-ice-900/50"
            onChange={(event) => setWorkspace(event.target.value)}
          />
          <div className="mt-3 grid gap-2">
            <button
              type="button"
              className="ui-pressable rounded-lg bg-ice-500 px-3 py-2 text-sm font-semibold text-white transition hover:bg-ice-400 disabled:cursor-not-allowed disabled:opacity-50"
              disabled={queryState === "loading"}
              onClick={() => void refreshProjects()}
            >
              {queryState === "loading" ? (isZh ? "刷新中..." : "Refreshing...") : isZh ? "刷新项目" : "Refresh projects"}
            </button>
            <button
              type="button"
              className="ui-pressable rounded-lg border border-border bg-surface px-3 py-2 text-sm font-medium text-text-secondary transition hover:bg-surface-raised hover:text-text-primary"
              onClick={() => onNavigate("/analysis/new")}
            >
              {isZh ? "打开工作台" : "Open workbench"}
            </button>
          </div>
        </div>

        <div className="border-t border-border/90 px-5 py-4">
          <div className="text-[11px] font-medium uppercase tracking-[0.16em] text-text-tertiary">{isZh ? "状态" : "State"}</div>
          <div className="mt-3 divide-y divide-border/90 border-y border-border/90">
            <div className="flex items-center justify-between py-3 text-sm">
              <span className="text-text-tertiary">{isZh ? "查询" : "Query"}</span>
              <span className={`rounded-full px-3 py-1 text-[11px] font-semibold uppercase ${queryTone(queryState)}`}>{queryState}</span>
            </div>
            <div className="flex items-center justify-between py-3 text-sm">
              <span className="text-text-tertiary">{isZh ? "项目" : "Projects"}</span>
              <span className="font-medium text-text-primary">{projects.length}</span>
            </div>
          </div>
        </div>
      </aside>

      <div className="ui-surface-enter min-w-0 bg-surface-raised">
        <div className="border-b border-border/90 px-6 py-5">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-xs font-medium uppercase tracking-[0.16em] text-text-tertiary">{isZh ? "项目" : "Projects"}</p>
              <h2 className="mt-1 text-lg font-semibold text-text-primary">{isZh ? "项目列表与创建" : "Project list and creation"}</h2>
              <p className="mt-2 text-sm leading-6 text-text-secondary">{helperText}</p>
            </div>
            <span className={`rounded-full px-3 py-1 text-[11px] font-semibold uppercase ${queryTone(queryState)}`}>{queryState}</span>
          </div>
        </div>

        <section>
          <div className="px-6 py-4">
            <h3 className="text-sm font-semibold text-text-primary">{isZh ? "创建项目" : "Create project"}</h3>
            <p className="mt-1 text-sm text-text-secondary">
              {isZh ? "使用当前工作区路径和项目名称创建新的元数据。" : "Use the current workspace path and a project name to create new metadata."}
            </p>
          </div>

          <div className="grid gap-3 border-y border-border/90 px-6 py-4 lg:grid-cols-[minmax(0,1fr)_auto]">
            <input
              type="text"
              value={projectName}
              placeholder={isZh ? "输入项目名称" : "Enter a project name"}
              className="w-full rounded-lg border border-border bg-surface-raised px-3 py-2 text-sm text-text-primary outline-none transition placeholder:text-text-tertiary focus:border-ice-400 focus:ring-2 focus:ring-ice-100 dark:focus:ring-ice-900/50"
              onChange={(event) => setProjectName(event.target.value)}
            />
            <button
              type="button"
              className="ui-pressable rounded-lg border border-border bg-surface px-4 py-2 text-sm font-medium text-text-secondary transition hover:bg-surface-raised hover:text-text-primary disabled:cursor-not-allowed disabled:opacity-45"
              disabled={!trimmedWorkspace || !trimmedProjectName || createState === "loading"}
              onClick={() => void handleCreateProject()}
            >
              {createState === "loading" ? (isZh ? "创建中..." : "Creating...") : isZh ? "创建项目" : "Create project"}
            </button>
          </div>

          {createError ? <div className="border-b border-border/90 bg-rose-50 px-6 py-4 text-sm text-rose-700 dark:bg-rose-950/30 dark:text-rose-200">{createError}</div> : null}
        </section>

        <section>
          <div className="px-6 py-4">
            <h3 className="text-sm font-semibold text-text-primary">{isZh ? "可用项目" : "Available projects"}</h3>
            <p className="mt-1 text-sm text-text-secondary">
              {isZh ? "扫描所选工作区中的 `.genomelens/project.json` 元数据。" : "Scan the selected workspace for `.genomelens/project.json` metadata."}
            </p>
          </div>

          {queryError ? <div className="border-y border-border/90 bg-rose-50 px-6 py-4 text-sm text-rose-700 dark:bg-rose-950/30 dark:text-rose-200">{queryError}</div> : null}

          {!trimmedWorkspace && queryState === "idle" ? (
            <div className="border-y border-border/90 px-6 py-10 text-sm text-text-secondary">
              {isZh ? "先在左侧输入工作区路径，再刷新读取项目元数据。" : "Enter a workspace path on the left, then refresh to query project metadata."}
            </div>
          ) : null}

          {trimmedWorkspace && queryState === "loading" ? (
            <div className="border-y border-border/90 px-6 py-10 text-sm text-text-secondary">{isZh ? "正在加载项目..." : "Loading projects..."}</div>
          ) : null}

          {trimmedWorkspace && queryState !== "loading" && projects.length === 0 && !queryError ? (
            <div className="border-y border-border/90 px-6 py-10 text-sm text-text-secondary">
              {isZh ? "当前工作区暂未返回任何项目。" : "No projects were returned for this workspace yet."}
            </div>
          ) : null}

          {projects.length > 0 ? (
            <div className="divide-y divide-border/90 border-y border-border/90">
              {projects.map((project) => (
                <article key={`${project.path}-${project.name}`} className="ui-row-item grid gap-4 px-6 py-4 lg:grid-cols-[minmax(0,1fr)_13rem]">
                  <div className="min-w-0">
                    <p className="text-sm font-semibold text-text-primary">{project.name}</p>
                    <p className="mt-1 break-all text-sm text-text-secondary">{project.path}</p>
                    <div className="mt-3 grid gap-2 text-xs text-text-tertiary">
                      <p>{isZh ? "配置" : "Config"}: {project.configPath ?? (isZh ? "不可用" : "Unavailable")}</p>
                      <p>JCVI config: {project.jcviConfigPath ?? (isZh ? "不可用" : "Unavailable")}</p>
                    </div>
                  </div>
                  <div className="grid gap-2 text-sm text-text-secondary">
                    <div className="flex items-center justify-between gap-4">
                      <span className="text-text-tertiary">{isZh ? "更新" : "Updated"}</span>
                      <span className="text-right text-text-primary">{formatTimestamp(project.updatedAt, isZh)}</span>
                    </div>
                    <div className="flex items-center justify-between gap-4">
                      <span className="text-text-tertiary">{isZh ? "创建" : "Created"}</span>
                      <span className="text-right text-text-primary">{formatTimestamp(project.createdAt, isZh)}</span>
                    </div>
                    <div className="flex items-center justify-between gap-4">
                      <span className="text-text-tertiary">{isZh ? "上次运行" : "Last run"}</span>
                      <span className="text-right text-text-primary">{formatTimestamp(project.lastRunAt, isZh)}</span>
                    </div>
                  </div>
                </article>
              ))}
            </div>
          ) : null}
        </section>
      </div>
    </section>
  );
}
