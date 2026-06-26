import { Plus, Search, Settings, X, ChevronRight, Trash2, LayoutPanelLeft } from "lucide-react";
import { useMemo, useState } from "react";

import { GameIcon, type GameIconName } from "./GameIcon";
import type { CapabilityEntry } from "../models/capability";
import { getCapabilitySubtitle } from "../models/capability";

export type LeftPanelTaskStatus =
  | "idle"
  | "confirming"
  | "starting"
  | "running"
  | "cancelling"
  | "cancelled"
  | "finished"
  | "error";

export interface LeftPanelTaskItem {
  id: string;
  title: string;
  subtitle: string;
  icon: GameIconName;
  runStatus: LeftPanelTaskStatus;
  onCanvas: boolean;
}

export interface QuickCapabilityTemplate {
  id: string;
  subtitle: string;
  icon: GameIconName;
  preset?: string;
}

export interface WorkbenchLeftPanelProps {
  tasks: LeftPanelTaskItem[];
  activeTaskId: string;
  isZh: boolean;
  capabilities: CapabilityEntry[];
  onSelectTask: (id: string) => void;
  onCloseTask: (id: string) => void;
  onAddTaskFromTemplate: (capabilityId: string, preset?: string) => void;
  onAddDataNode: () => void;
  onDeleteSavedTask: (id: string) => void;
  onOpenSettings: () => void;
}

