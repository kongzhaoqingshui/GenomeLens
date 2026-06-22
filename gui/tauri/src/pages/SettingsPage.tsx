import { useCallback, useEffect, useState } from "react";

import { CommandPreview } from "../components/CommandPreview";
import { useLanguage } from "../i18n/useLanguage";
import { getCheckToolItems, type CheckReport } from "../models/check-report";
import type { AppRoute } from "../routes/routes";
import { getAnalysisSchema } from "../services/analysis";
import { checkEnvironment } from "../services/workbench";

interface SettingsPageProps {
  route: AppRoute;
  onNavigate: (path: string) => void;
}

function statusClass(status: CheckReport["status"] | undefined) {
  if (status === "ok") {
    return "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-200";
  }
  if (status === "warning") {
    return "bg-amber-50 text-amber-700 dark:bg-amber-950/30 dark:text-amber-200";
  }
  return "bg-surface text-text-secondary";
}

function toolStatusClass(status: string) {
  if (status === "ok") {
    return "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-200";
  }
  if (status === "missing") {
    return "bg-rose-50 text-rose-700 dark:bg-rose-950/30 dark:text-rose-200";
  }
  return "bg-amber-50 text-amber-700 dark:bg-amber-950/30 dark:text-amber-200";
}

const SIDE_BUTTON_BASE =
  "ui-list-item flex w-full items-center justify-between rounded-lg px-3 py-2 text-left text-sm transition";

