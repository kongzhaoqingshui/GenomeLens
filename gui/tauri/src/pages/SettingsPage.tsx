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
    <section className="grid w-full gap-8 xl:grid-cols-[18rem_minmax(0,1fr)]">
      <aside className="grid content-start gap-6">
        <section className="overflow-hidden rounded-xl border border-slate-200 bg-slate-50">
          <div className="border-b border-slate-200/80 px-5 py-4">
            <p className="text-xs font-medium uppercase tracking-[0.18em] text-slate-400">{route.label}</p>
            <h1 className="mt-2 text-xl font-semibold text-slate-900">Environment and references</h1>
            <p className="mt-2 text-sm leading-6 text-slate-500">{route.description}</p>
          </div>
          <div className="p-4">
            <button
              type="button"
              className="mb-2 flex w-full items-center justify-between rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-50 hover:text-slate-900"
              onClick={() => onNavigate("/analysis/new")}
            >
              <span>Open workbench</span>
              <span className="text-slate-400">/analysis/new</span>
            </button>
            <button
              type="button"
              className="flex w-full items-center justify-between rounded-lg px-3 py-2 text-sm text-slate-600 transition hover:bg-white hover:text-slate-900"
              onClick={() => onNavigate("/")}
            >
              <span>Back to home</span>
              <span className="text-slate-400">/</span>
            </button>
          </div>
        </section>

        <section className="overflow-hidden rounded-xl border border-slate-200 bg-white">
          <div className="border-b border-slate-200/80 px-5 py-4">
            <h2 className="text-sm font-semibold text-slate-900">Environment status</h2>
            <p className="mt-1 text-sm text-slate-500">Live result from `check_environment()`.</p>
          </div>
          <div className="divide-y divide-slate-200/80">
            <div className="flex items-center justify-between px-5 py-4 text-sm">
              <span className="text-slate-400">State</span>
              <span className={`rounded-full px-3 py-1 text-[11px] font-semibold uppercase ${statusClass(report?.status)}`}>
                {loading ? "checking" : report?.status ?? "unknown"}
              </span>
            </div>
            <div className="flex items-center justify-between px-5 py-4 text-sm">
              <span className="text-slate-400">Tools</span>
              <span className="font-medium text-slate-900">{toolItems.length}</span>
            </div>
          </div>
        </section>
      </aside>

      <div className="grid content-start gap-6">
        <section className="overflow-hidden rounded-xl border border-slate-200 bg-white">
          <div className="flex items-start justify-between gap-4 border-b border-slate-200/80 px-5 py-4">
            <div>
              <h2 className="text-base font-semibold text-slate-900">Local toolchain</h2>
              <p className="mt-1 text-sm text-slate-500">Thin diagnostics surface for the current GenomeLens and JCVI toolchain.</p>
            </div>
            <span className={`rounded-full px-3 py-1 text-[11px] font-semibold uppercase ${statusClass(report?.status)}`}>
              {loading ? "checking" : report?.status ?? "unknown"}
            </span>
          </div>

          {error ? (
            <div className="border-b border-slate-200/80 bg-rose-50 px-5 py-4 text-sm text-rose-700">{error}</div>
          ) : null}

          <div className="divide-y divide-slate-200/80">
            {toolItems.map((item) => (
              <article key={item.id} className="px-5 py-4">
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0">
                    <p className="text-sm font-semibold text-slate-900">{item.label}</p>
                    <p className="mt-1 break-all font-mono text-xs text-slate-400">{item.path || "Path unavailable"}</p>
                  </div>
                  <span className={`rounded-full px-3 py-1 text-[11px] font-semibold uppercase ${toolStatusClass(item.status)}`}>
                    {item.status}
                  </span>
                </div>
                <p className="mt-3 text-sm leading-6 text-slate-500">{item.message || "No additional details."}</p>
              </article>
            ))}
          </div>
        </section>

        <CommandPreview
          title="AnalysisRequest schema"
          command="get_analysis_schema()"
          description="Keep the raw platform schema visible for contract checks and debugging."
          load={loadSchema}
        />
      </div>
    </section>
  );
}
