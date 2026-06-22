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
  statusLabel: "Connected" | "Reserved";
  workflowPreset?: McscanWorkflow;
}

const STARTUP_HINTS: Record<StartupResourceKey, string> = {
  version: "Checking GenomeLens and JCVI engine availability...",
  template: "Loading the MCSCAN template...",
  schema: "Preparing the workbench schema...",
};

const EMPTY_RESOURCE = { status: "loading" } as const;

const JCVI_CAPABILITIES: JcviCapabilityEntry[] = [
  {
    id: "pairwise-synteny",
    title: "Pairwise",
    subtitle: "Pairwise Synteny",
    description: "Open the current MCSCAN workbench with a pairwise workflow preset.",
    route: "/analysis/new",
    status: "connected",
    statusLabel: "Connected",
    workflowPreset: "mcscan_pairwise",
  },
  {
    id: "multi-species-synteny",
    title: "Multi-species",
    subtitle: "Multi-species Synteny",
    description: "Open the current MCSCAN workbench with a multi-species workflow preset.",
    route: "/analysis/new",
    status: "connected",
    statusLabel: "Connected",
    workflowPreset: "graphics_synteny",
  },
  {
    id: "local-synteny",
    title: "Local",
    subtitle: "Local Synteny",
    description: "Open the current MCSCAN workbench with a local synteny workflow preset.",
    route: "/analysis/new",
    status: "connected",
    statusLabel: "Connected",
    workflowPreset: "local_synteny",
  },
  {
    id: "dotplot",
    title: "Dotplot",
    subtitle: "Dotplot",
    description: "Reserved for a dedicated dotplot surface. The workflow preset is already wired.",
    route: "/analysis/new",
    status: "reserved",
    statusLabel: "Reserved",
    workflowPreset: "graphics_dotplot",
  },
  {
    id: "karyotype",
    title: "Karyotype",
    subtitle: "Karyotype",
    description: "Reserved for a dedicated karyotype surface. The workflow preset is already wired.",
    route: "/analysis/new",
    status: "reserved",
    statusLabel: "Reserved",
    workflowPreset: "graphics_karyotype",
  },
  {
    id: "ortholog-catalog",
    title: "Ortholog Catalog",
    subtitle: "Ortholog Catalog",
    description: "Reserved for a dedicated ortholog catalog surface. The workflow preset is already wired.",
    route: "/analysis/new",
    status: "reserved",
    statusLabel: "Reserved",
    workflowPreset: "catalog_ortholog",
  },
  {
    id: "environment-check",
    title: "Environment",
    subtitle: "Environment Check",
    description: "Open the settings surface and reuse the current diagnostics entry point.",
    route: "/settings",
    status: "connected",
    statusLabel: "Connected",
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
  const hints = pending.length > 0 ? pending.map((key) => STARTUP_HINTS[key]) : ["Workbench resources are ready."];

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
