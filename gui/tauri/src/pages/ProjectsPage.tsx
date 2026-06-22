import { useCallback, useMemo, useState } from "react";

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

function formatTimestamp(value?: string): string {
  if (!value) {
    return "Unavailable";
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

export default function ProjectsPage({ route, onNavigate }: ProjectsPageProps) {
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
      return "Enter a workspace path to load or create projects.";
    }
    if (queryState === "loading") {
      return "Loading projects from the selected workspace.";
    }
    if (queryState === "error") {
      return "The backend project command is unavailable or returned an error.";
    }
    if (projects.length === 0) {
      return "No project metadata found yet in this workspace.";
    }
    return `${projects.length} project${projects.length === 1 ? "" : "s"} loaded from the current workspace.`;
  }, [projects.length, queryState, trimmedWorkspace]);

  return (
    <section className="ui-page-enter grid w-full gap-0 overflow-hidden border border-slate-200 bg-white xl:grid-cols-[17rem_minmax(0,1fr)]">
      <aside className="border-r border-slate-200/80 bg-[#f6f8f9]">
        <div className="border-b border-slate-200/80 px-5 py-5">
          <p className="text-xs font-medium uppercase tracking-[0.18em] text-slate-400">{route.label}</p>
          <h1 className="mt-2 text-lg font-semibold text-slate-900">Workspace projects</h1>
          <p className="mt-2 text-sm leading-6 text-slate-500">{route.description}</p>
        </div>

        <div className="px-5 py-4">
          <label className="text-xs font-medium uppercase tracking-[0.18em] text-slate-400" htmlFor="projects-workspace">
            Workspace path
          </label>
          <input
            id="projects-workspace"
            type="text"
            value={workspace}
            placeholder="Enter a workspace directory"
            className="mt-3 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-ice-400 focus:ring-2 focus:ring-ice-100"
            onChange={(event) => setWorkspace(event.target.value)}
          />
          <div className="mt-3 grid gap-2">
            <button
              type="button"
              className="ui-pressable rounded-lg bg-slate-900 px-3 py-2 text-sm font-semibold text-white transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:bg-slate-300"
              disabled={queryState === "loading"}
              onClick={() => void refreshProjects()}
            >
              {queryState === "loading" ? "Refreshing..." : "Refresh projects"}
            </button>
            <button
              type="button"
              className="ui-pressable rounded-lg border border-slate-200 px-3 py-2 text-sm font-medium text-slate-600 transition hover:bg-white hover:text-slate-900"
              onClick={() => onNavigate("/analysis/new")}
            >
              Open workbench
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
              <span className="text-slate-400">Projects</span>
              <span className="font-medium text-slate-900">{projects.length}</span>
            </div>
          </div>
        </div>
      </aside>

      <div className="ui-surface-enter min-w-0 bg-white">
        <div className="border-b border-slate-200/80 px-6 py-5">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-xs font-medium uppercase tracking-[0.18em] text-slate-400">Projects</p>
              <h2 className="mt-1 text-lg font-semibold text-slate-900">Project list and creation</h2>
              <p className="mt-2 text-sm leading-6 text-slate-500">{helperText}</p>
            </div>
            <span className="rounded-full bg-slate-100 px-3 py-1 text-[11px] font-semibold uppercase text-slate-600">
              {queryState}
            </span>
          </div>
        </div>

        <section>
          <div className="px-6 py-4">
            <h3 className="text-sm font-semibold text-slate-900">Create project</h3>
            <p className="mt-1 text-sm text-slate-500">Use the current workspace path and a project name to create new metadata.</p>
          </div>

          <div className="grid gap-3 border-y border-slate-200/80 px-6 py-4 lg:grid-cols-[minmax(0,1fr)_auto]">
            <input
              type="text"
              value={projectName}
              placeholder="Enter a project name"
              className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-ice-400 focus:ring-2 focus:ring-ice-100"
              onChange={(event) => setProjectName(event.target.value)}
            />
            <button
              type="button"
              className="ui-pressable rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-50 hover:text-slate-900 disabled:cursor-not-allowed disabled:text-slate-400"
              disabled={!trimmedWorkspace || !trimmedProjectName || createState === "loading"}
              onClick={() => void handleCreateProject()}
            >
              {createState === "loading" ? "Creating..." : "Create project"}
            </button>
          </div>

          {createError ? <div className="border-b border-slate-200/80 bg-rose-50 px-6 py-4 text-sm text-rose-700">{createError}</div> : null}
        </section>

        <section>
          <div className="px-6 py-4">
            <h3 className="text-sm font-semibold text-slate-900">Available projects</h3>
            <p className="mt-1 text-sm text-slate-500">Scan the selected workspace for `.genomelens/project.json` metadata.</p>
          </div>

          {queryError ? <div className="border-y border-slate-200/80 bg-rose-50 px-6 py-4 text-sm text-rose-700">{queryError}</div> : null}

          {!trimmedWorkspace && queryState === "idle" ? (
            <div className="border-y border-slate-200/80 px-6 py-10 text-sm text-slate-500">
              Enter a workspace path on the left, then refresh to query project metadata.
            </div>
          ) : null}

          {trimmedWorkspace && queryState === "loading" ? (
            <div className="border-y border-slate-200/80 px-6 py-10 text-sm text-slate-500">Loading projects...</div>
          ) : null}

          {trimmedWorkspace && queryState !== "loading" && projects.length === 0 && !queryError ? (
            <div className="border-y border-slate-200/80 px-6 py-10 text-sm text-slate-500">
              No projects were returned for this workspace yet.
            </div>
          ) : null}

          {projects.length > 0 ? (
            <div className="divide-y divide-slate-200/80 border-y border-slate-200/80">
              {projects.map((project) => (
                <article key={`${project.path}-${project.name}`} className="ui-surface-enter grid gap-4 px-6 py-4 lg:grid-cols-[minmax(0,1fr)_13rem]">
                  <div className="min-w-0">
                    <p className="text-sm font-semibold text-slate-900">{project.name}</p>
                    <p className="mt-1 break-all text-sm text-slate-500">{project.path}</p>
                    <div className="mt-3 grid gap-2 text-xs text-slate-400">
                      <p>Config: {project.configPath ?? "Unavailable"}</p>
                      <p>JCVI config: {project.jcviConfigPath ?? "Unavailable"}</p>
                    </div>
                  </div>
                  <div className="grid gap-2 text-sm text-slate-500">
                    <div className="flex items-center justify-between gap-4">
                      <span className="text-slate-400">Updated</span>
                      <span className="text-right text-slate-900">{formatTimestamp(project.updatedAt)}</span>
                    </div>
                    <div className="flex items-center justify-between gap-4">
                      <span className="text-slate-400">Created</span>
                      <span className="text-right text-slate-900">{formatTimestamp(project.createdAt)}</span>
                    </div>
                    <div className="flex items-center justify-between gap-4">
                      <span className="text-slate-400">Last run</span>
                      <span className="text-right text-slate-900">{formatTimestamp(project.lastRunAt)}</span>
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
