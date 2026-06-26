import { Plus, X } from "lucide-react";
import {
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
  type PointerEvent as ReactPointerEvent,
} from "react";

import { GameIcon, type GameIconName } from "./GameIcon";

type NodeRunStatus =
  | "idle"
  | "confirming"
  | "starting"
  | "running"
  | "cancelling"
  | "cancelled"
  | "finished"
  | "error";

export interface TaskNodeItem {
  id: string;
  title: string;
  subtitle: string;
  icon: GameIconName;
  runStatus: NodeRunStatus;
  x: number;
  y: number;
}

interface TaskNodeCanvasProps {
  tasks: TaskNodeItem[];
  activeTaskId: string;
  isZh: boolean;
  onSelect: (id: string) => void;
  onClose: (id: string) => void;
  onAdd: () => void;
  onMove: (id: string, x: number, y: number) => void;
  canClose?: (id: string) => boolean;
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

function portTone(status: NodeRunStatus): string {
  switch (status) {
    case "finished":
      return "fill-emerald-500 stroke-emerald-200 dark:stroke-emerald-900";
    case "error":
      return "fill-rose-500 stroke-rose-200 dark:stroke-rose-900";
    case "running":
    case "starting":
      return "fill-sky-500 stroke-sky-200 dark:stroke-sky-900";
    case "cancelling":
    case "cancelled":
      return "fill-slate-400 stroke-slate-200 dark:stroke-slate-700";
    case "confirming":
      return "fill-amber-500 stroke-amber-200 dark:stroke-amber-900";
    default:
      return "fill-text-tertiary stroke-border";
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

interface PortRef {
  input: HTMLSpanElement | null;
  output: HTMLSpanElement | null;
}

interface DragState {
  taskId: string;
  startX: number;
  startY: number;
  initialX: number;
  initialY: number;
}

const NODE_WIDTH = 208;

export function TaskNodeCanvas({
  tasks,
  activeTaskId,
  isZh,
  onSelect,
  onClose,
  onAdd,
  onMove,
  canClose,
}: TaskNodeCanvasProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const portRefs = useRef<Record<string, PortRef>>({});
  const [paths, setPaths] = useState<{ id: string; d: string }[]>([]);
  const [drag, setDrag] = useState<DragState | null>(null);

  const recalculatePaths = useMemo(
    () => () => {
      const container = containerRef.current;
      if (!container) {
        return;
      }
      const containerRect = container.getBoundingClientRect();
      const nextPaths: { id: string; d: string }[] = [];
      for (let index = 0; index < tasks.length - 1; index++) {
        const current = tasks[index];
        const next = tasks[index + 1];
        const outEl = portRefs.current[current.id]?.output;
        const inEl = portRefs.current[next.id]?.input;
        if (!outEl || !inEl) {
          continue;
        }
        const outRect = outEl.getBoundingClientRect();
        const inRect = inEl.getBoundingClientRect();
        const x1 = outRect.left + outRect.width / 2 - containerRect.left;
        const y1 = outRect.top + outRect.height / 2 - containerRect.top;
        const x2 = inRect.left + inRect.width / 2 - containerRect.left;
        const y2 = inRect.top + inRect.height / 2 - containerRect.top;
        const controlOffset = Math.min(96, Math.abs(x2 - x1) * 0.5);
        const c1x = x1 + controlOffset;
        const c2x = x2 - controlOffset;
        nextPaths.push({
          id: `${current.id}->${next.id}`,
          d: `M ${x1} ${y1} C ${c1x} ${y1}, ${c2x} ${y2}, ${x2} ${y2}`,
        });
      }
      setPaths(nextPaths);
    },
    [tasks],
  );

  useLayoutEffect(() => {
    recalculatePaths();
  }, [recalculatePaths]);

  useEffect(() => {
    const handleResize = () => recalculatePaths();
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, [recalculatePaths]);

  useEffect(() => {
    if (!drag) {
      return;
    }
    const handleMove = (event: PointerEvent) => {
      const dx = event.clientX - drag.startX;
      const dy = event.clientY - drag.startY;
      onMove(drag.taskId, drag.initialX + dx, drag.initialY + dy);
    };

    const handleUp = () => {
      setDrag(null);
    };

    window.addEventListener("pointermove", handleMove);
    window.addEventListener("pointerup", handleUp);
    return () => {
      window.removeEventListener("pointermove", handleMove);
      window.removeEventListener("pointerup", handleUp);
    };
  }, [drag, onMove]);

  function handlePointerDown(
    event: ReactPointerEvent<HTMLDivElement>,
    task: TaskNodeItem,
  ) {
    if (event.button !== 0) {
      return;
    }
    event.preventDefault();
    event.stopPropagation();
    onSelect(task.id);
    setDrag({
      taskId: task.id,
      startX: event.clientX,
      startY: event.clientY,
      initialX: task.x,
      initialY: task.y,
    });
  }

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
      <svg
        className="pointer-events-none absolute inset-0 h-full w-full"
        xmlns="http://www.w3.org/2000/svg"
      >
        {paths.map((path) => (
          <path
            key={path.id}
            d={path.d}
            className="fill-none stroke-border"
            strokeWidth={2}
          />
        ))}
      </svg>

      {tasks.map((task) => {
        const isActive = task.id === activeTaskId;
        return (
          <div
            key={task.id}
            className="absolute"
            style={{
              left: task.x,
              top: task.y,
              width: NODE_WIDTH,
            }}
          >
            <div
              className={[
                "group relative rounded-xl border bg-surface-raised text-left shadow-card transition",
                isActive
                  ? "border-ice-400 shadow-glow"
                  : "border-border hover:border-ice-200",
              ].join(" ")}
            >
              <div
                className={[
                  "flex cursor-grab items-center justify-between gap-2 rounded-t-xl px-3 py-2 active:cursor-grabbing",
                  isActive ? "bg-ice-50/60 dark:bg-ice-900/20" : "bg-surface",
                ].join(" ")}
                onPointerDown={(event) => handlePointerDown(event, task)}
              >
                <div className="flex min-w-0 items-center gap-2">
                  <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-surface text-text-secondary">
                    <GameIcon name={task.icon} className="h-3.5 w-3.5" />
                  </span>
                  <span className="min-w-0">
                    <p className="truncate text-[12px] font-semibold leading-4 text-text-primary">
                      {task.title}
                    </p>
                    <p className="truncate text-[10px] leading-3 text-text-tertiary">
                      {task.subtitle}
                    </p>
                  </span>
                </div>
                {canClose?.(task.id) ? (
                  <button
                    type="button"
                    className="ui-pressable -mr-1 -mt-1 flex h-5 w-5 shrink-0 items-center justify-center rounded text-text-tertiary opacity-0 transition hover:bg-surface hover:text-text-primary group-hover:opacity-100"
                    onClick={(event) => {
                      event.stopPropagation();
                      onClose(task.id);
                    }}
                    onPointerDown={(event) => event.stopPropagation()}
                  >
                    <X className="h-3 w-3" />
                  </button>
                ) : null}
              </div>

              <div className="h-1 w-full">
                <div className={["h-full", statusTone(task.runStatus)].join(" ")} />
              </div>

              <div className="px-3 py-2">
                <p className="text-[10px] font-medium uppercase tracking-[0.12em] text-text-tertiary">
                  {statusLabel(task.runStatus, isZh)}
                </p>
              </div>

              <span
                ref={(element) => {
                  portRefs.current[task.id] = {
                    ...portRefs.current[task.id],
                    input: element,
                  };
                }}
                className={[
                  "absolute left-0 top-1/2 h-2.5 w-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full ring-2 ring-surface",
                  portTone(task.runStatus),
                ].join(" ")}
                title={statusLabel(task.runStatus, isZh)}
              />
              <span
                ref={(element) => {
                  portRefs.current[task.id] = {
                    ...portRefs.current[task.id],
                    output: element,
                  };
                }}
                className={[
                  "absolute right-0 top-1/2 h-2.5 w-2.5 translate-x-1/2 -translate-y-1/2 rounded-full ring-2 ring-surface",
                  portTone(task.runStatus),
                ].join(" ")}
                title={statusLabel(task.runStatus, isZh)}
              />
            </div>
          </div>
        );
      })}

      <button
        type="button"
        className="ui-pressable absolute bottom-6 right-6 flex items-center gap-1.5 rounded-full border border-dashed border-border bg-surface px-4 py-2 text-xs font-medium text-text-secondary shadow-card transition hover:border-ice-200 hover:bg-ice-50 hover:text-ice-700 dark:hover:border-ice-800 dark:hover:bg-ice-900/30 dark:hover:text-ice-200"
        onClick={onAdd}
      >
        <Plus className="h-3.5 w-3.5" />
        {isZh ? "添加节点" : "Add node"}
      </button>
    </div>
  );
}
