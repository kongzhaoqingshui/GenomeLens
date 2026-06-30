import { useRef, type PointerEvent as ReactPointerEvent } from "react";
import { X } from "lucide-react";
import { GameIcon, type GameIconName } from "../GameIcon";
import type { PortDeclaration, TaskNode as TaskNodeModel } from "../../models/workbench-graph";

type NodeRunStatus =
  | "idle"
  | "confirming"
  | "starting"
  | "running"
  | "cancelling"
  | "cancelled"
  | "finished"
  | "error";

interface TaskNodeProps {
  node: TaskNodeModel;
  title: string;
  subtitle: string;
  icon: GameIconName;
  runStatus: NodeRunStatus;
  active: boolean;
  isZh: boolean;
  onSelect: (nodeId: string) => void;
  onClose: (nodeId: string) => void;
  onMove: (nodeId: string, x: number, y: number) => void;
  onPortPointerDown: (nodeId: string, portId: string, event: ReactPointerEvent) => void;
  onPortPointerUp: (nodeId: string, portId: string) => void;
  canClose?: boolean;
}

function statusTone(status: NodeRunStatus): string {
  switch (status) {
    case "finished":
      return "bg-emerald-500";
    case "error":
      return "bg-rose-500";
    case "running":
    case "starting":
      return "bg-sky-500";
    case "cancelling":
    case "cancelled":
      return "bg-slate-400";
    case "confirming":
      return "bg-amber-500";
    default:
      return "bg-text-tertiary";
  }
}

function statusLabel(status: NodeRunStatus, isZh: boolean): string {
  if (!isZh) {
    return status;
  }
  switch (status) {
    case "idle":
      return "空闲";
    case "confirming":
      return "待确认";
    case "starting":
      return "启动中";
    case "running":
      return "运行中";
    case "cancelling":
      return "取消中";
    case "cancelled":
      return "已取消";
    case "finished":
      return "已完成";
    case "error":
      return "错误";
    default:
      return status;
  }
}

function portKindColor(kind: PortDeclaration["portKind"]): string {
  switch (kind) {
    case "species_pair":
      return "fill-sky-400 stroke-sky-200 dark:stroke-sky-900";
    case "artifact":
      return "fill-amber-400 stroke-amber-200 dark:stroke-amber-900";
    case "value":
    case "config":
      return "fill-slate-400 stroke-slate-200 dark:stroke-slate-700";
    default:
      return "fill-text-tertiary stroke-border";
  }
}

const NODE_WIDTH = 208;

export function TaskNode({
  node,
  title,
  subtitle,
  icon,
  runStatus,
  active,
  isZh,
  onSelect,
  onClose,
  onMove,
  onPortPointerDown,
  onPortPointerUp,
  canClose = true,
}: TaskNodeProps) {
  const dragRef = useRef<{ startX: number; startY: number; initialX: number; initialY: number } | null>(null);

  function handlePointerDown(event: ReactPointerEvent<HTMLDivElement>) {
    if (event.button !== 0) return;
    event.preventDefault();
    event.stopPropagation();
    onSelect(node.nodeId);
    dragRef.current = {
      startX: event.clientX,
      startY: event.clientY,
      initialX: node.x,
      initialY: node.y,
    };

    const handleMove = (ev: PointerEvent) => {
      if (!dragRef.current) return;
      const dx = ev.clientX - dragRef.current.startX;
      const dy = ev.clientY - dragRef.current.startY;
      onMove(node.nodeId, dragRef.current.initialX + dx, dragRef.current.initialY + dy);
    };

    const handleUp = () => {
      dragRef.current = null;
      window.removeEventListener("pointermove", handleMove);
      window.removeEventListener("pointerup", handleUp);
    };

    window.addEventListener("pointermove", handleMove);
    window.addEventListener("pointerup", handleUp);
  }

  return (
    <div
      className="absolute"
      style={{
        left: node.x,
        top: node.y,
        width: NODE_WIDTH,
      }}
    >
      <div
        className={[
          "group relative rounded-xl border bg-surface-raised text-left shadow-card transition",
          active
            ? "border-ice-400 shadow-glow"
            : "border-border hover:border-ice-200",
        ].join(" ")}
      >
        <div
          className={[
            "flex cursor-grab items-center justify-between gap-2 rounded-t-xl px-3 py-2 active:cursor-grabbing",
            active ? "bg-ice-50/60 dark:bg-ice-900/20" : "bg-surface",
          ].join(" ")}
          onPointerDown={handlePointerDown}
        >
          <div className="flex min-w-0 items-center gap-2">
            <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-surface text-text-secondary">
              <GameIcon name={icon} className="h-3.5 w-3.5" />
            </span>
            <span className="min-w-0">
              <p className="truncate text-[12px] font-semibold leading-4 text-text-primary">
                {title}
              </p>
              <p className="truncate text-[10px] leading-3 text-text-tertiary">
                {subtitle}
              </p>
            </span>
          </div>
          {canClose ? (
            <button
              type="button"
              className="ui-pressable -mr-1 -mt-1 flex h-5 w-5 shrink-0 items-center justify-center rounded text-text-tertiary opacity-0 transition hover:bg-surface hover:text-text-primary group-hover:opacity-100"
              onClick={(event) => {
                event.stopPropagation();
                onClose(node.nodeId);
              }}
              onPointerDown={(event) => event.stopPropagation()}
            >
              <X className="h-3 w-3" />
            </button>
          ) : null}
        </div>

        <div className="h-1 w-full">
          <div className={["h-full", statusTone(runStatus)].join(" ")} />
        </div>

        <div className="px-3 py-2">
          <p className="text-[10px] font-medium uppercase tracking-[0.12em] text-text-tertiary">
            {statusLabel(runStatus, isZh)}
          </p>
        </div>

        {/* Input ports */}
        <div className="absolute left-0 top-0 flex h-full flex-col justify-center gap-2" style={{ transform: "translateX(-50%)" }}>
          {node.inputs.map((port) => (
            <span
              key={port.portId}
              data-port-id={port.portId}
              data-node-id={node.nodeId}
              className={[
                "h-2.5 w-2.5 rounded-full ring-2 ring-surface cursor-pointer",
                portKindColor(port.portKind),
              ].join(" ")}
              title={port.label}
              onPointerUp={(event) => {
                event.stopPropagation();
                onPortPointerUp(node.nodeId, port.portId);
              }}
            />
          ))}
        </div>

        {/* Output ports */}
        <div className="absolute right-0 top-0 flex h-full flex-col justify-center gap-2" style={{ transform: "translateX(50%)" }}>
          {node.outputs.map((port) => (
            <span
              key={port.portId}
              data-port-id={port.portId}
              data-node-id={node.nodeId}
              className={[
                "h-2.5 w-2.5 rounded-full ring-2 ring-surface cursor-pointer",
                portKindColor(port.portKind),
              ].join(" ")}
              title={port.label}
              onPointerDown={(event) => {
                event.stopPropagation();
                onPortPointerDown(node.nodeId, port.portId, event);
              }}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
