import { Plus, Search, X } from "lucide-react";
import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";

import { GameIcon, type GameIconName } from "./GameIcon";

type BlockRunStatus =
  | "idle"
  | "confirming"
  | "starting"
  | "running"
  | "cancelling"
  | "cancelled"
  | "finished"
  | "error";

interface BlockTaskItem {
  id: string;
  title: string;
  subtitle: string;
  icon: GameIconName;
  runStatus: BlockRunStatus;
}

interface QuickCapabilityItem {
  id: string;
  subtitle: string;
  icon: GameIconName;
  preset?: string;
}

interface WorkbenchBlockPanelProps {
  tasks: BlockTaskItem[];
  activeTaskId: string;
  isZh: boolean;
  onSelect: (id: string) => void;
  onClose: (id: string) => void;
  onAdd: () => void;
  onAddCapability: (capabilityId: string, preset?: string) => void;
  quickCapabilities: QuickCapabilityItem[];
  canClose?: (id: string) => boolean;
}

function statusTone(status: BlockRunStatus): string {
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

function statusLabel(status: BlockRunStatus, isZh: boolean): string {
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

function portTone(status: BlockRunStatus): string {
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

interface PortRef {
  input: HTMLSpanElement | null;
  output: HTMLSpanElement | null;
}

export function WorkbenchBlockPanel({
  tasks,
  activeTaskId,
  isZh,
  onSelect,
  onClose,
  onAdd,
  onAddCapability,
  quickCapabilities,
  canClose,
}: WorkbenchBlockPanelProps) {
  const [query, setQuery] = useState("");
  const containerRef = useRef<HTMLDivElement>(null);
  const portRefs = useRef<Record<string, PortRef>>({});
  const [paths, setPaths] = useState<{ id: string; d: string }[]>([]);

  const visibleTasks = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    if (!normalized) {
      return tasks;
    }
    return tasks.filter(
      (task) =>
        task.title.toLowerCase().includes(normalized) ||
        task.subtitle.toLowerCase().includes(normalized),
    );
  }, [query, tasks]);

  const recalculatePaths = useMemo(
    () => () => {
      const container = containerRef.current;
      if (!container) {
        return;
      }
      const containerRect = container.getBoundingClientRect();
      const nextPaths: { id: string; d: string }[] = [];
      for (let index = 0; index < visibleTasks.length - 1; index++) {
        const current = visibleTasks[index];
        const next = visibleTasks[index + 1];
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
        const controlOffset = Math.min(64, Math.abs(y2 - y1) * 0.6);
        const c1x = x1 + controlOffset;
        const c2x = x2 - controlOffset;
        nextPaths.push({
          id: `${current.id}->${next.id}`,
          d: `M ${x1} ${y1} C ${c1x} ${y1}, ${c2x} ${y2}, ${x2} ${y2}`,
        });
      }
      setPaths(nextPaths);
    },
    [visibleTasks],
  );

  useLayoutEffect(() => {
    recalculatePaths();
  }, [recalculatePaths]);

  useEffect(() => {
    const handleResize = () => recalculatePaths();
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, [recalculatePaths]);

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="flex items-center gap-2 px-1 pb-3">
        <div className="flex flex-1 items-center gap-2 rounded-xl border border-border bg-surface-raised px-2.5 py-2">
          <Search className="h-4 w-4 text-text-tertiary" />
          <input
            className="min-w-0 flex-1 bg-transparent text-sm text-text-primary outline-none placeholder:text-text-tertiary"
            placeholder={isZh ? "搜索积木" : "Search blocks"}
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
        </div>
        <button
          type="button"
          className="ui-icon-button"
          title={isZh ? "添加积木" : "Add block"}
          onClick={onAdd}
        >
          <Plus className="h-4 w-4" />
        </button>
      </div>

      <div className="flex items-center justify-between gap-3 px-1 pb-2">
        <h2 className="text-xs font-semibold uppercase tracking-[0.14em] text-text-tertiary">
          {isZh ? "分析流水线" : "Analysis pipeline"}
        </h2>
        <span className="rounded-full bg-surface px-2 py-0.5 text-[10px] font-medium text-text-tertiary">
          {visibleTasks.length}
        </span>
      </div>

      <div
        ref={containerRef}
        className="relative min-h-0 flex-1 overflow-auto px-1"
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
              strokeDasharray="4 4"
            />
          ))}
        </svg>

        {visibleTasks.length === 0 ? (
          <div className="ui-empty-state mt-2">
            <Search className="h-8 w-8 text-text-tertiary" />
            <p className="text-sm font-semibold text-text-primary">
              {isZh ? "无匹配积木" : "No matching blocks"}
            </p>
          </div>
        ) : (
          <div className="relative py-2">
            {visibleTasks.map((task) => {
              const isActive = task.id === activeTaskId;
              return (
                <div key={task.id} className="relative mb-4">
                  <div
                    role="button"
                    tabIndex={0}
                    className={[
                      "ui-pressable group relative w-full rounded-xl border bg-surface-raised text-left shadow-card transition",
                      isActive
                        ? "border-ice-400 shadow-glow"
                        : "border-border hover:border-ice-200",
                    ].join(" ")}
                    onClick={() => onSelect(task.id)}
                    onKeyDown={(event) => {
                      if (event.key === "Enter" || event.key === " ") {
                        event.preventDefault();
                        onSelect(task.id);
                      }
                    }}
                  >
                    <div
                      className={[
                        "h-1.5 w-full rounded-t-xl",
                        statusTone(task.runStatus),
                      ].join(" ")}
                    />
                    <div className="flex items-start gap-2.5 px-3 py-2.5">
                      <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-surface text-text-secondary">
                        <GameIcon name={task.icon} className="h-4 w-4" />
                      </span>
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-[13px] font-semibold leading-5 text-text-primary">
                          {task.title}
                        </p>
                        <p className="truncate text-[11px] leading-4 text-text-tertiary">
                          {task.subtitle}
                        </p>
                      </div>
                      {canClose?.(task.id) ? (
                        <button
                          type="button"
                          className="ui-pressable -mr-1 -mt-1 flex h-6 w-6 shrink-0 items-center justify-center rounded-md text-text-tertiary opacity-0 transition group-hover:opacity-100 hover:bg-surface hover:text-text-primary"
                          onClick={(event) => {
                            event.stopPropagation();
                            onClose(task.id);
                          }}
                        >
                          <X className="h-3 w-3" />
                        </button>
                      ) : null}
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
              className="ui-pressable relative flex w-full items-center justify-center gap-1.5 rounded-xl border border-dashed border-border bg-surface-raised/60 px-3 py-3 text-xs font-medium text-text-secondary transition hover:border-ice-200 hover:bg-ice-50 hover:text-ice-700 dark:hover:border-ice-800 dark:hover:bg-ice-900/30 dark:hover:text-ice-200"
              onClick={onAdd}
            >
              <Plus className="h-3.5 w-3.5" />
              {isZh ? "添加节点" : "Add node"}
            </button>
          </div>
        )}
      </div>

      <div className="border-t border-border/90 px-1 pt-3">
        <p className="px-2 text-[10px] font-semibold uppercase tracking-[0.14em] text-text-tertiary">
          {isZh ? "快速添加" : "Quick add"}
        </p>
        <div className="mt-2 flex flex-wrap gap-2">
          {quickCapabilities.map((capability) => (
            <button
              key={capability.id}
              type="button"
              className="ui-pressable inline-flex items-center gap-1.5 rounded-lg border border-border bg-surface px-2 py-1.5 text-left text-xs text-text-secondary transition hover:bg-surface-raised hover:text-text-primary"
              onClick={() => onAddCapability(capability.id, capability.preset)}
              title={capability.subtitle}
            >
              <GameIcon name={capability.icon} className="h-3.5 w-3.5" />
              <span className="max-w-[8rem] truncate">{capability.subtitle}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
