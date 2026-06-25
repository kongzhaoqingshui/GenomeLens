import { open } from "@tauri-apps/plugin-dialog";
import { mkdir, writeTextFile } from "@tauri-apps/plugin-fs";
import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  type KeyboardEvent as ReactKeyboardEvent,
  type PointerEvent as ReactPointerEvent,
} from "react";

import { GameIcon, type GameIconName } from "../components/GameIcon";
import { SubmoduleForm } from "../components/SubmoduleForm";
import { useLanguage } from "../i18n/useLanguage";
import type { CapabilityEntry } from "../models/capability";
import { getCapabilitySubtitle, resolveLegacyCapabilityId } from "../models/capability";
import type { OutputFormat } from "../models/workflow-request";
import type { WorkflowRequestInputMode } from "../models/workflow-request-draft";
import type { SpeciesInputDraft, WorkflowRequestDraft } from "../models/workflow-request-draft";
import {
  createDraftForCapability,
  getJcviCapabilityById,
  listJcviCapabilities,
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
type ResizeSide = "left" | "right";
type InputMode = WorkflowRequestInputMode;
type SyntenyNumberField = "cscore" | "dist" | "iter";
type PlotNumberField = "dpi";
type LocalNumberField = "up" | "down";

interface ResizeDragState {
  side: ResizeSide;
  startX: number;
  startLeftWidth: number;
  startRightWidth: number;
}

interface WorkbenchWidths {
  left: number;
  right: number;
}

type RequestKind = "workflow" | "submodule";

interface WorkbenchTask {
  id: string;
  title: string;
  capabilityId: string | null;
  preset?: string;
  requestKind: RequestKind;
  icon: GameIconName;
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
  "mt-2 w-full rounded-lg border border-border bg-bg px-3 py-2 text-sm text-text-primary shadow-card outline-none transition focus:border-ice-400 focus:ring-2 focus:ring-ice-200 dark:focus:ring-ice-900/60";
const LABEL_CLASS = "text-xs font-semibold uppercase tracking-[0.14em] text-text-tertiary";
const CHECKBOX_CLASS = "h-4 w-4 rounded border-border text-ice-500 focus:ring-ice-500";
const PANEL_BODY_CLASS = "ui-surface-enter border-b border-border/90 bg-surface-raised/80 px-1 py-6 last:border-b-0";
const SECONDARY_BUTTON_CLASS =
  "ui-pressable rounded-lg border border-border bg-surface-raised/80 px-3 py-2 text-xs font-semibold text-text-secondary transition hover:border-ice-200 hover:bg-ice-50 hover:text-ice-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ice-500 dark:hover:border-ice-800 dark:hover:bg-ice-900/30 dark:hover:text-ice-200 disabled:cursor-not-allowed disabled:opacity-45";
const PRIMARY_BUTTON_CLASS =
  "ui-pressable rounded-lg bg-ice-500 px-4 py-2 text-sm font-semibold text-white shadow-lg shadow-ice-500/20 transition hover:bg-ice-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ice-500 focus-visible:ring-offset-2 focus-visible:ring-offset-bg disabled:cursor-not-allowed disabled:opacity-50";
const RECENT_OUTDIRS_KEY = "genomelens.gui.recentOutdirs";
const RECENT_REQUESTS_KEY = "genomelens.gui.recentRequests";
const WORKBENCH_LEFT_WIDTH_KEY = "genomelens.gui.workbench.leftWidth";
const WORKBENCH_RIGHT_WIDTH_KEY = "genomelens.gui.workbench.rightWidth";
const RECENT_HINT_LIMIT = 4;
const WORKBENCH_DEFAULT_LEFT_WIDTH = 320;
const WORKBENCH_DEFAULT_RIGHT_WIDTH = 368;
const WORKBENCH_MIN_LEFT_WIDTH = 248;
const WORKBENCH_MAX_LEFT_WIDTH = 480;
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

function clampWorkbenchWidths(leftWidth: number, rightWidth: number, width = viewportWidth()): WorkbenchWidths {
  let left = clampNumber(Math.round(leftWidth), WORKBENCH_MIN_LEFT_WIDTH, WORKBENCH_MAX_LEFT_WIDTH);
  let right = clampNumber(Math.round(rightWidth), WORKBENCH_MIN_RIGHT_WIDTH, WORKBENCH_MAX_RIGHT_WIDTH);
  const availableForSidebars = width - WORKBENCH_RESIZER_WIDTH * 2 - WORKBENCH_MIN_CENTER_WIDTH;

  if (availableForSidebars <= WORKBENCH_MIN_LEFT_WIDTH + WORKBENCH_MIN_RIGHT_WIDTH) {
    return {
      left: WORKBENCH_MIN_LEFT_WIDTH,
      right: WORKBENCH_MIN_RIGHT_WIDTH,
    };
  }

  const total = left + right;
  if (total <= availableForSidebars) {
    return { left, right };
  }

  let overflow = total - availableForSidebars;
  const rightShrink = Math.min(right - WORKBENCH_MIN_RIGHT_WIDTH, Math.ceil(overflow / 2));
  right -= rightShrink;
  overflow -= rightShrink;
  const leftShrink = Math.min(left - WORKBENCH_MIN_LEFT_WIDTH, overflow);
  left -= leftShrink;
  overflow -= leftShrink;

  if (overflow > 0) {
    right = Math.max(WORKBENCH_MIN_RIGHT_WIDTH, right - overflow);
  }

  return { left, right };
}

function readInitialWorkbenchWidths(): WorkbenchWidths {
  return clampWorkbenchWidths(
    readStoredNumber(WORKBENCH_LEFT_WIDTH_KEY, WORKBENCH_DEFAULT_LEFT_WIDTH),
    readStoredNumber(WORKBENCH_RIGHT_WIDTH_KEY, WORKBENCH_DEFAULT_RIGHT_WIDTH),
  );
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
  };
}

function statusTone(status: RunPanelStatus): string {
  switch (status) {
    case "running":
    case "starting":
      return "bg-sky-100 text-sky-700 dark:bg-sky-400/15 dark:text-sky-200";
    case "finished":
      return "bg-emerald-100 text-emerald-700 dark:bg-emerald-400/15 dark:text-emerald-200";
    case "cancelled":
      return "bg-slate-100 text-slate-600 dark:bg-slate-700/50 dark:text-slate-300";
    case "error":
      return "bg-rose-100 text-rose-700 dark:bg-rose-400/15 dark:text-rose-200";
    case "confirming":
    case "cancelling":
      return "bg-amber-100 text-amber-700 dark:bg-amber-400/15 dark:text-amber-200";
    default:
      return "bg-surface text-text-secondary";
  }
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
  const [taskFilter, setTaskFilter] = useState("");
  const [recentOutdirs, setRecentOutdirs] = useState<string[]>(() => readStoredJson<string[]>(RECENT_OUTDIRS_KEY, []));
  const [recentRequests, setRecentRequests] = useState<RecentRequestHint[]>(() =>
    readStoredJson<RecentRequestHint[]>(RECENT_REQUESTS_KEY, []),
  );
  const [sidebarWidths, setSidebarWidths] = useState(readInitialWorkbenchWidths);
  const [activeResize, setActiveResize] = useState<ResizeDragState | null>(null);
  const leftSidebarWidth = sidebarWidths.left;
  const rightSidebarWidth = sidebarWidths.right;

  useEffect(() => {
    writeStoredJson(RECENT_OUTDIRS_KEY, recentOutdirs);
  }, [recentOutdirs]);

  useEffect(() => {
    writeStoredJson(RECENT_REQUESTS_KEY, recentRequests);
  }, [recentRequests]);

  useEffect(() => {
    writeStoredNumber(WORKBENCH_LEFT_WIDTH_KEY, leftSidebarWidth);
  }, [leftSidebarWidth]);

  useEffect(() => {
    writeStoredNumber(WORKBENCH_RIGHT_WIDTH_KEY, rightSidebarWidth);
  }, [rightSidebarWidth]);

  useEffect(() => {
    const reclampWidths = () => {
      setSidebarWidths((currentWidths) => {
        const nextWidths = clampWorkbenchWidths(currentWidths.left, currentWidths.right);
        if (nextWidths.left === currentWidths.left && nextWidths.right === currentWidths.right) {
          return currentWidths;
        }
        return nextWidths;
      });
    };

    reclampWidths();
    window.addEventListener("resize", reclampWidths);

    return () => {
      window.removeEventListener("resize", reclampWidths);
    };
  }, []);

  const resizeSidebar = useCallback((side: ResizeSide, nextWidth: number) => {
    setSidebarWidths((currentWidths) =>
      clampWorkbenchWidths(
        side === "left" ? nextWidth : currentWidths.left,
        side === "right" ? nextWidth : currentWidths.right,
      ),
    );
  }, []);

  const handleResizeKeyDown = useCallback(
    (side: ResizeSide, event: ReactKeyboardEvent<HTMLDivElement>) => {
      const step = event.shiftKey ? 40 : 16;
      if (event.key === "Home") {
        event.preventDefault();
        resizeSidebar(side, side === "left" ? WORKBENCH_MIN_LEFT_WIDTH : WORKBENCH_MIN_RIGHT_WIDTH);
        return;
      }
      if (event.key === "End") {
        event.preventDefault();
        resizeSidebar(side, side === "left" ? WORKBENCH_MAX_LEFT_WIDTH : WORKBENCH_MAX_RIGHT_WIDTH);
        return;
      }
      if (event.key === "Enter") {
        event.preventDefault();
        resizeSidebar(side, side === "left" ? WORKBENCH_DEFAULT_LEFT_WIDTH : WORKBENCH_DEFAULT_RIGHT_WIDTH);
        return;
      }
      if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") {
        return;
      }

      event.preventDefault();
      const direction = event.key === "ArrowRight" ? 1 : -1;
      const currentWidth = side === "left" ? leftSidebarWidth : rightSidebarWidth;
      const nextWidth = side === "left" ? currentWidth + direction * step : currentWidth - direction * step;
      resizeSidebar(side, nextWidth);
    },
    [leftSidebarWidth, resizeSidebar, rightSidebarWidth],
  );

  const handleResizePointerDown = useCallback(
    (side: ResizeSide, event: ReactPointerEvent<HTMLDivElement>) => {
      event.preventDefault();
      event.currentTarget.setPointerCapture(event.pointerId);
      setActiveResize({
        side,
        startX: event.clientX,
        startLeftWidth: leftSidebarWidth,
        startRightWidth: rightSidebarWidth,
      });
    },
    [leftSidebarWidth, rightSidebarWidth],
  );

  const finishActiveResize = useCallback(() => {
    setActiveResize(null);
  }, []);

  useEffect(() => {
    if (!activeResize) {
      return;
    }

    const previousCursor = document.body.style.cursor;
    const previousUserSelect = document.body.style.userSelect;
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";

    const handlePointerMove = (event: PointerEvent) => {
      const delta = event.clientX - activeResize.startX;
      if (activeResize.side === "left") {
        setSidebarWidths(
          clampWorkbenchWidths(activeResize.startLeftWidth + delta, activeResize.startRightWidth),
        );
        return;
      }
      setSidebarWidths(
        clampWorkbenchWidths(activeResize.startLeftWidth, activeResize.startRightWidth - delta),
      );
    };

    window.addEventListener("pointermove", handlePointerMove);
    window.addEventListener("pointerup", finishActiveResize);
    window.addEventListener("pointercancel", finishActiveResize);
    window.addEventListener("lostpointercapture", finishActiveResize);

    return () => {
      window.removeEventListener("pointermove", handlePointerMove);
      window.removeEventListener("pointerup", finishActiveResize);
      window.removeEventListener("pointercancel", finishActiveResize);
      window.removeEventListener("lostpointercapture", finishActiveResize);
      document.body.style.cursor = previousCursor;
      document.body.style.userSelect = previousUserSelect;
    };
  }, [activeResize, finishActiveResize]);

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

  const visibleTasks = useMemo(() => {
    const query = taskFilter.trim().toLowerCase();
    if (!query) {
      return tasks;
    }
    return tasks.filter((task) => {
      const capabilityLabel = task.capability ? getCapabilitySubtitle(task.capability, isZh) : "";
      return [task.title, task.capabilityId, capabilityLabel]
        .filter(Boolean)
        .some((value) => String(value).toLowerCase().includes(query));
    });
  }, [isZh, taskFilter, tasks]);

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
      <section className="ui-page-enter ui-app-frame grid h-screen w-full content-center justify-center gap-4 text-center">
        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-text-tertiary">
          JCVI meow · {route.description}
        </p>
        <h1 className="text-[1.8rem] font-semibold text-text-primary">{isZh ? "正在准备多任务工作台" : "Preparing multi-task workbench"}</h1>
        <p className="text-sm text-text-secondary">{isZh ? "正在加载模板与分析 schema..." : "Loading template and analysis schema..."}</p>
      </section>
    );
  }

  if (loadError || !activeTask || !draft || validation === null) {
    return (
      <section className="ui-page-enter ui-app-frame grid h-screen w-full content-center justify-center gap-4 text-center">
        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-text-tertiary">
          JCVI meow · {route.description}
        </p>
        <h1 className="text-[1.8rem] font-semibold text-text-primary">{isZh ? "工作台初始化失败" : "Workbench failed to initialize"}</h1>
        <p className="max-w-2xl rounded-[1.35rem] border border-rose-200 bg-rose-50 p-4 text-left text-sm text-rose-700">
          {loadError ?? (isZh ? "无法初始化任务草稿。" : "Unable to initialize task draft.")}
        </p>
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
  const workbenchGridStyle = {
    gridTemplateColumns: `${leftSidebarWidth}px ${WORKBENCH_RESIZER_WIDTH}px minmax(0, 1fr) ${WORKBENCH_RESIZER_WIDTH}px ${rightSidebarWidth}px`,
  };

  return (
    <div className="ui-page-enter ui-app-frame grid h-screen w-full overflow-hidden" style={workbenchGridStyle}>
      <aside className="ui-shell-sidebar flex min-h-0 flex-col overflow-hidden border-r px-2.5 py-3">
        <div className="flex items-center gap-2.5 px-2.5 pb-3">
          <button type="button" className="ui-pressable text-sm text-text-secondary hover:text-text-primary" onClick={() => onNavigate("/")}>
            ←
          </button>
          <span className="text-sm font-semibold text-text-primary">JCVI meow</span>
        </div>

        <nav className="grid gap-1 px-1 pb-4 text-sm text-text-secondary">
          <button type="button" className="ui-list-item flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-left hover:bg-surface-raised/80" onClick={() => createTask()}>
            <GameIcon name="pairwise" className="h-4 w-4" />
            新任务
          </button>
          <label className="ui-list-item flex items-center gap-2.5 rounded-lg px-2.5 py-2 hover:bg-surface-raised/80">
            <GameIcon name="environment" className="h-4 w-4" />
            <input
              className="min-w-0 flex-1 bg-transparent text-sm text-text-primary outline-none placeholder:text-text-secondary"
              placeholder="搜索"
              value={taskFilter}
              onChange={(event) => setTaskFilter(event.target.value)}
            />
          </label>
        </nav>

        <div className="px-1.5 pb-2">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-xs font-medium text-text-tertiary">置顶</p>
              <h2 className="mt-3 text-sm font-semibold text-text-secondary">{isZh ? "任务" : "Tasks"}</h2>
            </div>
            <button type="button" className="ui-pressable rounded-lg px-2 py-1 text-base leading-none text-text-secondary hover:bg-surface-raised/80" onClick={() => createTask()}>
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
                "ui-list-item mb-1 grid w-full grid-cols-[1.5rem_minmax(0,1fr)_1.5rem] items-center gap-2 rounded-lg px-2.5 py-2 text-left transition",
                task.id === activeTask.id
                  ? "border border-border bg-surface-raised text-text-primary shadow-card"
                  : "bg-transparent text-text-secondary hover:bg-surface-raised/60",
              ].join(" ")}
              onClick={() => setActiveTaskId(task.id)}
            >
              <span className="flex h-6 w-6 items-center justify-center text-text-secondary">
                <GameIcon name={task.icon} className="h-[14px] w-[14px]" />
              </span>
              <span className="min-w-0">
                <span className="block truncate text-[13px] font-medium leading-5">{task.title}</span>
                <span className="mt-0.5 block truncate text-[11px] leading-4 text-text-tertiary">
                  {task.requestKind === "submodule" ? task.capabilityId ?? task.draft.workflowId : task.draft.workflowId}
                </span>
              </span>
              {tasks.length > 1 && canCloseTask(task) ? (
                <span
                  role="button"
                  tabIndex={0}
                  className="ui-pressable flex h-6 w-6 items-center justify-center rounded-md text-[11px] text-text-tertiary hover:bg-surface hover:text-text-primary"
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

        <div className="border-t border-border/90 px-1 py-2.5">
          <p className="hidden px-3 text-xs font-medium text-text-tertiary">快速创建</p>
          <div className="hidden">
            {capabilities.map((capability) => {
              const disabled = capability.status !== "connected" || capability.id === "environment-check";
              return (
                <button
                  key={capability.id}
                  type="button"
                  disabled={disabled}
                  className="flex items-center gap-2.5 rounded-lg px-2.5 py-1.5 text-left text-xs font-medium text-text-secondary transition hover:bg-surface-raised/80 disabled:cursor-not-allowed disabled:opacity-45"
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
            className="ui-list-item flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-left text-sm text-text-secondary hover:bg-surface-raised/80"
            onClick={() => onNavigate("/settings")}
          >
            <GameIcon name="environment" className="h-4 w-4" />
            设置
          </button>
        </div>
      </aside>

      <WorkbenchResizeHandle
        side="left"
        isActive={activeResize?.side === "left"}
        label={isZh ? "调整左侧栏宽度" : "Resize left sidebar"}
        value={leftSidebarWidth}
        min={WORKBENCH_MIN_LEFT_WIDTH}
        max={WORKBENCH_MAX_LEFT_WIDTH}
        onPointerDown={handleResizePointerDown}
        onKeyDown={handleResizeKeyDown}
        onResizeEnd={finishActiveResize}
      />

      <main className="flex min-w-0 flex-col overflow-hidden bg-surface-raised">
        <header className="flex h-16 shrink-0 items-center justify-between border-b border-border/90 px-6">
          <div className="min-w-0">
            <input
              className="w-full min-w-0 bg-transparent text-base font-semibold tracking-tight text-text-primary outline-none"
              value={activeTask.title}
              onChange={(event) => updateActiveTask((task) => ({ ...task, title: event.target.value }))}
            />
            <p className="mt-1 text-xs text-text-secondary">
              {isZh ? "创建于" : "Created"} {formatTime(activeTask.createdAt)} · {isZh ? "更新于" : "Updated"} {formatTime(activeTask.updatedAt)}
            </p>
          </div>
          <div className="flex shrink-0 items-center gap-3">
            <button
              type="button"
              className="ui-pressable rounded-xl border border-border bg-surface-raised px-3 py-2 text-xs font-medium text-text-secondary shadow-card"
              onClick={handleOpenOutput}
            >
              打开位置
            </button>
            <div className="flex items-center gap-1 rounded-xl bg-surface p-1">
              {(["setup", "run", "results"] satisfies WorkbenchView[]).map((view) => (
                <button
                  key={view}
                  type="button"
                  className={
                    activeTask.view === view
                      ? "ui-pressable rounded-lg border border-border bg-surface-raised px-3 py-1.5 text-xs font-semibold uppercase text-text-primary shadow-card"
                      : "ui-pressable rounded-lg px-3 py-1.5 text-xs font-semibold uppercase text-text-secondary hover:bg-surface-raised/80 hover:text-text-primary"
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
            activeTask.requestKind === "submodule" && activeTask.capability && activeTask.submoduleDraft ? (
              <SubmoduleForm
                draft={activeTask.submoduleDraft}
                spec={activeTask.capability}
                isZh={isZh}
                onChange={(nextDraft) =>
                  updateActiveTask((task) => ({ ...task, submoduleDraft: nextDraft }))
                }
                onPickFile={pickFile}
                onPickDirectory={pickDirectory}
              />
            ) : (
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
                      onChange={(event) => patchDraft({ inputMode: event.target.value as InputMode })}
                    >
                      <option value="auto_directory">auto_directory</option>
                      <option value="bed_cds">bed_cds</option>
                      <option value="gff_genome">gff_genome</option>
                    </select>
                  </label>
                  <label>
                    <span className={LABEL_CLASS}>workflow</span>
                    <input
                      className={FIELD_CLASS}
                      value={draft.workflowId}
                      readOnly
                      disabled
                    />
                  </label>
                </div>

                <div className="mt-4 grid gap-4">
                  <label>
                    <span className={LABEL_CLASS}>{isZh ? "输入目录" : "input directory"}</span>
                    <div className="mt-2 flex gap-2">
                      <input
                        className="min-w-0 flex-1 rounded-lg border border-border bg-bg px-3 py-2 text-sm text-text-primary shadow-card outline-none transition focus:border-ice-400 focus:ring-2 focus:ring-ice-200 dark:focus:ring-ice-900/60"
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
                        className="min-w-0 flex-1 rounded-lg border border-border bg-bg px-3 py-2 text-sm text-text-primary shadow-card outline-none transition focus:border-ice-400 focus:ring-2 focus:ring-ice-200 dark:focus:ring-ice-900/60"
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
                        <span className="text-[11px] font-medium uppercase tracking-[0.16em] text-text-tertiary">{isZh ? "最近输出目录" : "Recent outdir"}</span>
                        {recentOutdirs.map((path) => (
                          <button
                            key={path}
                            type="button"
                            className="ui-pressable rounded-full border border-border bg-surface-raised px-3 py-1 text-xs text-text-secondary hover:border-ice-200 hover:bg-ice-50 hover:text-ice-700 dark:hover:border-ice-800 dark:hover:bg-ice-900/30 dark:hover:text-ice-200"
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

                <div className="ui-muted-strip mt-5 rounded-xl border p-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold text-text-primary">{isZh ? "导入 request JSON" : "Import request JSON"}</p>
                      <p className="mt-1 text-sm leading-6 text-text-secondary">
                        {isZh
                          ? "附加一个现有的 request JSON 文件，直接运行，而不必重新填写向导。"
                          : "Attach an existing request JSON file and run it directly without rebuilding the request from the wizard."}
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
                    <div className="mt-4 grid gap-2 rounded-xl border border-border bg-surface-raised px-4 py-3 text-sm text-text-secondary">
                      <InfoRow label={isZh ? "来源" : "source"} value={isZh ? "导入的 request JSON" : "Imported request JSON"} />
                      <InfoRow label="request" value={importedRequest?.path ?? "-"} />
                      <InfoRow label={isZh ? "工作流" : "workflow"} value={importedRequest?.workflowId ?? "-"} />
                      <InfoRow label={isZh ? "类型" : "kind"} value={importedRequest?.kind ?? "-"} />
                      <InfoRow label={isZh ? "模式" : "mode"} value={importedRequest?.inputMode ?? "-"} />
                      <InfoRow
                        label={isZh ? "请求内 outdir" : "request outdir"}
                        value={importedRequest?.requestOutputDirectory || (isZh ? "导入 JSON 未声明" : "Not declared in imported JSON")}
                      />
                      <p className="pt-1 text-xs leading-5 text-text-secondary">
                        {isZh
                          ? "运行会直接使用上面的导入 request 路径，并配合当前面板里显示的任务输出目录。"
                          : "Run uses the imported request path above and the current task output directory shown in this panel."}
                      </p>
                    </div>
                  ) : (
                    <p className="mt-4 text-sm text-text-secondary">
                      {isZh
                        ? "当前没有附加导入请求，本任务仍会由向导草稿生成 request JSON。"
                        : "No imported request is attached. The current wizard draft still generates the request JSON for this task."}
                    </p>
                  )}
                  {recentRequests.length > 0 ? (
                    <div className="mt-4 flex flex-wrap items-center gap-2">
                      <span className="text-[11px] font-medium uppercase tracking-[0.16em] text-text-tertiary">{isZh ? "最近 request" : "Recent request"}</span>
                      {recentRequests.map((item) => (
                        <button
                          key={item.path}
                          type="button"
                          className="ui-pressable rounded-full border border-border bg-surface-raised px-3 py-1 text-left text-xs text-text-secondary hover:border-ice-200 hover:bg-ice-50 hover:text-ice-700 dark:hover:border-ice-800 dark:hover:bg-ice-900/30 dark:hover:text-ice-200"
                          onClick={() => void attachImportedRequest(item.path)}
                          title={item.path}
                        >
                          <span className="block max-w-56 truncate">{item.path}</span>
                          <span className="mt-0.5 block text-[10px] uppercase tracking-[0.14em] text-text-tertiary">
                            {item.kind ?? item.workflowId ?? "request"}
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
                  title={isZh ? "工作流选项" : "Workflow options"}
                  subtitle={isZh ? "保持 transport 字段与 GenomeLens WorkflowRequest 契约一致。" : "Keep transport fields aligned with the GenomeLens WorkflowRequest contract."}
                />
                <div className="mt-4 grid gap-4 lg:grid-cols-3">
                  <label>
                    <span className={LABEL_CLASS}>threads</span>
                    <input
                      className={FIELD_CLASS}
                      type="number"
                      min={1}
                      value={draft.runtime.threads ?? ""}
                      onChange={(event) => patchRuntime({ threads: updateNumber(event.target.value) })}
                    />
                    <IssueText issue={threadsIssue} />
                  </label>
                  <label>
                    <span className={LABEL_CLASS}>log level</span>
                    <select
                      className={FIELD_CLASS}
                      value={draft.runtime.logLevel}
                      onChange={(event) => patchRuntime({ logLevel: event.target.value as WorkflowRequestDraft["runtime"]["logLevel"] })}
                    >
                      {LOG_LEVELS.map((level) => (
                        <option key={level} value={level}>
                          {level}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    <span className={LABEL_CLASS}>reference index</span>
                    <input
                      className={FIELD_CLASS}
                      type="number"
                      min={0}
                      value={draft.referenceIndex}
                      onChange={(event) => patchDraft({ referenceIndex: Number(event.target.value) })}
                    />
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
                              ? draft.runtime.verbose
                              : draft.runtime.consoleLog
                        }
                        onChange={(event) => {
                          if (key === "forceOutput") {
                            patchDraft({ forceOutput: event.target.checked });
                          } else if (key === "verbose") {
                            patchRuntime({ verbose: event.target.checked });
                          } else {
                            patchRuntime({ consoleLog: event.target.checked });
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
                  title={isZh ? "Synteny 参数" : "Synteny parameters"}
                  subtitle={isZh ? "Synteny 算法与图件参数，保留为任务本地设置。" : "Synteny algorithm and figure parameters remain task-local."}
                />
                <div className="mt-4 grid gap-4 lg:grid-cols-3">
                  <label>
                    <span className={LABEL_CLASS}>align_soft</span>
                    <select
                      className={FIELD_CLASS}
                      value={draft.parameters.synteny.alignSoft}
                      onChange={(event) => patchSynteny({ alignSoft: event.target.value as WorkflowRequestDraft["parameters"]["synteny"]["alignSoft"] })}
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
                      value={draft.parameters.synteny.dbtype}
                      onChange={(event) => patchSynteny({ dbtype: event.target.value as WorkflowRequestDraft["parameters"]["synteny"]["dbtype"] })}
                    >
                      <option value="nucl">nucl</option>
                      <option value="prot">prot</option>
                    </select>
                  </label>
                  <label>
                    <span className={LABEL_CLASS}>figsize</span>
                    <input
                      className={FIELD_CLASS}
                      value={draft.parameters.plot.figsize}
                      onChange={(event) => patchPlot({ figsize: event.target.value })}
                    />
                  </label>
                  {SYNTENY_NUMBER_FIELDS.map(({ key, label, min, max, step }) => (
                    <label key={key}>
                      <span className={LABEL_CLASS}>{label}</span>
                      <input
                        className={FIELD_CLASS}
                        type="number"
                        min={min}
                        max={max}
                        step={step}
                        value={draft.parameters.synteny[key]}
                        onChange={(event) => patchSynteny({ [key]: Number(event.target.value) })}
                      />
                    </label>
                  ))}
                  <label>
                    <span className={LABEL_CLASS}>min block size</span>
                    <input
                      className={FIELD_CLASS}
                      type="number"
                      min={1}
                      value={draft.parameters.synteny.minBlockSize}
                      onChange={(event) => patchSynteny({ minBlockSize: updateNumber(event.target.value) ?? undefined })}
                    />
                    <IssueText issue={minBlockIssue} />
                  </label>
                </div>

                <div className="mt-5 grid gap-3 lg:grid-cols-2">
                  {[
                    ["allowSimplifiedFallback", "allow_simplified_fallback"],
                  ].map(([key, label]) => (
                    <label key={key} className="inline-flex items-center gap-2 text-sm font-medium text-text-secondary">
                      <input
                        className={CHECKBOX_CLASS}
                        type="checkbox"
                        checked={draft.parameters.synteny[key as keyof typeof draft.parameters.synteny] as boolean}
                        onChange={(event) => patchSynteny({ [key]: event.target.checked })}
                      />
                      {label}
                    </label>
                  ))}
                </div>
              </section>

              <section className={PANEL_BODY_CLASS}>
                <SectionTitle
                  title={isZh ? "图件参数" : "Plot parameters"}
                  subtitle={isZh ? "图件样式与 DPI 设置。" : "Figure styling and DPI settings."}
                />
                <div className="mt-4 grid gap-4 lg:grid-cols-3">
                  <label>
                    <span className={LABEL_CLASS}>glyphstyle</span>
                    <select
                      className={FIELD_CLASS}
                      value={draft.parameters.plot.glyphstyle}
                      onChange={(event) => patchPlot({ glyphstyle: event.target.value })}
                    >
                      <option value=""></option>
                      <option value="box">box</option>
                      <option value="arrow">arrow</option>
                    </select>
                  </label>
                  <label>
                    <span className={LABEL_CLASS}>glyphcolor</span>
                    <select
                      className={FIELD_CLASS}
                      value={draft.parameters.plot.glyphcolor}
                      onChange={(event) => patchPlot({ glyphcolor: event.target.value })}
                    >
                      <option value=""></option>
                      <option value="orientation">orientation</option>
                      <option value="orthogroup">orthogroup</option>
                    </select>
                  </label>
                  <label>
                    <span className={LABEL_CLASS}>shadestyle</span>
                    <select
                      className={FIELD_CLASS}
                      value={draft.parameters.plot.shadestyle}
                      onChange={(event) => patchPlot({ shadestyle: event.target.value })}
                    >
                      <option value=""></option>
                      <option value="curve">curve</option>
                      <option value="line">line</option>
                    </select>
                  </label>
                  {PLOT_NUMBER_FIELDS.map(({ key, label, min, step }) => (
                    <label key={key}>
                      <span className={LABEL_CLASS}>{label}</span>
                      <input
                        className={FIELD_CLASS}
                        type="number"
                        min={min}
                        step={step}
                        value={draft.parameters.plot[key]}
                        onChange={(event) => patchPlot({ [key]: Number(event.target.value) })}
                      />
                    </label>
                  ))}
                </div>
              </section>

              <section className={PANEL_BODY_CLASS}>
                <SectionTitle
                  title={isZh ? "局部共线性参数" : "Local synteny parameters"}
                  subtitle={isZh ? "目标基因与上下游窗口设置。" : "Target gene and flanking window settings."}
                />
                <div className="mt-4 grid gap-4 lg:grid-cols-3">
                  {LOCAL_NUMBER_FIELDS.map(({ key, label, min, step }) => (
                    <label key={key}>
                      <span className={LABEL_CLASS}>{label}</span>
                      <input
                        className={FIELD_CLASS}
                        type="number"
                        min={min}
                        step={step}
                        value={draft.parameters.localSynteny[key]}
                        onChange={(event) => patchLocalSynteny({ [key]: Number(event.target.value) })}
                      />
                    </label>
                  ))}
                </div>

                <label className="mt-4 block">
                  <span className={LABEL_CLASS}>target_gene_ids</span>
                  <textarea
                    className={`${FIELD_CLASS} min-h-24`}
                    value={targetGeneText}
                    onChange={(event) => patchLocalSynteny({ targetGeneIds: splitTargets(event.target.value) })}
                    placeholder="One gene id per line, or comma-separated"
                  />
                  <IssueText issue={issueFor(validation?.issues ?? [], "parameters.localSynteny.targetGeneIds")} />
                </label>

                <div className="mt-5 grid gap-3 lg:grid-cols-2">
                  {[
                    ["splitTargets", "split_targets"],
                    ["labelTargets", "label_targets"],
                    ["useNativeRenderer", "use_native_renderer"],
                  ].map(([key, label]) => (
                    <label key={key} className="inline-flex items-center gap-2 text-sm font-medium text-text-secondary">
                      <input
                        className={CHECKBOX_CLASS}
                        type="checkbox"
                        checked={draft.parameters.localSynteny[key as keyof typeof draft.parameters.localSynteny] as boolean}
                        onChange={(event) => patchLocalSynteny({ [key]: event.target.checked })}
                      />
                      {label}
                    </label>
                  ))}
                </div>
              </section>
            </div>
          )
          ) : null}

          {activeTask.view === "run" ? (
            <div className="mx-auto grid w-full max-w-4xl gap-6">
              <section className={PANEL_BODY_CLASS}>
                <SectionTitle
                  title={isZh ? "运行控制" : "Run control"}
                  subtitle={isZh ? "一个任务对应一个 request 文件和一次 GenomeLens 运行。" : "One task maps to one request file and one GenomeLens run."}
                />
                {usesImportedRequest ? (
                  <div className="mt-4 rounded-xl border border-border bg-surface px-4 py-3 text-sm text-text-secondary">
                    <p className="font-medium text-text-primary">{isZh ? "已附加导入请求" : "Imported request attached"}</p>
                    <p className="mt-1 break-all font-mono text-xs leading-6 text-text-secondary">{importedRequest?.path ?? "-"}</p>
                    <p className="mt-2 text-xs leading-5 text-text-secondary">
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
                    disabled={
                      activeTask.runStatus === "starting" ||
                      activeTask.runStatus === "running" ||
                      activeTask.runStatus === "cancelling"
                    }
                    onClick={handlePrepareRun}
                  >
                    {isZh ? "运行当前任务" : "Run active task"}
                  </button>
                  {activeTask.runStatus === "starting" ||
                  activeTask.runStatus === "running" ||
                  activeTask.runStatus === "cancelling" ? (
                    <button
                      type="button"
                      className={SECONDARY_BUTTON_CLASS}
                      data-testid="cancel-run-button"
                      disabled={activeTask.runStatus === "cancelling" || !activeTask.runState?.runId}
                      onClick={() => void handleCancelRun()}
                    >
                      {activeTask.runStatus === "cancelling"
                        ? isZh
                          ? "取消中..."
                          : "Cancelling..."
                        : isZh
                          ? "取消运行"
                          : "Cancel run"}
                    </button>
                  ) : null}
                  <button type="button" className={SECONDARY_BUTTON_CLASS} onClick={handleReadLog}>
                    {isZh ? "刷新日志" : "Refresh log"}
                  </button>
                  <button type="button" className={SECONDARY_BUTTON_CLASS} onClick={handleReadSummary}>
                    {isZh ? "读取摘要" : "Read summary"}
                  </button>
                  <button
                    type="button"
                    className={SECONDARY_BUTTON_CLASS}
                    data-testid="restore-run-snapshot-button"
                    disabled={!activeTask.runState?.outdir && !draft.outputDirectory.trim()}
                    onClick={() => void handleReadSnapshot()}
                  >
                    {isZh ? "恢复上下文" : "Restore context"}
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
                  <div className="grid gap-2 rounded-lg border border-border/90 bg-surface-raised/80 px-3 py-3 text-sm text-text-secondary">
                    <InfoRow label={isZh ? "来源" : "source"} value={requestSourceLabel} />
                    <InfoRow label="workflow" value={requestWorkflow} />
                    <InfoRow label={isZh ? "模式" : "mode"} value={requestMode} />
                    <InfoRow label="outdir" value={draft.outputDirectory || "-"} />
                    <InfoRow label="request" value={requestSourcePath} />
                    <p className="ui-message-enter text-xs leading-5 text-text-secondary">{runHint}</p>
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
                    <div className="ui-summary-reveal rounded-lg border border-border/90 bg-surface-raised/85 px-3 py-3">
                      <div className="flex items-center justify-between gap-3">
                        <p className="text-sm font-semibold text-text-primary">{isZh ? "摘要已就绪" : "Summary ready"}</p>
                        <span className="text-xs font-medium text-text-tertiary">{summaryView.status}</span>
                      </div>
                      <div className="mt-3 grid gap-2 text-sm text-text-secondary sm:grid-cols-3">
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
                  <h3 className="text-sm font-semibold text-text-primary">{isZh ? "确认 request JSON" : "Confirm request JSON"}</h3>
                  <div className="mt-3 grid gap-2 rounded-lg border border-amber-200/80 bg-surface-raised/85 px-3 py-3 text-sm text-text-secondary dark:border-amber-900/40">
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
                        <InfoRow label={isZh ? "类型" : "kind"} value={importedRequest?.kind ?? "-"} />
                      </>
                    ) : (
                      <InfoRow label="workflow" value={requestWorkflow} />
                    )}
                    <InfoRow
                      label="outdir"
                      value={
                        activeTask.requestKind === "submodule"
                          ? activeTask.submoduleDraft?.outputDirectory || "-"
                          : draft.outputDirectory || "-"
                      }
                    />
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
                      <InfoRow label={isZh ? "类型" : "kind"} value={importedRequest?.kind ?? "-"} />
                    </>
                  ) : (
                    <InfoRow label="workflow" value={requestWorkflow} />
                  )}
                </div>
                <pre className="mt-4 max-h-[28rem] overflow-auto rounded-lg border border-border bg-bg p-4 font-mono text-xs leading-6 text-text-secondary">
                  {requestPreviewJson}
                </pre>
              </section>
            </div>
          ) : null}
        </div>

        <div className="pointer-events-none border-t border-border/90 bg-surface-raised px-14 py-5">
          <div className="ui-surface-enter pointer-events-auto mx-auto flex max-w-4xl items-center gap-3 rounded-[1.1rem] border border-border bg-surface-raised px-4 py-3 shadow-[0_6px_20px_rgba(15,23,42,0.06)] dark:shadow-[0_6px_20px_rgba(2,6,23,0.35)]">
            <button type="button" className="ui-pressable text-2xl leading-none text-text-tertiary hover:text-text-primary" onClick={() => createTask()}>
              +
            </button>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm text-text-secondary">
                {usesImportedRequest ? requestSourceLabel : activeTask.title}
              </p>
              <div className="mt-1 flex flex-wrap gap-2 text-xs text-text-secondary">
                <span className="rounded-full bg-surface px-2.5 py-1">{requestWorkflow}</span>
                <span className="rounded-full bg-surface px-2.5 py-1">{draft.outputDirectory || (isZh ? "未选择 outdir" : "No outdir selected")}</span>
                <span className="rounded-full bg-surface px-2.5 py-1">{validation.issues.length === 0 ? (isZh ? "已就绪" : "ready") : isZh ? `${validation.issues.length} 个问题` : `${validation.issues.length} issue(s)`}</span>
              </div>
            </div>
            <button
              type="button"
              className="ui-pressable rounded-xl border border-border bg-surface px-3 py-2 text-xs font-medium text-text-secondary hover:bg-surface-raised hover:text-text-primary"
              onClick={() => setTaskView("setup")}
            >
              {isZh ? "配置" : "setup"}
            </button>
            <button
              type="button"
              className="ui-pressable rounded-xl border border-border bg-surface px-3 py-2 text-xs font-medium text-text-secondary hover:bg-surface-raised hover:text-text-primary"
              onClick={() => setTaskView("results")}
            >
              {isZh ? "结果" : "results"}
            </button>
            <button
              type="button"
              className={[
                "ui-pressable rounded-full bg-ice-500 px-4 py-2 text-sm font-semibold text-white shadow-card hover:bg-ice-400 disabled:cursor-not-allowed disabled:opacity-50",
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
              {activeTask.runStatus === "cancelling"
                ? isZh
                  ? "取消中"
                  : "Cancelling"
                : activeTask.runStatus === "starting" || activeTask.runStatus === "running"
                  ? isZh
                    ? "取消运行"
                    : "Cancel run"
                  : isZh
                    ? "运行"
                    : "Run"}
            </button>
          </div>
        </div>
      </main>

      <WorkbenchResizeHandle
        side="right"
        isActive={activeResize?.side === "right"}
        label={isZh ? "调整右侧栏宽度" : "Resize right sidebar"}
        value={rightSidebarWidth}
        min={WORKBENCH_MIN_RIGHT_WIDTH}
        max={WORKBENCH_MAX_RIGHT_WIDTH}
        onPointerDown={handleResizePointerDown}
        onKeyDown={handleResizeKeyDown}
        onResizeEnd={finishActiveResize}
      />

      <aside className="min-h-0 overflow-hidden border-l border-border/90 bg-surface-raised px-5 py-16">
        <div className="max-h-[calc(100vh-6rem)] overflow-auto">
        <div className="border-b border-border/90 pb-5">
          <p className="text-base font-medium text-text-secondary">环境信息</p>
          <h2 className="sr-only">Environment</h2>
        </div>
        <div className="pt-5">
          <section>
            <div className="flex items-center justify-between gap-3">
              <h3 className="text-sm font-medium text-text-primary">变更</h3>
              <button type="button" className="ui-pressable rounded-lg px-2 py-1 text-xl leading-none text-text-tertiary hover:bg-surface hover:text-text-primary" onClick={() => onNavigate("/settings")}>
                +
              </button>
            </div>
            <button type="button" className="ui-list-item mt-3 flex w-full items-center gap-3 rounded-lg px-2 py-2 text-left text-sm text-text-primary hover:bg-surface" onClick={() => onNavigate("/settings")}>
              <GameIcon name="environment" className="h-4 w-4" />
              环境诊断
            </button>
            <button type="button" className="ui-list-item flex w-full items-center gap-3 rounded-lg px-2 py-2 text-left text-sm text-text-primary hover:bg-surface" onClick={handleOpenOutput}>
              <GameIcon name="local" className="h-4 w-4" />
              工作树
            </button>
            <button type="button" className="ui-list-item flex w-full items-center gap-3 rounded-lg px-2 py-2 text-left text-sm text-text-primary hover:bg-surface" onClick={handlePrepareRun}>
              <GameIcon name="pairwise" className="h-4 w-4" />
              提交或推送
            </button>
            <div className="mt-3 hidden">
              <button type="button" className={SECONDARY_BUTTON_CLASS} onClick={() => onNavigate("/settings")}>
                Check
              </button>
            </div>
            <div className="mt-4 grid gap-2 text-sm text-text-secondary">
              <InfoRow
                label="workflow"
                value={
                  activeTask.requestKind === "submodule"
                    ? activeTask.capabilityId ?? "-"
                    : draft.workflowId
                }
              />
              <InfoRow
                label="input"
                value={
                  activeTask.requestKind === "submodule"
                    ? "-"
                    : draft.directory || "-"
                }
              />
              <InfoRow
                label="output"
                value={
                  activeTask.requestKind === "submodule"
                    ? activeTask.submoduleDraft?.outputDirectory || "-"
                    : draft.outputDirectory || "-"
                }
              />
              <InfoRow label="request" value={usesImportedRequest ? "imported" : "draft"} />
              <InfoRow label={isZh ? "问题" : "issues"} value={String(validation.issues.length)} />
            </div>
          </section>

          <section className="mt-5 border-t border-border/90 pt-5">
            <h3 className="text-sm font-medium text-text-primary">工作树</h3>
            <div className="mt-3 grid gap-2 text-sm text-text-secondary">
              <InfoRow label={isZh ? "状态" : "status"} value={runStatusLabel} />
              <InfoRow label={isZh ? "流程状态" : "state"} value={workflowStateLabel} />
              <InfoRow label={isZh ? "进度" : "progress"} value={`${Math.round(progress)}%`} />
              <InfoRow label="runId" value={activeTask.runState?.runId ?? "-"} />
            </div>
          </section>

          <section className="mt-5 border-t border-border/90 pt-5">
            <h3 className="text-sm font-medium text-text-primary">最近日志</h3>
            <div className="mt-3 grid gap-2">
              {recentEvents.length > 0 ? (
                recentEvents.map((line, index) => (
                  <div key={`${index}-${line}`} className="ui-log-line rounded-lg px-2 py-1.5 font-mono text-[11px] leading-5 text-text-secondary">
                    {line}
                  </div>
                ))
              ) : (
                <p className="rounded-lg px-2 py-1.5 text-sm text-text-secondary">
                  {isZh ? "运行事件会显示在这里。" : "Run events will appear here."}
                </p>
              )}
            </div>
          </section>

          <section className="mt-5 border-t border-border/90 pt-5">
            <h3 className="text-sm font-medium text-text-primary">来源</h3>
            <div className="mt-3 flex flex-wrap gap-2">
              <span className="rounded-full bg-surface px-3 py-1 text-xs text-text-secondary">GenomeLens CLI</span>
              <span className="rounded-full bg-surface px-3 py-1 text-xs text-text-secondary">JCVI engine</span>
              <span className="rounded-full bg-surface px-3 py-1 text-xs text-text-secondary">run.log</span>
            </div>
          </section>

          <section className="mt-5 border-t border-border/90 pt-5">
            <SectionTitle title={isZh ? "Workflow schema" : "Schema"} subtitle="get_workflow_schema()" />
            <pre className="mt-3 max-h-52 overflow-auto rounded-lg bg-surface p-3 font-mono text-[11px] leading-5 text-text-secondary">
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
      <span className="text-xs font-medium text-text-tertiary">{label}</span>
      <span className="truncate font-mono text-xs text-text-secondary" title={value}>
        {value}
      </span>
    </div>
  );
}

function WorkbenchResizeHandle({
  side,
  isActive,
  label,
  value,
  min,
  max,
  onPointerDown,
  onKeyDown,
  onResizeEnd,
}: {
  side: ResizeSide;
  isActive: boolean;
  label: string;
  value: number;
  min: number;
  max: number;
  onPointerDown: (side: ResizeSide, event: ReactPointerEvent<HTMLDivElement>) => void;
  onKeyDown: (side: ResizeSide, event: ReactKeyboardEvent<HTMLDivElement>) => void;
  onResizeEnd: () => void;
}) {
  return (
    <div
      role="separator"
      aria-label={label}
      aria-orientation="vertical"
      aria-valuemin={min}
      aria-valuemax={max}
      aria-valuenow={Math.round(value)}
      tabIndex={0}
      data-testid={`workbench-${side}-resize-handle`}
      className={[
        "group relative z-20 flex h-full cursor-col-resize items-center justify-center outline-none transition-colors",
        isActive ? "bg-ice-100" : "bg-transparent hover:bg-ice-50 focus-visible:bg-ice-50",
      ].join(" ")}
      title={label}
      onPointerDown={(event) => onPointerDown(side, event)}
      onPointerCancel={onResizeEnd}
      onLostPointerCapture={onResizeEnd}
      onKeyDown={(event) => onKeyDown(side, event)}
    >
      <span
        className={[
          "h-12 w-px rounded-full transition-colors",
          isActive ? "bg-ice-500" : "bg-border group-hover:bg-ice-300 group-focus-visible:bg-ice-400",
        ].join(" ")}
      />
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
