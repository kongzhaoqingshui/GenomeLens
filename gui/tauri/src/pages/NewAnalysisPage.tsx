/* eslint-disable @typescript-eslint/no-unused-vars */
import {
  ArrowLeft,
  Ban,
  Bookmark,
  Box,
  CheckCircle2,
  Copy,
  FileJson,
  FileText,
  FolderOpen,
  History,
  LayoutList,
  Loader2,
  Play,
  Plus,
  RefreshCw,
  Settings,
  Sliders,
  Terminal,
} from "lucide-react";
import { open } from "@tauri-apps/plugin-dialog";
import { mkdir, writeTextFile } from "@tauri-apps/plugin-fs";
import {
  useEffect,
  useMemo,
  useState,
} from "react";

import { WorkbenchShell } from "../components/WorkbenchShell";
import { WorkbenchLeftPanel } from "../components/WorkbenchLeftPanel";
import { type GameIconName } from "../components/GameIcon";
import { SectionHeader } from "../components/ui";
import { CollapsibleSection } from "../components/CollapsibleSection";
import { TaskNodeCanvas } from "../components/TaskNodeCanvas";
import { JcviMeowIcon } from "../components/JcviMeowIcon";
import { SubmoduleForm } from "../components/SubmoduleForm";
import { useLanguage } from "../i18n/useLanguage";
import type { CapabilityEntry } from "../models/capability";
import { getCapabilitySubtitle, resolveLegacyCapabilityId, isOneStopCapability } from "../models/capability";
import { WorkbenchRightPanel } from "../components/WorkbenchRightPanel";
import type { OutputFormat } from "../models/workflow-request";
import type { WorkflowRequestInputMode } from "../models/workflow-request-draft";
import type { SpeciesInputDraft, WorkflowRequestDraft } from "../models/workflow-request-draft";
import {
  createDraftForCapability,
  getJcviCapabilityById,
  type JcviCapabilityId,
} from "../models";
import { draftToWorkflowRequest, createDefaultWorkflowRequestDraft } from "../models/workflow-request-draft";
import {
  draftToSubmoduleRequest,
  type SubmoduleRequestDraft,
} from "../models/submodule-request-draft";
import {
  appendRunLogLines,
  applyWorkflowEvent,
  createWorkflowRunState,
  type WorkflowEvent,
  type WorkflowRunState,
  type WorkflowState,
} from "../models/run-session";
import { runSummaryToViewModel } from "../models/run-summary-view";
import { validateSubmoduleRequestDraft, validateWorkflowRequestDraft, type ValidationIssue } from "../models/validation";
import type { AppRoute } from "../routes/routes";
import {
  getWorkflowSchema,
  getCachedWorkflowSchema,
  getCachedTemplateDraft,
  getTemplateDraft,
  readRequestPreview,
  type JsonObject,
} from "../services/analysis";
import { describeCapability } from "../services/capability";
import { getSubmoduleTemplateDraft } from "../services/submodule";
import {
  cancelRun,
  listenToWorkflowEvents,
  openPath,
  readRunLog,
  readRunSnapshot,
  readSummaryView,
  runAnalysis,
} from "../services/workbench";

interface NewAnalysisPageProps {
  route: AppRoute;
  onNavigate: (path: string) => void;
  locationHash: string;
}

type RunPanelStatus = "idle" | "confirming" | "starting" | "running" | "cancelling" | "cancelled" | "finished" | "error";
type WorkbenchView = "setup" | "run" | "results";
type InputMode = WorkflowRequestInputMode;
type SyntenyNumberField = "cscore" | "dist" | "iter";
type PlotNumberField = "dpi";
type LocalNumberField = "up" | "down";

type RequestKind = "workflow" | "submodule";

interface WorkbenchTask {
  id: string;
  title: string;
  capabilityId: string | null;
  preset?: string;
  requestKind: RequestKind;
  icon: GameIconName;
  x: number;
  y: number;
  draft: WorkflowRequestDraft;
  submoduleDraft?: SubmoduleRequestDraft;
  capability?: CapabilityEntry;
  view: WorkbenchView;
  runStatus: RunPanelStatus;
  runState: WorkflowRunState | null;
  runError: string | null;
  pendingRequestJson: string;
  importedRequest: ImportedRequestState | null;
  createdAt: string;
  updatedAt: string;
  onCanvas: boolean;
}

interface ImportedRequestState {
  path: string;
  json: string;
  workflowId: string;
  kind: string;
  inputMode: string;
  requestOutputDirectory: string;
}

interface RecentRequestHint {
  path: string;
  workflowId?: string;
  kind?: string;
}

const FIELD_CLASS =
  "mt-2 w-full rounded-xl border border-border bg-bg px-3 py-2 text-sm text-text-primary shadow-card outline-none transition focus:border-ice-400 focus:ring-2 focus:ring-ice-200 dark:focus:ring-ice-900/60";
const LABEL_CLASS = "text-xs font-semibold uppercase tracking-[0.14em] text-text-tertiary";
const CHECKBOX_CLASS = "h-4 w-4 rounded border-border text-ice-500 focus:ring-ice-500";
const PANEL_BODY_CLASS = "ui-surface-enter ui-card mx-auto w-full max-w-4xl p-6";
const SECONDARY_BUTTON_CLASS =
  "ui-pressable inline-flex items-center gap-1.5 rounded-xl border border-border bg-surface px-3 py-2 text-xs font-semibold text-text-secondary transition hover:border-ice-200 hover:bg-ice-50 hover:text-ice-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ice-500 dark:hover:border-ice-800 dark:hover:bg-ice-900/30 dark:hover:text-ice-200 disabled:cursor-not-allowed disabled:opacity-45";
