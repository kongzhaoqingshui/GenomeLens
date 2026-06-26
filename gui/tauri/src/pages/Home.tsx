import {
  Cog,
  FlaskConical,
  LayoutGrid,
  RefreshCw,
  Rocket,
  Sparkles,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { CapabilityList } from "../components/CapabilityList";
import { CollapsibleSection } from "../components/CollapsibleSection";
import { GameIcon, type GameIconName } from "../components/GameIcon";
import { Badge, Card, EmptyState } from "../components/ui";
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

export default function Home({ onNavigate }: HomeProps) {
  const { language } = useLanguage();
  const isZh = language === "zh-CN";
  const [capabilities, setCapabilities] = useState<CapabilityEntry[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [filter, setFilter] = useState("");

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

  const filteredCapabilities = useMemo(() => {
    if (!capabilities) {
      return [];
    }
    const query = filter.trim().toLowerCase();
    if (!query) {
      return capabilities;
    }
    return capabilities.filter(
      (entry) =>
        entry.id.toLowerCase().includes(query) ||
        getCapabilitySubtitle(entry, isZh).toLowerCase().includes(query) ||
        getCapabilityDescription(entry, isZh).toLowerCase().includes(query),
    );
  }, [capabilities, filter, isZh]);

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

    const targetCapabilityId = entry.id === "synteny" ? "pairwise-synteny" : entry.id;
    onNavigate(`/analysis/new?capability=${encodeURIComponent(targetCapabilityId)}`);
  }

  if (loading) {
    return (
      <div className="ui-page-enter ui-app-frame grid h-screen w-full content-center justify-center gap-4 text-center">
        <div className="ui-floating ui-breathing mx-auto flex h-20 w-20 items-center justify-center rounded-[1.25rem] bg-surface">
          <JcviMeowIcon className="h-12 w-12" />
        </div>
        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-text-tertiary">
          JCVI meow · {isZh ? "首页" : "Home"}
        </p>
        <p className="text-sm text-text-secondary">{isZh ? "正在加载能力列表..." : "Loading capabilities..."}</p>
      </div>
    );
  }

  if (!selected) {
    return (
      <div className="ui-page-enter ui-app-frame grid h-screen w-full content-center justify-center gap-4 p-6 text-center">
        <EmptyState
          icon={FlaskConical}
          title={isZh ? "暂无可用能力" : "No capabilities available"}
          description={error ?? undefined}
          action={
            <button
              type="button"
              className="ui-icon-button border-ice-500 bg-ice-500 text-white hover:bg-ice-400 hover:border-ice-400"
              onClick={handleRetry}
            >
              {isZh ? "重试" : "Retry"}
            </button>
          }
        />
      </div>
    );
  }

  const tips = isZh
    ? [
        "输出目录建议选择空目录，避免旧文件被覆盖。",
        "运行前先打开环境诊断确认工具链完整。",
        "子模块适合作为自定义 pipeline 的构建块。",
      ]
    : [
        "Pick an empty output directory to avoid overwriting old files.",
        "Open Diagnostics before running to verify the toolchain.",
        "Submodules work well as building blocks for custom pipelines.",
      ];

  return (
    <div className="ui-page-enter ui-app-frame flex h-screen w-full flex-col overflow-hidden">
      <header className="flex h-16 shrink-0 items-center justify-between border-b border-border/90 px-6">
        <div className="flex items-center gap-3">
          <JcviMeowIcon className="h-8 w-8" />
          <h1 className="text-sm font-semibold text-text-primary">JCVI meow</h1>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            className="ui-icon-button"
            onClick={handleRetry}
            title={isZh ? "重新加载能力列表" : "Reload capability list"}
          >
            <RefreshCw className="h-4 w-4" />
          </button>
          <button
            type="button"
            className="ui-icon-button"
            onClick={() => onNavigate("/settings")}
            title={isZh ? "设置" : "Settings"}
          >
            <Cog className="h-4 w-4" />
          </button>
        </div>
      </header>

      <main className="grid min-h-0 flex-1 grid-cols-[20rem_minmax(0,1fr)_20rem] overflow-hidden">
        {/* Left sidebar */}
        <aside className="flex flex-col border-r border-border/90 bg-surface">
          <div className="flex items-center gap-2 border-b border-border/90 px-4 py-3">
            <LayoutGrid className="h-4 w-4 text-text-tertiary" />
            <input
              type="text"
              className="min-w-0 flex-1 bg-transparent text-sm text-text-primary outline-none placeholder:text-text-tertiary"
              placeholder={isZh ? "搜索能力..." : "Search capabilities..."}
              value={filter}
              onChange={(event) => setFilter(event.target.value)}
            />
          </div>
          <div className="min-h-0 flex-1 overflow-y-auto">
            <CapabilityList
              capabilities={filteredCapabilities}
              selectedId={selectedId}
              isZh={isZh}
              onSelect={setSelectedId}
              onOpen={handleOpenCapability}
            />
          </div>
        </aside>

        {/* Center */}
        <section className="min-h-0 overflow-y-auto px-6 py-8">
          <div className="mx-auto flex max-w-2xl flex-col gap-5">
            <div className="flex items-center justify-end gap-3">
              <Badge tone={statusTone(selected)} dot pulse={selected.status === "connected"}>
                {statusLabel(selected, isZh)}
              </Badge>
            </div>

            <Card className="relative overflow-hidden">
              <div className="absolute -right-10 -top-10 h-40 w-40 rounded-full bg-ice-400/10 blur-3xl" />
              <div className="relative flex flex-col gap-5 p-6">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex items-center gap-4">
                    <span className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl border border-border bg-surface shadow-card">
                      <GameIcon name={iconForCapability(selected.id)} className="h-7 w-7" />
                    </span>
                    <div className="min-w-0">
                      <p className="text-xs font-semibold uppercase tracking-[0.14em] text-text-tertiary">
                        {kindLabel(selected, isZh)}
                      </p>
                      <h1 className="mt-0.5 text-2xl font-semibold tracking-tight text-text-primary">
                        {getCapabilitySubtitle(selected, isZh)}
                      </h1>
                    </div>
                  </div>
                </div>

                <p className="max-w-2xl text-sm leading-7 text-text-secondary">
                  {getCapabilityDescription(selected, isZh)}
                </p>

                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    className="ui-pressable inline-flex items-center gap-2 rounded-full bg-ice-500 px-5 py-2.5 text-sm font-semibold text-white shadow-glow transition hover:bg-ice-400"
                    onClick={() => handleOpenCapability(selected)}
                  >
                    <Rocket className="h-4 w-4" />
                    {actionLabel(selected, isZh)}
                  </button>
                  {selected.route !== "/settings" ? (
                    <button
                      type="button"
                      className="ui-pressable inline-flex items-center gap-2 rounded-full border border-border bg-surface px-4 py-2.5 text-sm font-medium text-text-secondary transition hover:bg-surface-raised hover:text-text-primary"
                      onClick={() => onNavigate("/settings")}
                    >
                      <Cog className="h-4 w-4" />
                      {isZh ? "环境诊断" : "Diagnostics"}
                    </button>
                  ) : null}
                </div>
              </div>
            </Card>

            <CollapsibleSection
              title={isZh ? "提示" : "Hints"}
              subtitle={isZh ? "让分析更顺畅的小建议。" : "Small tips to keep analysis smooth."}
              defaultOpen={false}
            >
              <ul className="grid gap-3 sm:grid-cols-2">
                {tips.map((tip) => (
                  <li key={tip} className="flex items-start gap-2">
                    <Sparkles className="mt-0.5 h-4 w-4 shrink-0 text-amber-500" />
                    <span className="text-sm leading-6 text-text-secondary">{tip}</span>
                  </li>
                ))}
              </ul>
            </CollapsibleSection>
          </div>
        </section>

        {/* Right sidebar */}
        <aside className="flex flex-col border-l border-border/90 bg-surface">
          <div className="flex flex-1 items-center justify-center p-6">
            <EmptyState
              icon={LayoutGrid}
              title={isZh ? "扩展面板" : "Extension panel"}
              description={isZh ? "右侧区域预留，后续可放置快捷操作、最近运行或数据预览。" : "Reserved for future quick actions, recent runs, or data previews."}
            />
          </div>
        </aside>
      </main>
    </div>
  );
}
