import { useEffect, useMemo, useState } from "react";

import { GameIcon, type GameIconName } from "../components/GameIcon";
import { JcviMeowIcon } from "../components/JcviMeowIcon";
import { useLanguage } from "../i18n/useLanguage";
import {
  getCapabilityDescription,
  getCapabilitySubtitle,
  type CapabilityEntry,
} from "../models/capability";
import { listCapabilities, clearCapabilityCache } from "../services/capability";
import type { AppRoute } from "../routes/routes";

interface HomeProps {
  route: AppRoute;
  onNavigate: (path: string) => void;
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

function isActionableCapability(entry: CapabilityEntry): boolean {
  return entry.status !== "reserved";
}

function actionLabel(entry: CapabilityEntry, isZh: boolean): string {
  if (entry.route === "/settings") {
    return isZh ? "打开诊断" : "Open diagnostics";
  }
  return isActionableCapability(entry)
    ? isZh
      ? "打开工作台"
      : "Open workbench"
    : isZh
      ? "预览能力"
      : "Preview capability";
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

function createFallbackCapabilities(): CapabilityEntry[] {
  return [
    {
      id: "synteny",
      kind: "one_stop",
      name: "synteny",
      subtitle: "一站式 synteny 共线性",
      description: "端到端 synteny 一站式工作流，自动展开 pairwise 计算、全局图件与局部共线性。",
      status: "connected",
      status_label: "Connected",
      route: "/analysis/new",
      inputs: [],
      outputs: [],
      parameters: [],
      labels: [],
    },
  ];
}

interface CapabilityGroup {
  key: string;
  title: string;
  items: CapabilityEntry[];
}

function groupCapabilities(entries: CapabilityEntry[], isZh: boolean): CapabilityGroup[] {
  const oneStop = entries.filter((entry) => entry.kind === "one_stop");
  const lightweight = entries.filter(
    (entry) => entry.kind === "sub_module" && entry.module_kind === "lightweight",
  );
  const aggregate = entries.filter(
    (entry) => entry.kind === "sub_module" && entry.module_kind === "aggregate",
  );

  const groups: CapabilityGroup[] = [];
  if (oneStop.length > 0) {
    groups.push({
      key: "one-stop",
      title: isZh ? "一站式工作流" : "One-stop workflows",
      items: oneStop,
    });
  }
  if (lightweight.length > 0) {
    groups.push({
      key: "lightweight",
      title: isZh ? "轻量型子模块" : "Lightweight submodules",
      items: lightweight,
    });
  }
  if (aggregate.length > 0) {
    groups.push({
      key: "aggregate",
      title: isZh ? "聚合型子模块" : "Aggregate submodules",
      items: aggregate,
    });
  }
  return groups;
}

export default function Home({ onNavigate }: HomeProps) {
  const { language } = useLanguage();
  const isZh = language === "zh-CN";
  const [capabilities, setCapabilities] = useState<CapabilityEntry[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    listCapabilities("all")
      .then((entries) => {
        if (cancelled) {
          return;
        }
        setCapabilities(entries);
        const defaultSelected =
          entries.find((entry) => entry.kind === "one_stop" && isActionableCapability(entry)) ??
          entries.find((entry) => isActionableCapability(entry)) ??
          entries[0];
        setSelectedId((current) => current ?? defaultSelected?.id ?? null);
      })
      .catch((loadError: unknown) => {
        if (cancelled) {
          return;
        }
        const fallback = createFallbackCapabilities();
        setCapabilities(fallback);
        setSelectedId(fallback[0]?.id ?? null);
        setError(loadError instanceof Error ? loadError.message : String(loadError));
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const selected = useMemo(() => {
    if (!capabilities) {
      return undefined;
    }
    return (
      capabilities.find((entry) => entry.id === selectedId) ??
      capabilities.find((entry) => isActionableCapability(entry)) ??
      capabilities[0]
    );
  }, [capabilities, selectedId]);

  const groups = useMemo(
    () => (capabilities ? groupCapabilities(capabilities, isZh) : []),
    [capabilities, isZh],
  );

  function handleRetry() {
    clearCapabilityCache();
    setCapabilities(null);
    setSelectedId(null);
    setError(null);
    setLoading(true);
    listCapabilities("all")
      .then((entries) => {
        setCapabilities(entries);
        const defaultSelected =
          entries.find((entry) => entry.kind === "one_stop" && isActionableCapability(entry)) ??
          entries.find((entry) => isActionableCapability(entry)) ??
          entries[0];
        setSelectedId(defaultSelected?.id ?? null);
      })
      .catch((loadError: unknown) => {
        const fallback = createFallbackCapabilities();
        setCapabilities(fallback);
        setSelectedId(fallback[0]?.id ?? null);
        setError(loadError instanceof Error ? loadError.message : String(loadError));
      })
      .finally(() => setLoading(false));
  }

  function handleOpenCapability(entry: CapabilityEntry) {
    if (entry.status === "reserved") {
      setSelectedId(entry.id);
      return;
    }

    if (entry.route === "/settings") {
      onNavigate("/settings");
      return;
    }

    // Keep the existing synteny run flow intact by mapping the one-stop
    // workflow back to the legacy query parameter that the workbench already
    // understands. Submodule ids flow through as-is and will be handled by the
    // workbench once dual-protocol support lands.
    const targetCapabilityId = entry.id === "synteny" ? "pairwise-synteny" : entry.id;
    onNavigate(`/analysis/new?capability=${encodeURIComponent(targetCapabilityId)}`);
  }

  if (loading) {
    return (
      <div className="ui-page-enter ui-app-frame grid h-screen w-full content-center justify-center gap-3 text-center">
        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-text-tertiary">
          JCVI meow · {isZh ? "首页" : "Home"}
        </p>
        <p className="text-sm text-text-secondary">{isZh ? "正在加载能力列表..." : "Loading capabilities..."}</p>
      </div>
    );
  }

  if (!selected) {
    return (
      <div className="ui-page-enter ui-app-frame grid h-screen w-full content-center justify-center gap-3 text-center">
        <p className="text-base font-semibold text-text-primary">
          {isZh ? "暂无可用能力" : "No capabilities available"}
        </p>
        {error ? <p className="max-w-md text-sm text-text-secondary">{error}</p> : null}
      </div>
    );
  }

  return (
    <div className="ui-page-enter ui-app-frame grid h-screen w-full grid-cols-[18rem_minmax(0,1fr)_17rem] overflow-hidden">
      <aside className="ui-shell-sidebar flex min-h-0 flex-col border-r px-3 py-3">
        <div className="flex items-center gap-2.5 rounded-xl px-2.5 py-2">
          <JcviMeowIcon className="h-8 w-8" />
          <span className="min-w-0">
            <span className="jcvi-brand-title block truncate text-sm font-semibold text-text-primary">
              JCVI meow
            </span>
            <span className="block text-xs text-text-secondary">
              {isZh ? "桌面工作台" : "Desktop workbench"}
            </span>
          </span>
        </div>

        <button
          type="button"
          className="ui-pressable mt-3 rounded-lg bg-ice-500 px-3 py-2 text-left text-sm font-semibold text-white transition hover:bg-ice-400"
          onClick={() => handleOpenCapability(selected)}
        >
          {actionLabel(selected, isZh)}
        </button>

        <div className="mt-5 min-h-0 flex-1 overflow-y-auto overflow-x-hidden pr-1">
          {groups.map((group) => (
            <div key={group.key} className="mb-4">
              <div className="px-2.5 py-1.5 text-[11px] font-medium uppercase tracking-[0.16em] text-text-tertiary">
                {group.title}
              </div>
              <div className="mt-1">
                {group.items.map((entry) => {
                  const active = entry.id === selected.id;
                  return (
                    <button
                      key={entry.id}
                      type="button"
                      className={
                        active
                          ? "ui-list-item mb-1 flex w-full items-center gap-2.5 rounded-lg border border-border bg-surface-raised px-2.5 py-2 text-left shadow-card"
                          : "ui-list-item mb-1 flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-left text-text-secondary transition hover:bg-surface-raised/75 hover:text-text-primary"
                      }
                      onClick={() => setSelectedId(entry.id)}
                      title={getCapabilityDescription(entry, isZh)}
                    >
                      <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-surface text-text-secondary">
                        <GameIcon name={iconForCapability(entry.id)} className="h-4 w-4" />
                      </span>
                      <span className="min-w-0">
                        <span className="block truncate text-[13px] font-medium text-text-primary">
                          {getCapabilitySubtitle(entry, isZh)}
                        </span>
                        <span className="block truncate text-xs text-text-tertiary">
                          {statusLabel(entry, isZh)}
                        </span>
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>
          ))}
        </div>

        {error ? (
          <div className="mb-2 rounded-lg border border-amber-200 bg-amber-50 px-2.5 py-2 text-xs text-amber-800 dark:border-amber-900/40 dark:bg-amber-950/30 dark:text-amber-200">
            <p className="font-medium">{isZh ? "能力列表加载失败" : "Failed to load capabilities"}</p>
            <p className="mt-1 line-clamp-2">{error}</p>
            <button
              type="button"
              className="mt-1.5 font-medium underline hover:no-underline"
              onClick={handleRetry}
            >
              {isZh ? "重试" : "Retry"}
            </button>
          </div>
        ) : null}

        <div className="border-t border-border/90 pt-3">
          <button
            type="button"
            className="ui-list-item flex w-full items-center gap-3 rounded-lg px-2.5 py-2 text-left text-sm text-text-secondary transition hover:bg-surface-raised/75 hover:text-text-primary"
            onClick={() => onNavigate("/settings")}
          >
            <GameIcon name="environment" className="h-4 w-4" />
            {isZh ? "设置与诊断" : "Settings and diagnostics"}
          </button>
        </div>
      </aside>

      <main className="flex min-w-0 flex-col bg-surface-raised">
        <header className="flex h-14 items-center justify-between border-b border-border/90 px-7">
          <div>
            <p className="text-xs font-medium uppercase tracking-[0.16em] text-text-tertiary">
              {isZh ? "首页" : "Home"}
            </p>
            <h1 className="mt-1 text-base font-semibold text-text-primary">
              {getCapabilitySubtitle(selected, isZh)}
            </h1>
          </div>
          <span
            className={
              isActionableCapability(selected)
                ? "rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-200"
                : "rounded-full bg-surface px-3 py-1 text-xs font-semibold text-text-secondary"
            }
          >
            {statusLabel(selected, isZh)}
          </span>
        </header>

        <div className="min-h-0 flex-1 overflow-auto px-8 py-6">
          <div className="ui-surface-enter mx-auto max-w-[68rem]">
            <div className="flex items-start gap-4">
              <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border border-border bg-surface">
                <GameIcon name={iconForCapability(selected.id)} className="h-5 w-5" />
              </div>
              <div className="min-w-0">
                <h2 className="text-[1.4rem] font-semibold tracking-tight text-text-primary">
                  {getCapabilitySubtitle(selected, isZh)}
                </h2>
                <p className="mt-2 max-w-3xl text-sm leading-6 text-text-secondary">
                  {getCapabilityDescription(selected, isZh)}
                </p>
              </div>
            </div>

            <div className="mt-6 grid gap-5 xl:grid-cols-[minmax(0,1.05fr)_minmax(0,0.95fr)]">
              <section>
                <div className="border-b border-border/90 pb-3">
                  <h3 className="text-sm font-semibold text-text-primary">
                    {isZh ? "当前入口" : "Current surface"}
                  </h3>
                  <p className="mt-1 text-sm leading-6 text-text-secondary">
                    {isZh
                      ? "这里展示当前能力会进入哪个工作台入口。"
                      : "This is where the selected capability opens inside the workbench."}
                  </p>
                </div>
                <div className="divide-y divide-border/90 border-b border-border/90">
                  <div className="grid grid-cols-[8.5rem_minmax(0,1fr)] gap-4 py-3 text-sm">
                    <span className="text-text-tertiary">{isZh ? "路由" : "Route"}</span>
                    <span className="font-medium text-text-primary">{selected.route}</span>
                  </div>
                  <div className="grid grid-cols-[8.5rem_minmax(0,1fr)] gap-4 py-3 text-sm">
                    <span className="text-text-tertiary">{isZh ? "能力类型" : "Capability kind"}</span>
                    <span className="font-medium text-text-primary">{kindLabel(selected, isZh)}</span>
                  </div>
                  <div className="grid grid-cols-[8.5rem_minmax(0,1fr)] gap-4 py-3 text-sm">
                    <span className="text-text-tertiary">{isZh ? "主操作" : "Primary action"}</span>
                    <span className="font-medium text-text-primary">{actionLabel(selected, isZh)}</span>
                  </div>
                </div>
              </section>

              <section>
                <div className="border-b border-border/90 pb-3">
                  <h3 className="text-sm font-semibold text-text-primary">
                    {isZh ? "使用预期" : "What to expect"}
                  </h3>
                  <p className="mt-1 text-sm leading-6 text-text-secondary">
                    {isZh
                      ? "保持 run flow 清晰可预测: 配置、运行、查看日志、读取摘要。"
                      : "Keep the run flow predictable: configure, run, inspect logs, read summary."}
                  </p>
                </div>
                <div className="divide-y divide-border/90 border-b border-border/90">
                  {(isZh
                    ? [
                        "一站式工作流会自动编排多个子模块，适合端到端分析。",
                        "子模块可独立运行，也可作为自定义 pipeline 的构建块。",
                        "当本地工具链阻塞执行时，随时打开环境诊断。",
                      ]
                    : [
                        "One-stop workflows orchestrate multiple submodules for end-to-end analysis.",
                        "Submodules can run independently or serve as building blocks for custom pipelines.",
                        "Open diagnostics whenever a local toolchain issue blocks execution.",
                      ]
                  ).map((detail) => (
                    <div key={detail} className="py-3 text-sm leading-6 text-text-secondary">
                      {detail}
                    </div>
                  ))}
                </div>
              </section>
            </div>
          </div>
        </div>

        <div className="border-t border-border/90 bg-surface-raised px-8 py-4">
          <div className="ui-soft-panel mx-auto flex max-w-[68rem] items-center gap-3 rounded-xl border px-4 py-3">
            <button
              type="button"
              className="ui-pressable rounded-lg border border-border bg-surface px-3 py-2 text-xs font-medium text-text-secondary transition hover:bg-surface-raised hover:text-text-primary"
              onClick={() => onNavigate("/settings")}
            >
              {isZh ? "设置" : "Settings"}
            </button>
            <div className="min-w-0 flex-1">
              <p className="truncate text-[13px] text-text-secondary">
                {getCapabilitySubtitle(selected, isZh)} - {statusLabel(selected, isZh)} -{" "}
                {selected.route === "/analysis/new"
                  ? isZh
                    ? "可进入工作台"
                    : "Ready for the workbench"
                  : isZh
                    ? "打开诊断"
                    : "Opens diagnostics"}
              </p>
            </div>
            <button
              type="button"
              className={
                isActionableCapability(selected)
                  ? "ui-pressable rounded-full bg-ice-500 px-4 py-2 text-sm font-semibold text-white transition hover:bg-ice-400"
                  : "rounded-full bg-surface px-4 py-2 text-sm font-semibold text-text-tertiary"
              }
              disabled={!isActionableCapability(selected)}
              onClick={() => handleOpenCapability(selected)}
            >
              {actionLabel(selected, isZh)}
            </button>
          </div>
        </div>
      </main>

      <aside className="min-h-0 overflow-y-auto overflow-x-hidden border-l border-border/90 bg-surface-raised px-4 py-5">
        <section>
          <h2 className="text-sm font-semibold text-text-primary">
            {isZh ? "能力分组" : "Capability groups"}
          </h2>
          <div className="mt-3 grid gap-2">
            {groups.map((group) => (
              <button
                key={group.key}
                type="button"
                className="ui-list-item flex items-center justify-between rounded-lg px-2 py-2 text-left text-[13px] text-text-secondary transition hover:bg-surface hover:text-text-primary"
                onClick={() => {
                  const first = group.items.find((item) => isActionableCapability(item)) ?? group.items[0];
                  if (first) {
                    setSelectedId(first.id);
                  }
                }}
              >
                <span className="truncate">{group.title}</span>
                <span className="shrink-0 rounded-full bg-surface px-2 py-0.5 text-[10px] font-medium text-text-tertiary">
                  {group.items.length}
                </span>
              </button>
            ))}
          </div>
        </section>

        <section className="mt-6 border-t border-border/90 pt-6">
          <h2 className="text-sm font-semibold text-text-primary">{isZh ? "已接入" : "Connected"}</h2>
          <div className="mt-3 grid gap-2">
            {capabilities
              ?.filter((entry) => entry.status === "connected")
              .map((entry) => (
                <button
                  key={entry.id}
                  type="button"
                  className="ui-list-item flex items-center gap-2.5 rounded-lg px-2 py-2 text-left text-[13px] text-text-secondary transition hover:bg-surface hover:text-text-primary"
                  onClick={() => setSelectedId(entry.id)}
                >
                  <GameIcon name={iconForCapability(entry.id)} className="h-4 w-4" />
                  <span className="truncate">{getCapabilitySubtitle(entry, isZh)}</span>
                </button>
              ))}
          </div>
        </section>

        <section className="mt-6 border-t border-border/90 pt-6">
          <h2 className="text-sm font-semibold text-text-primary">{isZh ? "动作" : "Action"}</h2>
          <div className="mt-3 grid gap-2 text-sm text-text-secondary">
            <div className="grid grid-cols-[5.2rem_minmax(0,1fr)] gap-3">
              <span className="text-text-tertiary">{isZh ? "路由" : "Route"}</span>
              <span className="truncate text-text-primary">{selected.route}</span>
            </div>
            <div className="grid grid-cols-[5.2rem_minmax(0,1fr)] gap-3">
              <span className="text-text-tertiary">{isZh ? "类型" : "Kind"}</span>
              <span className="truncate text-text-primary">{kindLabel(selected, isZh)}</span>
            </div>
            <div className="grid grid-cols-[5.2rem_minmax(0,1fr)] gap-3">
              <span className="text-text-tertiary">{isZh ? "状态" : "Status"}</span>
              <span className="truncate text-text-primary">{statusLabel(selected, isZh)}</span>
            </div>
          </div>
        </section>
      </aside>
    </div>
  );
}
