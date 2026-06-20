import type { AnalysisRequest, McscanWorkflow } from "./analysis-request";
import type { AnalysisRequestDraft } from "./analysis-request-draft";
import type { VersionInfo } from "./version";

export type StartupResourceKey = "version" | "template" | "schema";
export type StartupResourceStatus = "loading" | "ready" | "error";
export type JcviCapabilityStatus = "connected" | "reserved";
export type JcviCapabilityId =
  | "pairwise-synteny"
  | "multi-species-synteny"
  | "local-synteny"
  | "dotplot"
  | "karyotype"
  | "ortholog-catalog"
  | "environment-check";

export interface StartupResourceState<TData> {
  status: StartupResourceStatus;
  data?: TData;
  error?: string;
}

export interface WorkbenchStartupResources {
  version: StartupResourceState<VersionInfo>;
  template: StartupResourceState<AnalysisRequest>;
  schema: StartupResourceState<Record<string, unknown>>;
}

export interface WorkbenchStartupState extends WorkbenchStartupResources {
  status: "loading" | "ready" | "error";
  pending: StartupResourceKey[];
  failed: StartupResourceKey[];
  readyCount: number;
  totalCount: number;
  activeHint: string;
  hints: string[];
  diagnosticsRoute: "/settings";
}

export interface JcviCapabilityEntry {
  id: JcviCapabilityId;
  title: string;
  subtitle: string;
  description: string;
  route: "/analysis/new" | "/settings";
  status: JcviCapabilityStatus;
  statusLabel: "已接入" | "预留";
  workflowPreset?: McscanWorkflow;
}

const STARTUP_HINTS: Record<StartupResourceKey, string> = {
  version: "正在检查 GenomeLens 与 JCVI 引擎...",
  template: "正在读取 MCSCAN 模板...",
  schema: "正在准备任务工作台...",
};

const EMPTY_RESOURCE = { status: "loading" } as const;

const JCVI_CAPABILITIES: JcviCapabilityEntry[] = [
  {
    id: "pairwise-synteny",
    title: "双物种共线性",
    subtitle: "Pairwise Synteny",
    description: "进入现有 MCSCAN wizard，并预设双物种 workflow。",
    route: "/analysis/new",
    status: "connected",
    statusLabel: "已接入",
    workflowPreset: "mcscan_pairwise",
  },
  {
    id: "multi-species-synteny",
    title: "多物种共线性",
    subtitle: "Multi-species Synteny",
    description: "进入现有 MCSCAN wizard，并预设多物种 workflow。",
    route: "/analysis/new",
    status: "connected",
    statusLabel: "已接入",
    workflowPreset: "graphics_synteny",
  },
  {
    id: "local-synteny",
    title: "局部共线性",
    subtitle: "Local Synteny",
    description: "进入现有 MCSCAN wizard，并预设 local_synteny workflow。",
    route: "/analysis/new",
    status: "connected",
    statusLabel: "已接入",
    workflowPreset: "local_synteny",
  },
  {
    id: "dotplot",
    title: "点图",
    subtitle: "Dotplot",
    description: "沿用现有 wizard 入口，保留 workflow 预设，等待专门交互补齐。",
    route: "/analysis/new",
    status: "reserved",
    statusLabel: "预留",
    workflowPreset: "graphics_dotplot",
  },
  {
    id: "karyotype",
    title: "核型总图",
    subtitle: "Karyotype",
    description: "沿用现有 wizard 入口，保留 workflow 预设，等待专门交互补齐。",
    route: "/analysis/new",
    status: "reserved",
    statusLabel: "预留",
    workflowPreset: "graphics_karyotype",
  },
  {
    id: "ortholog-catalog",
    title: "直系同源目录",
    subtitle: "Ortholog Catalog",
    description: "沿用现有 wizard 入口，保留 workflow 预设，等待专门交互补齐。",
    route: "/analysis/new",
    status: "reserved",
    statusLabel: "预留",
    workflowPreset: "catalog_ortholog",
  },
  {
    id: "environment-check",
    title: "环境诊断",
    subtitle: "Environment Check",
    description: "跳转设置页，复用现有环境检查入口。",
    route: "/settings",
    status: "connected",
    statusLabel: "已接入",
  },
];

export function createLoadingWorkbenchStartupResources(): WorkbenchStartupResources {
  return {
    version: { ...EMPTY_RESOURCE },
    template: { ...EMPTY_RESOURCE },
    schema: { ...EMPTY_RESOURCE },
  };
}

export function deriveWorkbenchStartupState(resources: WorkbenchStartupResources): WorkbenchStartupState {
  const entries = Object.entries(resources) as Array<[StartupResourceKey, StartupResourceState<unknown>]>;
  const pending = entries.filter(([, resource]) => resource.status === "loading").map(([key]) => key);
  const failed = entries.filter(([, resource]) => resource.status === "error").map(([key]) => key);
  const readyCount = entries.filter(([, resource]) => resource.status === "ready").length;
  const hints = pending.length > 0 ? pending.map((key) => STARTUP_HINTS[key]) : ["工作台已就绪。"];

  return {
    ...resources,
    status: failed.length > 0 ? "error" : pending.length > 0 ? "loading" : "ready",
    pending,
    failed,
    readyCount,
    totalCount: entries.length,
    activeHint: hints[0],
    hints,
    diagnosticsRoute: "/settings",
  };
}

export function listJcviCapabilities(): JcviCapabilityEntry[] {
  return JCVI_CAPABILITIES.map((entry) => ({ ...entry }));
}

export function getJcviCapabilityById(id: JcviCapabilityId): JcviCapabilityEntry | undefined {
  return JCVI_CAPABILITIES.find((entry) => entry.id === id);
}

export function applyWorkflowPresetToDraft(
  draft: AnalysisRequestDraft,
  workflow: McscanWorkflow,
): AnalysisRequestDraft {
  return {
    ...draft,
    mcscan: {
      ...draft.mcscan,
      workflow,
    },
  };
}

export function applyCapabilityPresetToDraft(
  draft: AnalysisRequestDraft,
  capability: Pick<JcviCapabilityEntry, "workflowPreset">,
): AnalysisRequestDraft {
  return capability.workflowPreset ? applyWorkflowPresetToDraft(draft, capability.workflowPreset) : draft;
}

export function createDraftForCapability(
  templateDraft: AnalysisRequestDraft,
  capabilityId: JcviCapabilityId,
): AnalysisRequestDraft {
  const capability = getJcviCapabilityById(capabilityId);
  return capability ? applyCapabilityPresetToDraft(templateDraft, capability) : templateDraft;
}