export default function SettingsPage({ route, onNavigate }: SettingsPageProps) {
  const { language, setLanguage } = useLanguage();
  const isZh = language === "zh-CN";
  const [report, setReport] = useState<CheckReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const loadSchema = useCallback(() => getAnalysisSchema(), []);

  useEffect(() => {
    let active = true;

    setLoading(true);
    setError(null);
    void checkEnvironment()
      .then((result) => {
        if (active) {
          setReport(result);
        }
      })
      .catch((checkError: unknown) => {
        if (active) {
          setError(checkError instanceof Error ? checkError.message : String(checkError));
        }
      })
      .finally(() => {
        if (active) {
          setLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, []);

  const toolItems = report ? getCheckToolItems(report) : [];

  return (
    <section className="ui-page-enter grid w-full gap-0 overflow-hidden border border-border bg-surface-raised xl:grid-cols-[16rem_minmax(0,1fr)]">
      <aside className="ui-shell-sidebar border-r">
        <div className="border-b border-border/90 px-5 py-5">
          <p className="text-xs font-medium uppercase tracking-[0.16em] text-text-tertiary">{route.label}</p>
          <h1 className="mt-2 text-lg font-semibold text-text-primary">{isZh ? "环境与参考" : "Environment and references"}</h1>
          <p className="mt-2 text-sm leading-6 text-text-secondary">{route.description}</p>
        </div>

        <nav className="px-3 py-3">
          <button
            type="button"
            className={`${SIDE_BUTTON_BASE} mb-1 border border-border bg-surface-raised font-medium text-text-primary shadow-card hover:bg-surface`}
            onClick={() => onNavigate("/analysis/new")}
          >
            <span>{isZh ? "打开工作台" : "Open workbench"}</span>
            <span className="text-text-tertiary">/analysis/new</span>
          </button>
          <button
            type="button"
            className={`${SIDE_BUTTON_BASE} text-text-secondary hover:bg-surface-raised hover:text-text-primary`}
            onClick={() => onNavigate("/")}
          >
            <span>{isZh ? "返回首页" : "Back to home"}</span>
            <span className="text-text-tertiary">/</span>
          </button>
        </nav>

        <div className="border-t border-border/90 px-5 py-4">
          <div className="text-[11px] font-medium uppercase tracking-[0.16em] text-text-tertiary">{isZh ? "概览" : "Overview"}</div>
          <div className="mt-3 divide-y divide-border/90 border-y border-border/90">
            <div className="flex items-center justify-between py-3 text-sm">
              <span className="text-text-tertiary">{isZh ? "状态" : "State"}</span>
              <span className={`rounded-full px-3 py-1 text-[11px] font-semibold uppercase ${statusClass(report?.status)}`}>
                {loading ? (isZh ? "检查中" : "checking") : report?.status ?? (isZh ? "未知" : "unknown")}
              </span>
            </div>
            <div className="flex items-center justify-between py-3 text-sm">
              <span className="text-text-tertiary">{isZh ? "工具" : "Tools"}</span>
              <span className="font-medium text-text-primary">{toolItems.length}</span>
            </div>
          </div>
        </div>
      </aside>

      <div className="ui-surface-enter min-w-0 bg-surface-raised">
        <div className="border-b border-border/90 px-6 py-5">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-xs font-medium uppercase tracking-[0.16em] text-text-tertiary">{isZh ? "诊断" : "Diagnostics"}</p>
              <h2 className="mt-1 text-lg font-semibold text-text-primary">{isZh ? "本地工具链" : "Local toolchain"}</h2>
              <p className="mt-2 text-sm leading-6 text-text-secondary">
                {isZh
                  ? "用于查看当前 GenomeLens 与 JCVI 工具链状态的轻量诊断界面。"
                  : "Thin diagnostics surface for the current GenomeLens and JCVI toolchain."}
              </p>
            </div>
            <span className={`rounded-full px-3 py-1 text-[11px] font-semibold uppercase ${statusClass(report?.status)}`}>
              {loading ? (isZh ? "检查中" : "checking") : report?.status ?? "unknown"}
            </span>
          </div>
        </div>

        {error ? <div className="border-b border-border/90 bg-rose-50 px-6 py-4 text-sm text-rose-700 dark:bg-rose-950/30 dark:text-rose-200">{error}</div> : null}

        <section>
          <div className="px-6 py-4">
            <h3 className="text-sm font-semibold text-text-primary">{isZh ? "语言" : "Language"}</h3>
            <p className="mt-1 text-sm text-text-secondary">
              {isZh ? "默认语言为中文，可随时切换界面显示语言。" : "Chinese is the default language. You can switch the interface language here."}
            </p>
          </div>
          <div className="border-y border-border/90 px-6 py-4">
            <div className="inline-flex items-center gap-1 rounded-lg bg-surface p-1">
              <button
                type="button"
                className={
                  language === "zh-CN"
                    ? "ui-pressable rounded-md border border-border bg-surface-raised px-3 py-1.5 text-sm font-semibold text-text-primary shadow-card"
                    : "ui-pressable rounded-md px-3 py-1.5 text-sm font-medium text-text-secondary hover:bg-surface-raised hover:text-text-primary"
                }
                onClick={() => setLanguage("zh-CN")}
              >
                中文
              </button>
              <button
                type="button"
                className={
                  language === "en"
                    ? "ui-pressable rounded-md border border-border bg-surface-raised px-3 py-1.5 text-sm font-semibold text-text-primary shadow-card"
                    : "ui-pressable rounded-md px-3 py-1.5 text-sm font-medium text-text-secondary hover:bg-surface-raised hover:text-text-primary"
                }
                onClick={() => setLanguage("en")}
              >
                English
              </button>
            </div>
          </div>
        </section>

        <section>
          <div className="px-6 py-4">
            <h3 className="text-sm font-semibold text-text-primary">{isZh ? "工具链状态" : "Toolchain status"}</h3>
            <p className="mt-1 text-sm text-text-secondary">
              {isZh ? "每一行都对应当前 `check_environment()` 的返回结果。" : "Each row reflects the current `check_environment()` result."}
            </p>
          </div>

          <div className="divide-y divide-border/90 border-y border-border/90">
            {toolItems.map((item) => (
              <article key={item.id} className="ui-row-item px-6 py-4">
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0">
                    <p className="text-sm font-semibold text-text-primary">{item.label}</p>
                    <p className="mt-1 break-all font-mono text-xs text-text-tertiary">{item.path || (isZh ? "路径不可用" : "Path unavailable")}</p>
                  </div>
                  <span className={`rounded-full px-3 py-1 text-[11px] font-semibold uppercase ${toolStatusClass(item.status)}`}>
                    {item.status}
                  </span>
                </div>
                <p className="mt-3 text-sm leading-6 text-text-secondary">{item.message || (isZh ? "暂无更多信息。" : "No additional details.")}</p>
              </article>
            ))}
          </div>
        </section>

        <section>
          <div className="px-6 py-4">
            <h3 className="text-sm font-semibold text-text-primary">{isZh ? "契约参考" : "Contract reference"}</h3>
            <p className="mt-1 text-sm text-text-secondary">
              {isZh ? "保留原始平台 schema，便于调试与契约核对。" : "Keep the raw platform schema visible for debugging and contract checks."}
            </p>
          </div>

          <CommandPreview
            title="AnalysisRequest schema"
            command="get_analysis_schema()"
            description={isZh ? "当前基线返回的平台原生 schema。" : "Platform-native schema returned from the current baseline."}
            load={loadSchema}
          />
        </section>
      </div>
    </section>
  );
}
