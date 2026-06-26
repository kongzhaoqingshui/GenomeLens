import type { WorkflowRequestDraft } from "./workflow-request-draft";

export type CapabilityKind = "one_stop" | "sub_module";
export type CapabilityStatus = "connected" | "available" | "reserved";

export interface CapabilityInputDeclaration {
  port_id: string;
  port_kind: "species_pair" | "artifact" | "value" | "config";
  required: boolean;
  description?: string;
  artifact_type?: string;
  accepted_formats?: string[];
}

export interface CapabilityOutputDeclaration {
  port_id: string;
  port_kind: "artifact" | "value";
  required: boolean;
  description?: string;
  artifact_type?: string;
  accepted_formats?: string[];
}

export interface CapabilityParameterDeclaration {
  param_id: string;
  param_type: "string" | "integer" | "number" | "boolean" | "array";
  required: boolean;
  default?: unknown;
  description?: string;
}

export interface CapabilityEntry {
  id: string;
  kind: CapabilityKind;
  name: string;
  subtitle: string;
  description: string;
  category?: string;
  domain?: string;
  module_kind?: "lightweight" | "aggregate";
  engine_workflow?: string;
  standalone?: boolean;
  inputs: CapabilityInputDeclaration[];
  outputs: CapabilityOutputDeclaration[];
  parameters: CapabilityParameterDeclaration[];
  labels: string[];
  status: CapabilityStatus;
  status_label: "Connected" | "Available" | "Reserved";
  route: "/analysis/new" | "/settings";
  preset?: CapabilityPreset;
}

export type CapabilityPreset = (draft: WorkflowRequestDraft) => WorkflowRequestDraft;

export type LegacyCapabilityId =
  | "pairwise-synteny"
  | "multi-species-synteny"
  | "local-synteny"
  | "dotplot"
  | "karyotype"
  | "ortholog-catalog"
  | "environment-check";

const LEGACY_CAPABILITY_MAP: Record<LegacyCapabilityId, { id: string; preset?: string }> = {
  "pairwise-synteny": { id: "synteny", preset: "pairwise" },
  "multi-species-synteny": { id: "synteny", preset: "multi" },
  "local-synteny": { id: "synteny", preset: "local" },
  dotplot: { id: "jcvi.graphics_dotplot" },
  karyotype: { id: "jcvi.graphics_karyotype" },
  "ortholog-catalog": { id: "jcvi.pairwise", preset: "ortholog" },
  "environment-check": { id: "environment-check" },
};

export function resolveLegacyCapabilityId(
  legacyId: LegacyCapabilityId | string,
): { id: string; preset?: string } {
  if (legacyId in LEGACY_CAPABILITY_MAP) {
    return LEGACY_CAPABILITY_MAP[legacyId as LegacyCapabilityId];
  }
  return { id: legacyId };
}

export function isOneStopCapability(capability: CapabilityEntry): boolean;
export function isOneStopCapability(capabilityId: string, capabilities: CapabilityEntry[]): boolean;
export function isOneStopCapability(
  capabilityOrId: CapabilityEntry | string,
  capabilities?: CapabilityEntry[],
): boolean {
  if (typeof capabilityOrId === "string") {
    const cap = capabilities?.find((c) => c.id === capabilityOrId);
    return cap?.kind === "one_stop";
  }
  return capabilityOrId.kind === "one_stop";
}

export function isSubmoduleCapability(capability: CapabilityEntry): boolean;
export function isSubmoduleCapability(capabilityId: string, capabilities: CapabilityEntry[]): boolean;
export function isSubmoduleCapability(
  capabilityOrId: CapabilityEntry | string,
  capabilities?: CapabilityEntry[],
): boolean {
  if (typeof capabilityOrId === "string") {
    const cap = capabilities?.find((c) => c.id === capabilityOrId);
    return cap?.kind === "sub_module";
  }
  return capabilityOrId.kind === "sub_module";
}

export function getCapabilitySubtitle(capability: CapabilityEntry, isZh: boolean): string {
  if (!isZh) {
    return capability.subtitle;
  }
  switch (capability.id) {
    case "synteny":
      return "一站式 synteny 共线性";
    case "jcvi.pairwise":
      return "Pairwise 共线性计算";
    case "jcvi.graphics_dotplot":
      return "点图";
    case "jcvi.graphics_synteny":
      return "共线性图";
    case "jcvi.graphics_karyotype":
      return "核型图";
    case "jcvi.local_synteny":
      return "局部共线性";
    case "jcvi.graphics_histogram":
      return "直方图";
    case "jcvi.graphics_heatmap":
      return "热图";
    case "jcvi.graphics_karyotype_global":
      return "全局核型总图";
    case "jcvi.local_synteny_multi":
      return "多物种局部共线性";
    default:
      return capability.subtitle;
  }
}

export function getCapabilityDescription(capability: CapabilityEntry, isZh: boolean): string {
  if (!isZh) {
    return capability.description;
  }
  switch (capability.id) {
    case "synteny":
      return "端到端 synteny 一站式工作流，自动展开 pairwise 计算、全局图件与局部共线性。";
    case "jcvi.pairwise":
      return "执行两个物种的 BLAST/LAST/Diamond 比对、锚点扫描与 block 计算。";
    case "jcvi.graphics_dotplot":
      return "基于锚点绘制两个物种的共线性点图。";
    case "jcvi.graphics_synteny":
      return "基于 blocks 与 layout 绘制多物种共线性对齐图。";
    case "jcvi.graphics_karyotype":
      return "绘制物种内或两物种核型共线性图。";
    case "jcvi.local_synteny":
      return "以目标基因为中心绘制局部共线性图。";
    case "jcvi.graphics_histogram":
      return "绘制数值分布直方图。";
    case "jcvi.graphics_heatmap":
      return "将矩阵 CSV 渲染为热图。";
    case "jcvi.graphics_karyotype_global":
      return "基于 tracks 与 edges 聚合全局核型总图。";
    case "jcvi.local_synteny_multi":
      return "在多个物种间以目标基因为中心绘制局部共线性总图。";
    default:
      return capability.description;
  }
}
