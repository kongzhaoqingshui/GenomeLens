import { invoke } from "@tauri-apps/api/core";
import type { CapabilityEntry } from "../models/capability";

export interface ListWorkflowsResult {
  one_stop_workflows?: unknown[];
  submodules?: unknown[];
}

function normalizeCapability(raw: unknown, defaultKind?: CapabilityEntry["kind"]): CapabilityEntry | null {
  if (typeof raw !== "object" || raw === null) {
    return null;
  }
  const item = raw as Record<string, unknown>;
  const kind: CapabilityEntry["kind"] =
    item.kind === "one_stop"
      ? "one_stop"
      : item.kind === "sub_module"
        ? "sub_module"
        : defaultKind ?? "sub_module";
  const id = String(item.workflow_id ?? item.module_id ?? "");
  if (!id) {
    return null;
  }
  const status: CapabilityEntry["status"] = kind === "one_stop" || id === "synteny" ? "connected" : "reserved";
  const statusLabel: CapabilityEntry["status_label"] =
    status === "connected" ? "Connected" : "Reserved";

  return {
    id,
    kind,
    name: String(item.name ?? id),
    subtitle: String(item.name ?? id),
    description: String(item.description ?? ""),
    category: typeof item.category === "string" ? item.category : undefined,
    domain: typeof item.domain === "string" ? item.domain : undefined,
    module_kind:
      item.module_kind === "lightweight" || item.module_kind === "aggregate"
        ? item.module_kind
        : undefined,
    engine_workflow: typeof item.engine_workflow === "string" ? item.engine_workflow : undefined,
    standalone: typeof item.standalone === "boolean" ? item.standalone : true,
    inputs: Array.isArray(item.inputs) ? (item.inputs as CapabilityEntry["inputs"]) : [],
    outputs: Array.isArray(item.outputs) ? (item.outputs as CapabilityEntry["outputs"]) : [],
    parameters: Array.isArray(item.parameters) ? (item.parameters as CapabilityEntry["parameters"]) : [],
    labels: Array.isArray(item.labels) ? (item.labels as string[]) : [],
    status,
    status_label: statusLabel,
    route: id === "environment-check" ? "/settings" : "/analysis/new",
  };
}

function normalizeCapabilityList(payload: ListWorkflowsResult): CapabilityEntry[] {
  const entries: CapabilityEntry[] = [];
  for (const raw of payload.one_stop_workflows ?? []) {
    const normalized = normalizeCapability(raw, "one_stop");
    if (normalized) {
      entries.push(normalized);
    }
  }
  for (const raw of payload.submodules ?? []) {
    const normalized = normalizeCapability(raw, "sub_module");
    if (normalized) {
      entries.push(normalized);
    }
  }
  return entries;
}

const capabilityListCache: {
  data: CapabilityEntry[] | null;
  promise: Promise<CapabilityEntry[]> | null;
} = { data: null, promise: null };

const capabilityDetailCache = new Map<string, CapabilityEntry>();
const capabilityDetailPromiseCache = new Map<string, Promise<CapabilityEntry>>();

export function listCapabilities(
  kind?: "one_stop" | "sub_module" | "all",
  module_kind?: "lightweight" | "aggregate" | "all",
): Promise<CapabilityEntry[]> {
  if (capabilityListCache.data) {
    return Promise.resolve(capabilityListCache.data);
  }
  if (capabilityListCache.promise) {
    return capabilityListCache.promise;
  }

  const nextPromise = invoke<ListWorkflowsResult>("list_workflows", { input: { kind, moduleKind: module_kind } })
    .then((result) => {
      const entries = normalizeCapabilityList(result);
      capabilityListCache.data = entries;
      capabilityListCache.promise = null;
      return entries;
    })
    .catch((error: unknown) => {
      capabilityListCache.promise = null;
      throw error;
    });

  capabilityListCache.promise = nextPromise;
  return nextPromise;
}

export function describeCapability(id: string): Promise<CapabilityEntry> {
  const cached = capabilityDetailCache.get(id);
  if (cached) {
    return Promise.resolve(cached);
  }

  const pending = capabilityDetailPromiseCache.get(id);
  if (pending) {
    return pending;
  }

  const nextPromise = invoke<unknown>("describe_workflow", { input: { id } })
    .then((raw) => {
      const normalized = normalizeCapability(raw);
      if (!normalized) {
        throw new Error(`Invalid capability description for ${id}`);
      }
      capabilityDetailCache.set(id, normalized);
      capabilityDetailPromiseCache.delete(id);
      return normalized;
    })
    .catch((error: unknown) => {
      capabilityDetailPromiseCache.delete(id);
      throw error;
    });

  capabilityDetailPromiseCache.set(id, nextPromise);
  return nextPromise;
}

export function getCachedCapabilities(): CapabilityEntry[] | null {
  return capabilityListCache.data;
}

export function getCachedCapability(id: string): CapabilityEntry | null {
  return capabilityDetailCache.get(id) ?? null;
}

export function clearCapabilityCache(): void {
  capabilityListCache.data = null;
  capabilityListCache.promise = null;
  capabilityDetailCache.clear();
  capabilityDetailPromiseCache.clear();
}

const ensureCache = new Map<string, CapabilityEntry>();

export async function ensureCapabilityOutputs(capability: CapabilityEntry): Promise<CapabilityEntry> {
  if (Array.isArray(capability.outputs) && capability.outputs.length > 0) {
    return capability;
  }
  const cached = ensureCache.get(capability.id);
  if (cached) {
    return cached;
  }
  try {
    const enriched = await describeCapability(capability.id);
    ensureCache.set(capability.id, enriched);
    return enriched;
  } catch {
    return capability;
  }
}