function statusTone(status: LeftPanelTaskStatus): string {
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

export function WorkbenchLeftPanel({
  tasks,
  activeTaskId,
  isZh,
  capabilities,
  onSelectTask,
  onCloseTask,
  onAddTaskFromTemplate,
  onAddDataNode,
  onDeleteSavedTask,
  onOpenSettings,
}: WorkbenchLeftPanelProps) {
  const [query, setQuery] = useState("");

  const normalizedQuery = query.trim().toLowerCase();

  const canvasTasks = useMemo(
    () =>
      tasks
        .filter((t) => t.onCanvas)
        .filter((t) =>
          normalizedQuery
            ? t.title.toLowerCase().includes(normalizedQuery) ||
              t.subtitle.toLowerCase().includes(normalizedQuery)
            : true,
        ),
    [tasks, normalizedQuery],
  );

  const savedTasks = useMemo(
    () =>
      tasks
        .filter((t) => !t.onCanvas)
        .filter((t) =>
          normalizedQuery
            ? t.title.toLowerCase().includes(normalizedQuery) ||
              t.subtitle.toLowerCase().includes(normalizedQuery)
            : true,
        ),
    [tasks, normalizedQuery],
  );

  const syntenyTemplates: QuickCapabilityTemplate[] = useMemo(() => {
    const presets = [
      { id: "synteny", preset: "pairwise", subtitle: isZh ? "Pairwise 共线性" : "Pairwise synteny", icon: "pairwise" as GameIconName },
      { id: "synteny", preset: "multi", subtitle: isZh ? "多物种共线性" : "Multi-species synteny", icon: "multi-species" as GameIconName },
      { id: "synteny", preset: "local", subtitle: isZh ? "局部共线性" : "Local synteny", icon: "local" as GameIconName },
    ];
    return presets;
  }, [isZh]);

  const submoduleTemplates: QuickCapabilityTemplate[] = useMemo(() => {
    const subs = capabilities.filter((c) => c.kind === "sub_module");
    return subs.map((c) => ({
      id: c.id,
      subtitle: getCapabilitySubtitle(c, isZh),
      icon: capabilityIcon(c.id),
    }));
  }, [capabilities, isZh]);

  return (
    <div className="flex h-full min-h-0 flex-col">
      {/* Search */}
      <div className="flex items-center gap-2 px-3 pb-3 pt-3">
        <div className="flex flex-1 items-center gap-2 rounded-xl border border-border bg-surface-raised px-2.5 py-2">
          <Search className="h-4 w-4 text-text-tertiary" />
          <input
            className="min-w-0 flex-1 bg-transparent text-sm text-text-primary outline-none placeholder:text-text-tertiary"
            placeholder={isZh ? "搜索任务" : "Search tasks"}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </div>
        <button
          type="button"
          className="ui-icon-button"
          title={isZh ? "设置" : "Settings"}
          onClick={onOpenSettings}
        >
          <Settings className="h-4 w-4" />
        </button>
      </div>

      {/* Canvas tasks */}
      <div className="min-h-0 flex-1 overflow-auto px-3">
        <div className="flex items-center justify-between gap-3 pb-2 pt-1">
          <h2 className="text-xs font-semibold uppercase tracking-[0.14em] text-text-tertiary">
            {isZh ? "画布上的任务" : "On canvas"}
          </h2>
          <span className="rounded-full bg-surface px-2 py-0.5 text-[10px] font-medium text-text-tertiary">
            {canvasTasks.length}
          </span>
        </div>

        {canvasTasks.length === 0 ? (
          <div className="ui-empty-state mt-2">
            <LayoutPanelLeft className="h-8 w-8 text-text-tertiary" />
            <p className="text-sm font-semibold text-text-primary">
              {isZh ? "画布暂无任务" : "No tasks on canvas"}
            </p>
          </div>
        ) : (
          <div className="space-y-2 pb-2">
            {canvasTasks.map((task) => (
              <TaskRow
                key={task.id}
                task={task}
                isActive={task.id === activeTaskId}
                isZh={isZh}
                onSelect={() => onSelectTask(task.id)}
                onClose={() => onCloseTask(task.id)}
              />
            ))}
          </div>
        )}

        {/* Saved tasks */}
        {savedTasks.length > 0 && (
          <>
            <div className="flex items-center justify-between gap-3 border-t border-border/90 pb-2 pt-3">
              <h2 className="text-xs font-semibold uppercase tracking-[0.14em] text-text-tertiary">
                {isZh ? "已保存任务" : "Saved tasks"}
              </h2>
              <span className="rounded-full bg-surface px-2 py-0.5 text-[10px] font-medium text-text-tertiary">
                {savedTasks.length}
              </span>
            </div>
            <div className="space-y-2 pb-2">
              {savedTasks.map((task) => (
                <SavedTaskRow
                  key={task.id}
                  task={task}
                  isZh={isZh}
                  onAddToCanvas={() => onAddTaskFromTemplate(task.id)}
                  onDelete={() => onDeleteSavedTask(task.id)}
                />
              ))}
            </div>
          </>
        )}
      </div>

      {/* Quick add */}
      <div className="border-t border-border/90 px-3 pt-3 pb-3">
        <p className="px-1 text-[10px] font-semibold uppercase tracking-[0.14em] text-text-tertiary">
          {isZh ? "快速新建" : "Quick add"}
        </p>
        <div className="mt-2 flex flex-wrap gap-2">
          {syntenyTemplates.map((cap) => (
            <button
              key={`${cap.id}-${cap.preset ?? "default"}`}
              type="button"
              className="ui-pressable inline-flex items-center gap-1.5 rounded-lg border border-border bg-surface px-2 py-1.5 text-left text-xs text-text-secondary transition hover:bg-surface-raised hover:text-text-primary"
              onClick={() => onAddTaskFromTemplate(cap.id, cap.preset)}
              title={cap.subtitle}
            >
              <GameIcon name={cap.icon} className="h-3.5 w-3.5" />
              <span className="max-w-[8rem] truncate">{cap.subtitle}</span>
            </button>
          ))}
          {submoduleTemplates.map((cap) => (
            <button
              key={cap.id}
              type="button"
              className="ui-pressable inline-flex items-center gap-1.5 rounded-lg border border-border bg-surface px-2 py-1.5 text-left text-xs text-text-secondary transition hover:bg-surface-raised hover:text-text-primary"
              onClick={() => onAddTaskFromTemplate(cap.id)}
              title={cap.subtitle}
            >
              <GameIcon name={cap.icon} className="h-3.5 w-3.5" />
              <span className="max-w-[8rem] truncate">{cap.subtitle}</span>
            </button>
          ))}
        </div>
        <button
          type="button"
          className="ui-pressable mt-2 flex w-full items-center justify-center gap-1.5 rounded-xl border border-dashed border-border bg-surface-raised/60 px-3 py-2 text-xs font-medium text-text-secondary transition hover:border-ice-200 hover:bg-ice-50 hover:text-ice-700 dark:hover:border-ice-800 dark:hover:bg-ice-900/30 dark:hover:text-ice-200"
          onClick={onAddDataNode}
        >
          <Plus className="h-3.5 w-3.5" />
          {isZh ? "添加数据节点" : "Add data node"}
        </button>
      </div>
    </div>
  );
}

function TaskRow({
  task,
  isActive,
  isZh,
  onSelect,
  onClose,
}: {
  task: LeftPanelTaskItem;
  isActive: boolean;
  isZh: boolean;
  onSelect: () => void;
  onClose: () => void;
}) {
  return (
    <div
      role="button"
      tabIndex={0}
      className={[
        "ui-pressable group relative flex w-full items-center gap-2.5 rounded-xl border bg-surface-raised text-left shadow-card transition",
        isActive ? "border-ice-400 shadow-glow" : "border-border hover:border-ice-200",
      ].join(" ")}
      onClick={onSelect}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onSelect();
        }
      }}
    >
      <div
        className={["h-full w-1.5 rounded-l-xl", statusTone(task.runStatus)].join(" ")}
      />
      <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-surface text-text-secondary">
        <GameIcon name={task.icon} className="h-4 w-4" />
      </span>
      <div className="min-w-0 flex-1 py-2.5">
        <p className="truncate text-[13px] font-semibold leading-5 text-text-primary">
          {task.title}
        </p>
        <p className="truncate text-[11px] leading-4 text-text-tertiary">
          {task.subtitle}
        </p>
      </div>
      <button
        type="button"
        className="ui-pressable -mr-1 flex h-6 w-6 shrink-0 items-center justify-center rounded-md text-text-tertiary opacity-0 transition group-hover:opacity-100 hover:bg-surface hover:text-text-primary"
        title={isZh ? "从画布移除" : "Remove from canvas"}
        onClick={(e) => {
          e.stopPropagation();
          onClose();
        }}
      >
        <X className="h-3 w-3" />
      </button>
    </div>
  );
}

