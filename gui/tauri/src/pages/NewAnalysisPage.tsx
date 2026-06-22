import { open } from "@tauri-apps/plugin-dialog";
import { mkdir, readTextFile, writeTextFile } from "@tauri-apps/plugin-fs";
import { useEffect, useMemo, useState } from "react";

import { GameIcon, type GameIconName } from "../components/GameIcon";
import type {
  AlignSoft,
  AnalysisInputMode,
  AnalysisRequest,
  DbType,
  LogLevel,
  McscanWorkflow,
  OutputFormat,
} from "../models/analysis-request";
import type { AnalysisRequestDraft, SpeciesInputDraft } from "../models/analysis-request-draft";
import {
  createDraftForCapability,
  getJcviCapabilityById,
  listJcviCapabilities,
  type JcviCapabilityId,
} from "../models";
import { draftToAnalysisRequest } from "../models/analysis-request-draft";
import {
  appendRunLogLines,
  applyAnalysisEvent,
  createAnalysisRunState,
  type AnalysisEvent,
  type AnalysisRunState,
} from "../models/run-session";
import { validateAnalysisRequestDraft, type ValidationIssue } from "../models/validation";
import type { AppRoute } from "../routes/routes";
import { getAnalysisSchema, getTemplateDraft, type JsonObject } from "../services/analysis";
import { listenToAnalysisEvents, openPath, readRunLog, readSummaryView, runAnalysis } from "../services/workbench";

interface NewAnalysisPageProps {
  route: AppRoute;
  onNavigate: (path: string) => void;
  locationHash: string;
}

type RunPanelStatus = "idle" | "confirming" | "starting" | "running" | "finished" | "error";
type WorkbenchView = "setup" | "run" | "results";
type McscanNumberField = "cscore" | "dist" | "iter" | "up" | "down" | "dpi";

interface WorkbenchTask {
  id: string;
  title: string;
  capabilityId: JcviCapabilityId | null;
  icon: GameIconName;
  draft: AnalysisRequestDraft;
  view: WorkbenchView;
  runStatus: RunPanelStatus;
  runState: AnalysisRunState | null;
  runError: string | null;
  pendingRequestJson: string;
  importedRequest: ImportedRequestState | null;
  createdAt: string;
  updatedAt: string;
}

interface ImportedRequestState {
  path: string;
  json: string;
  method: string;
  workflow: string;
  inputMode: string;
  requestOutputDirectory: string;
}

const FIELD_CLASS =
  "mt-2 w-full rounded-lg border border-border bg-bg px-3 py-2 text-sm text-text-primary shadow-sm outline-none transition focus:border-ice-400 focus:ring-2 focus:ring-ice-200 dark:focus:ring-ice-900/60";
const LABEL_CLASS = "text-xs font-semibold uppercase tracking-[0.14em] text-text-tertiary";
const CHECKBOX_CLASS = "h-4 w-4 rounded border-border text-ice-500 focus:ring-ice-500";
const PANEL_BODY_CLASS = "ui-surface-enter border-b border-slate-200/80 bg-white px-1 py-6 last:border-b-0";
const SECONDARY_BUTTON_CLASS =
  "ui-pressable rounded-lg border border-border bg-surface-raised/80 px-3 py-2 text-xs font-semibold text-text-secondary transition hover:border-ice-200 hover:bg-ice-50 hover:text-ice-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ice-500 dark:hover:border-ice-800 dark:hover:bg-ice-900/30 dark:hover:text-ice-200 disabled:cursor-not-allowed disabled:opacity-45";
const PRIMARY_BUTTON_CLASS =
  "ui-pressable rounded-lg bg-ice-500 px-4 py-2 text-sm font-semibold text-white shadow-lg shadow-ice-500/20 transition hover:bg-ice-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ice-500 focus-visible:ring-offset-2 focus-visible:ring-offset-bg disabled:cursor-not-allowed disabled:opacity-50";

const WORKFLOW_OPTIONS: McscanWorkflow[] = [
  "mcscan_pairwise",
  "graphics_synteny",
  "graphics_dotplot",
  "graphics_karyotype",
  "catalog_ortholog",
  "local_synteny",
];
const LOG_LEVELS: LogLevel[] = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"];
const FORMAT_OPTIONS: OutputFormat[] = ["png", "pdf", "svg"];
const MCSCAN_NUMBER_FIELDS: Array<{
  key: McscanNumberField;
  label: string;
  min: number;
  max?: number;
  step: number;
}> = [
  { key: "cscore", label: "cscore", min: 0, max: 1, step: 0.05 },
  { key: "dist", label: "dist", min: 1, step: 1 },
  { key: "iter", label: "iter", min: 1, step: 1 },
  { key: "up", label: "upstream", min: 0, step: 1 },
  { key: "down", label: "downstream", min: 0, step: 1 },
  { key: "dpi", label: "dpi", min: 1, step: 1 },
];

const CAPABILITY_ICON: Record<JcviCapabilityId, GameIconName> = {
  "pairwise-synteny": "pairwise",
  "multi-species-synteny": "multi-species",
  "local-synteny": "local",
  dotplot: "dotplot",
  karyotype: "karyotype",
  "ortholog-catalog": "ortholog",
  "environment-check": "environment",
};

function nowIso(): string {
  return new Date().toISOString();
}

