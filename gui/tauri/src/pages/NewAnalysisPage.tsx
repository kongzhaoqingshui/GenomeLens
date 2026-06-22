import { open } from "@tauri-apps/plugin-dialog";
import { mkdir, writeTextFile } from "@tauri-apps/plugin-fs";
import { useEffect, useMemo, useState } from "react";

import { GameIcon, type GameIconName } from "../components/GameIcon";
import { useLanguage } from "../i18n/useLanguage";
import type {
  AlignSoft,
  AnalysisInputMode,
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
  type WorkflowState,
} from "../models/run-session";
import { validateAnalysisRequestDraft, type ValidationIssue } from "../models/validation";
import type { AppRoute } from "../routes/routes";
import { getAnalysisSchema, getTemplateDraft, readRequestPreview, type JsonObject } from "../services/analysis";
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

interface RecentRequestHint {
  path: string;
  method?: string;
  workflow?: string;
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
const RECENT_OUTDIRS_KEY = "genomelens.gui.recentOutdirs";
const RECENT_REQUESTS_KEY = "genomelens.gui.recentRequests";
const RECENT_HINT_LIMIT = 4;

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

function parseImportedRequest(preview: {
  requestPath: string;
  json: Record<string, unknown> | unknown;
  method?: string;
  workflow?: string;
}): ImportedRequestState {
  const root = asObject(preview.json);
  if (!root) {
    throw new Error("Imported request must be a JSON object.");
  }

  const input = asObject(root.input);
  const output = asObject(root.output);
  const methodConfig = asObject(root.method_config);

  return {
    path: preview.requestPath,
    json: stringifyJson(preview.json),
    method: preview.method ?? (typeof root.method === "string" ? root.method : "unknown"),
    workflow: preview.workflow ?? (typeof methodConfig?.workflow === "string" ? methodConfig.workflow : "unknown"),
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

function readStoredJson<T>(key: string, fallback: T): T {
  try {
    const raw = window.localStorage.getItem(key);
    if (!raw) {
      return fallback;
    }
    return JSON.parse(raw) as T;
  } catch {
    return fallback;
  }
}

function writeStoredJson(key: string, value: unknown) {
  try {
    window.localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // Ignore local-only persistence failures.
  }
}

function rememberRecentText(items: string[], nextValue: string): string[] {
  const value = nextValue.trim();
  if (!value) {
    return items;
  }
  return [value, ...items.filter((item) => item !== value)].slice(0, RECENT_HINT_LIMIT);
}

function rememberRecentRequest(items: RecentRequestHint[], nextValue: RecentRequestHint): RecentRequestHint[] {
  const path = nextValue.path.trim();
  if (!path) {
    return items;
  }

  return [{ ...nextValue, path }, ...items.filter((item) => item.path !== path)].slice(0, RECENT_HINT_LIMIT);
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

function localizeWorkflowState(state: WorkflowState, language: "zh-CN" | "en"): string {
  if (language === "en") {
    return state;
  }

  switch (state) {
    case "PENDING":
      return "等待中";
    case "VALIDATING_INPUTS":
      return "校验输入";
    case "PREPROCESSING_ANNOTATIONS":
      return "预处理注释";
    case "PREPARING_WORKSPACE":
      return "准备工作区";
    case "CHECKING_TOOLCHAIN":
      return "检查工具链";
    case "WRITING_MANIFEST":
      return "写入清单";
    case "RUNNING_ENGINE":
      return "运行引擎";
    case "PARSING_ENGINE_SUMMARY":
      return "解析引擎摘要";
    case "FINALIZING":
      return "收尾整理";
    case "SUCCEEDED":
      return "已完成";
    case "FAILED":
      return "失败";
    case "CANCELLED":
      return "已取消";
    default:
      return state;
  }
}

function localizeRunPrompt(
  key: "importedRequestOutdir" | "draftOutdir" | "validationErrors",
  language: "zh-CN" | "en",
): string {
  if (language === "en") {
    switch (key) {
      case "importedRequestOutdir":
        return "Choose an output directory before running an imported request.";
      case "draftOutdir":
        return "Choose an output directory before generating a request JSON.";
      case "validationErrors":
        return "Please fix validation errors before running this task.";
      default:
        return "";
    }
  }

  switch (key) {
    case "importedRequestOutdir":
      return "运行导入的 request 前，请先选择输出目录。";
    case "draftOutdir":
      return "生成 request JSON 前，请先选择输出目录。";
    case "validationErrors":
      return "运行当前任务前，请先修复校验问题。";
    default:
      return "";
  }
}

export default function NewAnalysisPage({ route, onNavigate, locationHash }: NewAnalysisPageProps) {
  const { language } = useLanguage();
  const isZh = language === "zh-CN";
  const [templateDraft, setTemplateDraft] = useState<AnalysisRequestDraft | null>(null);
  const [schema, setSchema] = useState<JsonObject | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [tasks, setTasks] = useState<WorkbenchTask[]>([]);
  const [activeTaskId, setActiveTaskId] = useState("");
  const [taskCounter, setTaskCounter] = useState(1);
  const [taskFilter, setTaskFilter] = useState("");
  const [recentOutdirs, setRecentOutdirs] = useState<string[]>(() => readStoredJson<string[]>(RECENT_OUTDIRS_KEY, []));
  const [recentRequests, setRecentRequests] = useState<RecentRequestHint[]>(() =>
    readStoredJson<RecentRequestHint[]>(RECENT_REQUESTS_KEY, []),
  );
  const capabilityId = useMemo(() => readCapabilityFromHash(locationHash), [locationHash]);

  useEffect(() => {
    writeStoredJson(RECENT_OUTDIRS_KEY, recentOutdirs);
  }, [recentOutdirs]);

  useEffect(() => {
    writeStoredJson(RECENT_REQUESTS_KEY, recentRequests);
  }, [recentRequests]);

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

  async function attachImportedRequest(requestPath: string) {
    const preview = await readRequestPreview({ requestPath });
    const nextImportedRequest = parseImportedRequest(preview);
    setRecentRequests((current) =>
      rememberRecentRequest(current, {
        path: nextImportedRequest.path,
        method: nextImportedRequest.method,
        workflow: nextImportedRequest.workflow,
      }),
    );
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
      await attachImportedRequest(selected);
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
          runError: localizeRunPrompt("importedRequestOutdir", language),
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
        runError: localizeRunPrompt("validationErrors", language),
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
          ? localizeRunPrompt("importedRequestOutdir", language)
          : localizeRunPrompt("draftOutdir", language),
        view: "setup",
      }));
      return;
    }

    const request = imported ? null : draftToAnalysisRequest(activeTask.draft);
    const json = imported?.json ?? (request ? stringifyJson(request) : "");
    const requestPath = imported ? imported.path : joinPath(outdir, `genomelens-request-${timestampForFilename()}.json`);

    updateTask(taskId, (task) => ({ ...task, runStatus: "starting", runError: null, runState: null, view: "run" }));

    try {
      setRecentOutdirs((current) => rememberRecentText(current, outdir));
      if (imported) {
        setRecentRequests((current) =>
          rememberRecentRequest(current, {
            path: imported.path,
            method: imported.method,
            workflow: imported.workflow,
          }),
        );
      }
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
        <h1 className="text-2xl font-semibold text-slate-900">{isZh ? "正在准备多任务工作台" : "Preparing multi-task workbench"}</h1>
        <p className="text-sm text-slate-500">{isZh ? "正在加载模板与分析 schema..." : "Loading template and analysis schema..."}</p>
      </section>
    );
  }

