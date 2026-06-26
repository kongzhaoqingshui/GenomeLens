import { mkdir, writeTextFile } from "@tauri-apps/plugin-fs";
import type { WorkbenchGraph, TaskNode } from "./workbench-graph";
import { topologicalSort, resolveInputValue } from "./workbench-graph";
import type { WorkbenchTask } from "./workbench-preset";
import type { WorkflowRequestDraft, SpeciesInputDraft } from "./workflow-request-draft";
import { draftToWorkflowRequest } from "./workflow-request-draft";
import type { SubmoduleRequestDraft } from "./submodule-request-draft";
import { draftToSubmoduleRequest } from "./submodule-request-draft";
import type { ArtifactRecord } from "./run-summary";
import type { WorkflowRunState } from "./run-session";
import { runAnalysis, readSummaryView } from "../services/workbench";

export type RunPanelStatus = "pending" | "running" | "finished" | "error";

export interface RunnerCallbacks {
  onNodeStatusChange: (
    nodeId: string,
    status: RunPanelStatus,
    runState: WorkflowRunState | null,
  ) => void;
  onNodeError: (nodeId: string, error: string) => void;
  onLog?: (nodeId: string, line: string) => void;
}

export interface RunPipelineOptions {
  graph: WorkbenchGraph;
  tasks: WorkbenchTask[];
  baseOutdir: string;
  callbacks: RunnerCallbacks;
  waitForRunFinish: (runId: string) => Promise<void>;
}

export function artifactPathForType(
  artifactIndex: ArtifactRecord[],
  artifactType: string,
): string | undefined {
  const record = artifactIndex.find(
    (a) => a.artifact_type === artifactType,
  );
  return record?.path;
}

export function buildRunnerState(
  outdir: string,
  runId: string,
): WorkflowRunState {
  return {
    runId,
    outdir,
    requestPath: "",
    status: "RUNNING",
    progress: 0,
    startedAt: new Date().toISOString(),
    finished: false,
    logLines: [],
  };
}

export async function runPipeline(
  options: RunPipelineOptions,
): Promise<Map<string, Map<string, unknown>>> {
  const { graph, tasks, baseOutdir, callbacks, waitForRunFinish } = options;

  const taskNodes = graph.nodes.filter(
    (n): n is TaskNode => n.kind === "task",
  );

  const sortedNodeIds = topologicalSort(graph);
  if (sortedNodeIds.length < taskNodes.length) {
    throw new Error("Cycle detected in workbench graph");
  }

  const orderedTaskNodes = sortedNodeIds
    .map((id) => taskNodes.find((n) => n.nodeId === id))
    .filter((n): n is TaskNode => n !== undefined);

  const outputsMap = new Map<string, Map<string, unknown>>();

  for (const node of orderedTaskNodes) {
    outputsMap.set(node.nodeId, new Map<string, unknown>());
  }

  for (const node of orderedTaskNodes) {
    const task = tasks.find((t) => t.taskId === node.taskId);
    if (!task) {
      callbacks.onNodeError(node.nodeId, `Task preset not found: ${node.taskId}`);
      throw new Error(`Task preset not found: ${node.taskId}`);
    }

    const nodeOutdir = `${baseOutdir}/${task.taskId}`;
    await mkdir(nodeOutdir, { recursive: true });

    let requestPath: string;
    let runState: WorkflowRunState | undefined;

    try {
      callbacks.onNodeStatusChange(node.nodeId, "running", null);

      const draft = task.draft;

      if (draft.kind === "submodule_request") {
        const submoduleDraft: SubmoduleRequestDraft = {
          ...draft,
          outputDirectory: nodeOutdir,
        };

        const fallbackValues = new Map<string, unknown>();
        for (const [portId, value] of Object.entries(draft.inputs)) {
          fallbackValues.set(portId, value);
        }

        for (const port of node.inputs) {
          const resolved = resolveInputValue(
            node.nodeId,
            port.portId,
            graph,
            outputsMap,
            fallbackValues,
          );
          if (resolved !== undefined) {
            submoduleDraft.inputs[port.portId] = resolved;
          }
        }

        const request = draftToSubmoduleRequest(submoduleDraft);
        requestPath = `${nodeOutdir}/request.json`;
        await writeTextFile(requestPath, JSON.stringify(request, null, 2));
      } else {
        const workflowDraft: WorkflowRequestDraft = {
          ...draft,
          outputDirectory: nodeOutdir,
        };

        const speciesPairPort = node.inputs.find(
          (p) => p.portKind === "species_pair",
        );
        if (speciesPairPort) {
          const upstreamEdges = graph.edges.filter(
            (e) =>
              e.targetNodeId === node.nodeId &&
              e.targetPortId === speciesPairPort.portId,
          );
          if (upstreamEdges.length > 0) {
            const firstEdge = upstreamEdges[0];
            const sourceOutputs = outputsMap.get(firstEdge.sourceNodeId);
            if (sourceOutputs) {
              const speciesPair = sourceOutputs.get(firstEdge.sourcePortId) as
                | { reference: SpeciesInputDraft; target: SpeciesInputDraft }
                | undefined;
              if (speciesPair) {
                workflowDraft.species = [
                  speciesPair.reference,
                  speciesPair.target,
                ];
              }
            }
          }
        }

        const request = draftToWorkflowRequest(workflowDraft);
        requestPath = `${nodeOutdir}/request.json`;
        await writeTextFile(requestPath, JSON.stringify(request, null, 2));
      }

      const { runId } = await runAnalysis({ requestPath, outdir: nodeOutdir });
      runState = buildRunnerState(nodeOutdir, runId);
      callbacks.onNodeStatusChange(node.nodeId, "running", runState);

      await waitForRunFinish(runId);

      const summary = await readSummaryView({ outdir: nodeOutdir });

      const nodeOutputs = outputsMap.get(node.nodeId)!;
      for (const port of node.outputs) {
        const artifactType = port.artifactType ?? port.portId;
        const path = artifactPathForType(summary.artifactIndex, artifactType);
        if (path !== undefined) {
          nodeOutputs.set(port.portId, path);
        }
      }

      callbacks.onNodeStatusChange(node.nodeId, "finished", runState);
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      callbacks.onNodeError(node.nodeId, message);
      callbacks.onNodeStatusChange(node.nodeId, "error", runState ?? null);
      throw error;
    }
  }

  return outputsMap;
}