function formatTime(value: string | undefined): string {
  if (!value) {
    return "--:--";
  }
  return new Date(value).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function issueFor(issues: ValidationIssue[], field: string): ValidationIssue | undefined {
  return issues.find((item) => item.field === field);
}

function IssueText({ issue }: { issue?: ValidationIssue }) {
  if (issue === undefined) {
    return null;
  }

  return <p className="mt-2 text-xs font-medium text-rose-600 dark:text-rose-300">{issue.message}</p>;
}

function SectionTitle({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <div>
      <h2 className="text-base font-semibold text-text-primary">{title}</h2>
      <p className="mt-1 text-sm leading-6 text-text-secondary">{subtitle}</p>
    </div>
  );
}

function updateNumber(value: string): number | null {
  if (value.trim().length === 0) {
    return null;
  }
  const next = Number(value);
  return Number.isFinite(next) ? next : null;
}

function emptySpecies(inputMode: AnalysisInputMode): SpeciesInputDraft {
  const speciesMode = inputMode === "gff_genome" ? "gff_genome" : "bed_cds";
  return {
    name: "",
    inputMode: speciesMode,
    bed: "",
    cds: "",
    gff: "",
    genome: "",
  };
}

function splitTargets(value: string): string[] {
  return value
    .split(/[\n,]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function stringifyJson(value: unknown): string {
  return JSON.stringify(value, null, 2);
}

function asObject(value: unknown): Record<string, unknown> | null {
  if (typeof value === "object" && value !== null && !Array.isArray(value)) {
    return value as Record<string, unknown>;
  }
  return null;
}

function parseImportedRequest(path: string, sourceText: string): ImportedRequestState {
  const parsed = JSON.parse(sourceText) as AnalysisRequest;
  const root = asObject(parsed);
  if (!root) {
    throw new Error("Imported request must be a JSON object.");
  }

  const input = asObject(root.input);
  const output = asObject(root.output);
  const methodConfig = asObject(root.method_config);

  return {
    path,
    json: stringifyJson(parsed),
    method: typeof root.method === "string" ? root.method : "unknown",
    workflow: typeof methodConfig?.workflow === "string" ? methodConfig.workflow : "unknown",
    inputMode: typeof input?.mode === "string" ? input.mode : "unknown",
    requestOutputDirectory: typeof output?.directory === "string" ? output.directory : "",
  };
}

function joinPath(directory: string, filename: string): string {
  const separator = directory.includes("\\") ? "\\" : "/";
  return `${directory.replace(/[\\/]+$/, "")}${separator}${filename}`;
}

function timestampForFilename(): string {
  return new Date().toISOString().replace(/[:.]/g, "-");
}

function toProgressPercent(value: number): number {
  if (!Number.isFinite(value)) {
    return 0;
  }
  return value <= 1 ? value * 100 : value;
}

function coerceDialogPath(value: string | string[] | null): string | null {
  if (Array.isArray(value)) {
    return value[0] ?? null;
  }
  return value;
}

function readCapabilityFromHash(locationHash: string): JcviCapabilityId | null {
  const queryIndex = locationHash.indexOf("?");
  if (queryIndex < 0) {
    return null;
  }

  const params = new URLSearchParams(locationHash.slice(queryIndex + 1));
  const capability = params.get("capability");
  if (
    capability === "pairwise-synteny" ||
    capability === "multi-species-synteny" ||
    capability === "local-synteny" ||
    capability === "dotplot" ||
    capability === "karyotype" ||
    capability === "ortholog-catalog" ||
    capability === "environment-check"
  ) {
    return capability;
  }
  return null;
}

function createTaskFromTemplate(
  templateDraft: AnalysisRequestDraft,
  capabilityId: JcviCapabilityId | null,
  index: number,
): WorkbenchTask {
  const capability = capabilityId ? getJcviCapabilityById(capabilityId) : undefined;
  const draft = capabilityId ? createDraftForCapability(templateDraft, capabilityId) : templateDraft;
  const title = capability ? `${capability.subtitle} #${index}` : `MCSCAN Task #${index}`;
  const createdAt = nowIso();

  return {
    id: `task-${createdAt}-${index}`,
    title,
    capabilityId,
    icon: capabilityId ? CAPABILITY_ICON[capabilityId] : "pairwise",
    draft: {
      ...draft,
      species: draft.species.map((species) => ({ ...species })),
      formats: [...draft.formats],
      options: { ...draft.options },
      mcscan: { ...draft.mcscan, targetGeneIds: [...draft.mcscan.targetGeneIds] },
    },
    view: "setup",
    runStatus: "idle",
    runState: null,
    runError: null,
    pendingRequestJson: "",
    importedRequest: null,
    createdAt,
    updatedAt: createdAt,
  };
}

function statusTone(status: RunPanelStatus): string {
  switch (status) {
    case "running":
    case "starting":
      return "bg-sky-100 text-sky-700 dark:bg-sky-400/15 dark:text-sky-200";
    case "finished":
      return "bg-emerald-100 text-emerald-700 dark:bg-emerald-400/15 dark:text-emerald-200";
    case "error":
      return "bg-rose-100 text-rose-700 dark:bg-rose-400/15 dark:text-rose-200";
    case "confirming":
      return "bg-amber-100 text-amber-700 dark:bg-amber-400/15 dark:text-amber-200";
    default:
      return "bg-slate-100 text-slate-600 dark:bg-slate-700/50 dark:text-slate-300";
  }
}

function applyEventStatus(currentStatus: RunPanelStatus, event: AnalysisEvent): RunPanelStatus {
  if (event.name === "analysis:stdout" || event.name === "analysis:state") {
    return currentStatus === "finished" || currentStatus === "error" ? currentStatus : "running";
  }
  if (event.name === "analysis:finished") {
    return event.payload.status === "SUCCEEDED" ? "finished" : "error";
  }
  return "error";
}

function canCloseTask(task: WorkbenchTask): boolean {
  return task.runStatus !== "confirming" && task.runStatus !== "starting" && task.runStatus !== "running";
}

export default function NewAnalysisPage({ route, onNavigate, locationHash }: NewAnalysisPageProps) {
  const [templateDraft, setTemplateDraft] = useState<AnalysisRequestDraft | null>(null);
  const [schema, setSchema] = useState<JsonObject | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [tasks, setTasks] = useState<WorkbenchTask[]>([]);
  const [activeTaskId, setActiveTaskId] = useState("");
  const [taskCounter, setTaskCounter] = useState(1);
  const [taskFilter, setTaskFilter] = useState("");
  const capabilityId = useMemo(() => readCapabilityFromHash(locationHash), [locationHash]);

  useEffect(() => {
    let cancelled = false;

    setLoading(true);
    setLoadError(null);
    void Promise.all([getTemplateDraft("mcscan"), getAnalysisSchema()])
      .then(([nextTemplateDraft, analysisSchema]) => {
        if (cancelled) {
          return;
        }
        const firstTask = createTaskFromTemplate(nextTemplateDraft, capabilityId, 1);
        setTemplateDraft(nextTemplateDraft);
        setSchema(analysisSchema);
        setTasks([firstTask]);
        setActiveTaskId(firstTask.id);
        setTaskCounter(2);
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setLoadError(error instanceof Error ? error.message : String(error));
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [capabilityId]);

  useEffect(() => {
    let active = true;
    let stopListening: (() => void) | null = null;

    void listenToAnalysisEvents((event) => {
      if (!active) {
        return;
      }

      setTasks((currentTasks) =>
        currentTasks.map((task) => {
          if (task.runState?.runId !== event.payload.runId) {
            return task;
          }

          return {
            ...task,
            runStatus: applyEventStatus(task.runStatus, event),
            runError: event.name === "analysis:error" ? event.payload.message : task.runError,
            runState: applyAnalysisEvent(task.runState, event),
            updatedAt: nowIso(),
          };
        }),
      );
    }).then((unlisten) => {
      if (active) {
        stopListening = unlisten;
      } else {
        unlisten();
      }
    });

    return () => {
      active = false;
      stopListening?.();
    };
  }, []);

  const activeTask = tasks.find((task) => task.id === activeTaskId) ?? tasks[0] ?? null;
  const draft = activeTask?.draft ?? null;
  const validation = useMemo(() => (draft ? validateAnalysisRequestDraft(draft) : null), [draft]);
  const requestJson = useMemo(() => (draft ? stringifyJson(draftToAnalysisRequest(draft)) : ""), [draft]);
  const schemaJson = useMemo(() => (schema ? stringifyJson(schema) : ""), [schema]);
  const targetGeneText = draft?.mcscan.targetGeneIds.join("\n") ?? "";
  const importedRequest = activeTask?.importedRequest ?? null;
  const requestPreviewJson = importedRequest?.json ?? requestJson;

  useEffect(() => {
    if (!activeTask?.runState || !activeTask.runState.finished || activeTask.runState.summaryView !== undefined) {
      return;
    }

    const taskId = activeTask.id;
    void readSummaryView({ outdir: activeTask.runState.outdir })
      .then((nextSummaryView) => {
        setTasks((currentTasks) =>
          currentTasks.map((task) =>
            task.id === taskId && task.runState
              ? {
                  ...task,
                  runState: {
                    ...task.runState,
                    summaryView: nextSummaryView,
                    summaryPath: task.runState.summaryPath || nextSummaryView.runSummaryPath,
                    logPath: task.runState.logPath || nextSummaryView.runLogPath,
                  },
                  updatedAt: nowIso(),
                }
              : task,
          ),
        );
      })
      .catch((error: unknown) => {
        setTasks((currentTasks) =>
          currentTasks.map((task) =>
            task.id === taskId
              ? { ...task, runError: error instanceof Error ? error.message : String(error), updatedAt: nowIso() }
              : task,
          ),
        );
      });
  }, [activeTask]);

  const visibleTasks = useMemo(() => {
    const query = taskFilter.trim().toLowerCase();
    if (!query) {
      return tasks;
    }
    return tasks.filter((task) => {
      const capability = task.capabilityId ? getJcviCapabilityById(task.capabilityId) : null;
      return [task.title, task.draft.mcscan.workflow, capability?.title, capability?.subtitle]
        .filter(Boolean)
        .some((value) => String(value).toLowerCase().includes(query));
    });
  }, [taskFilter, tasks]);

  const capabilities = useMemo(() => listJcviCapabilities(), []);

  function updateTask(taskId: string, updater: (task: WorkbenchTask) => WorkbenchTask) {
    setTasks((currentTasks) =>
      currentTasks.map((task) => (task.id === taskId ? { ...updater(task), updatedAt: nowIso() } : task)),
    );
  }

  function updateActiveTask(updater: (task: WorkbenchTask) => WorkbenchTask) {
    if (!activeTask) {
      return;
    }
    updateTask(activeTask.id, updater);
  }

  function patchDraft(patch: Partial<AnalysisRequestDraft>) {
    updateActiveTask((task) => ({ ...task, draft: { ...task.draft, ...patch } }));
  }

  function patchOptions(patch: Partial<AnalysisRequestDraft["options"]>) {
    updateActiveTask((task) => ({
      ...task,
      draft: { ...task.draft, options: { ...task.draft.options, ...patch } },
    }));
  }

  function patchMcscan(patch: Partial<AnalysisRequestDraft["mcscan"]>) {
    updateActiveTask((task) => ({
      ...task,
      draft: { ...task.draft, mcscan: { ...task.draft.mcscan, ...patch } },
    }));
  }

  function updateSpecies(index: number, patch: Partial<SpeciesInputDraft>) {
    updateActiveTask((task) => {
      const species = task.draft.species.map((item, itemIndex) =>
        itemIndex === index ? { ...item, ...patch } : item,
      );
      return { ...task, draft: { ...task.draft, species } };
    });
  }

  function addSpecies() {
    updateActiveTask((task) => ({
      ...task,
      draft: { ...task.draft, species: [...task.draft.species, emptySpecies(task.draft.inputMode)] },
    }));
  }

  function removeSpecies(index: number) {
    updateActiveTask((task) => ({
      ...task,
      draft: { ...task.draft, species: task.draft.species.filter((_, itemIndex) => itemIndex !== index) },
    }));
  }

  function toggleFormat(format: OutputFormat) {
    updateActiveTask((task) => {
      const formats = task.draft.formats.includes(format)
        ? task.draft.formats.filter((item) => item !== format)
        : [...task.draft.formats, format];
      return { ...task, draft: { ...task.draft, formats } };
    });
  }

  function setTaskView(view: WorkbenchView) {
    updateActiveTask((task) => ({ ...task, view }));
  }

  function createTask(capability: JcviCapabilityId | null = null) {
    if (!templateDraft) {
      return;
    }
    const nextTask = createTaskFromTemplate(templateDraft, capability, taskCounter);
    setTaskCounter((current) => current + 1);
    setTasks((currentTasks) => [nextTask, ...currentTasks]);
    setActiveTaskId(nextTask.id);
  }

  function closeTask(taskId: string) {
    setTasks((currentTasks) => {
      if (currentTasks.length <= 1) {
        return currentTasks;
      }
      const taskToClose = currentTasks.find((task) => task.id === taskId);
      if (taskToClose && !canCloseTask(taskToClose)) {
        return currentTasks;
      }
      const nextTasks = currentTasks.filter((task) => task.id !== taskId);
      if (activeTaskId === taskId) {
        setActiveTaskId(nextTasks[0]?.id ?? "");
      }
      return nextTasks;
    });
  }

  async function pickDirectory(onSelect: (path: string) => void) {
    const selected = coerceDialogPath(await open({ directory: true, multiple: false }));
    if (selected) {
      onSelect(selected);
    }
  }

  async function pickFile(onSelect: (path: string) => void) {
    const selected = coerceDialogPath(await open({ directory: false, multiple: false }));
    if (selected) {
      onSelect(selected);
    }
  }

  async function handleImportRequestJson() {
    if (!activeTask) {
      return;
    }

    const selected = coerceDialogPath(
      await open({
        directory: false,
        multiple: false,
        filters: [{ name: "JSON", extensions: ["json"] }],
      }),
    );

    if (!selected) {
      return;
    }

    try {
      const sourceText = await readTextFile(selected);
      const nextImportedRequest = parseImportedRequest(selected, sourceText);
      updateActiveTask((task) => ({
        ...task,
        runStatus: task.runStatus === "confirming" ? "idle" : task.runStatus,
        runError: null,
        pendingRequestJson: "",
        importedRequest: nextImportedRequest,
        draft:
          task.draft.outputDirectory.trim().length === 0 && nextImportedRequest.requestOutputDirectory
            ? { ...task.draft, outputDirectory: nextImportedRequest.requestOutputDirectory }
            : task.draft,
      }));
    } catch (error: unknown) {
      updateActiveTask((task) => ({
        ...task,
        runStatus: "error",
        runError: error instanceof Error ? error.message : String(error),
        view: "setup",
      }));
    }
  }

  function clearImportedRequest() {
    updateActiveTask((task) => ({
      ...task,
      importedRequest: null,
      pendingRequestJson: "",
      runStatus: task.runStatus === "confirming" ? "idle" : task.runStatus,
      runError: null,
    }));
  }

  async function handlePrepareRun() {
    if (!activeTask) {
      return;
    }

    if (activeTask.importedRequest) {
      if (!activeTask.draft.outputDirectory.trim()) {
        updateActiveTask((task) => ({
          ...task,
          runStatus: "error",
          runError: "Choose an output directory before running an imported request.",
          view: "setup",
        }));
        return;
      }

      updateActiveTask((task) => ({
        ...task,
        runError: null,
        pendingRequestJson: task.importedRequest?.json ?? "",
        runStatus: "confirming",
        view: "run",
      }));
      return;
    }

    if (!validation) {
      return;
    }

    if (!validation.ok) {
      updateActiveTask((task) => ({
        ...task,
        runStatus: "error",
        runError: "Please fix validation errors before running this task.",
        view: "setup",
      }));
      return;
    }

    updateActiveTask((task) => ({
      ...task,
      runError: null,
      pendingRequestJson: requestJson,
      runStatus: "confirming",
      view: "run",
    }));
  }

  async function handleConfirmRun() {
    if (!activeTask) {
      return;
    }

    const taskId = activeTask.id;
    const outdir = activeTask.draft.outputDirectory.trim();
    const imported = activeTask.importedRequest;

    if (!outdir) {
      updateTask(taskId, (task) => ({
        ...task,
        runStatus: "error",
        runError: imported
          ? "Choose an output directory before running an imported request."
          : "Choose an output directory before generating a request JSON.",
        view: "setup",
      }));
      return;
    }

    const request = imported ? null : draftToAnalysisRequest(activeTask.draft);
    const json = imported?.json ?? (request ? stringifyJson(request) : "");
    const requestPath = imported ? imported.path : joinPath(outdir, `genomelens-request-${timestampForFilename()}.json`);

    updateTask(taskId, (task) => ({ ...task, runStatus: "starting", runError: null, runState: null, view: "run" }));

    try {
      await mkdir(outdir, { recursive: true });
      if (!imported) {
        await writeTextFile(requestPath, `${json}\n`);
      }
      const handle = await runAnalysis({ requestPath, outdir });
      updateTask(taskId, (task) => ({
        ...task,
        runState: createAnalysisRunState(handle),
        runStatus: "running",
        pendingRequestJson: "",
        view: "run",
      }));
    } catch (error: unknown) {
      updateTask(taskId, (task) => ({
        ...task,
        runStatus: "error",
        runError: error instanceof Error ? error.message : String(error),
      }));
    }
  }

  async function handleReadSummary() {
    if (!activeTask) {
      return;
    }
    const outdir = activeTask.runState?.outdir ?? activeTask.draft.outputDirectory;
    if (!outdir) {
      return;
    }
    try {
      const nextSummaryView = await readSummaryView({ outdir });
      updateTask(activeTask.id, (task) =>
        task.runState
          ? {
              ...task,
              view: "results",
              runState: {
                ...task.runState,
                summaryView: nextSummaryView,
                summaryPath: task.runState.summaryPath || nextSummaryView.runSummaryPath,
                logPath: task.runState.logPath || nextSummaryView.runLogPath,
              },
            }
          : task,
      );
    } catch (error: unknown) {
      updateActiveTask((task) => ({ ...task, runError: error instanceof Error ? error.message : String(error) }));
    }
  }

  async function handleReadLog() {
    if (!activeTask) {
      return;
    }
    const outdir = activeTask.runState?.outdir ?? activeTask.draft.outputDirectory;
    if (!outdir) {
      return;
    }
    try {
      const snapshot = await readRunLog({ outdir, tailLines: 100 });
      updateTask(activeTask.id, (task) =>
        task.runState
          ? {
              ...task,
              view: "run",
              runState: appendRunLogLines(
                {
                  ...task.runState,
                  logPath: snapshot.logPath,
                  logLines: [],
                  lastLogLine: undefined,
                },
                snapshot.lines,
              ),
            }
          : task,
      );
    } catch (error: unknown) {
      updateActiveTask((task) => ({ ...task, runError: error instanceof Error ? error.message : String(error) }));
    }
  }

  async function handleOpenOutput() {
    const outdir = activeTask?.runState?.outdir ?? activeTask?.draft.outputDirectory ?? "";
    if (outdir) {
      await openPath({ path: outdir });
    }
  }

  async function handleOpenLog() {
    const path = activeTask?.runState?.logPath ?? activeTask?.runState?.summaryView?.runLogPath ?? "";
    if (path) {
      await openPath({ path });
    }
  }

  async function handleOpenSummary() {
    const path = activeTask?.runState?.summaryPath ?? activeTask?.runState?.summaryView?.runSummaryPath ?? "";
    if (path) {
      await openPath({ path });
    }
  }

  if (loading) {
    return (
      <section className="ui-page-enter grid h-screen w-full content-center justify-center gap-4 bg-[#f4fbfd] text-center">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-400">
          JCVI meow · {route.description}
        </p>
        <h1 className="text-2xl font-semibold text-slate-900">Preparing multi-task workbench</h1>
        <p className="text-sm text-slate-500">Loading template and analysis schema...</p>
      </section>
    );
  }

  if (loadError || !activeTask || !draft || validation === null) {
    return (
      <section className="ui-page-enter grid h-screen w-full content-center justify-center gap-4 bg-[#f4fbfd] text-center">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-400">
          JCVI meow · {route.description}
        </p>
        <h1 className="text-2xl font-semibold text-slate-900">Workbench failed to initialize</h1>
        <p className="max-w-2xl rounded-[1.35rem] border border-rose-200 bg-rose-50 p-4 text-left text-sm text-rose-700">
          {loadError ?? "Unable to initialize AnalysisRequestDraft."}
        </p>
      </section>
    );
  }

  const directoryIssue = issueFor(validation.issues, "input.directory");
  const outputIssue = issueFor(validation.issues, "output.directory");
  const threadsIssue = issueFor(validation.issues, "options.threads");
  const minBlockIssue = issueFor(validation.issues, "options.min_block_size");
  const workflowState = activeTask.runState?.status ?? "PENDING";
  const progress = toProgressPercent(activeTask.runState?.progress ?? 0);
  const logLines = activeTask.runState?.logLines ?? [];
  const summaryView = activeTask.runState?.summaryView ?? null;
  const resolvedLogPath = activeTask.runState?.logPath ?? summaryView?.runLogPath ?? "";
  const resolvedSummaryPath = activeTask.runState?.summaryPath ?? summaryView?.runSummaryPath ?? "";
  const recentEvents = logLines.slice(-6).reverse();
  const usesImportedRequest = importedRequest !== null;

  return (
    <div className="ui-page-enter grid h-screen w-full grid-cols-[20rem_minmax(0,1fr)_23rem] overflow-hidden bg-white">
      <aside className="flex min-h-0 flex-col overflow-hidden border-r border-slate-200/80 bg-[#eaf7fb] px-3 py-4">
        <div className="flex items-center gap-3 px-3 pb-4">
          <button type="button" className="ui-pressable text-sm text-slate-500 hover:text-slate-900" onClick={() => onNavigate("/")}>
            ←
          </button>
          <span className="text-sm font-semibold text-slate-900">JCVI meow</span>
        </div>

        <nav className="grid gap-1 px-1 pb-5 text-sm text-slate-700">
          <button type="button" className="ui-list-item flex items-center gap-3 rounded-lg px-3 py-2 text-left hover:bg-white/75" onClick={() => createTask()}>
            <GameIcon name="pairwise" className="h-4 w-4" />
            新任务
          </button>
          <label className="ui-list-item flex items-center gap-3 rounded-lg px-3 py-2 hover:bg-white/75">
            <GameIcon name="environment" className="h-4 w-4" />
            <input
              className="min-w-0 flex-1 bg-transparent text-sm outline-none placeholder:text-slate-500"
              placeholder="搜索"
              value={taskFilter}
              onChange={(event) => setTaskFilter(event.target.value)}
            />
          </label>
        </nav>

        <div className="px-2 pb-3">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-xs font-medium text-slate-400">置顶</p>
              <h2 className="mt-4 text-sm font-semibold text-slate-500">Tasks</h2>
            </div>
            <button type="button" className="ui-pressable rounded-lg px-2 py-1 text-lg leading-none text-slate-500 hover:bg-white/75" onClick={() => createTask()}>
              +
            </button>
          </div>
        </div>

        <div className="min-h-0 flex-1 overflow-auto px-1">
          {visibleTasks.map((task) => (
            <button
              key={task.id}
              type="button"
              className={[
                "ui-list-item mb-1 grid w-full grid-cols-[1.75rem_minmax(0,1fr)_auto] items-center gap-3 rounded-xl px-3 py-2.5 text-left transition",
                task.id === activeTask.id
                  ? "bg-white/75 text-slate-900 shadow-sm"
                  : "bg-transparent text-slate-600 hover:bg-white/55",
              ].join(" ")}
              onClick={() => setActiveTaskId(task.id)}
            >
              <span className="flex h-7 w-7 items-center justify-center text-slate-500">
                <GameIcon name={task.icon} className="h-4 w-4" />
              </span>
              <span className="min-w-0">
                <span className="block truncate text-sm font-medium">{task.title}</span>
                <span className="mt-0.5 block truncate text-xs text-slate-400">{task.draft.mcscan.workflow}</span>
              </span>
              {tasks.length > 1 && canCloseTask(task) ? (
                <span
                  role="button"
                  tabIndex={0}
                  className="ui-pressable rounded-md px-2 py-1 text-xs text-slate-400 hover:bg-slate-100 hover:text-slate-700"
                  onClick={(event) => {
                    event.stopPropagation();
                    closeTask(task.id);
                  }}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") {
                      event.preventDefault();
                      event.stopPropagation();
                      closeTask(task.id);
                    }
                  }}
                >
                  x
                </span>
              ) : null}
            </button>
          ))}
        </div>

        <div className="border-t border-slate-200/80 px-1 py-3">
          <p className="hidden px-3 text-xs font-medium text-slate-400">快速创建</p>
          <div className="hidden">
            {capabilities.map((capability) => {
              const disabled = capability.status !== "connected" || capability.id === "environment-check";
              return (
                <button
                  key={capability.id}
                  type="button"
                  disabled={disabled}
                  className="flex items-center gap-3 rounded-lg px-3 py-1.5 text-left text-xs font-medium text-slate-500 transition hover:bg-white/75 disabled:cursor-not-allowed disabled:opacity-45"
                  onClick={() => createTask(capability.id)}
                  title={capability.description}
                >
                  <GameIcon name={CAPABILITY_ICON[capability.id]} className="h-4 w-4" />
                  <span className="truncate">{capability.subtitle}</span>
                </button>
              );
            })}
          </div>
          <button
            type="button"
            className="ui-list-item flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left text-sm text-slate-600 hover:bg-white/75"
            onClick={() => onNavigate("/settings")}
          >
            <GameIcon name="environment" className="h-4 w-4" />
            设置
          </button>
        </div>
      </aside>

      <main className="flex min-w-0 flex-col overflow-hidden bg-white">
        <header className="flex h-16 shrink-0 items-center justify-between border-b border-slate-200/80 px-6">
          <div className="min-w-0">
            <input
              className="w-full min-w-0 bg-transparent text-base font-semibold tracking-tight text-slate-900 outline-none"
              value={activeTask.title}
              onChange={(event) => updateActiveTask((task) => ({ ...task, title: event.target.value }))}
            />
            <p className="mt-1 text-xs text-slate-500">
              Created {formatTime(activeTask.createdAt)} · Updated {formatTime(activeTask.updatedAt)}
            </p>
          </div>
          <div className="flex shrink-0 items-center gap-3">
            <button
              type="button"
              className="ui-pressable rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-medium text-slate-700 shadow-sm"
              onClick={handleOpenOutput}
            >
              打开位置
            </button>
            <div className="flex items-center gap-1 rounded-xl bg-slate-100 p-1">
              {(["setup", "run", "results"] satisfies WorkbenchView[]).map((view) => (
                <button
                  key={view}
                  type="button"
                  className={
                    activeTask.view === view
                      ? "ui-pressable rounded-lg bg-white px-3 py-1.5 text-xs font-semibold uppercase text-slate-900 shadow-sm"
                      : "ui-pressable rounded-lg px-3 py-1.5 text-xs font-semibold uppercase text-slate-500 hover:text-slate-900"
                  }
                  onClick={() => setTaskView(view)}
                >
                  {view}
                </button>
              ))}
            </div>
          </div>
          <div className="hidden" aria-hidden="true">
            <div className="min-w-0">
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-ice-600 dark:text-ice-300">
                JCVI meow · {route.description}
              </p>
              <input
                className="mt-2 w-full min-w-0 bg-transparent text-2xl font-semibold tracking-tight text-text-primary outline-none"
                value=""
                onChange={(event) => updateActiveTask((task) => ({ ...task, title: event.target.value }))}
              />
              <p className="mt-1 text-sm text-text-secondary">
                Created {formatTime(activeTask.createdAt)} · Updated {formatTime(activeTask.updatedAt)}
              </p>
            </div>
            <div className="flex shrink-0 items-center gap-2">
              {(["setup", "run", "results"] satisfies WorkbenchView[]).map((view) => (
                <button
                  key={view}
                  type="button"
                  className={
                    activeTask.view === view
                      ? "rounded-lg bg-ice-500 px-3 py-2 text-xs font-semibold uppercase text-white"
                      : SECONDARY_BUTTON_CLASS
                  }
                  onClick={() => setTaskView(view)}
                >
                  {view}
                </button>
              ))}
            </div>
          </div>
        </header>

        <div className="min-h-0 flex-1 overflow-auto px-14 pb-32 pt-8">
          {activeTask.view === "setup" ? (
            <div className="mx-auto grid w-full max-w-4xl gap-6">
              <section className={PANEL_BODY_CLASS}>
                <SectionTitle
                  title="Inputs and output"
                  subtitle="Choose the data source, output directory, and task-level options for the active task."
                />
                <div className="mt-4 grid gap-4 lg:grid-cols-2">
                  <label>
                    <span className={LABEL_CLASS}>input mode</span>
                    <select
                      className={FIELD_CLASS}
                      value={draft.inputMode}
                      onChange={(event) => patchDraft({ inputMode: event.target.value as AnalysisInputMode })}
                    >
                      <option value="auto_directory">auto_directory</option>
                      <option value="bed_cds">bed_cds</option>
                      <option value="gff_genome">gff_genome</option>
                    </select>
                  </label>
                  <label>
                    <span className={LABEL_CLASS}>workflow</span>
                    <select
                      className={FIELD_CLASS}
                      value={draft.mcscan.workflow}
                      onChange={(event) => patchMcscan({ workflow: event.target.value as McscanWorkflow })}
                    >
                      {WORKFLOW_OPTIONS.map((workflow) => (
                        <option key={workflow} value={workflow}>
                          {workflow}
                        </option>
                      ))}
                    </select>
                  </label>
                </div>

                <div className="mt-4 grid gap-4">
                  <label>
                    <span className={LABEL_CLASS}>input directory</span>
                    <div className="mt-2 flex gap-2">
                      <input
                        className="min-w-0 flex-1 rounded-lg border border-border bg-bg px-3 py-2 text-sm text-text-primary shadow-sm outline-none transition focus:border-ice-400 focus:ring-2 focus:ring-ice-200 dark:focus:ring-ice-900/60"
                        value={draft.directory}
                        onChange={(event) => patchDraft({ directory: event.target.value })}
                        placeholder="Select a workspace or request input directory"
                      />
                      <button type="button" className={SECONDARY_BUTTON_CLASS} onClick={() => pickDirectory((path) => patchDraft({ directory: path }))}>
                        Browse
                      </button>
                    </div>
                    <IssueText issue={directoryIssue} />
                  </label>

                  <label>
                    <span className={LABEL_CLASS}>output directory</span>
                    <div className="mt-2 flex gap-2">
                      <input
                        className="min-w-0 flex-1 rounded-lg border border-border bg-bg px-3 py-2 text-sm text-text-primary shadow-sm outline-none transition focus:border-ice-400 focus:ring-2 focus:ring-ice-200 dark:focus:ring-ice-900/60"
                        value={draft.outputDirectory}
                        onChange={(event) => patchDraft({ outputDirectory: event.target.value })}
                        placeholder="Select where this task should write outputs"
                      />
                      <button
                        type="button"
                        className={SECONDARY_BUTTON_CLASS}
                        onClick={() => pickDirectory((path) => patchDraft({ outputDirectory: path }))}
                      >
                        Browse
                      </button>
                    </div>
                    <IssueText issue={outputIssue} />
                  </label>
                </div>

                <div className="mt-5 rounded-xl border border-slate-200/80 bg-slate-50/80 p-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold text-slate-900">Import request JSON</p>
                      <p className="mt-1 text-sm leading-6 text-slate-500">
                        Attach an existing AnalysisRequest file and run it directly without rebuilding the request from the wizard.
                      </p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <button type="button" className={SECONDARY_BUTTON_CLASS} onClick={handleImportRequestJson}>
                        Import request JSON
                      </button>
                      {usesImportedRequest ? (
                        <button type="button" className={SECONDARY_BUTTON_CLASS} onClick={clearImportedRequest}>
                          Clear imported request
                        </button>
                      ) : null}
                    </div>
                  </div>

                  {usesImportedRequest ? (
                    <div className="mt-4 grid gap-2 rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-600">
                      <InfoRow label="source" value="Imported request JSON" />
                      <InfoRow label="request" value={importedRequest?.path ?? "-"} />
                      <InfoRow label="method" value={importedRequest?.method ?? "-"} />
                      <InfoRow label="workflow" value={importedRequest?.workflow ?? "-"} />
                      <InfoRow label="mode" value={importedRequest?.inputMode ?? "-"} />
                      <InfoRow
                        label="request outdir"
                        value={importedRequest?.requestOutputDirectory || "Not declared in imported JSON"}
                      />
                      <p className="pt-1 text-xs leading-5 text-slate-500">
                        Run uses the imported request path above and the current task output directory shown in this panel.
                      </p>
                    </div>
                  ) : (
                    <p className="mt-4 text-sm text-slate-500">
                      No imported request is attached. The current wizard draft still generates the request JSON for this task.
                    </p>
                  )}
                </div>
              </section>

              {draft.inputMode !== "auto_directory" ? (
                <section className={PANEL_BODY_CLASS}>
                  <div className="flex items-start justify-between gap-3">
                    <SectionTitle
                      title="Species inputs"
                      subtitle="Explicit species mode is available for workflows that do not use auto_directory."
                    />
                    <button type="button" className={SECONDARY_BUTTON_CLASS} onClick={addSpecies}>
                      Add species
                    </button>
                  </div>
                  <div className="mt-4 grid gap-3">
                    {draft.species.map((species, index) => (
                      <div key={index} className="rounded-lg border border-border bg-bg p-3">
                        <div className="flex items-start justify-between gap-3">
                          <label className="min-w-0 flex-1">
                            <span className={LABEL_CLASS}>species name</span>
                            <input
                              className={FIELD_CLASS}
                              value={species.name}
                              onChange={(event) => updateSpecies(index, { name: event.target.value })}
                            />
                          </label>
                          <button type="button" className={SECONDARY_BUTTON_CLASS} onClick={() => removeSpecies(index)}>
                            Remove
                          </button>
                        </div>
                        {species.inputMode === "bed_cds" ? (
                          <div className="mt-3 grid gap-3 lg:grid-cols-2">
                            <PathField label="BED" value={species.bed} onChange={(path) => updateSpecies(index, { bed: path })} pickFile={pickFile} />
                            <PathField label="CDS" value={species.cds} onChange={(path) => updateSpecies(index, { cds: path })} pickFile={pickFile} />
                          </div>
                        ) : (
                          <div className="mt-3 grid gap-3 lg:grid-cols-2">
                            <PathField label="GFF" value={species.gff} onChange={(path) => updateSpecies(index, { gff: path })} pickFile={pickFile} />
                            <PathField
                              label="Genome"
                              value={species.genome}
                              onChange={(path) => updateSpecies(index, { genome: path })}
                              pickFile={pickFile}
                            />
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </section>
              ) : null}

              <section className={PANEL_BODY_CLASS}>
                <SectionTitle title="Analysis options" subtitle="Keep transport fields aligned with the GenomeLens request contract." />
                <div className="mt-4 grid gap-4 lg:grid-cols-3">
                  <label>
                    <span className={LABEL_CLASS}>threads</span>
                    <input
                      className={FIELD_CLASS}
                      type="number"
                      min={1}
                      value={draft.options.threads ?? ""}
                      onChange={(event) => patchOptions({ threads: updateNumber(event.target.value) })}
                    />
                    <IssueText issue={threadsIssue} />
                  </label>
                  <label>
                    <span className={LABEL_CLASS}>min block size</span>
                    <input
                      className={FIELD_CLASS}
                      type="number"
                      min={1}
                      value={draft.options.minBlockSize ?? ""}
                      onChange={(event) => patchOptions({ minBlockSize: updateNumber(event.target.value) })}
                    />
                    <IssueText issue={minBlockIssue} />
                  </label>
                  <label>
                    <span className={LABEL_CLASS}>log level</span>
                    <select
                      className={FIELD_CLASS}
                      value={draft.options.logLevel}
                      onChange={(event) => patchOptions({ logLevel: event.target.value as LogLevel })}
                    >
                      {LOG_LEVELS.map((level) => (
                        <option key={level} value={level}>
                          {level}
                        </option>
                      ))}
                    </select>
                  </label>
                </div>

                <div className="mt-5 flex flex-wrap gap-4">
                  {FORMAT_OPTIONS.map((format) => (
                    <label key={format} className="inline-flex items-center gap-2 text-sm font-medium text-text-secondary">
                      <input
                        className={CHECKBOX_CLASS}
                        type="checkbox"
                        checked={draft.formats.includes(format)}
                        onChange={() => toggleFormat(format)}
                      />
                      {format}
                    </label>
                  ))}
                  {[
                    ["forceOutput", "force output"],
                    ["verbose", "verbose"],
                    ["consoleLog", "console log"],
                  ].map(([key, label]) => (
                    <label key={key} className="inline-flex items-center gap-2 text-sm font-medium text-text-secondary">
                      <input
                        className={CHECKBOX_CLASS}
                        type="checkbox"
                        checked={
                          key === "forceOutput"
                            ? draft.forceOutput
                            : key === "verbose"
                              ? draft.options.verbose
                              : draft.options.consoleLog
                        }
                        onChange={(event) => {
                          if (key === "forceOutput") {
                            patchDraft({ forceOutput: event.target.checked });
                          } else if (key === "verbose") {
                            patchOptions({ verbose: event.target.checked });
                          } else {
                            patchOptions({ consoleLog: event.target.checked });
                          }
                        }}
                      />
                      {label}
                    </label>
                  ))}
                </div>
              </section>

              <section className={PANEL_BODY_CLASS}>
                <SectionTitle title="MCSCAN parameters" subtitle="Advanced options remain task-local and can diverge per task." />
                <div className="mt-4 grid gap-4 lg:grid-cols-3">
                  <label>
                    <span className={LABEL_CLASS}>align_soft</span>
                    <select
                      className={FIELD_CLASS}
                      value={draft.mcscan.alignSoft}
                      onChange={(event) => patchMcscan({ alignSoft: event.target.value as AlignSoft })}
                    >
                      <option value="blast">blast</option>
                      <option value="last">last</option>
                      <option value="diamond_blastp">diamond_blastp</option>
                    </select>
                  </label>
                  <label>
                    <span className={LABEL_CLASS}>dbtype</span>
                    <select
                      className={FIELD_CLASS}
                      value={draft.mcscan.dbtype}
                      onChange={(event) => patchMcscan({ dbtype: event.target.value as DbType })}
                    >
                      <option value="nucl">nucl</option>
                      <option value="prot">prot</option>
                    </select>
                  </label>
                  <label>
                    <span className={LABEL_CLASS}>figsize</span>
                    <input className={FIELD_CLASS} value={draft.mcscan.figsize} onChange={(event) => patchMcscan({ figsize: event.target.value })} />
                  </label>
                  {MCSCAN_NUMBER_FIELDS.map(({ key, label, min, max, step }) => (
                    <label key={key}>
                      <span className={LABEL_CLASS}>{label}</span>
                      <input
                        className={FIELD_CLASS}
                        type="number"
                        min={min}
                        max={max}
                        step={step}
                        value={draft.mcscan[key]}
                        onChange={(event) => patchMcscan({ [key]: Number(event.target.value) })}
                      />
                    </label>
                  ))}
                </div>

                <label className="mt-4 block">
                  <span className={LABEL_CLASS}>target_gene_ids</span>
                  <textarea
                    className={`${FIELD_CLASS} min-h-24`}
                    value={targetGeneText}
                    onChange={(event) => patchMcscan({ targetGeneIds: splitTargets(event.target.value) })}
                    placeholder="One gene id per line, or comma-separated"
                  />
                  <IssueText issue={issueFor(validation.issues, "method_config.target_gene_ids")} />
                </label>

                <div className="mt-5 grid gap-3 lg:grid-cols-2">
                  {[
                    ["allowSimplifiedFallback", "allow_simplified_fallback"],
                    ["splitTargets", "split_targets"],
                    ["labelTargets", "label_targets"],
                    ["optimizeFigsize", "optimize_figsize"],
                    ["rewriteLayoutLinks", "rewrite_layout_links"],
                    ["trimCrossChromosomeBlocks", "trim_cross_chromosome_blocks"],
                  ].map(([key, label]) => (
                    <label key={key} className="inline-flex items-center gap-2 text-sm font-medium text-text-secondary">
                      <input
                        className={CHECKBOX_CLASS}
                        type="checkbox"
                        checked={draft.mcscan[key as keyof AnalysisRequestDraft["mcscan"]] as boolean}
                        onChange={(event) => patchMcscan({ [key]: event.target.checked } as Partial<AnalysisRequestDraft["mcscan"]>)}
                      />
                      {label}
                    </label>
                  ))}
                </div>
              </section>
            </div>
          ) : null}

          {activeTask.view === "run" ? (
            <div className="mx-auto grid w-full max-w-4xl gap-6">
              <section className={PANEL_BODY_CLASS}>
                <SectionTitle title="Run control" subtitle="One task maps to one request file and one GenomeLens run." />
                {usesImportedRequest ? (
                  <div className="mt-4 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
                    <p className="font-medium text-slate-900">Imported request attached</p>
                    <p className="mt-1 break-all font-mono text-xs leading-6 text-slate-500">{importedRequest?.path ?? "-"}</p>
                    <p className="mt-2 text-xs leading-5 text-slate-500">
                      This run will use the imported request file directly. Current task outdir: {draft.outputDirectory || "-"}.
                    </p>
                  </div>
                ) : null}
                <div className="mt-4 flex flex-wrap items-center gap-3">
                  <button
                    type="button"
                    className={PRIMARY_BUTTON_CLASS}
                    disabled={activeTask.runStatus === "starting" || activeTask.runStatus === "running"}
                    onClick={handlePrepareRun}
                  >
                    Run active task
                  </button>
                  <button type="button" className={SECONDARY_BUTTON_CLASS} onClick={handleReadLog}>
                    Refresh log
                  </button>
                  <button type="button" className={SECONDARY_BUTTON_CLASS} onClick={handleReadSummary}>
                    Read summary
                  </button>
                  <button type="button" className={SECONDARY_BUTTON_CLASS} disabled={!resolvedLogPath} onClick={handleOpenLog}>
                    Open log
                  </button>
                  <button
                    type="button"
                    className={SECONDARY_BUTTON_CLASS}
                    disabled={!resolvedSummaryPath}
                    onClick={handleOpenSummary}
                  >
                    Open summary
                  </button>
                  <button type="button" className={SECONDARY_BUTTON_CLASS} onClick={handleOpenOutput}>
                    Open output
                  </button>
                </div>

                <div className="mt-5 grid gap-3 rounded-lg border border-border bg-bg p-4">
                  <div className="flex items-center justify-between gap-3">
                    <span className="text-xs font-semibold uppercase tracking-[0.14em] text-text-tertiary">status</span>
                    <span className={`rounded-full px-3 py-1 text-xs font-semibold uppercase ${statusTone(activeTask.runStatus)}`}>
                      {activeTask.runStatus} / {workflowState}
                    </span>
                  </div>
                  <div className="h-2 overflow-hidden rounded-full bg-ice-100 dark:bg-ice-900/40">
                    <div
                      className={[
                        "h-full rounded-full bg-ice-500 transition-all",
                        activeTask.runStatus === "starting" || activeTask.runStatus === "running" ? "ui-running-progress" : "",
                      ].join(" ")}
                      style={{ width: `${Math.max(0, Math.min(progress, 100))}%` }}
                    />
                  </div>
                  {activeTask.runState ? (
                    <div className="grid gap-2 font-mono text-xs text-text-tertiary">
                      <span>runId: {activeTask.runState.runId}</span>
                      <span>pid: {activeTask.runState.pid ?? "-"}</span>
                      <span>outdir: {activeTask.runState.outdir}</span>
                      <span>exitCode: {activeTask.runState.exitCode ?? "-"}</span>
                      <span>logPath: {resolvedLogPath || "-"}</span>
                      <span>summaryPath: {resolvedSummaryPath || "-"}</span>
                    </div>
                  ) : null}
                  {activeTask.runError ? (
                    <p className="text-sm font-medium text-rose-600 dark:text-rose-300">{activeTask.runError}</p>
                  ) : null}
                </div>
              </section>

              {activeTask.runStatus === "confirming" ? (
                <section className="ui-surface-enter rounded-lg border border-amber-200 bg-amber-50 p-4 dark:border-amber-900/40 dark:bg-amber-950/20">
                  <h3 className="text-sm font-semibold text-text-primary">Confirm AnalysisRequest JSON</h3>
                  <div className="mt-3 grid gap-2 rounded-lg border border-amber-200/80 bg-white/80 px-3 py-3 text-sm text-slate-600">
                    <InfoRow label="source" value={usesImportedRequest ? "Imported request JSON" : "Generated from active draft"} />
                    {usesImportedRequest ? (
                      <>
                        <InfoRow label="request" value={importedRequest?.path ?? "-"} />
                        <InfoRow label="mode" value={importedRequest?.inputMode ?? "-"} />
                        <InfoRow label="workflow" value={importedRequest?.workflow ?? "-"} />
                      </>
                    ) : (
                      <InfoRow label="workflow" value={draft.mcscan.workflow} />
                    )}
                    <InfoRow label="outdir" value={draft.outputDirectory || "-"} />
                  </div>
                  <pre className="mt-3 max-h-72 overflow-auto rounded-lg border border-border bg-bg p-3 font-mono text-xs leading-6 text-text-secondary">
                    {activeTask.pendingRequestJson}
                  </pre>
                  <div className="mt-3 flex gap-2">
                    <button type="button" className={PRIMARY_BUTTON_CLASS} onClick={handleConfirmRun}>
                      Confirm run
                    </button>
                    <button type="button" className={SECONDARY_BUTTON_CLASS} onClick={() => updateActiveTask((task) => ({ ...task, runStatus: "idle" }))}>
                      Cancel
                    </button>
                  </div>
                </section>
              ) : null}

              <section className={PANEL_BODY_CLASS}>
                <SectionTitle title="Live log" subtitle="Stable run.log lines are streamed into this task context." />
                <div className="mt-4 max-h-[30rem] overflow-auto rounded-lg border border-border bg-bg p-4 font-mono text-xs leading-6 text-text-secondary">
                  {logLines.length > 0 ? (
                    <div className="grid gap-1">
                      {logLines.map((line, index) => (
                        <div key={`${index}-${line}`} className="ui-log-line whitespace-pre-wrap break-words">
                          {line}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-text-secondary">Waiting for analysis:stdout or read_run_log().</div>
                  )}
                </div>
              </section>
            </div>
          ) : null}

          {activeTask.view === "results" ? (
            <div className="mx-auto grid w-full max-w-4xl gap-6">
              <section className={PANEL_BODY_CLASS}>
                <SectionTitle title="Results" subtitle="Read run_summary.json for the active task." />
                {summaryView ? (
                  <div className="mt-4 grid gap-4">
                    <div className="grid gap-2 rounded-lg border border-border bg-bg p-4 text-sm text-text-secondary">
                      <div className="flex justify-between gap-3">
                        <span>status</span>
                        <span className="font-semibold text-text-primary">{summaryView.status}</span>
                      </div>
                      <div className="flex justify-between gap-3">
                        <span>workflow</span>
                        <span className="font-semibold text-text-primary">{summaryView.workflow}</span>
                      </div>
                      <div className="flex justify-between gap-3">
                        <span>progress</span>
                        <span className="font-semibold text-text-primary">{toProgressPercent(summaryView.progress)}%</span>
                      </div>
                    </div>
                    <div>
                      <h3 className="text-sm font-semibold text-text-primary">Figure assets</h3>
                      <div className="mt-3 grid gap-2">
                        {summaryView.figureAssets.length > 0 ? (
                          summaryView.figureAssets.slice(0, 12).map((asset) => (
                            <div key={asset.path} className="ui-surface-enter rounded-lg border border-border bg-bg p-3">
                              <p className="text-sm font-semibold text-text-primary">{asset.name}</p>
                              <p className="mt-1 break-all font-mono text-xs text-text-tertiary">{asset.path}</p>
                            </div>
                          ))
                        ) : (
                          <p className="rounded-lg border border-border bg-bg p-3 text-sm text-text-secondary">
                            No figure assets listed in summary yet.
                          </p>
                        )}
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="mt-4 rounded-lg border border-border bg-bg p-4">
                    <p className="text-sm text-text-secondary">No summary loaded for this task.</p>
                    <button type="button" className={`${PRIMARY_BUTTON_CLASS} mt-4`} onClick={handleReadSummary}>
                      Read summary
                    </button>
                  </div>
                )}
              </section>

              <section className={PANEL_BODY_CLASS}>
                <SectionTitle
                  title="Request JSON"
                  subtitle={
                    usesImportedRequest
                      ? "Preview of the imported request file used by this task."
                      : "Current task request preview generated from the active draft."
                  }
                />
                <div className="mt-4 grid gap-2 rounded-lg border border-border bg-bg px-4 py-3 text-sm text-text-secondary">
                  <InfoRow label="source" value={usesImportedRequest ? "Imported request JSON" : "Generated draft"} />
                  {usesImportedRequest ? (
                    <>
                      <InfoRow label="request" value={importedRequest?.path ?? "-"} />
                      <InfoRow label="mode" value={importedRequest?.inputMode ?? "-"} />
                      <InfoRow label="workflow" value={importedRequest?.workflow ?? "-"} />
                    </>
                  ) : (
                    <InfoRow label="workflow" value={draft.mcscan.workflow} />
                  )}
                </div>
                <pre className="mt-4 max-h-[28rem] overflow-auto rounded-lg border border-border bg-bg p-4 font-mono text-xs leading-6 text-text-secondary">
                  {requestPreviewJson}
                </pre>
              </section>
            </div>
          ) : null}
        </div>

        <div className="pointer-events-none border-t border-slate-200/80 bg-white px-14 py-5">
          <div className="ui-surface-enter pointer-events-auto mx-auto flex max-w-4xl items-center gap-3 rounded-[1.1rem] border border-slate-200 bg-white px-4 py-3 shadow-[0_6px_20px_rgba(15,23,42,0.06)]">
            <button type="button" className="ui-pressable text-2xl leading-none text-slate-400 hover:text-slate-700" onClick={() => createTask()}>
              +
            </button>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm text-slate-500">
                {activeTask.title} · {draft.mcscan.workflow} · {validation.issues.length === 0 ? "ready" : `${validation.issues.length} issue(s)`}
              </p>
            </div>
            <button
              type="button"
              className="ui-pressable rounded-xl border border-slate-200 px-3 py-2 text-xs font-medium text-slate-700 hover:bg-slate-50"
              onClick={() => setTaskView("setup")}
            >
              setup
            </button>
            <button
              type="button"
              className="ui-pressable rounded-xl border border-slate-200 px-3 py-2 text-xs font-medium text-slate-700 hover:bg-slate-50"
              onClick={() => setTaskView("results")}
            >
              results
            </button>
            <button
              type="button"
              className={[
                "ui-pressable rounded-full bg-slate-900 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-50",
                activeTask.runStatus === "starting" || activeTask.runStatus === "running" ? "ui-running-progress" : "",
              ].join(" ")}
              disabled={activeTask.runStatus === "starting" || activeTask.runStatus === "running"}
              onClick={handlePrepareRun}
            >
              Run
            </button>
          </div>
        </div>
      </main>

      <aside className="min-h-0 overflow-hidden border-l border-slate-100 bg-white px-5 py-16">
        <div className="max-h-[calc(100vh-6rem)] overflow-auto">
        <div className="border-b border-slate-100 pb-5">
          <p className="text-base font-medium text-slate-500">环境信息</p>
          <h2 className="sr-only">Environment</h2>
        </div>
        <div className="pt-5">
          <section>
            <div className="flex items-center justify-between gap-3">
              <h3 className="text-sm font-medium text-slate-900">变更</h3>
              <button type="button" className="ui-pressable rounded-lg px-2 py-1 text-xl leading-none text-slate-400 hover:bg-slate-100 hover:text-slate-700" onClick={() => onNavigate("/settings")}>
                +
              </button>
            </div>
            <button type="button" className="ui-list-item mt-3 flex w-full items-center gap-3 rounded-lg px-2 py-2 text-left text-sm text-slate-700 hover:bg-slate-50" onClick={() => onNavigate("/settings")}>
              <GameIcon name="environment" className="h-4 w-4" />
              环境诊断
            </button>
            <button type="button" className="ui-list-item flex w-full items-center gap-3 rounded-lg px-2 py-2 text-left text-sm text-slate-700 hover:bg-slate-50" onClick={handleOpenOutput}>
              <GameIcon name="local" className="h-4 w-4" />
              工作树
            </button>
            <button type="button" className="ui-list-item flex w-full items-center gap-3 rounded-lg px-2 py-2 text-left text-sm text-slate-700 hover:bg-slate-50" onClick={handlePrepareRun}>
              <GameIcon name="pairwise" className="h-4 w-4" />
              提交或推送
            </button>
            <div className="mt-3 hidden">
              <button type="button" className={SECONDARY_BUTTON_CLASS} onClick={() => onNavigate("/settings")}>
                Check
              </button>
            </div>
            <div className="mt-4 grid gap-2 text-sm text-text-secondary">
              <InfoRow label="workflow" value={draft.mcscan.workflow} />
              <InfoRow label="input" value={draft.directory || "-"} />
              <InfoRow label="output" value={draft.outputDirectory || "-"} />
              <InfoRow label="request" value={usesImportedRequest ? "imported" : "draft"} />
              <InfoRow label="issues" value={String(validation.issues.length)} />
            </div>
          </section>

          <section className="mt-5 border-t border-slate-100 pt-5">
            <h3 className="text-sm font-medium text-slate-900">工作树</h3>
            <div className="mt-3 grid gap-2 text-sm text-text-secondary">
              <InfoRow label="status" value={activeTask.runStatus} />
              <InfoRow label="state" value={workflowState} />
              <InfoRow label="progress" value={`${Math.round(progress)}%`} />
              <InfoRow label="runId" value={activeTask.runState?.runId ?? "-"} />
            </div>
          </section>

          <section className="mt-5 border-t border-slate-100 pt-5">
            <h3 className="text-sm font-medium text-slate-900">最近日志</h3>
            <div className="mt-3 grid gap-2">
              {recentEvents.length > 0 ? (
                recentEvents.map((line, index) => (
                  <div key={`${index}-${line}`} className="ui-log-line rounded-lg px-2 py-1.5 font-mono text-[11px] leading-5 text-slate-500">
                    {line}
                  </div>
                ))
              ) : (
                <p className="rounded-lg px-2 py-1.5 text-sm text-slate-500">
                  Run events will appear here.
                </p>
              )}
            </div>
          </section>

          <section className="mt-5 border-t border-slate-100 pt-5">
            <h3 className="text-sm font-medium text-slate-900">来源</h3>
            <div className="mt-3 flex flex-wrap gap-2">
              <span className="rounded-full bg-slate-100 px-3 py-1 text-xs text-slate-600">GenomeLens CLI</span>
              <span className="rounded-full bg-slate-100 px-3 py-1 text-xs text-slate-600">JCVI engine</span>
              <span className="rounded-full bg-slate-100 px-3 py-1 text-xs text-slate-600">run.log</span>
            </div>
          </section>

          <section className="mt-5 border-t border-slate-100 pt-5">
            <SectionTitle title="Schema" subtitle="get_analysis_schema()" />
            <pre className="mt-3 max-h-52 overflow-auto rounded-lg bg-slate-50 p-3 font-mono text-[11px] leading-5 text-slate-500">
              {schemaJson || "Schema not loaded."}
            </pre>
          </section>
        </div>
        </div>
      </aside>
    </div>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="grid grid-cols-[5rem_minmax(0,1fr)] gap-3 rounded-lg px-2 py-1.5">
      <span className="text-xs font-medium text-slate-400">{label}</span>
      <span className="truncate font-mono text-xs text-slate-600" title={value}>
        {value}
      </span>
    </div>
  );
}

function PathField({
  label,
  value,
  onChange,
  pickFile,
}: {
  label: string;
  value: string;
  onChange: (path: string) => void;
  pickFile: (onSelect: (path: string) => void) => Promise<void>;
}) {
  return (
    <label>
      <span className={LABEL_CLASS}>{label}</span>
      <div className="mt-2 flex gap-2">
        <input
          className="min-w-0 flex-1 rounded-lg border border-border bg-bg px-3 py-2 text-sm text-text-primary shadow-sm outline-none transition focus:border-ice-400 focus:ring-2 focus:ring-ice-200 dark:focus:ring-ice-900/60"
          value={value}
          onChange={(event) => onChange(event.target.value)}
        />
        <button type="button" className={SECONDARY_BUTTON_CLASS} onClick={() => void pickFile(onChange)}>
          Browse
        </button>
      </div>
    </label>
  );
}
