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
    return "bg-emerald-50 text-emerald-700";
  }
  if (status === "warning") {
    return "bg-amber-50 text-amber-700";
  }
  return "bg-slate-100 text-slate-600";
}

function toolStatusClass(status: string) {
  if (status === "ok") {
    return "bg-emerald-50 text-emerald-700";
  }
  if (status === "missing") {
    return "bg-rose-50 text-rose-700";
  }
  return "bg-amber-50 text-amber-700";
}

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
    <section className="ui-page-enter grid w-full gap-0 overflow-hidden border border-slate-200 bg-white xl:grid-cols-[16rem_minmax(0,1fr)]">
      <aside className="border-r border-slate-200/80 bg-[#f6f8f9]">
        <div className="border-b border-slate-200/80 px-5 py-5">
          <p className="text-xs font-medium uppercase tracking-[0.18em] text-slate-400">{route.label}</p>
          <h1 className="mt-2 text-lg font-semibold text-slate-900">{isZh ? "环境与参考" : "Environment and references"}</h1>
          <p className="mt-2 text-sm leading-6 text-slate-500">{route.description}</p>
        </div>

        <nav className="px-3 py-3">
          <button
            type="button"
            className="ui-list-item mb-1 flex w-full items-center justify-between rounded-lg bg-white px-3 py-2 text-left text-sm font-medium text-slate-800 shadow-sm transition hover:bg-slate-50"
            onClick={() => onNavigate("/analysis/new")}
          >
            <span>{isZh ? "打开工作台" : "Open workbench"}</span>
            <span className="text-slate-400">/analysis/new</span>
          </button>
          <button
            type="button"
            className="ui-list-item flex w-full items-center justify-between rounded-lg px-3 py-2 text-left text-sm text-slate-600 transition hover:bg-white hover:text-slate-900"
            onClick={() => onNavigate("/")}
          >
            <span>{isZh ? "返回首页" : "Back to home"}</span>
            <span className="text-slate-400">/</span>
          </button>
        </nav>

        <div className="border-t border-slate-200/80 px-5 py-4">
          <div className="text-[11px] font-medium uppercase tracking-[0.18em] text-slate-400">{isZh ? "概览" : "Overview"}</div>
          <div className="mt-3 divide-y divide-slate-200/80 border-y border-slate-200/80">
            <div className="flex items-center justify-between py-3 text-sm">
              <span className="text-slate-400">{isZh ? "状态" : "State"}</span>
              <span className={`rounded-full px-3 py-1 text-[11px] font-semibold uppercase ${statusClass(report?.status)}`}>
                {loading ? (isZh ? "检查中" : "checking") : report?.status ?? (isZh ? "未知" : "unknown")}
              </span>
            </div>
            <div className="flex items-center justify-between py-3 text-sm">
              <span className="text-slate-400">{isZh ? "工具" : "Tools"}</span>
              <span className="font-medium text-slate-900">{toolItems.length}</span>
            </div>
          </div>
        </div>
      </aside>

      <div className="ui-surface-enter min-w-0 bg-white">
        <div className="border-b border-slate-200/80 px-6 py-5">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-xs font-medium uppercase tracking-[0.18em] text-slate-400">{isZh ? "诊断" : "Diagnostics"}</p>
              <h2 className="mt-1 text-lg font-semibold text-slate-900">{isZh ? "本地工具链" : "Local toolchain"}</h2>
              <p className="mt-2 text-sm leading-6 text-slate-500">
                {isZh ? "用于查看当前 GenomeLens 与 JCVI 工具链状态的轻量诊断界面。" : "Thin diagnostics surface for the current GenomeLens and JCVI toolchain."}
              </p>
            </div>
            <span className={`rounded-full px-3 py-1 text-[11px] font-semibold uppercase ${statusClass(report?.status)}`}>
              {loading ? (isZh ? "检查中" : "checking") : report?.status ?? (isZh ? "unknown" : "unknown")}
            </span>
          </div>
        </div>

        {error ? <div className="border-b border-slate-200/80 bg-rose-50 px-6 py-4 text-sm text-rose-700">{error}</div> : null}

        <section>
          <div className="px-6 py-4">
            <h3 className="text-sm font-semibold text-slate-900">{isZh ? "语言" : "Language"}</h3>
            <p className="mt-1 text-sm text-slate-500">
              {isZh ? "默认语言为中文，可随时切换界面显示语言。" : "Chinese is the default language. You can switch the interface language here."}
            </p>
          </div>
          <div className="border-y border-slate-200/80 px-6 py-4">
            <div className="inline-flex items-center gap-1 rounded-lg bg-slate-100 p-1">
              <button
                type="button"
                className={language === "zh-CN" ? "ui-pressable rounded-md bg-white px-3 py-1.5 text-sm font-semibold text-slate-900 shadow-sm" : "ui-pressable rounded-md px-3 py-1.5 text-sm font-medium text-slate-500 hover:text-slate-900"}
                onClick={() => setLanguage("zh-CN")}
              >
                中文
              </button>
              <button
                type="button"
                className={language === "en" ? "ui-pressable rounded-md bg-white px-3 py-1.5 text-sm font-semibold text-slate-900 shadow-sm" : "ui-pressable rounded-md px-3 py-1.5 text-sm font-medium text-slate-500 hover:text-slate-900"}
                onClick={() => setLanguage("en")}
              >
                English
              </button>
            </div>
          </div>
        </section>

        <section>
          <div className="px-6 py-4">
            <h3 className="text-sm font-semibold text-slate-900">{isZh ? "工具链状态" : "Toolchain status"}</h3>
            <p className="mt-1 text-sm text-slate-500">{isZh ? "每一行都对应当前 `check_environment()` 的返回结果。" : "Each row reflects the current `check_environment()` result."}</p>
          </div>

          <div className="divide-y divide-slate-200/80 border-y border-slate-200/80">
            {toolItems.map((item) => (
              <article key={item.id} className="px-6 py-4">
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0">
                    <p className="text-sm font-semibold text-slate-900">{item.label}</p>
                    <p className="mt-1 break-all font-mono text-xs text-slate-400">{item.path || (isZh ? "路径不可用" : "Path unavailable")}</p>
                  </div>
                  <span className={`rounded-full px-3 py-1 text-[11px] font-semibold uppercase ${toolStatusClass(item.status)}`}>
                    {item.status}
                  </span>
                </div>
                <p className="mt-3 text-sm leading-6 text-slate-500">{item.message || (isZh ? "暂无更多信息。" : "No additional details.")}</p>
              </article>
            ))}
          </div>
        </section>

        <section>
          <div className="px-6 py-4">
            <h3 className="text-sm font-semibold text-slate-900">{isZh ? "契约参考" : "Contract reference"}</h3>
            <p className="mt-1 text-sm text-slate-500">{isZh ? "保留原始平台 schema，便于调试与契约核对。" : "Keep the raw platform schema visible for debugging and contract checks."}</p>
          </div>

          <CommandPreview
            title={isZh ? "AnalysisRequest schema" : "AnalysisRequest schema"}
            command="get_analysis_schema()"
            description={isZh ? "当前基线返回的平台原生 schema。" : "Platform-native schema returned from the current baseline."}
            load={loadSchema}
          />
        </section>
      </div>
    </section>
  );
}
