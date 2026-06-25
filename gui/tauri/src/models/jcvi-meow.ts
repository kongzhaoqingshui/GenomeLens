import type { CapabilityPreset } from "./capability";
import type { WorkflowRequestDraft } from "./workflow-request-draft";
import type { VersionInfo } from "./version";

export type { CapabilityPreset } from "./capability";

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
  template: StartupResourceState<Record<string, unknown>>;
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
  preset?: CapabilityPreset;
}

const STARTUP_HINTS: Record<StartupResourceKey, string> = {
  version: "Checking GenomeLens and JCVI engine availability...",
  template: "Loading the synteny workflow template...",
  schema: "Preparing the workbench schema...",
};

const EMPTY_RESOURCE = { status: "loading" } as const;

function bedCdsSpecies(name: string): WorkflowRequestDraft["species"][number] {
  return {
    name,
    inputMode: "bed_cds",
    bed: "",
    cds: "",
    gff: "",
    genome: "",
  };
}

function withSpeciesCount(count: number): CapabilityPreset {
  return (draft) => {
    const species = Array.from({ length: count }, (_, index) =>
      bedCdsSpecies(draft.species[index]?.name ?? `species_${String.fromCharCode(97 + index)}`),
    );
    return { ...draft, species };
  };
}

function withLocalSyntenyHint(): CapabilityPreset {
  return (draft) => ({
    ...draft,
    species: draft.species.length < 2 ? [bedCdsSpecies("species_a"), bedCdsSpecies("species_b")] : draft.species,
    parameters: {
      ...draft.parameters,
      localSynteny: {
        ...draft.parameters.localSynteny,
        targetGeneIds: draft.parameters.localSynteny.targetGeneIds.length > 0 ? draft.parameters.localSynteny.targetGeneIds : ["example_gene_id"],
      },
    },
  });
}

const JCVI_CAPABILITIES: JcviCapabilityEntry[] = [
  {
    id: "pairwise-synteny",
    title: "Pairwise",
    subtitle: "Pairwise Synteny",
    description: "Open the synteny workbench with a two-species pairwise preset.",
    route: "/analysis/new",
    status: "connected",
    statusLabel: "Connected",
    preset: withSpeciesCount(2),
  },
  {
    id: "multi-species-synteny",
    title: "Multi-species",
    subtitle: "Multi-species Synteny",
    description: "Open the synteny workbench with a three-species preset.",
    route: "/analysis/new",
    status: "connected",
    statusLabel: "Connected",
    preset: withSpeciesCount(3),
  },
  {
    id: "local-synteny",
    title: "Local",
    subtitle: "Local Synteny",
    description: "Open the synteny workbench with a local synteny preset (target genes enabled).",
    route: "/analysis/new",
    status: "connected",
    statusLabel: "Connected",
    preset: withLocalSyntenyHint(),
  },
  {
    id: "dotplot",
    title: "Dotplot",
    subtitle: "Dotplot",
    description: "Reserved for a dedicated dotplot surface.",
    route: "/analysis/new",
    status: "reserved",
    statusLabel: "Reserved",
  },
  {
    id: "karyotype",
    title: "Karyotype",
    subtitle: "Karyotype",
    description: "Reserved for a dedicated karyotype surface.",
    route: "/analysis/new",
    status: "reserved",
    statusLabel: "Reserved",
  },
  {
    id: "ortholog-catalog",
    title: "Ortholog Catalog",
    subtitle: "Ortholog Catalog",
    description: "Reserved for a dedicated ortholog catalog surface.",
    route: "/analysis/new",
    status: "reserved",
    statusLabel: "Reserved",
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

export function applyCapabilityPresetToDraft(
  draft: WorkflowRequestDraft,
  capability: Pick<JcviCapabilityEntry, "preset">,
): WorkflowRequestDraft {
  return capability.preset ? capability.preset(draft) : draft;
}

export function createDraftForCapability(
  templateDraft: WorkflowRequestDraft,
  capabilityId: JcviCapabilityId,
): WorkflowRequestDraft {
  const capability = getJcviCapabilityById(capabilityId);
  return capability ? applyCapabilityPresetToDraft(templateDraft, capability) : templateDraft;
}

// 移除已废弃的 workflowPreset 相关函数；如外部仍有引用，请改用 createDraftForCapability。