const PRIMARY_BUTTON_CLASS =
  "ui-pressable inline-flex items-center gap-1.5 rounded-xl bg-ice-500 px-4 py-2 text-sm font-semibold text-white shadow-lg shadow-ice-500/20 transition hover:bg-ice-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ice-500 focus-visible:ring-offset-2 focus-visible:ring-offset-bg disabled:cursor-not-allowed disabled:opacity-50";
const ICON_BUTTON_CLASS =
  "ui-pressable inline-flex h-9 w-9 items-center justify-center rounded-xl border border-border bg-surface text-text-secondary transition hover:bg-surface-raised hover:text-text-primary disabled:cursor-not-allowed disabled:opacity-45";
const RECENT_OUTDIRS_KEY = "genomelens.gui.recentOutdirs";
const RECENT_REQUESTS_KEY = "genomelens.gui.recentRequests";
const WORKBENCH_RIGHT_WIDTH_KEY = "genomelens.gui.workbench.rightWidth";
const RECENT_HINT_LIMIT = 4;
const WORKBENCH_DEFAULT_RIGHT_WIDTH = 368;
const WORKBENCH_MIN_RIGHT_WIDTH = 280;
const WORKBENCH_MAX_RIGHT_WIDTH = 520;
const WORKBENCH_MIN_CENTER_WIDTH = 300;
const WORKBENCH_RESIZER_WIDTH = 6;

const LOG_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"];
const FORMAT_OPTIONS: OutputFormat[] = ["png", "pdf", "svg"];
const SYNTENY_NUMBER_FIELDS: Array<{
  key: SyntenyNumberField;
  label: string;
  min: number;
  max?: number;
  step: number;
}> = [
  { key: "cscore", label: "cscore", min: 0, max: 1, step: 0.05 },
  { key: "dist", label: "dist", min: 1, step: 1 },
  { key: "iter", label: "iter", min: 1, step: 1 },
];
const PLOT_NUMBER_FIELDS: Array<{
  key: PlotNumberField;
  label: string;
  min: number;
  step: number;
}> = [{ key: "dpi", label: "dpi", min: 1, step: 1 }];
const LOCAL_NUMBER_FIELDS: Array<{
  key: LocalNumberField;
  label: string;
  min: number;
  step: number;
}> = [
  { key: "up", label: "upstream", min: 0, step: 1 },
  { key: "down", label: "downstream", min: 0, step: 1 },
];

function capabilityIcon(id: string | null): GameIconName {
  if (id && id in CAPABILITY_ICON) {
    return CAPABILITY_ICON[id as JcviCapabilityId];
  }
  switch (id) {
    case "synteny":
      return "multi-species";
    case "jcvi.pairwise":
      return "pairwise";
    case "jcvi.graphics_dotplot":
      return "dotplot";
    case "jcvi.graphics_synteny":
      return "multi-species";
    case "jcvi.graphics_karyotype":
    case "jcvi.graphics_karyotype_global":
      return "karyotype";
    case "jcvi.local_synteny":
    case "jcvi.local_synteny_multi":
      return "local";
    case "environment-check":
      return "environment";
    default:
      return "dotplot";
  }
}

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

function issueFor(issues: ValidationIssue[], field: string): ValidationIssue | undefined {
  return issues.find((item) => item.field === field);
}

function IssueText({ issue }: { issue?: ValidationIssue }) {
  if (issue === undefined) {
    return null;
  }

  return <p className="mt-2 text-xs font-medium text-rose-600 dark:text-rose-300">{issue.message}</p>;
}

function SectionTitle({ title, subtitle, action }: { title: string; subtitle: string; action?: React.ReactNode }) {
  return <SectionHeader title={title} subtitle={subtitle} action={action} />;
}

function updateNumber(value: string): number | null {
  if (value.trim().length === 0) {
    return null;
  }
  const next = Number(value);
  return Number.isFinite(next) ? next : null;
}

function emptySpecies(inputMode: InputMode): SpeciesInputDraft {
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
  workflowId?: string;
  kind?: string;
}): ImportedRequestState {
  const root = asObject(preview.json);
  if (!root) {
    throw new Error("Imported request must be a JSON object.");
  }

  const output = asObject(root.output);
  const species = Array.isArray(root.species) ? root.species : [];

  return {
    path: preview.requestPath,
    json: stringifyJson(preview.json),
    workflowId: preview.workflowId ?? (typeof root.workflow_id === "string" ? root.workflow_id : "unknown"),
    kind: preview.kind ?? (typeof root.kind === "string" ? root.kind : "unknown"),
    inputMode: species.length > 0 ? "bed_cds" : "unknown",
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

function readStoredNumber(key: string, fallback: number): number {
  try {
    const raw = window.localStorage.getItem(key);
    if (!raw) {
      return fallback;
    }
    const value = Number(raw);
    return Number.isFinite(value) ? value : fallback;
  } catch {
    return fallback;
  }
}

function writeStoredNumber(key: string, value: number) {
  try {
    window.localStorage.setItem(key, String(Math.round(value)));
  } catch {
    // Ignore local-only persistence failures.
  }
}

function clampNumber(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), Math.max(min, max));
}

function viewportWidth(): number {
  return typeof window === "undefined" ? 1440 : window.innerWidth;
}

function clampWorkbenchRightWidth(rightWidth: number, width = viewportWidth()): number {
  const right = clampNumber(Math.round(rightWidth), WORKBENCH_MIN_RIGHT_WIDTH, WORKBENCH_MAX_RIGHT_WIDTH);
  const availableForRight = width - WORKBENCH_RESIZER_WIDTH - WORKBENCH_MIN_CENTER_WIDTH;
  return Math.min(right, Math.max(WORKBENCH_MIN_RIGHT_WIDTH, availableForRight));
}