  if (loadError || !activeTask || !draft || validation === null) {
    return (
      <section className="ui-page-enter grid h-screen w-full content-center justify-center gap-4 bg-[#f4fbfd] text-center">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-400">
          JCVI meow · {route.description}
        </p>
        <h1 className="text-2xl font-semibold text-slate-900">{isZh ? "工作台初始化失败" : "Workbench failed to initialize"}</h1>
        <p className="max-w-2xl rounded-[1.35rem] border border-rose-200 bg-rose-50 p-4 text-left text-sm text-rose-700">
          {loadError ?? (isZh ? "无法初始化 AnalysisRequestDraft。" : "Unable to initialize AnalysisRequestDraft.")}
        </p>
      </section>
    );
  }

  const directoryIssue = issueFor(validation.issues, "input.directory");
  const outputIssue = issueFor(validation.issues, "output.directory");
  const threadsIssue = issueFor(validation.issues, "options.threads");
  const minBlockIssue = issueFor(validation.issues, "options.min_block_size");
  const workflowState = activeTask.runState?.status ?? "PENDING";
  const workflowStateLabel = localizeWorkflowState(workflowState, language);
  const progress = toProgressPercent(activeTask.runState?.progress ?? 0);
  const logLines = activeTask.runState?.logLines ?? [];
  const summaryView = activeTask.runState?.summaryView ?? null;
  const resolvedLogPath = activeTask.runState?.logPath ?? summaryView?.runLogPath ?? "";
  const resolvedSummaryPath = activeTask.runState?.summaryPath ?? summaryView?.runSummaryPath ?? "";
  const recentEvents = logLines.slice(-6).reverse();
  const usesImportedRequest = importedRequest !== null;
  const requestWorkflow = usesImportedRequest ? importedRequest?.workflow ?? draft.mcscan.workflow : draft.mcscan.workflow;
  const requestMode = usesImportedRequest ? importedRequest?.inputMode ?? draft.inputMode : draft.inputMode;
  const requestSourceLabel = usesImportedRequest
    ? isZh
      ? "导入的请求 JSON"
      : "Imported request JSON"
    : isZh
      ? "当前草稿生成"
      : "Generated draft";
  const requestSourcePath = usesImportedRequest
    ? importedRequest?.path ?? "-"
    : isZh
      ? "会写入所选输出目录"
      : "Will be written into the selected outdir";
  const runStatusLabel =
    activeTask.runStatus === "starting"
      ? isZh
        ? "正在启动"
        : "Starting run"
      : activeTask.runStatus === "running"
        ? isZh
          ? "运行中"
          : "Running analysis"
        : activeTask.runStatus === "finished"
          ? isZh
            ? "运行完成"
            : "Run finished"
          : activeTask.runStatus === "error"
            ? isZh
              ? "需要处理"
              : "Attention needed"
            : activeTask.runStatus === "confirming"
              ? isZh
                ? "确认请求"
                : "Confirm request"
              : isZh
                ? "准备运行"
                : "Ready to run";
  const runHint =
    activeTask.runStatus === "starting" || activeTask.runStatus === "running"
      ? isZh
        ? "GenomeLens 正在把 run.log 更新持续写入当前任务。"
        : "GenomeLens is streaming run.log updates into this task."
      : activeTask.runStatus === "finished"
        ? isZh
          ? "下方与结果页都可以继续查看 summary 元数据。"
          : "Summary metadata is available below and in Results."
        : usesImportedRequest
          ? isZh
            ? "本次运行会直接使用导入的 request 路径，并配合当前任务的输出目录。"
            : "Run uses the imported request path plus the current task output directory."
          : validation.issues.length === 0
            ? isZh
              ? "草稿校验已通过，确认请求预览后即可运行。"
              : "Draft validation is clean. Review the request preview, then run."
            : isZh
              ? `仍有 ${validation.issues.length} 个校验问题，生成 request 前需要先处理。`
              : `${validation.issues.length} validation issue(s) still need attention before generating a request.`;
  const summaryFigureCount = summaryView?.figureAssets.length ?? 0;
  const summaryArtifactCount = summaryView?.artifactIndex.length ?? 0;

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
              <h2 className="mt-4 text-sm font-semibold text-slate-500">{isZh ? "任务" : "Tasks"}</h2>
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
              {isZh ? "创建于" : "Created"} {formatTime(activeTask.createdAt)} · {isZh ? "更新于" : "Updated"} {formatTime(activeTask.updatedAt)}
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
                  {view === "setup" ? (isZh ? "配置" : "setup") : view === "run" ? (isZh ? "运行" : "run") : isZh ? "结果" : "results"}
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
                  title={isZh ? "输入与输出" : "Inputs and output"}
                  subtitle={
                    isZh
                      ? "为当前任务选择数据来源、输出目录和任务级选项。"
                      : "Choose the data source, output directory, and task-level options for the active task."
                  }
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
                    <span className={LABEL_CLASS}>{isZh ? "输入目录" : "input directory"}</span>
                    <div className="mt-2 flex gap-2">
                      <input
                        className="min-w-0 flex-1 rounded-lg border border-border bg-bg px-3 py-2 text-sm text-text-primary shadow-sm outline-none transition focus:border-ice-400 focus:ring-2 focus:ring-ice-200 dark:focus:ring-ice-900/60"
                        value={draft.directory}
                        onChange={(event) => patchDraft({ directory: event.target.value })}
                        placeholder={isZh ? "选择工作区或 request 输入目录" : "Select a workspace or request input directory"}
                      />
                      <button type="button" className={SECONDARY_BUTTON_CLASS} onClick={() => pickDirectory((path) => patchDraft({ directory: path }))}>
                        Browse
                      </button>
                    </div>
                    <IssueText issue={directoryIssue} />
                  </label>

