import { Plus, Workflow, Database } from "lucide-react";
import {
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
  type PointerEvent as ReactPointerEvent,
} from "react";

import type { GameIconName } from "./GameIcon";
import { TaskNode } from "./nodes/TaskNode";
import { DataNode } from "./nodes/DataNode";
import type { WorkbenchGraph } from "../models/workbench-graph";

type RunPanelStatus = "idle" | "confirming" | "starting" | "running" | "cancelling" | "cancelled" | "finished" | "error";

interface NodeCanvasProps {
  graph: WorkbenchGraph;
  tasks: Array<{
    id: string;
    title: string;
    subtitle: string;
    icon: GameIconName;
    runStatus: RunPanelStatus | "idle" | "starting" | "running" | "cancelling" | "cancelled" | "finished" | "error";
    x: number;
    y: number;
  }>;
  activeNodeId: string | null;
  isZh: boolean;
  onSelectNode: (nodeId: string) => void;
  onCloseNode: (nodeId: string) => void;
  onAddNode: (kind: "task" | "data") => void;
  onMoveNode: (nodeId: string, x: number, y: number) => void;
  onPortPointerDown: (nodeId: string, portId: string, event: ReactPointerEvent) => void;
  onPortPointerUp: (nodeId: string, portId: string) => void;
  connectingEdge?: { sourceNodeId: string; sourcePortId: string } | null;
  onEdgeClick: (edgeId: string) => void;
}

interface PortRefEntry {
  element: HTMLSpanElement | null;
  nodeId: string;
  portId: string;
}

interface EdgePath {
  edgeId: string;
  d: string;
}

