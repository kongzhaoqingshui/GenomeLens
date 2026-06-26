import { LayoutGrid } from "lucide-react";

import { GameIcon, type GameIconName } from "./GameIcon";
import { Badge, EmptyState } from "./ui";
import {
  getCapabilitySubtitle,
  type CapabilityEntry,
} from "../models/capability";

export interface CapabilityListProps {
  capabilities: CapabilityEntry[];
  selectedId: string | null;
  isZh: boolean;
  onSelect: (id: string) => void;
  onOpen: (entry: CapabilityEntry) => void;
}

function iconForCapability(id: string): GameIconName {
  if (id === "environment-check") {
    return "environment";
  }
  if (id === "synteny" || id.includes("multi")) {
    return "multi-species";
  }
  if (id.includes("dotplot")) {
    return "dotplot";
  }
  if (id.includes("karyotype")) {
    return "karyotype";
  }
  if (id.includes("pairwise") || id.includes("ortholog")) {
    return "pairwise";
  }
  if (id.includes("local")) {
    return "local";
  }
  if (id.includes("histogram") || id.includes("heatmap")) {
    return "ortholog";
  }
  return "multi-species";
}

function kindLabel(entry: CapabilityEntry, isZh: boolean): string {
  if (entry.kind === "one_stop") {
    return isZh ? "一站式工作流" : "One-stop workflow";
  }
  if (entry.module_kind === "aggregate") {
    return isZh ? "聚合型子模块" : "Aggregate submodule";
  }
  if (entry.module_kind === "lightweight") {
    return isZh ? "轻量型子模块" : "Lightweight submodule";
  }
  return isZh ? "可编排子模块" : "Orchestratable submodule";
}

function statusLabel(entry: CapabilityEntry, isZh: boolean): string {
  if (!isZh) {
    return entry.status_label;
  }
  switch (entry.status) {
    case "connected":
      return "已接入";
    case "available":
      return "可用";
    case "reserved":
      return "预留";
    default:
      return entry.status_label;
  }
}

function statusTone(entry: CapabilityEntry): NonNullable<React.ComponentProps<typeof Badge>["tone"]> {
  switch (entry.status) {
    case "connected":
      return "success";
    case "available":
      return "info";
    case "reserved":
      return "default";
    default:
      return "default";
  }
}

function isActionableCapability(entry: CapabilityEntry): boolean {
  return entry.status !== "reserved";
}

function groupKey(entry: CapabilityEntry): string {
  if (entry.kind === "one_stop") return "one_stop";
  if (entry.module_kind === "lightweight") return "lightweight";
  if (entry.module_kind === "aggregate") return "aggregate";
  return "other";
}

function groupTitle(key: string, isZh: boolean): string {
  switch (key) {
    case "one_stop":
      return isZh ? "一站式工作流" : "One-stop workflows";
    case "lightweight":
      return isZh ? "轻量子模块" : "Lightweight submodules";
    case "aggregate":
      return isZh ? "聚合子模块" : "Aggregate submodules";
    default:
      return isZh ? "其他" : "Other";
  }
}

export function CapabilityList({
  capabilities,
  selectedId,
  isZh,
  onSelect,
  onOpen,
}: CapabilityListProps) {
  if (capabilities.length === 0) {
    return (
      <div className="p-4">
        <EmptyState
          icon={LayoutGrid}
          title={isZh ? "没有匹配的能力" : "No matching capabilities"}
          description={isZh ? "尝试其他关键词。" : "Try a different keyword."}
        />
      </div>
    );
  }

  const groups: Record<string, CapabilityEntry[]> = {};
  for (const entry of capabilities) {
    const key = groupKey(entry);
    if (!groups[key]) groups[key] = [];
    groups[key].push(entry);
  }

  const groupOrder = ["one_stop", "lightweight", "aggregate", "other"];
  const orderedKeys = groupOrder.filter((k) => groups[k] && groups[k].length > 0);

  return (
    <div className="flex flex-col gap-1 overflow-y-auto px-3 py-2">
      {orderedKeys.map((key) => (
        <div key={key} className="flex flex-col gap-1">
          <p className="px-2 py-1 text-[11px] font-semibold uppercase tracking-[0.12em] text-text-tertiary">
            {groupTitle(key, isZh)}
          </p>
          {groups[key].map((entry) => {
            const active = entry.id === selectedId;
            return (
              <div
                key={entry.id}
                className={[
                  "group flex cursor-pointer items-center gap-3 rounded-xl border px-3 py-2.5 transition",
                  active
                    ? "border-ice-400 bg-ice-50/60 shadow-glow dark:border-ice-700 dark:bg-ice-900/20"
                    : "border-transparent bg-surface hover:border-ice-200 hover:bg-surface-raised",
                ].join(" ")}
                onClick={() => onSelect(entry.id)}
                onDoubleClick={() => onOpen(entry)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    onSelect(entry.id);
                  }
                }}
              >
                <span
                  className={[
                    "flex h-9 w-9 shrink-0 items-center justify-center rounded-xl transition",
                    active
                      ? "bg-ice-100 text-ice-600 dark:bg-ice-900/40 dark:text-ice-200"
                      : "bg-surface-raised text-text-tertiary",
                  ].join(" ")}
                >
                  <GameIcon name={iconForCapability(entry.id)} className="h-4 w-4" />
                </span>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="truncate text-sm font-semibold text-text-primary">
                      {getCapabilitySubtitle(entry, isZh)}
                    </span>
                    <Badge tone={statusTone(entry)} dot pulse={entry.status === "connected"}>
                      {statusLabel(entry, isZh)}
                    </Badge>
                  </div>
                  <p className="truncate text-xs text-text-tertiary">
                    {kindLabel(entry, isZh)}
                  </p>
                </div>
                {isActionableCapability(entry) && (
                  <button
                    type="button"
                    className="ui-pressable hidden shrink-0 rounded-lg bg-ice-500 px-2.5 py-1 text-xs font-semibold text-white shadow-glow transition hover:bg-ice-400 group-hover:inline-flex"
                    onClick={(e) => {
                      e.stopPropagation();
                      onOpen(entry);
                    }}
                  >
                    {isZh ? "打开" : "Open"}
                  </button>
                )}
              </div>
            );
          })}
        </div>
      ))}
    </div>
  );
}
