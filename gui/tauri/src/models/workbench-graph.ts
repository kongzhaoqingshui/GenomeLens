import type { SpeciesInputDraft } from "./workflow-request-draft";

export type DataNodeKind = "species_pair" | "artifact" | "value";

export interface PortDeclaration {
  portId: string;
  portKind: "species_pair" | "artifact" | "value" | "config";
  artifactType?: string;
  direction: "in" | "out";
  label: string;
}

export interface BaseGraphNode {
  nodeId: string;
  x: number;
  y: number;
}

export interface TaskNode extends BaseGraphNode {
  kind: "task";
  taskId: string;
  capabilityId: string;
  inputs: PortDeclaration[];
  outputs: PortDeclaration[];
}

export interface DataNode extends BaseGraphNode {
  kind: "data";
  dataKind: DataNodeKind;
  label: string;
  value: unknown;
}

export type GraphNode = TaskNode | DataNode;

export interface GraphEdge {
  edgeId: string;
  sourceNodeId: string;
  sourcePortId: string;
  targetNodeId: string;
  targetPortId: string;
}

export interface WorkbenchGraph {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export function emptyGraph(): WorkbenchGraph {
  return { nodes: [], edges: [] };
}

export function topologicalSort(graph: WorkbenchGraph): string[] {
  const inDegree = new Map<string, number>();
  const adj = new Map<string, string[]>();

  for (const node of graph.nodes) {
    inDegree.set(node.nodeId, 0);
    adj.set(node.nodeId, []);
  }

  for (const edge of graph.edges) {
    const list = adj.get(edge.sourceNodeId);
    if (list) {
      list.push(edge.targetNodeId);
    }
    const deg = inDegree.get(edge.targetNodeId) ?? 0;
    inDegree.set(edge.targetNodeId, deg + 1);
  }

  const queue: string[] = [];
  for (const [nodeId, deg] of inDegree.entries()) {
    if (deg === 0) {
      queue.push(nodeId);
    }
  }

  const result: string[] = [];
  while (queue.length > 0) {
    const current = queue.shift()!;
    result.push(current);
    for (const neighbor of adj.get(current) ?? []) {
      const nextDeg = (inDegree.get(neighbor) ?? 1) - 1;
      inDegree.set(neighbor, nextDeg);
      if (nextDeg === 0) {
        queue.push(neighbor);
      }
    }
  }

  return result;
}

export function isPortCompatible(
  source: PortDeclaration,
  target: PortDeclaration,
): boolean {
  if (source.direction !== "out" || target.direction !== "in") {
    return false;
  }
  if (source.portKind !== target.portKind) {
    return false;
  }
  if (source.portKind === "artifact") {
    const sourceType = source.artifactType;
    const targetType = target.artifactType;
    if (sourceType && targetType && sourceType !== targetType) {
      return false;
    }
  }
  return true;
}

export function getUpstreamEdges(
  nodeId: string,
  portId: string | undefined,
  graph: WorkbenchGraph,
): GraphEdge[] {
  return graph.edges.filter((edge) => {
    if (edge.targetNodeId !== nodeId) return false;
    if (portId !== undefined && edge.targetPortId !== portId) return false;
    return true;
  });
}

export function addEdge(graph: WorkbenchGraph, edge: GraphEdge): WorkbenchGraph {
  const exists = graph.edges.some(
    (e) =>
      e.sourceNodeId === edge.sourceNodeId &&
      e.sourcePortId === edge.sourcePortId &&
      e.targetNodeId === edge.targetNodeId &&
      e.targetPortId === edge.targetPortId,
  );
  if (exists) {
    return graph;
  }
  return {
    nodes: graph.nodes,
    edges: [...graph.edges, edge],
  };
}

export function removeEdge(graph: WorkbenchGraph, edgeId: string): WorkbenchGraph {
  return {
    nodes: graph.nodes,
    edges: graph.edges.filter((e) => e.edgeId !== edgeId),
  };
}

export function resolveInputValue(
  nodeId: string,
  portId: string,
  graph: WorkbenchGraph,
  outputsMap: Map<string, Map<string, unknown>>,
  fallbackValues: Map<string, unknown>,
): unknown {
  const upstream = getUpstreamEdges(nodeId, portId, graph);
  if (upstream.length > 0) {
    const first = upstream[0];
    const nodeOutputs = outputsMap.get(first.sourceNodeId);
    if (nodeOutputs) {
      return nodeOutputs.get(first.sourcePortId);
    }
  }
  return fallbackValues.get(portId);
}

export function getNodeById(graph: WorkbenchGraph, nodeId: string): GraphNode | undefined {
  return graph.nodes.find((n) => n.nodeId === nodeId);
}

export function getDataNodeSpeciesPairValue(
  value: unknown,
): { reference: SpeciesInputDraft; target: SpeciesInputDraft } | undefined {
  if (
    typeof value === "object" &&
    value !== null &&
    "reference" in value &&
    "target" in value
  ) {
    const v = value as Record<string, unknown>;
    if (
      typeof v.reference === "object" &&
      v.reference !== null &&
      typeof v.target === "object" &&
      v.target !== null
    ) {
      return v as { reference: SpeciesInputDraft; target: SpeciesInputDraft };
    }
  }
  return undefined;
}