export function NodeCanvas({
  graph,
  tasks,
  activeNodeId,
  isZh,
  onSelectNode,
  onCloseNode,
  onAddNode,
  onMoveNode,
  onPortPointerDown,
  onPortPointerUp,
  connectingEdge,
  onEdgeClick,
}: NodeCanvasProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const portRefs = useRef<PortRefEntry[]>([]);
  const [edgePaths, setEdgePaths] = useState<EdgePath[]>([]);
  const [tempLine, setTempLine] = useState<{ x1: number; y1: number; x2: number; y2: number } | null>(null);

  const taskMap = useMemo(() => {
    const map = new Map<string, (typeof tasks)[number]>();
    for (const t of tasks) map.set(t.id, t);
    return map;
  }, [tasks]);

  const recalculateEdges = useMemo(
    () => () => {
      const container = containerRef.current;
      if (!container) return;
      const containerRect = container.getBoundingClientRect();
      const nextPaths: EdgePath[] = [];

      for (const edge of graph.edges) {
        const sourceRef = portRefs.current.find(
          (r) => r.nodeId === edge.sourceNodeId && r.portId === edge.sourcePortId
        );
        const targetRef = portRefs.current.find(
          (r) => r.nodeId === edge.targetNodeId && r.portId === edge.targetPortId
        );
        if (!sourceRef?.element || !targetRef?.element) continue;

        const sRect = sourceRef.element.getBoundingClientRect();
        const tRect = targetRef.element.getBoundingClientRect();
        const x1 = sRect.left + sRect.width / 2 - containerRect.left;
        const y1 = sRect.top + sRect.height / 2 - containerRect.top;
        const x2 = tRect.left + tRect.width / 2 - containerRect.left;
        const y2 = tRect.top + tRect.height / 2 - containerRect.top;
        const controlOffset = Math.min(96, Math.abs(x2 - x1) * 0.5);
        const c1x = x1 + controlOffset;
        const c2x = x2 - controlOffset;
        nextPaths.push({
          edgeId: edge.edgeId,
          d: `M ${x1} ${y1} C ${c1x} ${y1}, ${c2x} ${y2}, ${x2} ${y2}`,
        });
      }
      setEdgePaths(nextPaths);
    },
    [graph.edges]
  );

  useLayoutEffect(() => {
    recalculateEdges();
  }, [recalculateEdges]);

  useEffect(() => {
    const handleResize = () => recalculateEdges();
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, [recalculateEdges]);

  // Temporary connecting line
  useEffect(() => {
    if (!connectingEdge) {
      setTempLine(null);
      return;
    }

    const sourceRef = portRefs.current.find(
      (r) => r.nodeId === connectingEdge.sourceNodeId && r.portId === connectingEdge.sourcePortId
    );
    if (!sourceRef?.element) return;

    const container = containerRef.current;
    const containerRect = container?.getBoundingClientRect();
    const sRect = sourceRef.element.getBoundingClientRect();
    const x1 = sRect.left + sRect.width / 2 - (containerRect?.left ?? 0);
    const y1 = sRect.top + sRect.height / 2 - (containerRect?.top ?? 0);

    const handleMove = (ev: PointerEvent) => {
      const cx = containerRect?.left ?? 0;
      const cy = containerRect?.top ?? 0;
      setTempLine({ x1, y1, x2: ev.clientX - cx, y2: ev.clientY - cy });
    };

    window.addEventListener("pointermove", handleMove);
    return () => window.removeEventListener("pointermove", handleMove);
  }, [connectingEdge]);

  const isEmpty = graph.nodes.length === 0;

  return (
    <div
      ref={containerRef}
      className="relative h-full w-full overflow-hidden"
      style={{
        backgroundImage:
          "radial-gradient(circle, hsl(var(--color-border)) 1px, transparent 1px)",
        backgroundSize: "20px 20px",
      }}
    >
      {/* SVG edges */}
      <svg
        className="pointer-events-none absolute inset-0 h-full w-full"
        xmlns="http://www.w3.org/2000/svg"
      >
        {edgePaths.map((path) => (
          <path
            key={path.edgeId}
            d={path.d}
            className="fill-none stroke-border"
            strokeWidth={2}
          />
        ))}
        {tempLine && (
          <path
            d={`M ${tempLine.x1} ${tempLine.y1} L ${tempLine.x2} ${tempLine.y2}`}
            className="fill-none stroke-ice-400"
            strokeWidth={2}
            strokeDasharray="4 4"
          />
        )}
      </svg>

      {/* Clickable edge overlays */}
      {edgePaths.map((path) => (
        <button
          key={`hit-${path.edgeId}`}
          type="button"
          className="absolute text-[10px] text-text-tertiary opacity-0 hover:opacity-100"
          style={{
            left: "50%",
            top: "50%",
            transform: "translate(-50%, -50%)",
          }}
          onClick={() => onEdgeClick(path.edgeId)}
        >
          {path.edgeId}
        </button>
      ))}

      {/* Nodes */}
      {graph.nodes.map((node) => {
        if (node.kind === "task") {
          const task = taskMap.get(node.taskId);
          return (
            <TaskNode
              key={node.nodeId}
              node={node}
              title={task?.title ?? node.taskId}
              subtitle={task?.subtitle ?? node.capabilityId}
              icon={task?.icon ?? "dotplot"}
              runStatus={task?.runStatus ?? "idle"}
              active={activeNodeId === node.nodeId}
              isZh={isZh}
              onSelect={onSelectNode}
              onClose={onCloseNode}
              onMove={onMoveNode}
              onPortPointerDown={onPortPointerDown}
              onPortPointerUp={onPortPointerUp}
              canClose={task ? task.runStatus !== "starting" && task.runStatus !== "running" && task.runStatus !== "cancelling" && task.runStatus !== "confirming" : true}
            />
          );
        }
        return (
          <DataNode
            key={node.nodeId}
            node={node}
            active={activeNodeId === node.nodeId}
            onSelect={onSelectNode}
            onMove={onMoveNode}
          />
        );
      })}

      {/* Empty state */}
      {isEmpty && (
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="ui-empty-state ui-surface-enter flex flex-col items-center gap-4 px-8 py-10">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-surface shadow-card">
              <Plus className="h-5 w-5 text-text-tertiary" />
            </div>
            <div className="text-center">
              <p className="text-sm font-semibold text-text-primary">
                {isZh ? "工作区为空" : "Workbench is empty"}
              </p>
              <p className="mt-1 text-xs text-text-secondary">
                {isZh ? "添加任务或数据节点开始构建工作流" : "Add a task or data node to start building your workflow"}
              </p>
            </div>
            <div className="flex items-center gap-2">
              <button
                type="button"
                className="ui-pressable inline-flex items-center gap-1.5 rounded-xl border border-border bg-surface px-4 py-2 text-xs font-semibold text-text-secondary transition hover:border-ice-200 hover:bg-ice-50 hover:text-ice-700 dark:hover:border-ice-800 dark:hover:bg-ice-900/30 dark:hover:text-ice-200"
                onClick={() => onAddNode("task")}
              >
                <Workflow className="h-3.5 w-3.5" />
                {isZh ? "添加任务" : "Add task"}
              </button>
              <button
                type="button"
                className="ui-pressable inline-flex items-center gap-1.5 rounded-xl border border-border bg-surface px-4 py-2 text-xs font-semibold text-text-secondary transition hover:border-ice-200 hover:bg-ice-50 hover:text-ice-700 dark:hover:border-ice-800 dark:hover:bg-ice-900/30 dark:hover:text-ice-200"
                onClick={() => onAddNode("data")}
              >
                <Database className="h-3.5 w-3.5" />
                {isZh ? "添加数据" : "Add data"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