function readInitialWorkbenchRightWidth(): number {
  return clampWorkbenchRightWidth(readStoredNumber(WORKBENCH_RIGHT_WIDTH_KEY, WORKBENCH_DEFAULT_RIGHT_WIDTH));
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

function readCapabilityFromHash(locationHash: string): { id: string; preset?: string } | null {
  const queryIndex = locationHash.indexOf("?");
  if (queryIndex < 0) {
    return null;
  }

  const params = new URLSearchParams(locationHash.slice(queryIndex + 1));
  const raw = params.get("capability");
  if (!raw) {
    return null;
  }

  return resolveLegacyCapabilityId(raw);
}

function legacyCapabilityIdForSyntenyPreset(preset?: string): JcviCapabilityId {
  switch (preset) {
    case "multi":
      return "multi-species-synteny";
    case "local":
      return "local-synteny";
    case "pairwise":
    default:
      return "pairwise-synteny";
  }
}

function createWorkflowTaskFromTemplate(
  templateDraft: WorkflowRequestDraft,
  capabilityId: string | null,
  preset: string | undefined,
  index: number,
): WorkbenchTask {
  const legacyCapabilityId =
    capabilityId === "synteny"
      ? legacyCapabilityIdForSyntenyPreset(preset)
      : capabilityId && capabilityId in { "pairwise-synteny": true, "multi-species-synteny": true, "local-synteny": true, dotplot: true, karyotype: true, "ortholog-catalog": true, "environment-check": true }
        ? (capabilityId as JcviCapabilityId)
        : null;
  const capability = legacyCapabilityId ? getJcviCapabilityById(legacyCapabilityId) : undefined;
  const draft = legacyCapabilityId ? createDraftForCapability(templateDraft, legacyCapabilityId) : templateDraft;
  const title = capability ? `${capability.subtitle} #${index}` : `Synteny Task #${index}`;
  const createdAt = nowIso();

  return {
    id: `task-${createdAt}-${index}`,
    title,
    capabilityId: capabilityId ?? legacyCapabilityId ?? null,
    preset,
    requestKind: "workflow",
    icon: capability ? CAPABILITY_ICON[legacyCapabilityId as JcviCapabilityId] : "pairwise",
    x: 24 + index * 240,
    y: 80,
    draft: {
      ...draft,
      species: draft.species.map((species) => ({ ...species })),
      formats: [...draft.formats],
      runtime: { ...draft.runtime },
      parameters: {
        synteny: { ...draft.parameters.synteny },
        localSynteny: { ...draft.parameters.localSynteny, targetGeneIds: [...draft.parameters.localSynteny.targetGeneIds] },
        plot: { ...draft.parameters.plot },
        histogram: { ...draft.parameters.histogram, inputs: [...draft.parameters.histogram.inputs], columns: [...draft.parameters.histogram.columns] },
        heatmap: { ...draft.parameters.heatmap },
        extras: { ...draft.parameters.extras },
      },
    },
    view: "setup",
    runStatus: "idle",
    runState: null,
    runError: null,
    pendingRequestJson: "",
    importedRequest: null,
    createdAt,
    updatedAt: createdAt,
    onCanvas: true,
  };
}

function createSubmoduleTask(
  capability: CapabilityEntry,
  submoduleDraft: SubmoduleRequestDraft,
  index: number,
): WorkbenchTask {
  const createdAt = nowIso();
  return {
    id: `task-${createdAt}-${index}`,
    title: `${capability.subtitle} #${index}`,
    capabilityId: capability.id,
    requestKind: "submodule",
    icon: "dotplot",
    x: 24 + index * 240,
    y: 80,
    draft: createDefaultWorkflowRequestDraft(),
    submoduleDraft: {
      ...submoduleDraft,
      inputs: { ...submoduleDraft.inputs },
      parameters: { ...submoduleDraft.parameters },
      formats: [...submoduleDraft.formats],
      runtime: { ...submoduleDraft.runtime },
    },
    capability,
    view: "setup",
    runStatus: "idle",
    runState: null,
    runError: null,
    pendingRequestJson: "",
    importedRequest: null,
    createdAt,
    updatedAt: createdAt,
    onCanvas: true,
  };
}

function applyEventStatus(currentStatus: RunPanelStatus, event: WorkflowEvent): RunPanelStatus {
  if (event.name === "analysis:stdout" || event.name === "analysis:state") {
    if (event.name === "analysis:state" && event.payload.state === "CANCELLED") {
      return "cancelled";
    }
    if (currentStatus === "cancelling") {
      return "cancelling";
    }
    return currentStatus === "finished" || currentStatus === "error" ? currentStatus : "running";
  }
  if (event.name === "analysis:finished") {
    if (event.payload.status === "CANCELLED") {
      return "cancelled";
    }
    return event.payload.status === "SUCCEEDED" ? "finished" : "error";
  }
  return event.payload.code === "cancelled" ? "cancelled" : "error";
}

function canCloseTask(task: WorkbenchTask): boolean {
  return (
    task.runStatus !== "confirming" &&
    task.runStatus !== "starting" &&
    task.runStatus !== "running" &&
    task.runStatus !== "cancelling"
  );
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

function createCachedWorkbenchState(capabilityQuery: { id: string; preset?: string } | null) {
  if (capabilityQuery && capabilityQuery.id !== "synteny" && !capabilityQuery.id.startsWith("jcvi.")) {
    // Legacy non-synteny ids are not cached here; they are loaded async.
  }
  if (capabilityQuery?.id.startsWith("jcvi.")) {
    return null;
  }

  const cachedTemplateDraft = getCachedTemplateDraft("workflow", "synteny");
  const cachedSchema = getCachedWorkflowSchema();
  if (!cachedTemplateDraft || !cachedSchema) {
    return null;
  }

  const firstTask = createWorkflowTaskFromTemplate(
    cachedTemplateDraft,
    capabilityQuery?.id ?? null,
    capabilityQuery?.preset,
    1,
  );
  return {
    activeTaskId: firstTask.id,
    schema: cachedSchema,
    taskCounter: 2,
    tasks: [firstTask],
    templateDraft: cachedTemplateDraft,
  };
}

export default function NewAnalysisPage({ route, onNavigate, locationHash }: NewAnalysisPageProps) {
  const { language } = useLanguage();
  const isZh = language === "zh-CN";
  const capabilityQuery = useMemo(() => readCapabilityFromHash(locationHash), [locationHash]);
  const initialWorkbench = useMemo(() => createCachedWorkbenchState(capabilityQuery), [capabilityQuery]);
  const [templateDraft, setTemplateDraft] = useState<WorkflowRequestDraft | null>(
    () => initialWorkbench?.templateDraft ?? null,
  );
  const [schema, setSchema] = useState<JsonObject | null>(() => initialWorkbench?.schema ?? null);
  const [loading, setLoading] = useState(() => initialWorkbench === null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [tasks, setTasks] = useState<WorkbenchTask[]>(() => initialWorkbench?.tasks ?? []);
  const [activeTaskId, setActiveTaskId] = useState(() => initialWorkbench?.activeTaskId ?? "");
  const [taskCounter, setTaskCounter] = useState(() => initialWorkbench?.taskCounter ?? 1);
  const [recentOutdirs, setRecentOutdirs] = useState<string[]>(() => readStoredJson<string[]>(RECENT_OUTDIRS_KEY, []));
  const [recentRequests, setRecentRequests] = useState<RecentRequestHint[]>(() =>
    readStoredJson<RecentRequestHint[]>(RECENT_REQUESTS_KEY, []),
  );
  const [rightSidebarWidth, setRightSidebarWidth] = useState(readInitialWorkbenchRightWidth);
  const [leftSidebarWidth, setLeftSidebarWidth] = useState(() => readStoredNumber("genomelens.gui.workbench.leftWidth", 288));
  const [capabilities, setCapabilities] = useState<CapabilityEntry[]>([]);

  useEffect(() => {
    writeStoredNumber("genomelens.gui.workbench.leftWidth", leftSidebarWidth);
  }, [leftSidebarWidth]);

  useEffect(() => {
    import("../services/capability").then(({ listCapabilities }) => {
      listCapabilities("all", "all").then(setCapabilities).catch(() => {});
    });
  }, []);

  useEffect(() => {
    writeStoredJson(RECENT_OUTDIRS_KEY, recentOutdirs);
  }, [recentOutdirs]);

  useEffect(() => {
    writeStoredJson(RECENT_REQUESTS_KEY, recentRequests);
  }, [recentRequests]);

  useEffect(() => {
    const reclampWidth = () => {
      setRightSidebarWidth((current) => {
        const next = clampWorkbenchRightWidth(current);
        return next === current ? current : next;
      });
    };

    reclampWidth();
    window.addEventListener("resize", reclampWidth);

    return () => {
      window.removeEventListener("resize", reclampWidth);
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    const cachedWorkbench = createCachedWorkbenchState(capabilityQuery);

    if (cachedWorkbench) {
      setTemplateDraft(cachedWorkbench.templateDraft);
      setSchema(cachedWorkbench.schema);
      setTasks(cachedWorkbench.tasks);
      setActiveTaskId(cachedWorkbench.activeTaskId);
      setTaskCounter(cachedWorkbench.taskCounter);
      setLoadError(null);
      setLoading(false);
      return () => {
        cancelled = true;
      };
    }

    setLoading(true);
    setLoadError(null);

    async function loadInitialWorkbench() {
      try {
        const [nextTemplateDraft, analysisSchema] = await Promise.all([
          getTemplateDraft("workflow", "synteny"),
          getWorkflowSchema(),
        ]);
        if (cancelled) {
          return;
        }

        let firstTask: WorkbenchTask;
        if (capabilityQuery?.id.startsWith("jcvi.")) {
          const [capability, submoduleDraft] = await Promise.all([
            describeCapability(capabilityQuery.id),
            getSubmoduleTemplateDraft(capabilityQuery.id),
          ]);
          if (cancelled) {
            return;
          }
          firstTask = createSubmoduleTask(capability, submoduleDraft, 1);
        } else {
          firstTask = createWorkflowTaskFromTemplate(
            nextTemplateDraft,
            capabilityQuery?.id ?? null,
            capabilityQuery?.preset,
            1,
          );
        }

        if (cancelled) {
          return;
        }
        setTemplateDraft(nextTemplateDraft);
        setSchema(analysisSchema);
        setTasks([firstTask]);
        setActiveTaskId(firstTask.id);
        setTaskCounter(2);
      } catch (error: unknown) {
        if (!cancelled) {
          setLoadError(error instanceof Error ? error.message : String(error));
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void loadInitialWorkbench();

    return () => {
      cancelled = true;
    };
  }, [capabilityQuery]);

  useEffect(() => {
    let active = true;
    let stopListening: (() => void) | null = null;

    void listenToWorkflowEvents((event) => {
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
            runError:
              event.name === "analysis:error"
                ? event.payload.code === "cancelled"
                  ? null
                  : event.payload.message
                : task.runError,
            runState: applyWorkflowEvent(task.runState, event),
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
  const submoduleDraft = activeTask?.submoduleDraft ?? null;
  const validation = useMemo(() => {
    if (!activeTask) {
      return null;
    }
    if (activeTask.requestKind === "submodule") {
      if (!submoduleDraft || !activeTask.capability) {
        return null;
      }
      return validateSubmoduleRequestDraft(submoduleDraft, activeTask.capability);
    }
    return draft ? validateWorkflowRequestDraft(draft) : null;
  }, [activeTask, draft, submoduleDraft]);
  const requestJson = useMemo(() => {
    if (!activeTask) {
      return "";
    }
    if (activeTask.requestKind === "submodule") {
      return submoduleDraft ? stringifyJson(draftToSubmoduleRequest(submoduleDraft)) : "";
    }
    return draft ? stringifyJson(draftToWorkflowRequest(draft)) : "";
  }, [activeTask, draft, submoduleDraft]);
  const schemaJson = useMemo(() => (schema ? stringifyJson(schema) : ""), [schema]);
  const targetGeneText = draft?.parameters.localSynteny.targetGeneIds.join("\n") ?? "";
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

  const nodeTasks = useMemo(
    () =>
      tasks
        .filter((task) => task.onCanvas)
        .map((task) => ({
          id: task.id,
          title: task.title,
          subtitle:
            task.requestKind === "submodule"
              ? task.capability
                ? getCapabilitySubtitle(task.capability, isZh)
                : task.capabilityId ?? "submodule"
              : task.capabilityId
                ? (getJcviCapabilityById(task.capabilityId as JcviCapabilityId)?.subtitle ?? task.capabilityId)
                : task.draft.workflowId,
          icon: capabilityIcon(task.capabilityId ?? task.draft.workflowId),
          runStatus: task.runStatus,
          x: task.x,
          y: task.y,
        })),
    [isZh, tasks],
  );

  const leftPanelTasks = useMemo(
    () =>
      tasks.map((task) => ({
        id: task.id,
        title: task.title,
        subtitle:
          task.requestKind === "submodule"
            ? task.capability
              ? getCapabilitySubtitle(task.capability, isZh)
              : task.capabilityId ?? "submodule"
            : task.capabilityId
              ? (getJcviCapabilityById(task.capabilityId as JcviCapabilityId)?.subtitle ?? task.capabilityId)
              : task.draft.workflowId,
        icon: capabilityIcon(task.capabilityId ?? task.draft.workflowId),
        runStatus: task.runStatus,
        onCanvas: task.onCanvas,
      })),
    [isZh, tasks],
  );

  function updateTask(taskId: string, updater: (task: WorkbenchTask) => WorkbenchTask) {
    setTasks((currentTasks) =>
      currentTasks.map((task) => (task.id === taskId ? { ...updater(task), updatedAt: nowIso() } : task)),
    );
  }

  function moveTask(taskId: string, x: number, y: number) {
    updateTask(taskId, (task) => ({ ...task, x, y }));
  }

  function updateActiveTask(updater: (task: WorkbenchTask) => WorkbenchTask) {
    if (!activeTask) {
      return;
    }
    updateTask(activeTask.id, updater);
  }

  function patchDraft(patch: Partial<WorkflowRequestDraft>) {
    updateActiveTask((task) => ({ ...task, draft: { ...task.draft, ...patch } }));
  }

  function patchRuntime(patch: Partial<WorkflowRequestDraft["runtime"]>) {
    updateActiveTask((task) => ({
      ...task,
      draft: { ...task.draft, runtime: { ...task.draft.runtime, ...patch } },
    }));
  }

  function patchSynteny(patch: Partial<WorkflowRequestDraft["parameters"]["synteny"]>) {
    updateActiveTask((task) => ({
      ...task,
      draft: {
        ...task.draft,
        parameters: { ...task.draft.parameters, synteny: { ...task.draft.parameters.synteny, ...patch } },
      },
    }));
  }

  function patchPlot(patch: Partial<WorkflowRequestDraft["parameters"]["plot"]>) {
    updateActiveTask((task) => ({
      ...task,
      draft: {
        ...task.draft,
        parameters: { ...task.draft.parameters, plot: { ...task.draft.parameters.plot, ...patch } },
      },
    }));
  }

  function patchLocalSynteny(patch: Partial<WorkflowRequestDraft["parameters"]["localSynteny"]>) {
    updateActiveTask((task) => ({
      ...task,
      draft: {
        ...task.draft,
        parameters: { ...task.draft.parameters, localSynteny: { ...task.draft.parameters.localSynteny, ...patch } },
      },
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

  async function createTask(capabilityId: string | null = null, preset?: string) {
    if (capabilityId?.startsWith("jcvi.")) {
      try {
        const [capability, submoduleDraft] = await Promise.all([
          describeCapability(capabilityId),
          getSubmoduleTemplateDraft(capabilityId),
        ]);
        const nextTask = createSubmoduleTask(capability, submoduleDraft, taskCounter);
        setTaskCounter((current) => current + 1);
        setTasks((currentTasks) => [nextTask, ...currentTasks]);
        setActiveTaskId(nextTask.id);
      } catch (error: unknown) {
        updateActiveTask((task) => ({
          ...task,
          runStatus: "error",
          runError: error instanceof Error ? error.message : String(error),
          view: "setup",
        }));
      }
      return;
    }

    if (!templateDraft) {
      return;
    }
    const nextTask = createWorkflowTaskFromTemplate(templateDraft, capabilityId, preset, taskCounter);
    setTaskCounter((current) => current + 1);
    setTasks((currentTasks) => [nextTask, ...currentTasks]);
    setActiveTaskId(nextTask.id);
  }

  function closeTask(taskId: string) {
    setTasks((currentTasks) =>
      currentTasks.map((task) =>
        task.id === taskId ? { ...task, onCanvas: false, updatedAt: nowIso() } : task,
      ),
    );
    if (activeTaskId === taskId) {
      const remaining = tasks.filter((t) => t.id !== taskId && t.onCanvas);
      setActiveTaskId(remaining[0]?.id ?? tasks.find((t) => t.onCanvas)?.id ?? "");
    }
  }

  function deleteTask(taskId: string) {
    setTasks((currentTasks) => {
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
        workflowId: nextImportedRequest.workflowId,
        kind: nextImportedRequest.kind,
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
    const outdir =
      activeTask.requestKind === "submodule"
        ? activeTask.submoduleDraft?.outputDirectory.trim() ?? ""
        : activeTask.draft.outputDirectory.trim();
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

    let json = "";
    let requestPath = "";

    if (imported) {
      json = imported.json;
      requestPath = imported.path;
    } else if (activeTask.requestKind === "submodule") {
      const request = draftToSubmoduleRequest(activeTask.submoduleDraft!);
      json = stringifyJson(request);
      requestPath = joinPath(outdir, `genomelens-submodule-request-${timestampForFilename()}.json`);
    } else {
      const request = draftToWorkflowRequest(activeTask.draft);
      json = stringifyJson(request);
      requestPath = joinPath(outdir, `genomelens-request-${timestampForFilename()}.json`);
    }

    updateTask(taskId, (task) => ({ ...task, runStatus: "starting", runError: null, runState: null, view: "run" }));

    try {
      setRecentOutdirs((current) => rememberRecentText(current, outdir));
      if (imported) {
        setRecentRequests((current) =>
          rememberRecentRequest(current, {
            path: imported.path,
            workflowId: imported.workflowId,
            kind: imported.kind,
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
        runState: createWorkflowRunState(handle),
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

  async function handleCancelRun() {
    if (!activeTask?.runState?.runId) {
      return;
    }

    const taskId = activeTask.id;
    const runId = activeTask.runState.runId;
    updateTask(taskId, (task) => ({ ...task, runStatus: "cancelling", runError: null, view: "run" }));

    try {
      await cancelRun({ runId });
    } catch (error: unknown) {
      updateTask(taskId, (task) => ({
        ...task,
        runStatus: "error",
        runError: error instanceof Error ? error.message : String(error),
      }));
    }
  }

  async function handleReadSnapshot() {
    if (!activeTask) {
      return;
    }

    const taskId = activeTask.id;
    const activeOutdir =
      activeTask.requestKind === "submodule"
        ? activeTask.submoduleDraft?.outputDirectory
        : activeTask.draft.outputDirectory;
    const outdir = (activeTask.runState?.outdir ?? activeOutdir ?? "").trim();
    if (!outdir) {
      updateTask(taskId, (task) => ({ ...task, runError: localizeRunPrompt("draftOutdir", language), view: "setup" }));
      return;
    }

    try {
      const snapshot = await readRunSnapshot({ outdir, tailLines: 120 });
      const summaryView = snapshot.summary ? runSummaryToViewModel(snapshot.summary) : undefined;
      const summaryStatus = snapshot.summary?.status;
      const shouldKeepActiveStatus =
        activeTask.runStatus === "starting" ||
        activeTask.runStatus === "running" ||
        activeTask.runStatus === "cancelling";
      const nextStatus: RunPanelStatus =
        summaryStatus === "SUCCEEDED"
          ? "finished"
          : summaryStatus === "FAILED"
            ? "error"
            : summaryStatus === "CANCELLED"
              ? "cancelled"
              : shouldKeepActiveStatus
                ? activeTask.runStatus
              : activeTask.runStatus === "error"
                ? "error"
                : "idle";

      updateTask(taskId, (task) => {
        const baseState: WorkflowRunState =
          task.runState ??
          {
            runId: `snapshot:${outdir}`,
            outdir: snapshot.outdir,
            requestPath: task.importedRequest?.path ?? "-",
            logPath: snapshot.logPath || snapshot.log.logPath,
            summaryPath: snapshot.summaryPath,
            status: snapshot.summary?.ui?.state ?? summaryStatus ?? "PENDING",
            progress: snapshot.summary?.ui?.progress ?? 0,
            finished: summaryStatus === "SUCCEEDED" || summaryStatus === "FAILED" || summaryStatus === "CANCELLED",
            logLines: [],
          };

        return {
          ...task,
          view: summaryView ? "results" : "run",
          runStatus: nextStatus,
          runError: null,
          runState: appendRunLogLines(
            {
              ...baseState,
              outdir: snapshot.outdir,
              logPath: snapshot.logPath || snapshot.log.logPath || baseState.logPath,
              summaryPath: snapshot.summaryPath || baseState.summaryPath,
              status: snapshot.summary?.ui?.state ?? summaryStatus ?? baseState.status,
              progress: snapshot.summary?.ui?.progress ?? baseState.progress,
              finished:
                baseState.finished ||
                summaryStatus === "SUCCEEDED" ||
                summaryStatus === "FAILED" ||
                summaryStatus === "CANCELLED",
              summary: snapshot.summary ?? baseState.summary,
              summaryView: summaryView ?? baseState.summaryView,
              logLines: [],
              lastLogLine: undefined,
            },
            snapshot.log.lines,
          ),
        };
      });
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
    const outdir =
      activeTask.runState?.outdir ??
      (activeTask.requestKind === "submodule"
        ? activeTask.submoduleDraft?.outputDirectory
        : activeTask.draft.outputDirectory);
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
    const outdir =
      activeTask.runState?.outdir ??
      (activeTask.requestKind === "submodule"
        ? activeTask.submoduleDraft?.outputDirectory
        : activeTask.draft.outputDirectory);
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
    const outdir =
      activeTask?.runState?.outdir ??
      (activeTask?.requestKind === "submodule"
        ? activeTask?.submoduleDraft?.outputDirectory
        : activeTask?.draft.outputDirectory) ??
      "";
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
      <section className="ui-page-enter ui-app-frame grid h-screen w-full content-center justify-center gap-5 text-center"
      >
        <div className="ui-floating ui-breathing mx-auto flex h-24 w-24 items-center justify-center rounded-[1.35rem] bg-surface shadow-card"
        >
          <JcviMeowIcon className="h-14 w-14" />
        </div>
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-text-tertiary"
          >
            JCVI meow · {route.description}
          </p>
          <h1 className="mt-2 text-[1.8rem] font-semibold text-text-primary"
          >
            {isZh ? "正在准备多任务工作台" : "Preparing multi-task workbench"}
          </h1>
        </div>
        <p className="text-sm text-text-secondary"
        >{isZh ? "正在加载模板与分析 schema..." : "Loading template and analysis schema..."}</p>
      </section>
    );
  }

  if (loadError || !activeTask || !draft || validation === null) {
    return (
      <section className="ui-page-enter ui-app-frame grid h-screen w-full content-center justify-center gap-5 p-6 text-center"
      >
        <div className="mx-auto flex h-20 w-20 items-center justify-center rounded-2xl bg-rose-50 text-rose-500 dark:bg-rose-950/30"
        >
          <Loader2 className="h-10 w-10" />
        </div>
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-text-tertiary"
          >
            JCVI meow · {route.description}
          </p>
          <h1 className="mt-2 text-[1.8rem] font-semibold text-text-primary"
          >
            {isZh ? "工作台初始化失败" : "Workbench failed to initialize"}
          </h1>
        </div>
        <div className="max-w-2xl rounded-2xl border border-rose-200 bg-rose-50 p-5 text-left text-sm text-rose-700 dark:border-rose-900/40 dark:bg-rose-950/20 dark:text-rose-200"
        >
          <p className="font-semibold">{isZh ? "错误信息" : "Error message"}</p>
          <p className="mt-2 leading-relaxed">{loadError ?? (isZh ? "无法初始化任务草稿。" : "Unable to initialize task draft.")}</p>
        </div>
      </section>
    );
  }

  const directoryIssue = issueFor(validation.issues, "directory");
  const outputIssue = issueFor(validation.issues, "outputDirectory");
  const threadsIssue = issueFor(validation.issues, "runtime.threads");
  const minBlockIssue = issueFor(validation.issues, "parameters.synteny.minBlockSize");
  const workflowState = activeTask.runState?.status ?? "PENDING";
  const workflowStateLabel = localizeWorkflowState(workflowState, language);
  const progress = toProgressPercent(activeTask.runState?.progress ?? 0);
  const logLines = activeTask.runState?.logLines ?? [];
  const summaryView = activeTask.runState?.summaryView ?? null;
  const resolvedLogPath = activeTask.runState?.logPath ?? summaryView?.runLogPath ?? "";
  const resolvedSummaryPath = activeTask.runState?.summaryPath ?? summaryView?.runSummaryPath ?? "";
  const recentEvents = logLines.slice(-6).reverse();
  const usesImportedRequest = importedRequest !== null;
  const requestWorkflow = usesImportedRequest
    ? importedRequest?.kind ?? (activeTask.requestKind === "submodule" ? activeTask.capabilityId ?? "-" : draft.workflowId)
    : activeTask.requestKind === "submodule"
      ? activeTask.capabilityId ?? "-"
      : draft.workflowId;
  const requestMode = usesImportedRequest ? importedRequest?.inputMode ?? draft.inputMode : draft.inputMode;
  const requestSourceLabel = usesImportedRequest
    ? isZh
      ? "导入的请求 JSON"
      : "Imported request JSON"
    : isZh
      ? "当前草稿生成"
      : "Generated draft";
  const runStatusLabel =
    activeTask.runStatus === "starting"
      ? isZh
        ? "正在启动"
        : "Starting run"
      : activeTask.runStatus === "running"
        ? isZh
          ? "运行中"
          : "Running analysis"
        : activeTask.runStatus === "cancelling"
          ? isZh
            ? "正在取消"
            : "Cancelling run"
          : activeTask.runStatus === "cancelled"
            ? isZh
              ? "已取消"
              : "Run cancelled"
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
      : activeTask.runStatus === "cancelling"
        ? isZh
          ? "已请求取消，正在等待运行进程退出。"
          : "Cancel requested. Waiting for the run process to exit."
        : activeTask.runStatus === "cancelled"
          ? isZh
            ? "运行已取消，可以检查日志、恢复上下文或重新运行。"
            : "Run cancelled. You can inspect logs, restore context, or run again."
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
    <WorkbenchShell
      leftWidth={leftSidebarWidth}
      rightWidth={rightSidebarWidth}
      onLeftResize={setLeftSidebarWidth}
      onRightResize={setRightSidebarWidth}
      topBar={
        <header className="flex h-14 shrink-0 items-center justify-between gap-3 border-b border-border/90 bg-surface px-4">
          <button
            type="button"
            className={ICON_BUTTON_CLASS}
            title={isZh ? "返回首页" : "Back to home"}
            onClick={() => onNavigate("/")}
          >
            <ArrowLeft className="h-4 w-4" />
          </button>
          <span className="text-sm font-semibold text-text-primary">JCVI meow</span>
          <button
            type="button"
            className={ICON_BUTTON_CLASS}
            title={isZh ? "设置" : "Settings"}
            onClick={() => onNavigate("/settings")}
          >
            <Settings className="h-4 w-4" />
          </button>
        </header>
      }
      leftPanel={
        <WorkbenchLeftPanel
          tasks={leftPanelTasks}
          activeTaskId={activeTaskId}
          isZh={isZh}
          capabilities={capabilities}
          onSelectTask={setActiveTaskId}
          onCloseTask={closeTask}
          onAddTaskFromTemplate={(capabilityId, preset) => void createTask(capabilityId, preset)}
          onAddDataNode={() => {}}
          onDeleteSavedTask={deleteTask}
          onOpenSettings={() => onNavigate("/settings")}
        />
      }
      rightPanel={
        <WorkbenchRightPanel
          title={activeTask?.title ?? (isZh ? "未选择" : "No selection")}
          isZh={isZh}
          view={activeTask?.view ?? "setup"}
          onChangeView={(view) => activeTask && setTaskView(view)}
          onChangeTitle={(title) => activeTask && updateActiveTask((task) => ({ ...task, title }))}
          capabilities={capabilities}
          selectedCapabilityId={activeTask?.capabilityId ?? null}
          onChangeCapability={(id) => activeTask && updateActiveTask((task) => ({ ...task, capabilityId: id, requestKind: isOneStopCapability(id, capabilities) ? "workflow" : "submodule" }))}
        >
          <div className="text-sm text-text-secondary">
            {isZh ? "右侧 Inspector 内容正在接入..." : "Right inspector integration in progress..."}
          </div>
        </WorkbenchRightPanel>
      }
    >
      <div className="relative h-full w-full">
        <div className="absolute inset-0">
          <TaskNodeCanvas
            tasks={nodeTasks}
            activeTaskId={activeTaskId}
            isZh={isZh}
            onSelect={setActiveTaskId}
            onClose={closeTask}
            onAdd={() => void createTask()}
            onMove={moveTask}
            canClose={(taskId) => {
              const task = tasks.find((item) => item.id === taskId);
              return task ? canCloseTask(task) : false;
            }}
          />
        </div>

        <div className="pointer-events-none absolute inset-x-0 bottom-0 border-t border-border/90 bg-surface-raised/80 px-6 py-4 backdrop-blur">
          <div className="ui-surface-enter pointer-events-auto mx-auto flex max-w-4xl items-center gap-3 rounded-2xl border border-border bg-surface px-3 py-2 shadow-[0_6px_20px_rgba(15,23,42,0.06)] dark:shadow-[0_6px_20px_rgba(2,6,23,0.35)]">
            <button
              type="button"
              className={ICON_BUTTON_CLASS}
              title={isZh ? "新建任务" : "New task"}
              onClick={() => void createTask()}
            >
              <Plus className="h-4 w-4" />
            </button>

            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium text-text-primary">
                {usesImportedRequest ? requestSourceLabel : activeTask.title}
              </p>
              <div className="mt-1 flex flex-wrap gap-2 text-xs text-text-secondary">
                <span className="inline-flex items-center gap-1 rounded-full bg-surface px-2.5 py-1">
                  <Box className="h-3 w-3" />
                  {requestWorkflow}
                </span>
                <span className="inline-flex items-center gap-1 rounded-full bg-surface px-2.5 py-1">
                  <FolderOpen className="h-3 w-3" />
                  {draft.outputDirectory || (isZh ? "未选择 outdir" : "No outdir selected")}
                </span>
                <span
                  className={[
                    "inline-flex items-center gap-1 rounded-full px-2.5 py-1",
                    validation.issues.length === 0
                      ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-200"
                      : "bg-amber-50 text-amber-700 dark:bg-amber-950/30 dark:text-amber-200",
                  ].join(" ")}
                >
                  {validation.issues.length === 0 ? (
                    <>
                      <CheckCircle2 className="h-3 w-3" />
                      {isZh ? "已就绪" : "ready"}
                    </>
                  ) : (
                    <>
                      {isZh ? `${validation.issues.length} 个问题` : `${validation.issues.length} issue(s)`}
                    </>
                  )}
                </span>
              </div>
            </div>

            <div className="hidden shrink-0 items-center gap-2 sm:flex">
              <button
                type="button"
                className={ICON_BUTTON_CLASS}
                title={isZh ? "打开输出目录" : "Open output directory"}
                onClick={() => void handleOpenOutput()}
              >
                <FolderOpen className="h-4 w-4" />
              </button>
            </div>

            <button
              type="button"
              className={[
                "ui-pressable inline-flex items-center gap-1.5 rounded-full bg-ice-500 px-4 py-2 text-sm font-semibold text-white shadow-card hover:bg-ice-400 disabled:cursor-not-allowed disabled:opacity-50",
                activeTask.runStatus === "starting" || activeTask.runStatus === "running" || activeTask.runStatus === "cancelling"
                  ? "ui-running-progress"
                  : "",
              ].join(" ")}
              data-testid="bottom-run-action-button"
              disabled={activeTask.runStatus === "cancelling" || ((activeTask.runStatus === "starting" || activeTask.runStatus === "running") && !activeTask.runState?.runId)}
              onClick={
                activeTask.runStatus === "starting" || activeTask.runStatus === "running" || activeTask.runStatus === "cancelling"
                  ? () => void handleCancelRun()
                  : handlePrepareRun
              }
            >
              {activeTask.runStatus === "cancelling" ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  {isZh ? "取消中" : "Cancelling"}
                </>
              ) : activeTask.runStatus === "starting" || activeTask.runStatus === "running" ? (
                <>
                  <Ban className="h-4 w-4" />
                  {isZh ? "取消运行" : "Cancel run"}
                </>
              ) : (
                <>
                  <Play className="h-4 w-4" />
                  {isZh ? "运行" : "Run"}
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </WorkbenchShell>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="grid grid-cols-[5rem_minmax(0,1fr)] gap-3 rounded-lg px-2 py-1.5">
      <span className="text-xs font-medium text-text-tertiary">{label}</span>
      <span className="truncate font-mono text-xs text-text-secondary" title={value}>
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
          className="min-w-0 flex-1 rounded-lg border border-border bg-bg px-3 py-2 text-sm text-text-primary shadow-card outline-none transition focus:border-ice-400 focus:ring-2 focus:ring-ice-200 dark:focus:ring-ice-900/60"
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