                  <label>
                    <span className={LABEL_CLASS}>{isZh ? "输出目录" : "output directory"}</span>
                    <div className="mt-2 flex gap-2">
                      <input
                        className="min-w-0 flex-1 rounded-lg border border-border bg-bg px-3 py-2 text-sm text-text-primary shadow-sm outline-none transition focus:border-ice-400 focus:ring-2 focus:ring-ice-200 dark:focus:ring-ice-900/60"
                        value={draft.outputDirectory}
                        onChange={(event) => patchDraft({ outputDirectory: event.target.value })}
                        placeholder={isZh ? "选择当前任务的输出位置" : "Select where this task should write outputs"}
                      />
                      <button
                        type="button"
                        className={SECONDARY_BUTTON_CLASS}
                        onClick={() => pickDirectory((path) => patchDraft({ outputDirectory: path }))}
                      >
                        {isZh ? "浏览" : "Browse"}
                      </button>
                    </div>
                    {recentOutdirs.length > 0 ? (
                      <div className="mt-3 flex flex-wrap items-center gap-2">
                        <span className="text-[11px] font-medium uppercase tracking-[0.16em] text-slate-400">{isZh ? "最近输出目录" : "Recent outdir"}</span>
                        {recentOutdirs.map((path) => (
                          <button
                            key={path}
                            type="button"
                            className="ui-pressable rounded-full border border-slate-200 bg-white px-3 py-1 text-xs text-slate-600 hover:border-ice-200 hover:bg-ice-50 hover:text-ice-700"
                            onClick={() => patchDraft({ outputDirectory: path })}
                            title={path}
                          >
                            <span className="block max-w-56 truncate">{path}</span>
                          </button>
                        ))}
                      </div>
                    ) : null}
                    <IssueText issue={outputIssue} />
                  </label>
                </div>

