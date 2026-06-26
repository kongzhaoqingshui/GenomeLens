import { useRef, useState, type PointerEvent as ReactPointerEvent } from "react";
import type { DataNode as DataNodeModel } from "../../models/workbench-graph";

interface DataNodeProps {
  node: DataNodeModel;
  active: boolean;
  onSelect: (nodeId: string) => void;
  onMove: (nodeId: string, x: number, y: number) => void;
  onPortPointerUp: (nodeId: string, portId: string) => void;
}

function dataKindBadge(kind: DataNodeModel["dataKind"]): string {
  switch (kind) {
    case "species_pair":
      return "bg-sky-50 text-sky-700 dark:bg-sky-950/30 dark:text-sky-200";
    case "artifact":
      return "bg-amber-50 text-amber-700 dark:bg-amber-950/30 dark:text-amber-200";
    case "value":
      return "bg-slate-50 text-slate-700 dark:bg-slate-950/30 dark:text-slate-200";
    default:
      return "bg-surface text-text-secondary";
  }
}

function dataKindLabel(kind: DataNodeModel["dataKind"]): string {
  switch (kind) {
    case "species_pair":
      return "species pair";
    case "artifact":
      return "artifact";
    case "value":
      return "value";
    default:
      return kind;
  }
}

function truncatePreview(value: unknown): string {
  if (value === null || value === undefined) return "—";
  const str = typeof value === "string" ? value : JSON.stringify(value);
  if (str.length <= 48) return str;
  return str.slice(0, 48) + "…";
}

const NODE_WIDTH = 176;

export function DataNode({ node, active, onSelect, onMove, onPortPointerUp }: DataNodeProps) {
  const [dragging, setDragging] = useState(false);
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
    setDragging(true);

    const handleMove = (ev: PointerEvent) => {
      if (!dragRef.current) return;
      const dx = ev.clientX - dragRef.current.startX;
      const dy = ev.clientY - dragRef.current.startY;
      onMove(node.nodeId, dragRef.current.initialX + dx, dragRef.current.initialY + dy);
    };

    const handleUp = () => {
      setDragging(false);
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
          <span className="min-w-0">
            <p className="truncate text-[12px] font-semibold leading-4 text-text-primary">
              {node.label}
            </p>
          </span>
          <span
            className={[
              "shrink-0 rounded-full px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider",
              dataKindBadge(node.dataKind),
            ].join(" ")}
          >
            {dataKindLabel(node.dataKind)}
          </span>
        </div>

        <div className="px-3 py-2">
          <p className="truncate text-[10px] leading-3 text-text-tertiary" title={truncatePreview(node.value)}>
            {truncatePreview(node.value)}
          </p>
        </div>

        {/* Output port */}
        <span
          data-port-id="output"
          data-node-id={node.nodeId}
          className="absolute right-0 top-1/2 h-2.5 w-2.5 translate-x-1/2 -translate-y-1/2 rounded-full ring-2 ring-surface fill-slate-400 stroke-slate-200 dark:stroke-slate-700 cursor-pointer"
          title="output"
          onPointerDown={(event) => {
            event.stopPropagation();
            // Data nodes only have output; drag starts here but handled by parent via onPortPointerDown if wired.
            // Since DataNode props don't include onPortPointerDown, we rely on the parent not wiring drag from data nodes for now.
          }}
        />
      </div>
    </div>
  );
}
