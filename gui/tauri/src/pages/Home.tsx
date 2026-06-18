import { useEffect, useState } from "react";

import type { VersionInfo } from "../models/version";
import { getVersion } from "../services/version";
import type { AppRoute } from "../routes/routes";

const EMPTY_VERSION: VersionInfo = {
  platform: { ok: false, command: "genomelens --version", version: "", error: "尚未检测" },
  engine: { ok: false, command: "jcvi-genomelens --version", version: "", error: "尚未检测" },
};

const ANALYSIS_ENTRIES = [
  {
    title: "双物种共线性",
    subtitle: "Pairwise Synteny",
    description: "从 BED+CDS 或 GFF+FASTA 输入生成 dotplot 与 synteny 图件。",
  },
  {
    title: "多物种共线性",
    subtitle: "Multi-species Synteny",
    description: "围绕 species[] 协议组织 all-vs-all pairwise 编排与汇总。",
  },
  {
    title: "局部共线性",
    subtitle: "Local Synteny",
    description: "以参考物种目标基因为中心查看上下游共线性结构。",
  },
];

function VersionStatus({ label, value }: { label: string; value: VersionInfo["platform"] }) {
  return (
    <div className="rounded-xl border border-border bg-surface-raised/90 p-4 shadow-card transition duration-200 hover:-translate-y-0.5 hover:shadow-card-hover">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-sm font-semibold text-text-primary">{label}</p>
          <p className="mt-1 font-mono text-xs text-text-tertiary">{value.command}</p>
        </div>
        <span
          className={
            value.ok
              ? "rounded-full bg-emerald-100 px-3 py-1 text-[11px] font-semibold text-emerald-700 dark:bg-emerald-400/15 dark:text-emerald-200"
              : "rounded-full bg-amber-100 px-3 py-1 text-[11px] font-semibold text-amber-700 dark:bg-amber-400/15 dark:text-amber-200"
          }
        >
          {value.ok ? "READY" : "PENDING"}
        </span>
      </div>
      <p className="mt-3 text-sm leading-6 text-text-secondary">{value.ok ? value.version : value.error}</p>
    </div>
  );
}

interface HomeProps {
  route: AppRoute;
  onNavigate: (path: string) => void;
}

export default function Home({ route, onNavigate }: HomeProps) {
  const [version, setVersion] = useState<VersionInfo>(EMPTY_VERSION);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    void getVersion()
      .then(setVersion)
      .catch((error: unknown) => {
        const message = error instanceof Error ? error.message : String(error);
        setVersion({
          platform: { ...EMPTY_VERSION.platform, error: message },
          engine: { ...EMPTY_VERSION.engine, error: message },
        });
      })
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="grid w-full gap-8 lg:grid-cols-[1.08fr_0.92fr]">
      <section className="flex flex-col justify-center">
        <p className="text-sm font-semibold uppercase tracking-[0.2em] text-ice-600 dark:text-ice-300">
          GenomeLens GUI · {route.description}
        </p>
        <h1 className="mt-5 max-w-3xl text-4xl font-bold leading-tight text-text-primary lg:text-[44px]">
          比较基因组学分析工作台
        </h1>
        <p className="mt-5 max-w-2xl text-base leading-8 text-text-secondary">
          从物种输入到共线性图件，一站式可视化分析。Phase 0 先搭建前端底座、主题系统与核心导航，
          后续通过 Tauri Command 复用 GenomeLens CLI 的 AnalysisRequest 协议。
        </p>

        <div className="mt-8 flex flex-wrap gap-3">
          <button
            type="button"
            className="rounded-lg bg-ice-500 px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-ice-500/20 transition duration-200 hover:-translate-y-0.5 hover:bg-ice-400 active:scale-[0.98] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ice-500 focus-visible:ring-offset-2 focus-visible:ring-offset-bg"
            onClick={() => onNavigate("/analysis/new")}
          >
            新建分析任务
          </button>
          <button
            type="button"
            className="rounded-lg border border-ice-200 bg-surface-raised/80 px-5 py-2.5 text-sm font-semibold text-ice-700 transition duration-200 hover:bg-ice-50 active:scale-[0.98] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ice-500 focus-visible:ring-offset-2 focus-visible:ring-offset-bg dark:border-ice-800 dark:text-ice-200 dark:hover:bg-ice-900/30"
            onClick={() => onNavigate("/projects")}
          >
            打开最近项目
          </button>
        </div>

        <div className="mt-10 grid gap-4 md:grid-cols-3">
          {ANALYSIS_ENTRIES.map((entry) => (
            <article
              key={entry.title}
              className="rounded-xl border border-border bg-surface/80 p-4 shadow-card transition duration-200 hover:-translate-y-0.5 hover:border-ice-200 hover:shadow-card-hover dark:hover:border-ice-800"
            >
              <div className="mb-4 h-1 w-12 rounded-full bg-ice-400" />
              <h2 className="text-base font-semibold text-text-primary">{entry.title}</h2>
              <p className="mt-1 text-xs font-medium text-ice-600 dark:text-ice-300">{entry.subtitle}</p>
              <p className="mt-3 text-sm leading-6 text-text-secondary">{entry.description}</p>
            </article>
          ))}
        </div>
      </section>

      <aside className="flex flex-col justify-center gap-5">
        <section className="rounded-2xl border border-ice-100 bg-surface/80 p-5 shadow-xl shadow-ice-500/10 backdrop-blur dark:border-ice-900/40">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold text-text-primary">引擎与工具</h2>
              <p className="text-sm text-text-secondary">Tauri command: get_version()</p>
            </div>
            {loading ? (
              <span className="relative overflow-hidden rounded-full bg-ice-100 px-3 py-1 text-xs font-medium text-ice-700 dark:bg-ice-900/40 dark:text-ice-200">
                检测中
              </span>
            ) : null}
          </div>
          <div className="grid gap-3">
            <VersionStatus label="Platform CLI" value={version.platform} />
            <VersionStatus label="JCVI Engine" value={version.engine} />
          </div>
        </section>

        <section className="rounded-2xl border border-border bg-surface/70 p-5 shadow-card">
          <h2 className="text-lg font-semibold text-text-primary">导航入口</h2>
          <div className="mt-4 grid gap-2">
            {[
              ["/projects", "项目列表", "Project Workspace"],
              ["/analysis/new", "任务创建向导", "Analysis Wizard"],
              ["/results", "结果与图件预览", "Run Summary"],
              ["/settings", "设置与环境诊断", "Settings"],
            ].map(([path, label, subtitle]) => (
              <button
                key={path}
                type="button"
                className="flex items-center justify-between rounded-lg border border-transparent px-3 py-2 text-left transition hover:border-ice-200 hover:bg-ice-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ice-500 dark:hover:border-ice-800 dark:hover:bg-ice-900/30"
                onClick={() => onNavigate(path)}
              >
                <span>
                  <span className="block text-sm font-semibold text-text-primary">{label}</span>
                  <span className="block text-xs text-text-tertiary">{subtitle}</span>
                </span>
                <span className="text-sm text-ice-500">→</span>
              </button>
            ))}
          </div>
        </section>
      </aside>
    </div>
  );
}