                <div className="mt-5 rounded-xl border border-slate-200/80 bg-slate-50/80 p-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold text-slate-900">{isZh ? "导入 request JSON" : "Import request JSON"}</p>
                      <p className="mt-1 text-sm leading-6 text-slate-500">
                        {isZh
                          ? "附加一个现有的 AnalysisRequest 文件，直接运行，而不必重新填写向导。"
                          : "Attach an existing AnalysisRequest file and run it directly without rebuilding the request from the wizard."}
                      </p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <button type="button" className={SECONDARY_BUTTON_CLASS} onClick={handleImportRequestJson}>
                        {isZh ? "导入 request JSON" : "Import request JSON"}
                      </button>
                      {usesImportedRequest ? (
                        <button type="button" className={SECONDARY_BUTTON_CLASS} onClick={clearImportedRequest}>
                          {isZh ? "清除导入请求" : "Clear imported request"}
                        </button>
                      ) : null}
                    </div>
                  </div>

                  {usesImportedRequest ? (
                    <div className="mt-4 grid gap-2 rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-600">
                      <InfoRow label={isZh ? "来源" : "source"} value={isZh ? "导入的 request JSON" : "Imported request JSON"} />
                      <InfoRow label="request" value={importedRequest?.path ?? "-"} />
                      <InfoRow label={isZh ? "方法" : "method"} value={importedRequest?.method ?? "-"} />
                      <InfoRow label="workflow" value={importedRequest?.workflow ?? "-"} />
                      <InfoRow label={isZh ? "模式" : "mode"} value={importedRequest?.inputMode ?? "-"} />
                      <InfoRow
                        label={isZh ? "请求内 outdir" : "request outdir"}
                        value={importedRequest?.requestOutputDirectory || (isZh ? "导入 JSON 未声明" : "Not declared in imported JSON")}
                      />
                      <p className="pt-1 text-xs leading-5 text-slate-500">
                        {isZh
                          ? "运行会直接使用上面的导入 request 路径，并配合当前面板里显示的任务输出目录。"
                          : "Run uses the imported request path above and the current task output directory shown in this panel."}
                      </p>
                    </div>
                  ) : (
                    <p className="mt-4 text-sm text-slate-500">
                      {isZh
                        ? "当前没有附加导入请求，本任务仍会由向导草稿生成 request JSON。"
                        : "No imported request is attached. The current wizard draft still generates the request JSON for this task."}
                    </p>
                  )}
                  {recentRequests.length > 0 ? (
                    <div className="mt-4 flex flex-wrap items-center gap-2">
                      <span className="text-[11px] font-medium uppercase tracking-[0.16em] text-slate-400">{isZh ? "最近 request" : "Recent request"}</span>
                      {recentRequests.map((item) => (
                        <button
                          key={item.path}
                          type="button"
                          className="ui-pressable rounded-full border border-slate-200 bg-white px-3 py-1 text-left text-xs text-slate-600 hover:border-ice-200 hover:bg-ice-50 hover:text-ice-700"
                          onClick={() => void attachImportedRequest(item.path)}
                          title={item.path}
                        >
                          <span className="block max-w-56 truncate">{item.path}</span>
                          <span className="mt-0.5 block text-[10px] uppercase tracking-[0.14em] text-slate-400">
                            {item.workflow ?? item.method ?? "request"}
                          </span>
                        </button>
                      ))}
                    </div>
                  ) : null}
                </div>
              </section>

