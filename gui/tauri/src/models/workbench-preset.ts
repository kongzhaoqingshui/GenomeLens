import type { WorkbenchGraph } from "./workbench-graph";
import type { WorkflowRequestDraft } from "./workflow-request-draft";
import type { SubmoduleRequestDraft } from "./submodule-request-draft";

export interface WorkbenchTask {
  taskId: string;
  capabilityId: string;
  name: string;
  draft: WorkflowRequestDraft | SubmoduleRequestDraft;
}

export interface SavedTaskPreset extends WorkbenchTask {
  onCanvas: boolean;
}

const TASK_PRESETS_KEY = "genomelens.gui.taskPresets";
const WORKBENCH_GRAPH_KEY = "genomelens.gui.workbenchGraph";

export function loadTaskPresets(): SavedTaskPreset[] {
  try {
    const raw = localStorage.getItem(TASK_PRESETS_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as unknown;
    if (Array.isArray(parsed)) {
      return parsed as SavedTaskPreset[];
    }
  } catch {
    // silently ignore
  }
  return [];
}

export function saveTaskPresets(presets: SavedTaskPreset[]): void {
  try {
    localStorage.setItem(TASK_PRESETS_KEY, JSON.stringify(presets));
  } catch {
    // silently ignore
  }
}

export function loadWorkbenchGraph(): WorkbenchGraph {
  try {
    const raw = localStorage.getItem(WORKBENCH_GRAPH_KEY);
    if (!raw) return { nodes: [], edges: [] };
    const parsed = JSON.parse(raw) as unknown;
    if (
      typeof parsed === "object" &&
      parsed !== null &&
      "nodes" in parsed &&
      "edges" in parsed &&
      Array.isArray((parsed as Record<string, unknown>).nodes) &&
      Array.isArray((parsed as Record<string, unknown>).edges)
    ) {
      return parsed as WorkbenchGraph;
    }
  } catch {
    // silently ignore
  }
  return { nodes: [], edges: [] };
}

export function saveWorkbenchGraph(graph: WorkbenchGraph): void {
  try {
    localStorage.setItem(WORKBENCH_GRAPH_KEY, JSON.stringify(graph));
  } catch {
    // silently ignore
  }
}
