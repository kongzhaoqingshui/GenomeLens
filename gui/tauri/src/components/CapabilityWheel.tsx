import { ChevronLeft, ChevronRight } from "lucide-react";
import { useRef } from "react";

import { GameIcon } from "./GameIcon";
import { getCapabilitySubtitle, type CapabilityEntry } from "../models/capability";

interface CapabilityWheelProps {
  capabilities: CapabilityEntry[];
  selectedId: string | null;
  isZh: boolean;
  onSelect: (id: string) => void;
}

function kindLabel(entry: CapabilityEntry, isZh: boolean): string {
  if (entry.kind === "one_stop") {
    return isZh ? "一站式" : "One-stop";
  }
  if (entry.module_kind === "aggregate") {
    return isZh ? "聚合" : "Aggregate";
  }
  if (entry.module_kind === "lightweight") {
    return isZh ? "轻量" : "Lightweight";
  }
  return isZh ? "子模块" : "Submodule";
}

function iconForCapability(id: string) {
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

export function CapabilityWheel({
  capabilities,
  selectedId,
  isZh,
  onSelect,
}: CapabilityWheelProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  const scrollBy = (direction: number) => {
    const container = scrollRef.current;
    if (!container) {
      return;
    }
    const cardWidth = container.firstElementChild?.getBoundingClientRect().width ?? 128;
    container.scrollBy({ left: direction * cardWidth, behavior: "smooth" });
  };

  return (
    <div className="relative flex items-center gap-2">
      <button
        type="button"
        className="ui-icon-button shrink-0"
        onClick={() => scrollBy(-1)}
        aria-label={isZh ? "向左滚动" : "Scroll left"}
      >
        <ChevronLeft className="h-4 w-4" />
      </button>

      <div
        ref={scrollRef}
        className="flex min-h-0 flex-1 gap-3 overflow-x-auto scroll-smooth pb-2 pt-1 scrollbar-hide"
        style={{ scrollSnapType: "x mandatory" }}
      >
        {capabilities.map((entry) => {
          const active = entry.id === selectedId;
          return (
            <button
              key={entry.id}
              type="button"
              onClick={() => onSelect(entry.id)}
              className={[
                "ui-pressable flex w-28 shrink-0 snap-start flex-col items-center gap-2 rounded-2xl border px-3 py-4 text-center transition",
                active
                  ? "border-ice-400 bg-ice-50/60 shadow-glow dark:border-ice-700 dark:bg-ice-900/20"
                  : "border-border bg-surface hover:border-ice-200 hover:bg-surface-raised",
              ].join(" ")}
            >
              <span
                className={[
                  "flex h-10 w-10 items-center justify-center rounded-xl transition",
                  active
                    ? "bg-ice-100 text-ice-600 dark:bg-ice-900/40 dark:text-ice-200"
                    : "bg-surface-raised text-text-tertiary",
                ].join(" ")}
              >
                <GameIcon name={iconForCapability(entry.id)} className="h-5 w-5" />
              </span>
              <span className="block w-full">
                <span
                  className={[
                    "block truncate text-[11px] font-semibold leading-4",
                    active ? "text-text-primary" : "text-text-secondary",
                  ].join(" ")}
                >
                  {getCapabilitySubtitle(entry, isZh)}
                </span>
                <span className="mt-0.5 block truncate text-[10px] text-text-tertiary">
                  {kindLabel(entry, isZh)}
                </span>
              </span>
            </button>
          );
        })}
      </div>

      <button
        type="button"
        className="ui-icon-button shrink-0"
        onClick={() => scrollBy(1)}
        aria-label={isZh ? "向右滚动" : "Scroll right"}
      >
        <ChevronRight className="h-4 w-4" />
      </button>
    </div>
  );
}