              {draft.inputMode !== "auto_directory" ? (
                <section className={PANEL_BODY_CLASS}>
                  <div className="flex items-start justify-between gap-3">
                    <SectionTitle
                      title={isZh ? "物种输入" : "Species inputs"}
                      subtitle={
                        isZh
                          ? "当 workflow 不使用 auto_directory 时，可以改用显式物种输入。"
                          : "Explicit species mode is available for workflows that do not use auto_directory."
                      }
                    />
                    <button type="button" className={SECONDARY_BUTTON_CLASS} onClick={addSpecies}>
                      {isZh ? "添加物种" : "Add species"}
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
                <SectionTitle
                  title={isZh ? "分析选项" : "Analysis options"}
                  subtitle={isZh ? "保持 transport 字段与 GenomeLens request 契约一致。" : "Keep transport fields aligned with the GenomeLens request contract."}
                />
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
                <SectionTitle
                  title={isZh ? "MCSCAN 参数" : "MCSCAN parameters"}
                  subtitle={isZh ? "高级选项保留为任务本地设置，不同任务可以独立调整。" : "Advanced options remain task-local and can diverge per task."}
                />
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
                <SectionTitle
                  title={isZh ? "运行控制" : "Run control"}
                  subtitle={isZh ? "一个任务对应一个 request 文件和一次 GenomeLens 运行。" : "One task maps to one request file and one GenomeLens run."}
                />
                {usesImportedRequest ? (
                  <div className="mt-4 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
                    <p className="font-medium text-slate-900">{isZh ? "已附加导入请求" : "Imported request attached"}</p>
                    <p className="mt-1 break-all font-mono text-xs leading-6 text-slate-500">{importedRequest?.path ?? "-"}</p>
                    <p className="mt-2 text-xs leading-5 text-slate-500">
                      {isZh
                        ? `本次运行会直接使用该 request 文件。当前任务 outdir：${draft.outputDirectory || "-" }。`
                        : `This run will use the imported request file directly. Current task outdir: ${draft.outputDirectory || "-"}.`}
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
                    {isZh ? "运行当前任务" : "Run active task"}
                  </button>
                  <button type="button" className={SECONDARY_BUTTON_CLASS} onClick={handleReadLog}>
                    {isZh ? "刷新日志" : "Refresh log"}
                  </button>
                  <button type="button" className={SECONDARY_BUTTON_CLASS} onClick={handleReadSummary}>
                    {isZh ? "读取摘要" : "Read summary"}
                  </button>
                  <button type="button" className={SECONDARY_BUTTON_CLASS} disabled={!resolvedLogPath} onClick={handleOpenLog}>
                    {isZh ? "打开日志" : "Open log"}
                  </button>
                  <button
                    type="button"
                    className={SECONDARY_BUTTON_CLASS}
                    disabled={!resolvedSummaryPath}
                    onClick={handleOpenSummary}
                  >
                    {isZh ? "打开摘要" : "Open summary"}
                  </button>
                  <button type="button" className={SECONDARY_BUTTON_CLASS} onClick={handleOpenOutput}>
                    {isZh ? "打开输出目录" : "Open output"}
                  </button>
                </div>

                <div className="mt-5 grid gap-3 rounded-lg border border-border bg-bg p-4">
                  <div className="flex items-center justify-between gap-3">
                    <span className="text-xs font-semibold uppercase tracking-[0.14em] text-text-tertiary">{isZh ? "状态" : "status"}</span>
                    <span
                      className={[
                        "rounded-full px-3 py-1 text-xs font-semibold uppercase",
                        statusTone(activeTask.runStatus),
                        activeTask.runStatus === "starting" || activeTask.runStatus === "running"
                          ? "ui-status-live"
                          : activeTask.runStatus === "finished" || activeTask.runStatus === "error"
                            ? "ui-status-settle"
                            : "",
                      ].join(" ")}
                    >
                      {runStatusLabel} / {workflowStateLabel}
                    </span>
                  </div>
                  <div className="grid gap-2 rounded-lg border border-slate-200/80 bg-white/75 px-3 py-3 text-sm text-slate-600">
                    <InfoRow label={isZh ? "来源" : "source"} value={requestSourceLabel} />
                    <InfoRow label="workflow" value={requestWorkflow} />
                    <InfoRow label={isZh ? "模式" : "mode"} value={requestMode} />
                    <InfoRow label="outdir" value={draft.outputDirectory || "-"} />
                    <InfoRow label="request" value={requestSourcePath} />
                    <p className="ui-message-enter text-xs leading-5 text-slate-500">{runHint}</p>
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
                  {summaryView ? (
                    <div className="ui-summary-reveal rounded-lg border border-slate-200/80 bg-white/80 px-3 py-3">
                      <div className="flex items-center justify-between gap-3">
                        <p className="text-sm font-semibold text-slate-900">{isZh ? "摘要已就绪" : "Summary ready"}</p>
                        <span className="text-xs font-medium text-slate-400">{summaryView.status}</span>
                      </div>
                      <div className="mt-3 grid gap-2 text-sm text-slate-600 sm:grid-cols-3">
                        <InfoRow label={isZh ? "图件" : "figures"} value={String(summaryFigureCount)} />
                        <InfoRow label={isZh ? "产物" : "artifacts"} value={String(summaryArtifactCount)} />
                        <InfoRow label={isZh ? "摘要" : "summary"} value={resolvedSummaryPath || "-"} />
                      </div>
                    </div>
                  ) : null}
                </div>
              </section>

              {activeTask.runStatus === "confirming" ? (
                <section className="ui-surface-enter rounded-lg border border-amber-200 bg-amber-50 p-4 dark:border-amber-900/40 dark:bg-amber-950/20">
                  <h3 className="text-sm font-semibold text-text-primary">{isZh ? "确认 AnalysisRequest JSON" : "Confirm AnalysisRequest JSON"}</h3>
                  <div className="mt-3 grid gap-2 rounded-lg border border-amber-200/80 bg-white/80 px-3 py-3 text-sm text-slate-600">
                    <InfoRow
                      label={isZh ? "来源" : "source"}
                      value={
                        usesImportedRequest
                          ? isZh
                            ? "导入的 request JSON"
                            : "Imported request JSON"
                          : isZh
                            ? "当前草稿生成"
                            : "Generated from active draft"
                      }
                    />
                    {usesImportedRequest ? (
                      <>
                        <InfoRow label="request" value={importedRequest?.path ?? "-"} />
                        <InfoRow label={isZh ? "模式" : "mode"} value={importedRequest?.inputMode ?? "-"} />
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
                      {isZh ? "确认运行" : "Confirm run"}
                    </button>
                    <button type="button" className={SECONDARY_BUTTON_CLASS} onClick={() => updateActiveTask((task) => ({ ...task, runStatus: "idle" }))}>
                      {isZh ? "取消" : "Cancel"}
                    </button>
                  </div>
                </section>
              ) : null}

              <section className={PANEL_BODY_CLASS}>
                <SectionTitle
                  title={isZh ? "实时日志" : "Live log"}
                  subtitle={isZh ? "稳定的 run.log 行会持续流入当前任务上下文。" : "Stable run.log lines are streamed into this task context."}
                />
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
                    <div className="text-text-secondary">{isZh ? "等待 analysis:stdout 或 read_run_log()..." : "Waiting for analysis:stdout or read_run_log()."}</div>
                  )}
                </div>
              </section>
            </div>
          ) : null}

          {activeTask.view === "results" ? (
            <div className="mx-auto grid w-full max-w-4xl gap-6">
              <section className={PANEL_BODY_CLASS}>
                <SectionTitle title={isZh ? "结果" : "Results"} subtitle={isZh ? "读取当前任务的 run_summary.json。" : "Read run_summary.json for the active task."} />
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
                      <h3 className="text-sm font-semibold text-text-primary">{isZh ? "图件资源" : "Figure assets"}</h3>
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
                            {isZh ? "summary 中暂时还没有列出图件资源。" : "No figure assets listed in summary yet."}
                          </p>
                        )}
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="mt-4 rounded-lg border border-border bg-bg p-4">
                    <p className="text-sm text-text-secondary">{isZh ? "当前任务还没有加载 summary。" : "No summary loaded for this task."}</p>
                    <button type="button" className={`${PRIMARY_BUTTON_CLASS} mt-4`} onClick={handleReadSummary}>
                      {isZh ? "读取摘要" : "Read summary"}
                    </button>
                  </div>
                )}
              </section>