function SavedTaskRow({
  task,
  isZh,
  onAddToCanvas,
  onDelete,
}: {
  task: LeftPanelTaskItem;
  isZh: boolean;
  onAddToCanvas: () => void;
  onDelete: () => void;
}) {
  return (
    <div className="ui-pressable group relative flex w-full items-center gap-2.5 rounded-xl border border-border bg-surface text-left shadow-card transition hover:border-ice-200">
      <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-surface text-text-secondary">
        <GameIcon name={task.icon} className="h-4 w-4" />
      </span>
      <div className="min-w-0 flex-1 py-2.5">
        <p className="truncate text-[13px] font-semibold leading-5 text-text-primary">
          {task.title}
        </p>
        <p className="truncate text-[11px] leading-4 text-text-tertiary">
          {task.subtitle}
        </p>
      </div>
      <div className="flex shrink-0 items-center gap-1 pr-2 opacity-0 transition group-hover:opacity-100">
        <button
          type="button"
          className="ui-pressable flex h-6 w-6 items-center justify-center rounded-md text-text-tertiary hover:bg-surface hover:text-text-primary"
          title={isZh ? "添加到画布" : "Add to canvas"}
          onClick={onAddToCanvas}
        >
          <ChevronRight className="h-3 w-3" />
        </button>
        <button
          type="button"
          className="ui-pressable flex h-6 w-6 items-center justify-center rounded-md text-text-tertiary hover:bg-surface hover:text-rose-500"
          title={isZh ? "删除" : "Delete"}
          onClick={onDelete}
        >
          <Trash2 className="h-3 w-3" />
        </button>
      </div>
    </div>
  );
}

function capabilityIcon(id: string): GameIconName {
  switch (id) {
    case "synteny":
      return "multi-species";
    case "jcvi.pairwise":
      return "pairwise";
    case "jcvi.graphics_dotplot":
      return "dotplot";
    case "jcvi.graphics_synteny":
      return "multi-species";
    case "jcvi.graphics_karyotype":
    case "jcvi.graphics_karyotype_global":
      return "karyotype";
    case "jcvi.local_synteny":
    case "jcvi.local_synteny_multi":
      return "local";
    case "environment-check":
      return "environment";
    default:
      return "dotplot";
  }
}
