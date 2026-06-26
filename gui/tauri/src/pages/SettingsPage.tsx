import {
  AlertTriangle,
  Box,
  CheckCircle2,
  Cpu,
  FileJson,
  Globe,
  HardHat,
  HelpCircle,
  Languages,
  Package,
  Puzzle,
  RefreshCw,
  Settings2,
  Wrench,
  XCircle,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { CommandPreview } from "../components/CommandPreview";
import { Badge, Card, EmptyState, SectionHeader, StatCard } from "../components/ui";
import { useLanguage } from "../i18n/useLanguage";
import { getCheckToolItems, getEngineProbeInfo, type CheckReport, type CheckToolStatus } from "../models/check-report";
import type { AppRoute } from "../routes/routes";
import { getWorkflowSchema } from "../services/analysis";
import { checkEnvironment } from "../services/workbench";

interface SettingsPageProps {
  route: AppRoute;
  onNavigate: (path: string) => void;
}

function statusTone(status: CheckToolStatus | undefined): NonNullable<React.ComponentProps<typeof Badge>["tone"]> {
  if (status === "ok") {
    return "success";
  }
  if (status === "warning") {
    return "warning";
  }
  if (status === "missing" || status === "error") {
    return "error";
  }
  return "default";
}

function ToolStatusIcon({ status }: { status: CheckToolStatus }) {
  if (status === "ok") {
    return <CheckCircle2 className="h-4 w-4 text-emerald-600 dark:text-emerald-200" />;
  }
  if (status === "missing") {
    return <XCircle className="h-4 w-4 text-rose-600 dark:text-rose-200" />;
  }
  if (status === "warning") {
    return <AlertTriangle className="h-4 w-4 text-amber-600 dark:text-amber-200" />;
  }
  return <HelpCircle className="h-4 w-4 text-text-tertiary" />;
}

const TOOL_ICONS: Record<"blastn" | "makeblastdb" | "magick" | "jcvi_engine", typeof Wrench> = {
  blastn: Wrench,
  makeblastdb: Wrench,
  magick: Package,
  jcvi_engine: Cpu,
};

export default function SettingsPage({ route, onNavigate }: SettingsPageProps) {
  const { language, setLanguage } = useLanguage();
  const isZh = language === "zh-CN";
  const [report, setReport] = useState<CheckReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const loadSchema = useCallback(() => getWorkflowSchema(), []);

  const runCheck = useCallback(() => {
    setLoading(true);
    setError(null);
    void checkEnvironment()
      .then((result) => {
        setReport(result);
      })
      .catch((checkError: unknown) => {
        setError(checkError instanceof Error ? checkError.message : String(checkError));
      })
      .finally(() => {
        setLoading(false);
      });
  }, []);

  useEffect(() => {
    runCheck();
  }, [runCheck]);

  const toolItems = report ? getCheckToolItems(report) : [];
  const probe = report ? getEngineProbeInfo(report) : null;

  return (
    <section className="ui-page-enter grid h-screen w-full gap-0 overflow-hidden border border-border bg-surface-raised xl:grid-cols-[18rem_minmax(0,1fr)]">
      <aside className="ui-shell-sidebar flex min-h-0 flex-col border-r px-4 py-4">
        <div className="border-b border-border/90 px-2 pb-4">
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-text-tertiary">{route.label}</p>
          <h1 className="mt-2 text-lg font-semibold text-text-primary">{isZh ? "环境与参考" : "Environment and references"}</h1>
          <p className="mt-2 text-sm leading-6 text-text-secondary">{route.description}</p>
        </div>

        <nav className="mt-4 grid gap-2 px-2">
          <button
            type="button"
            className="ui-pressable inline-flex items-center justify-between rounded-xl border border-border bg-surface px-3 py-2 text-sm font-medium text-text-secondary transition hover:bg-surface-raised hover:text-text-primary"
            onClick={() => onNavigate("/analysis/new")}
          >
            <span className="flex items-center gap-2">
              <Settings2 className="h-4 w-4" />
              {isZh ? "打开工作台" : "Open workbench"}
            </span>
            <span className="text-text-tertiary">/analysis/new</span>
          </button>
          <button
            type="button"
            className="ui-pressable inline-flex items-center justify-between rounded-xl px-3 py-2 text-sm font-medium text-text-secondary transition hover:bg-surface-raised hover:text-text-primary"
            onClick={() => onNavigate("/")}
          >
            <span className="flex items-center gap-2">
              <Globe className="h-4 w-4" />
              {isZh ? "返回首页" : "Back to home"}
            </span>
            <span className="text-text-tertiary">/</span>
          </button>
        </nav>

        <div className="mt-auto border-t border-border/90 px-2 pt-4">
          <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-text-tertiary">{isZh ? "概览" : "Overview"}</p>
          <div className="mt-3 grid gap-3">
            <StatCard
              label={isZh ? "状态" : "State"}
              value={loading ? (isZh ? "检查中" : "checking") : report?.status ?? (isZh ? "未知" : "unknown")}
              tone={statusTone(loading ? "unknown" : report?.status)}
              icon={loading ? RefreshCw : report?.status === "ok" ? CheckCircle2 : AlertTriangle}
            />
            <StatCard label={isZh ? "工具" : "Tools"} value={toolItems.length} tone="info" icon={Wrench} />
            <StatCard label={isZh ? "引擎" : "Engine"} value={probe?.engineVersion || (isZh ? "未返回" : "Not returned")} tone="default" icon={Cpu} />
          </div>
        </div>
      </aside>

      <div className="ui-surface-enter min-h-0 overflow-auto bg-surface-raised px-6 py-6">
        <div className="mx-auto max-w-5xl">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-text-tertiary">{isZh ? "诊断" : "Diagnostics"}</p>
              <h2 className="mt-1 text-2xl font-semibold tracking-tight text-text-primary">{isZh ? "环境、工具链与契约" : "Environment, toolchain, and contract"}</h2>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-text-secondary">
                {isZh
                  ? "查看当前 GenomeLens 与 JCVI 工具链状态、引擎 probe 信息，以及平台 schema 参考。"
                  : "Inspect the current GenomeLens and JCVI toolchain, engine probe metadata, and platform schema reference."}
              </p>
            </div>
            <div className="flex shrink-0 items-center gap-2">
              <Badge tone={statusTone(loading ? "unknown" : report?.status)} dot pulse={loading}>
                {loading ? (isZh ? "检查中" : "checking") : report?.status ?? (isZh ? "未知" : "unknown")}
              </Badge>
              <button
                type="button"
                className="ui-icon-button"
                title={isZh ? "重新检查" : "Recheck"}
                disabled={loading}
                onClick={runCheck}
              >
                <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
              </button>
            </div>
          </div>

          {error ? (
            <div className="mt-5 flex items-start gap-3 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700 dark:border-rose-900/40 dark:bg-rose-950/20 dark:text-rose-200"
            >
              <XCircle className="mt-0.5 h-4 w-4 shrink-0" />
              {error}
            </div>
          ) : null}

          <Card className="mt-6">
            <SectionHeader
              title={isZh ? "语言" : "Language"}
              subtitle={isZh ? "默认语言为中文，可随时切换界面显示语言。" : "Chinese is the default language. You can switch the interface language here."}
              action={
                <span className="inline-flex items-center gap-1.5 text-sm text-text-secondary">
                  <Languages className="h-4 w-4" />
                  {isZh ? "语言" : "Language"}
                </span>
              }
            />
            <div className="mt-4 inline-flex items-center gap-1 rounded-xl bg-surface p-1">
              <button
                type="button"
                className={
                  language === "zh-CN"
                    ? "ui-pressable rounded-lg border border-border bg-surface-raised px-3 py-1.5 text-sm font-semibold text-text-primary shadow-card"
                    : "ui-pressable rounded-lg px-3 py-1.5 text-sm font-medium text-text-secondary hover:bg-surface-raised hover:text-text-primary"
                }
                onClick={() => setLanguage("zh-CN")}
              >
                中文
              </button>
              <button
                type="button"
                className={
                  language === "en"
                    ? "ui-pressable rounded-lg border border-border bg-surface-raised px-3 py-1.5 text-sm font-semibold text-text-primary shadow-card"
                    : "ui-pressable rounded-lg px-3 py-1.5 text-sm font-medium text-text-secondary hover:bg-surface-raised hover:text-text-primary"
                }
                onClick={() => setLanguage("en")}
              >
                English
              </button>
            </div>
          </Card>

          <Card className="mt-6">
            <SectionHeader
              title={isZh ? "工具链状态" : "Toolchain status"}
              subtitle={isZh ? "每一行都对应当前 `check_environment()` 的返回结果。" : "Each row reflects the current `check_environment()` result."}
              action={
                <Badge tone={statusTone(report?.status)}>
                  <CheckCircle2 className="mr-1 h-3 w-3" />
                  {toolItems.length}
                </Badge>
              }
            />

            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              {toolItems.map((item) => {
                const Icon = TOOL_ICONS[item.id] ?? Wrench;
                return (
                  <div
                    key={item.id}
                    className="ui-row-item flex items-start gap-3 rounded-xl border border-border bg-surface p-4"
                  >
                    <span
                      className={[
                        "flex h-10 w-10 shrink-0 items-center justify-center rounded-xl",
                        item.status === "ok"
                          ? "bg-emerald-50 text-emerald-600 dark:bg-emerald-950/30 dark:text-emerald-200"
                          : item.status === "missing" || item.status === "error"
                            ? "bg-rose-50 text-rose-600 dark:bg-rose-950/30 dark:text-rose-200"
                            : "bg-amber-50 text-amber-600 dark:bg-amber-950/30 dark:text-amber-200",
                      ].join(" ")}
                    >
                      <Icon className="h-5 w-5" />
                    </span>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center justify-between gap-3">
                        <p className="text-sm font-semibold text-text-primary">{item.label}</p>
                        <Badge tone={statusTone(item.status)}>
                          <ToolStatusIcon status={item.status} />
                          {item.status}
                        </Badge>
                      </div>
                      <p className="mt-1 break-all font-mono text-[11px] text-text-tertiary">{item.path || (isZh ? "路径不可用" : "Path unavailable")}</p>
                      <p className="mt-2 text-sm leading-6 text-text-secondary">{item.message || (isZh ? "暂无更多信息。" : "No additional details.")}</p>
                    </div>
                  </div>
                );
              })}
            </div>
          </Card>

          <Card className="mt-6">
            <SectionHeader
              title={isZh ? "引擎探测信息" : "Engine probe"}
              subtitle={isZh ? "`check_environment()` 在 JCVI 引擎项中附带的 probe 元数据。" : "Probe metadata attached to the JCVI engine item from `check_environment()`."}
              action={
                <span className="inline-flex items-center gap-1.5 text-sm text-text-secondary">
                  <Cpu className="h-4 w-4" />
                  {isZh ? "引擎" : "Engine"}
                </span>
              }
            />

            <div className="mt-4">
              {probe ? (
                <div className="grid gap-4">
                  <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                    <StatCard label={isZh ? "引擎名称" : "Engine name"} value={probe.engineName} tone="default" icon={Cpu} />
                    <StatCard label={isZh ? "引擎版本" : "Engine version"} value={probe.engineVersion || (isZh ? "未返回" : "Not returned")} tone="info" icon={HardHat} />
                    <StatCard label={isZh ? "JCVI 上游版本" : "JCVI upstream"} value={probe.jcviUpstreamVersion || (isZh ? "未返回" : "Not returned")} tone="default" icon={Package} />
                    <StatCard label={isZh ? "Patchset" : "Patchset"} value={probe.patchset || (isZh ? "未返回" : "Not returned")} tone="default" icon={Puzzle} />
                    <StatCard label={isZh ? "Python" : "Python"} value={probe.python || (isZh ? "未返回" : "Not returned")} tone="default" icon={Globe} />
                    <StatCard label={isZh ? "平台" : "Platform"} value={probe.platform || (isZh ? "未返回" : "Not returned")} tone="default" icon={Globe} />
                    <StatCard label={isZh ? "发行版" : "Distribution"} value={probe.distribution || (isZh ? "未返回" : "Not returned")} tone="default" icon={Box} />
                  </div>

                  <div className="grid gap-4 lg:grid-cols-2">
                    <div className="rounded-xl border border-border bg-surface p-4">
                      <p className="text-xs font-semibold uppercase tracking-[0.14em] text-text-tertiary">{isZh ? "支持的能力" : "Capabilities"}</p>
                      <div className="mt-2 flex flex-wrap gap-2">
                        {probe.capabilities.length > 0 ? (
                          probe.capabilities.map((capability) => (
                            <span
                              key={capability}
                              className="rounded-full bg-ice-50 px-2.5 py-1 text-[11px] font-semibold uppercase text-ice-700 dark:bg-ice-900/30 dark:text-ice-200"
                            >
                              {capability}
                            </span>
                          ))
                        ) : (
                          <span className="text-sm text-text-secondary">{isZh ? "无" : "None"}</span>
                        )}
                      </div>
                    </div>

                    <div className="rounded-xl border border-border bg-surface p-4">
                      <p className="text-xs font-semibold uppercase tracking-[0.14em] text-text-tertiary">{isZh ? "可分发工作流" : "Dispatchable workflows"}</p>
                      <div className="mt-2 flex flex-wrap gap-2">
                        {probe.dispatchableWorkflows.length > 0 ? (
                          probe.dispatchableWorkflows.map((workflow) => (
                            <span
                              key={workflow}
                              className="rounded-full bg-surface px-2.5 py-1 text-[11px] font-semibold uppercase text-text-secondary"
                            >
                              {workflow}
                            </span>
                          ))
                        ) : (
                          <span className="text-sm text-text-secondary">{isZh ? "无" : "None"}</span>
                        )}
                      </div>
                    </div>

                    <div className="rounded-xl border border-border bg-surface p-4 lg:col-span-2">
                      <p className="text-xs font-semibold uppercase tracking-[0.14em] text-text-tertiary">{isZh ? "捆绑的 JCVI 模块" : "Bundled JCVI modules"}</p>
                      <div className="mt-2 flex flex-wrap gap-2">
                        {probe.bundledJcviModules.length > 0 ? (
                          probe.bundledJcviModules.map((moduleName) => (
                            <span
                              key={moduleName}
                              className="rounded-full bg-surface px-2.5 py-1 text-[11px] font-semibold uppercase text-text-secondary"
                            >
                              {moduleName}
                            </span>
                          ))
                        ) : (
                          <span className="text-sm text-text-secondary">{isZh ? "无" : "None"}</span>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              ) : (
                <EmptyState
                  icon={Cpu}
                  title={isZh ? "当前检查报告未包含引擎 probe 信息。" : "The current check report does not include engine probe information."}
                  description={isZh ? "检查完成后会在此处显示引擎版本与能力列表。" : "Engine version and capability list will appear here after the check completes."}
                />
              )}
            </div>
          </Card>

          <div className="mt-6">
            <SectionHeader
              title={isZh ? "契约参考" : "Contract reference"}
              subtitle={isZh ? "保留原始平台 schema，便于调试与契约核对。" : "Keep the raw platform schema visible for debugging and contract checks."}
              action={
                <span className="inline-flex items-center gap-1.5 text-sm text-text-secondary">
                  <FileJson className="h-4 w-4" />
                  JSON
                </span>
              }
            />
            <div className="mt-4">
              <CommandPreview
                title="WorkflowRequest schema"
                command="get_workflow_schema()"
                description={isZh ? "当前基线返回的平台原生 schema。" : "Platform-native schema returned from the current baseline."}
                load={loadSchema}
              />
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