              <section className={PANEL_BODY_CLASS}>
                <SectionTitle
                  title="Request JSON"
                  subtitle={
                    usesImportedRequest
                      ? isZh
                        ? "当前任务使用的导入 request 文件预览。"
                        : "Preview of the imported request file used by this task."
                      : isZh
                        ? "当前任务由草稿生成的 request 预览。"
                        : "Current task request preview generated from the active draft."
                  }
                />
                <div className="mt-4 grid gap-2 rounded-lg border border-border bg-bg px-4 py-3 text-sm text-text-secondary">
                  <InfoRow label={isZh ? "来源" : "source"} value={usesImportedRequest ? (isZh ? "导入的 request JSON" : "Imported request JSON") : isZh ? "当前草稿生成" : "Generated draft"} />
                  {usesImportedRequest ? (
                    <>
                      <InfoRow label="request" value={importedRequest?.path ?? "-"} />
                      <InfoRow label={isZh ? "模式" : "mode"} value={importedRequest?.inputMode ?? "-"} />
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
                {usesImportedRequest ? requestSourceLabel : activeTask.title}
              </p>
              <div className="mt-1 flex flex-wrap gap-2 text-xs text-slate-500">
                <span className="rounded-full bg-slate-100 px-2.5 py-1">{requestWorkflow}</span>
                <span className="rounded-full bg-slate-100 px-2.5 py-1">{draft.outputDirectory || (isZh ? "未选择 outdir" : "No outdir selected")}</span>
                <span className="rounded-full bg-slate-100 px-2.5 py-1">{validation.issues.length === 0 ? (isZh ? "已就绪" : "ready") : isZh ? `${validation.issues.length} 个问题` : `${validation.issues.length} issue(s)`}</span>
              </div>
            </div>
            <button
              type="button"
              className="ui-pressable rounded-xl border border-slate-200 px-3 py-2 text-xs font-medium text-slate-700 hover:bg-slate-50"
              onClick={() => setTaskView("setup")}
            >
              {isZh ? "配置" : "setup"}
            </button>
            <button
              type="button"
              className="ui-pressable rounded-xl border border-slate-200 px-3 py-2 text-xs font-medium text-slate-700 hover:bg-slate-50"
              onClick={() => setTaskView("results")}
            >
              {isZh ? "结果" : "results"}
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
              {activeTask.runStatus === "starting" || activeTask.runStatus === "running" ? (isZh ? "运行中" : "Running") : isZh ? "运行" : "Run"}
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
              <InfoRow label={isZh ? "问题" : "issues"} value={String(validation.issues.length)} />
            </div>
          </section>

          <section className="mt-5 border-t border-slate-100 pt-5">
            <h3 className="text-sm font-medium text-slate-900">工作树</h3>
            <div className="mt-3 grid gap-2 text-sm text-text-secondary">
              <InfoRow label={isZh ? "状态" : "status"} value={runStatusLabel} />
              <InfoRow label={isZh ? "流程状态" : "state"} value={workflowStateLabel} />
              <InfoRow label={isZh ? "进度" : "progress"} value={`${Math.round(progress)}%`} />
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
                  {isZh ? "运行事件会显示在这里。" : "Run events will appear here."}
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
            <SectionTitle title={isZh ? "分析 schema" : "Schema"} subtitle="get_analysis_schema()" />
            <pre className="mt-3 max-h-52 overflow-auto rounded-lg bg-slate-50 p-3 font-mono text-[11px] leading-5 text-slate-500">
              {schemaJson || (isZh ? "尚未加载 schema。" : "Schema not loaded.")}
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
