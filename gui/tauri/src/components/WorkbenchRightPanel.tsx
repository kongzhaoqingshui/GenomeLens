import { Sliders, Play, CheckCircle2, ChevronDown } from "lucide-react";
import { useCallback, useMemo, useState } from "react";
import type { CapabilityEntry } from "../models/capability";
import { isOneStopCapability, isSubmoduleCapability, getCapabilitySubtitle } from "../models/capability";

export interface WorkbenchRightPanelProps {
  title: string;
  isZh: boolean;
  view: "setup" | "run" | "results";
  onChangeView: (view: "setup" | "run" | "results") => void;
  onChangeTitle: (title: string) => void;
  capabilities?: CapabilityEntry[];
  selectedCapabilityId?: string | null;
  onChangeCapability?: (id: string) => void;
  children: React.ReactNode;
}

function CapabilitySelector({
  value,
  capabilities,
  isZh,
  onChange,
}: {
  value: string | null;
  capabilities: CapabilityEntry[];
  isZh: boolean;
  onChange: (capabilityId: string) => void;
}) {
  const [open, setOpen] = useState(false);

  const selected = useMemo(
    () => capabilities.find((c) => c.id === value) ?? null,
    [capabilities, value],
  );

  const oneStops = useMemo(
    () => capabilities.filter((c) => isOneStopCapability(c)),
    [capabilities],
  );
  const submodules = useMemo(
    () => capabilities.filter((c) => isSubmoduleCapability(c)),
    [capabilities],
  );
  const others = useMemo(
    () => capabilities.filter((c) => !isOneStopCapability(c) && !isSubmoduleCapability(c)),
    [capabilities],
  );

  const handleSelect = useCallback(
    (capabilityId: string) => {
      onChange(capabilityId);
      setOpen(false);
    },
    [onChange],
  );

  return (
    <div className="relative">
      <button
        type="button"
        className="flex w-full items-center justify-between rounded-lg border border-border bg-bg px-3 py-2 text-sm text-text-primary shadow-card outline-none transition focus:border-ice-400 focus:ring-2 focus:ring-ice-200 dark:focus:ring-ice-900/60"
        onClick={() => setOpen((prev) => !prev)}
      >
        <span className="truncate">
          {selected ? getCapabilitySubtitle(selected, isZh) : isZh ? "选择能力..." : "Select capability..."}
        </span>
        <ChevronDown className={`h-4 w-4 shrink-0 text-text-tertiary transition ${open ? "rotate-180" : ""}`} />
      </button>

      {open ? (
        <div className="absolute z-50 mt-1 max-h-72 w-full overflow-auto rounded-lg border border-border bg-surface shadow-lg">
          {oneStops.length > 0 ? (
            <div className="py-1">
              <p className="px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.14em] text-text-tertiary">
                {isZh ? "One-stop" : "One-stop"}
              </p>
              {oneStops.map((cap) => (
                <button
                  key={cap.id}
                  type="button"
                  className={`block w-full px-3 py-2 text-left text-sm transition hover:bg-ice-50 dark:hover:bg-ice-900/30 ${cap.id === value ? "bg-ice-50 text-ice-700 dark:bg-ice-900/30 dark:text-ice-200" : "text-text-secondary"}`}
                  onClick={() => handleSelect(cap.id)}
                >
                  {getCapabilitySubtitle(cap, isZh)}
                </button>
              ))}
            </div>
          ) : null}

          {submodules.length > 0 ? (
            <div className="border-t border-border py-1">
              <p className="px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.14em] text-text-tertiary">
                {isZh ? "Submodules" : "Submodules"}
              </p>
              {submodules.map((cap) => (
                <button
                  key={cap.id}
                  type="button"
                  className={`block w-full px-3 py-2 text-left text-sm transition hover:bg-ice-50 dark:hover:bg-ice-900/30 ${cap.id === value ? "bg-ice-50 text-ice-700 dark:bg-ice-900/30 dark:text-ice-200" : "text-text-secondary"}`}
                  onClick={() => handleSelect(cap.id)}
                >
                  {getCapabilitySubtitle(cap, isZh)}
                </button>
              ))}
            </div>
          ) : null}

          {others.length > 0 ? (
            <div className="border-t border-border py-1">
              <p className="px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.14em] text-text-tertiary">
                {isZh ? "其他" : "Other"}
              </p>
              {others.map((cap) => (
                <button
                  key={cap.id}
                  type="button"
                  className={`block w-full px-3 py-2 text-left text-sm transition hover:bg-ice-50 dark:hover:bg-ice-900/30 ${cap.id === value ? "bg-ice-50 text-ice-700 dark:bg-ice-900/30 dark:text-ice-200" : "text-text-secondary"}`}
                  onClick={() => handleSelect(cap.id)}
                >
                  {getCapabilitySubtitle(cap, isZh)}
                </button>
              ))}
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

export function WorkbenchRightPanel({
  title,
  isZh,
  view,
  onChangeView,
  onChangeTitle,
  capabilities,
  selectedCapabilityId,
  onChangeCapability,
  children,
}: WorkbenchRightPanelProps) {
  const tabs: Array<{ key: "setup" | "run" | "results"; label: string; icon: typeof Sliders }> = [
    { key: "setup", label: isZh ? "配置" : "Setup", icon: Sliders },
    { key: "run", label: isZh ? "运行" : "Run", icon: Play },
    { key: "results", label: isZh ? "结果" : "Results", icon: CheckCircle2 },
  ];

  return (
    <div className="flex h-full flex-col overflow-hidden border-l border-border/90 bg-surface">
      <header className="shrink-0 space-y-3 border-b border-border/90 bg-surface-raised/50 px-4 py-3 backdrop-blur">
        <input
          className="w-full rounded-xl border border-border bg-bg px-3 py-2 text-sm text-text-primary shadow-card outline-none transition focus:border-ice-400 focus:ring-2 focus:ring-ice-200 dark:focus:ring-ice-900/60"
          value={title}
          onChange={(event) => onChangeTitle(event.target.value)}
          placeholder={isZh ? "标题" : "Title"}
        />

        <div className="flex items-center gap-1 rounded-xl bg-surface p-1 shadow-card">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const active = view === tab.key;
            return (
              <button
                key={tab.key}
                type="button"
                className={[
                  "ui-pressable inline-flex flex-1 items-center justify-center gap-1.5 rounded-lg px-2.5 py-1.5 text-[10px] font-semibold uppercase tracking-[0.14em] transition",
                  active
                    ? "bg-ice-50 text-ice-700 dark:bg-ice-900/30 dark:text-ice-200"
                    : "text-text-secondary hover:bg-surface-raised/80 hover:text-text-primary",
                ].join(" ")}
                onClick={() => onChangeView(tab.key)}
              >
                <Icon className="h-3.5 w-3.5" />
                {tab.label}
              </button>
            );
          })}
        </div>

        {capabilities && capabilities.length > 0 && onChangeCapability ? (
          <CapabilitySelector
            value={selectedCapabilityId ?? null}
            capabilities={capabilities}
            isZh={isZh}
            onChange={onChangeCapability}
          />
        ) : null}
      </header>

      <div className="flex-1 overflow-auto px-4 py-4">{children}</div>
    </div>
  );
}
