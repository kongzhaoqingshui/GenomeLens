import { useEffect, useMemo, useState } from "react";

import { JcviMeowIcon } from "../components/JcviMeowIcon";
import { listJcviCapabilities } from "../models";
import type { VersionInfo } from "../models/version";
import type { AppRoute } from "../routes/routes";
import { getVersion } from "../services/version";

const EMPTY_VERSION: VersionInfo = {
  platform: { ok: false, command: "genomelens --version", version: "", error: "尚未探测" },
  engine: { ok: false, command: "jcvi-genomelens probe", version: "", error: "尚未探测" },
};

const CAPABILITY_LAYOUT = {
  "pairwise-synteny": { offsetX: -182, offsetY: -124 },
  "multi-species-synteny": { offsetX: 174, offsetY: -108 },
  "local-synteny": { offsetX: -214, offsetY: 18 },
  dotplot: { offsetX: 200, offsetY: 4 },
  karyotype: { offsetX: -118, offsetY: 156 },
  "ortholog-catalog": { offsetX: 146, offsetY: 170 },
  "environment-check": { offsetX: 6, offsetY: -206 },
} as const;

function VersionStatus({ label, value }: { label: string; value: VersionInfo["platform"] }) {
  return (
    <div className="rounded-2xl border border-border bg-surface-raised/90 p-4 shadow-card">
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
          {value.ok ? "READY" : "CHECK"}
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

  useEffect(() => {
    void getVersion()
      .then(setVersion)
      .catch((error: unknown) => {
        const message = error instanceof Error ? error.message : String(error);
        setVersion({
          platform: { ...EMPTY_VERSION.platform, error: message },
          engine: { ...EMPTY_VERSION.engine, error: message },
        });
      });
  }, []);

  const readyCount = useMemo(() => [version.platform.ok, version.engine.ok].filter(Boolean).length, [version]);
  const capabilities = useMemo(
    () =>
      listJcviCapabilities().map((capability) => ({
        ...capability,
        ...CAPABILITY_LAYOUT[capability.id],
      })),
    [],
  );

  function handleCapabilityClick(path: string, capabilityId: string, status: "connected" | "reserved") {
    if (status === "reserved") {
      return;
    }
    if (path === "/analysis/new") {
      onNavigate(`${path}?capability=${capabilityId}`);
      return;
    }
    onNavigate(path);
  }

  return (
    <div className="grid w-full gap-8 xl:grid-cols-[minmax(0,1.28fr)_minmax(21rem,0.72fr)]">
      <section className="relative overflow-hidden rounded-[32px] border border-border bg-surface/75 p-6 shadow-card lg:p-8">
        <div className="pointer-events-none absolute inset-0">
          <div className="absolute left-1/2 top-1/2 h-[34rem] w-[34rem] -translate-x-1/2 -translate-y-1/2 rounded-full border border-ice-100/70 dark:border-ice-900/60" />
          <div className="absolute left-1/2 top-1/2 h-[26rem] w-[26rem] -translate-x-1/2 -translate-y-1/2 rounded-full border border-dashed border-ice-200/80 dark:border-ice-800/70" />
          <div className="absolute left-1/2 top-1/2 h-[18rem] w-[18rem] -translate-x-1/2 -translate-y-1/2 rounded-full border border-ice-100/70 dark:border-ice-900/60" />
          <div className="absolute left-1/2 top-1/2 h-72 w-72 -translate-x-1/2 -translate-y-1/2 rounded-full bg-ice-100/60 blur-3xl dark:bg-ice-900/20" />
        </div>

        <div className="relative flex flex-col gap-8">
          <div className="max-w-2xl">
            <p className="text-sm font-semibold uppercase tracking-[0.24em] text-ice-600 dark:text-ice-300">
              JCVI喵 · {route.description}
            </p>
            <h1 className="mt-4 text-4xl font-semibold tracking-tight text-text-primary lg:text-[46px]">
              把 JCVI 分析入口收进一张真正可用的桌面工作台
            </h1>
            <p className="mt-4 max-w-2xl text-sm leading-8 text-text-secondary lg:text-base">
              从 Pairwise、Multi-species 到 Local Synteny，先进入能力环，再落到当前任务工作台。底层仍然复用
              GenomeLens CLI、AnalysisRequest、run summary 和 run log。
            </p>
          </div>

          <div className="relative flex min-h-[560px] items-center justify-center overflow-hidden rounded-[28px] border border-ice-100/80 bg-bg/70 px-4 py-8 shadow-inner dark:border-ice-900/60">
            {capabilities.map((entry) => (
              <button
                key={entry.id}
                type="button"
                className={[
                  "group absolute flex w-44 -translate-x-1/2 -translate-y-1/2 items-center gap-3 rounded-2xl border px-3 py-3 text-left shadow-card transition duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ice-500",
                  entry.status === "connected"
                    ? "border-border bg-surface-raised/90 hover:-translate-y-[calc(50%+3px)] hover:border-ice-300 hover:shadow-card-hover dark:hover:border-ice-800"
                    : "cursor-default border-border/70 bg-surface-raised/60 opacity-70",
                ].join(" ")}
                style={{
                  left: "50%",
                  top: "50%",
                  transform: `translate(calc(-50% + ${entry.offsetX}px), calc(-50% + ${entry.offsetY}px))`,
                }}
                onClick={() => handleCapabilityClick(entry.route, entry.id, entry.status)}
              >
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-ice-50 text-[11px] font-semibold uppercase tracking-[0.12em] text-ice-700 ring-1 ring-ice-100 transition group-hover:bg-ice-100 dark:bg-ice-950/70 dark:text-ice-200 dark:ring-ice-900/60 dark:group-hover:bg-ice-900/40">
                  {entry.subtitle.slice(0, 2)}
                </span>
                <span className="min-w-0">
                  <span className="block text-sm font-semibold text-text-primary">{entry.title}</span>
                  <span className="block text-[11px] text-text-tertiary">{entry.subtitle}</span>
                  <span className="mt-1 block text-[10px] uppercase tracking-[0.14em] text-ice-600 dark:text-ice-300">
                    {entry.status === "connected" ? entry.statusLabel : "Preview · Reserved"}
                  </span>
                </span>
              </button>
            ))}

            <div className="relative z-10 flex h-64 w-64 flex-col items-center justify-center rounded-full border border-ice-200/80 bg-surface-raised/95 p-8 text-center shadow-2xl shadow-ice-500/10 dark:border-ice-900/60">
              <div className="flex h-24 w-24 items-center justify-center rounded-full bg-ice-50 text-ice-500 ring-1 ring-ice-100 dark:bg-ice-950/70 dark:ring-ice-900/60">
                <JcviMeowIcon className="h-16 w-16" />
              </div>
              <h2 className="mt-5 text-2xl font-semibold text-text-primary">JCVI喵</h2>
              <p className="mt-2 text-sm leading-6 text-text-secondary">中心能力环已经接上现有工作台入口。</p>
              <p className="mt-3 text-xs text-text-tertiary">Powered by GenomeLens</p>
            </div>
          </div>
        </div>
      </section>

      <aside className="grid content-start gap-5">
        <section className="rounded-[28px] border border-border bg-surface/80 p-5 shadow-card">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-sm font-semibold text-text-primary">桌面就绪状态</p>
              <p className="mt-1 text-sm text-text-secondary">启动层结束后，这里继续承接平台与引擎状态。</p>
            </div>
            <span className="rounded-full bg-ice-100 px-3 py-1 text-[11px] font-semibold text-ice-700 dark:bg-ice-900/40 dark:text-ice-200">
              {readyCount}/2 READY
            </span>
          </div>
          <div className="mt-4 grid gap-3">
            <VersionStatus label="GenomeLens Platform" value={version.platform} />
            <VersionStatus label="JCVI Engine" value={version.engine} />
          </div>
        </section>

        <section className="rounded-[28px] border border-border bg-surface/80 p-5 shadow-card">
          <h2 className="text-lg font-semibold text-text-primary">进入方式</h2>
          <div className="mt-4 grid gap-2">
            <button
              type="button"
              className="flex items-center justify-between rounded-2xl border border-border bg-bg px-4 py-3 text-left transition hover:border-ice-200 hover:bg-ice-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ice-500 dark:hover:border-ice-800 dark:hover:bg-ice-900/30"
              onClick={() => onNavigate("/analysis/new")}
            >
              <span>
                <span className="block text-sm font-semibold text-text-primary">进入分析工作台</span>
                <span className="block text-xs text-text-tertiary">现有 Run flow 从这里继续。</span>
              </span>
              <span className="text-sm font-semibold text-ice-500">→</span>
            </button>
            <button
              type="button"
              className="flex items-center justify-between rounded-2xl border border-border bg-bg px-4 py-3 text-left transition hover:border-ice-200 hover:bg-ice-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ice-500 dark:hover:border-ice-800 dark:hover:bg-ice-900/30"
              onClick={() => onNavigate("/settings")}
            >
              <span>
                <span className="block text-sm font-semibold text-text-primary">环境诊断</span>
                <span className="block text-xs text-text-tertiary">查看工具链、路径和 schema 参考。</span>
              </span>
              <span className="text-sm font-semibold text-ice-500">→</span>
            </button>
          </div>
        </section>

        <section className="rounded-[28px] border border-border bg-surface/80 p-5 shadow-card">
          <h2 className="text-lg font-semibold text-text-primary">本轮重点</h2>
          <div className="mt-4 grid gap-3 text-sm text-text-secondary">
            <p>启动层先出现，再并行预热后端能力。</p>
            <p>首页能力环负责把入口送进现有工作台，而不是营销式 hero。</p>
            <p>工作台继续复用已打通的状态、日志和 summary 契约。</p>
          </div>
        </section>
      </aside>
    </div>
  );
}
