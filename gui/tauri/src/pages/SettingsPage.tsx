import { useCallback, useEffect, useState } from "react";

import { CommandPreview } from "../components/CommandPreview";
import { getCheckToolItems, type CheckReport } from "../models/check-report";
import type { AppRoute } from "../routes/routes";
import { getAnalysisSchema } from "../services/analysis";
import { checkEnvironment } from "../services/workbench";

interface SettingsPageProps {
  route: AppRoute;
  onNavigate: (path: string) => void;
}

export default function SettingsPage({ route, onNavigate }: SettingsPageProps) {
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
    <section className="grid w-full gap-6 xl:grid-cols-[minmax(0,0.95fr)_minmax(0,1.05fr)]">
      <div className="grid content-start gap-6">
        <section className="rounded-[28px] border border-border bg-surface/80 p-6 shadow-card">
          <p className="text-sm font-semibold uppercase tracking-[0.24em] text-ice-600 dark:text-ice-300">
            JCVI meow · {route.description}
          </p>
          <h1 className="mt-4 text-4xl font-semibold tracking-tight text-text-primary">环境诊断与设置</h1>
          <p className="mt-4 text-sm leading-8 text-text-secondary">
            启动层超过 10 秒时会把用户引导到这里。当前页面承接工具链诊断、契约参考，以及回到分析工作台的快捷入口。
          </p>

          <div className="mt-6 flex flex-wrap gap-3">
            <button
              type="button"
              className="rounded-lg bg-ice-500 px-4 py-2 text-sm font-semibold text-white shadow-lg shadow-ice-500/20 transition hover:bg-ice-400"
              onClick={() => onNavigate("/analysis/new")}
            >
              回到分析工作台
            </button>
            <button
              type="button"
              className="rounded-lg border border-border bg-surface-raised/80 px-4 py-2 text-sm font-semibold text-text-secondary transition hover:border-ice-200 hover:bg-ice-50 hover:text-ice-700 dark:hover:border-ice-800 dark:hover:bg-ice-900/30 dark:hover:text-ice-200"
              onClick={() => onNavigate("/")}
            >
              返回 JCVI meow桌面
            </button>
          </div>
        </section>

        <section className="rounded-[28px] border border-border bg-surface/80 p-6 shadow-card">
          <div className="flex items-center justify-between gap-3">
            <div>
              <h2 className="text-lg font-semibold text-text-primary">本地工具链诊断</h2>
              <p className="mt-1 text-sm text-text-secondary">Tauri command: check_environment()</p>
            </div>
            <span
              className={
                report?.status === "ok"
                  ? "rounded-full bg-emerald-100 px-3 py-1 text-[11px] font-semibold text-emerald-700 dark:bg-emerald-400/15 dark:text-emerald-200"
                  : "rounded-full bg-amber-100 px-3 py-1 text-[11px] font-semibold text-amber-700 dark:bg-amber-400/15 dark:text-amber-200"
              }
            >
              {loading ? "CHECKING" : report?.status?.toUpperCase?.() ?? "UNKNOWN"}
            </span>
          </div>

          {error ? (
            <p className="mt-4 rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700 dark:border-rose-900/60 dark:bg-rose-950/30 dark:text-rose-200">
              {error}
            </p>
          ) : null}

          <div className="mt-4 grid gap-3">
            {toolItems.map((item) => (
              <article key={item.id} className="rounded-2xl border border-border bg-bg p-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold text-text-primary">{item.label}</p>
                    <p className="mt-1 break-all font-mono text-xs text-text-tertiary">{item.path || "未提供路径"}</p>
                  </div>
                  <span
                    className={
                      item.status === "ok"
                        ? "rounded-full bg-emerald-100 px-3 py-1 text-[11px] font-semibold text-emerald-700 dark:bg-emerald-400/15 dark:text-emerald-200"
                        : item.status === "missing"
                          ? "rounded-full bg-rose-100 px-3 py-1 text-[11px] font-semibold text-rose-700 dark:bg-rose-400/15 dark:text-rose-200"
                          : "rounded-full bg-amber-100 px-3 py-1 text-[11px] font-semibold text-amber-700 dark:bg-amber-400/15 dark:text-amber-200"
                    }
                  >
                    {item.status}
                  </span>
                </div>
                <p className="mt-3 text-sm leading-6 text-text-secondary">{item.message || "暂无额外说明。"}</p>
              </article>
            ))}
          </div>
        </section>
      </div>

      <CommandPreview
        title="AnalysisRequest Schema"
        command="get_analysis_schema()"
        description="保留平台原始 schema 展示，供工作台、诊断和契约核对使用。"
        load={loadSchema}
      />
    </section>
  );
}
