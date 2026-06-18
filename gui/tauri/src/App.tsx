import { useEffect, useState } from "react";

import { getVersion } from "./services/version";
import type { VersionInfo } from "./models/version";

const EMPTY_VERSION: VersionInfo = {
  platform: { ok: false, command: "genomelens --version", version: "", error: "尚未检测" },
  engine: { ok: false, command: "jcvi-genomelens --version", version: "", error: "尚未检测" },
};

function VersionRow({ label, value }: { label: string; value: VersionInfo["platform"] }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white/80 p-4 shadow-sm">
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="text-sm font-semibold text-slate-900">{label}</p>
          <p className="mt-1 font-mono text-xs text-slate-500">{value.command}</p>
        </div>
        <span
          className={
            value.ok
              ? "rounded-full bg-emerald-100 px-3 py-1 text-xs font-medium text-emerald-700"
              : "rounded-full bg-amber-100 px-3 py-1 text-xs font-medium text-amber-700"
          }
        >
          {value.ok ? "READY" : "PENDING"}
        </span>
      </div>
      <p className="mt-3 text-sm text-slate-700">{value.ok ? value.version : value.error || "未返回版本信息"}</p>
    </div>
  );
}

export default function App() {
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
    <main className="min-h-screen bg-gradient-to-br from-ice-50 via-white to-slate-50 text-slate-950">
      <section className="mx-auto flex min-h-screen w-full max-w-6xl flex-col px-8 py-8">
        <header className="flex items-center justify-between border-b border-slate-200 pb-5">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-ice-500 text-lg font-bold text-white shadow-lg shadow-ice-500/20">
              G
            </div>
            <div>
              <p className="text-lg font-semibold tracking-tight">GenomeLens</p>
              <p className="text-xs text-slate-500">Comparative Genomics Workbench</p>
            </div>
          </div>
          <span className="rounded-full border border-ice-200 bg-white/70 px-3 py-1 text-xs font-medium text-ice-700">
            Phase 0 Skeleton
          </span>
        </header>

        <div className="grid flex-1 items-center gap-10 py-12 lg:grid-cols-[1.1fr_0.9fr]">
          <section>
            <p className="text-sm font-semibold uppercase tracking-[0.2em] text-ice-600">GenomeLens GUI</p>
            <h1 className="mt-4 max-w-3xl text-4xl font-bold leading-tight text-slate-950">
              比较基因组学分析工作台
            </h1>
            <p className="mt-5 max-w-2xl text-base leading-8 text-slate-600">
              Phase 0 聚焦 Tauri 骨架、Rust command、开发脚本与前后端契约。GUI 只作为平台交互外壳，
              分析逻辑继续由 GenomeLens CLI 和 engine 协议承载。
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <button className="rounded-lg bg-ice-500 px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-ice-500/20 transition hover:-translate-y-0.5 hover:bg-ice-400">
                新建分析任务
              </button>
              <button className="rounded-lg border border-ice-200 bg-white/80 px-5 py-2.5 text-sm font-semibold text-ice-700 transition hover:bg-ice-50">
                打开最近项目
              </button>
            </div>
          </section>

          <section className="rounded-2xl border border-ice-100 bg-white/70 p-5 shadow-xl shadow-ice-500/10 backdrop-blur">
            <div className="mb-4 flex items-center justify-between">
              <div>
                <h2 className="text-lg font-semibold text-slate-900">环境版本探测</h2>
                <p className="text-sm text-slate-500">Tauri command: get_version()</p>
              </div>
              {loading ? <span className="text-xs text-slate-500">检测中...</span> : null}
            </div>
            <div className="grid gap-3">
              <VersionRow label="Platform CLI" value={version.platform} />
              <VersionRow label="JCVI Engine" value={version.engine} />
            </div>
          </section>
        </div>
      </section>
    </main>
  );
}
