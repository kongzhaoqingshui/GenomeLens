import { useMemo, useState } from "react";

import { GameIcon, type GameIconName } from "../components/GameIcon";
import { useLanguage } from "../i18n/useLanguage";
import { JcviMeowIcon } from "../components/JcviMeowIcon";
import {
  listJcviCapabilities,
  type JcviCapabilityEntry,
  type JcviCapabilityId,
} from "../models";
import type { AppRoute } from "../routes/routes";

const CAPABILITY_ICON: Record<JcviCapabilityId, GameIconName> = {
  "pairwise-synteny": "pairwise",
  "multi-species-synteny": "multi-species",
  "local-synteny": "local",
  dotplot: "dotplot",
  karyotype: "karyotype",
  "ortholog-catalog": "ortholog",
  "environment-check": "environment",
};

interface HomeProps {
  route: AppRoute;
  onNavigate: (path: string) => void;
}

function actionLabel(entry: JcviCapabilityEntry, isZh: boolean): string {
  if (entry.route === "/settings") {
    return isZh ? "打开诊断" : "Open diagnostics";
  }
  return entry.status === "connected" ? (isZh ? "打开工作台" : "Open workbench") : isZh ? "预览能力" : "Preview capability";
}

function capabilitySubtitle(entry: JcviCapabilityEntry, isZh: boolean): string {
  if (!isZh) {
    return entry.subtitle;
  }
  switch (entry.id) {
    case "pairwise-synteny":
      return "双物种共线性";
    case "multi-species-synteny":
      return "多物种共线性";
    case "local-synteny":
      return "局部共线性";
    case "dotplot":
      return "点图";
    case "karyotype":
      return "核型总图";
    case "ortholog-catalog":
      return "直系同源目录";
    case "environment-check":
      return "环境诊断";
    default:
      return entry.subtitle;
  }
}

function capabilityDescription(entry: JcviCapabilityEntry, isZh: boolean): string {
  if (!isZh) {
    return entry.description;
  }
  switch (entry.id) {
    case "pairwise-synteny":
      return "打开当前 MCSCAN 工作台，并预设双物种共线性 workflow。";
    case "multi-species-synteny":
      return "打开当前 MCSCAN 工作台，并预设多物种共线性 workflow。";
    case "local-synteny":
      return "打开当前 MCSCAN 工作台，并预设局部共线性 workflow。";
    case "dotplot":
      return "为独立点图界面预留，相关 workflow 预设已经接好。";
    case "karyotype":
      return "为独立核型总图界面预留，相关 workflow 预设已经接好。";
    case "ortholog-catalog":
      return "为独立直系同源目录界面预留，相关 workflow 预设已经接好。";
    case "environment-check":
      return "打开设置页并复用当前环境诊断入口。";
    default:
      return entry.description;
  }
}

function capabilityStatusLabel(entry: JcviCapabilityEntry, isZh: boolean): string {
  if (!isZh) {
    return entry.statusLabel;
  }
  return entry.status === "connected" ? "已接入" : "预留";
}

export default function Home({ onNavigate }: HomeProps) {
  const { language } = useLanguage();
  const isZh = language === "zh-CN";
  const capabilities = useMemo(() => listJcviCapabilities(), []);
  const [selectedId, setSelectedId] = useState<JcviCapabilityId>("pairwise-synteny");
  const selected =
    capabilities.find((entry) => entry.id === selectedId) ??
    capabilities.find((entry) => entry.status === "connected") ??
    capabilities[0];
  if (!selected) {
    return null;
  }
  const connected = capabilities.filter((entry) => entry.status === "connected");
  const reserved = capabilities.filter((entry) => entry.status === "reserved");

  function openCapability(entry: JcviCapabilityEntry) {
    if (entry.status === "reserved") {
      setSelectedId(entry.id);
      return;
    }

    if (entry.route === "/analysis/new") {
      onNavigate(`${entry.route}?capability=${entry.id}`);
      return;
    }

    onNavigate(entry.route);
  }

  return (
    <div className="ui-page-enter grid h-screen w-full grid-cols-[18rem_minmax(0,1fr)_20rem] overflow-hidden bg-surface-raised">
      <aside className="flex min-h-0 flex-col overflow-hidden border-r border-border bg-surface px-3 py-4">
        <div className="flex items-center gap-3 rounded-xl px-3 py-2">
          <JcviMeowIcon className="h-9 w-9" />
          <span>
            <span className="jcvi-brand-title block text-sm font-semibold text-slate-900">JCVI meow</span>
            <span className="block text-xs text-slate-500">{isZh ? "桌面工作台" : "Desktop workbench"}</span>
          </span>
        </div>

        <button
          type="button"
          className="ui-pressable mt-4 rounded-lg bg-slate-900 px-3 py-2 text-left text-sm font-semibold text-white transition hover:bg-slate-700"
          onClick={() => openCapability(selected)}
        >
          {actionLabel(selected, isZh)}
        </button>

        <div className="mt-6 px-3 text-[11px] font-medium uppercase tracking-[0.18em] text-slate-400">{isZh ? "能力" : "Capabilities"}</div>
        <div className="mt-2 min-h-0 flex-1 overflow-y-auto overflow-x-hidden pr-1">
          {capabilities.map((entry) => (
            <button
              key={entry.id}
              type="button"
              className={
                entry.id === selected.id
                  ? "ui-list-item mb-1 flex w-full items-center gap-3 rounded-lg bg-white px-3 py-2 text-left shadow-sm"
                  : "ui-list-item mb-1 flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left text-slate-600 transition hover:bg-white/70 hover:text-slate-900"
              }
              onClick={() => setSelectedId(entry.id)}
            >
              <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-slate-100 text-slate-600">
                <GameIcon name={CAPABILITY_ICON[entry.id]} className="h-4 w-4" />
              </span>
              <span className="min-w-0">
                <span className="block truncate text-sm font-medium text-slate-900">{capabilitySubtitle(entry, isZh)}</span>
                <span className="block truncate text-xs text-slate-400">{capabilityStatusLabel(entry, isZh)}</span>
              </span>
            </button>
          ))}
        </div>

        <div className="border-t border-slate-200/80 pt-3">
          <button
            type="button"
            className="ui-list-item flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left text-sm text-slate-600 transition hover:bg-white/70 hover:text-slate-900"
            onClick={() => onNavigate("/settings")}
          >
            <GameIcon name="environment" className="h-4 w-4" />
            {isZh ? "设置与诊断" : "Settings and diagnostics"}
          </button>
        </div>
      </aside>

      <main className="flex min-w-0 flex-col bg-surface-raised">
        <header className="flex h-16 items-center justify-between border-b border-border px-8">
          <div>
            <p className="text-xs font-medium uppercase tracking-[0.18em] text-slate-400">{isZh ? "首页" : "Home"}</p>
            <h1 className="mt-1 text-base font-semibold text-slate-900">{capabilitySubtitle(selected, isZh)}</h1>
          </div>
          <span
            className={
              selected.status === "connected"
                ? "rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700"
                : "rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600"
            }
          >
            {capabilityStatusLabel(selected, isZh)}
          </span>
        </header>

        <div className="min-h-0 flex-1 overflow-auto px-10 py-8">
          <div className="ui-surface-enter mx-auto max-w-5xl">
            <div className="flex items-start gap-5">
              <div className="flex h-16 w-16 items-center justify-center rounded-2xl border border-slate-200 bg-slate-50">
                <GameIcon name={CAPABILITY_ICON[selected.id]} className="h-7 w-7" />
              </div>
              <div className="min-w-0">
                <h2 className="text-3xl font-semibold tracking-tight text-slate-900">{capabilitySubtitle(selected, isZh)}</h2>
                <p className="mt-3 max-w-3xl text-sm leading-7 text-slate-500">{capabilityDescription(selected, isZh)}</p>
              </div>
            </div>

            <div className="mt-8 grid gap-6 xl:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)]">
              <section>
                <div className="border-b border-slate-200/80 pb-3">
                  <h3 className="text-sm font-semibold text-slate-900">{isZh ? "当前入口" : "Current surface"}</h3>
                  <p className="mt-1 text-sm text-slate-500">{isZh ? "这里展示当前能力会进入哪个工作台入口。" : "This is where the selected capability opens inside the workbench."}</p>
                </div>
                <div className="divide-y divide-slate-200/80 border-b border-slate-200/80">
                  <div className="grid grid-cols-[11rem_minmax(0,1fr)] gap-4 py-4 text-sm">
                    <span className="text-slate-400">{isZh ? "路由" : "Route"}</span>
                    <span className="font-medium text-slate-900">{selected.route}</span>
                  </div>
                  <div className="grid grid-cols-[11rem_minmax(0,1fr)] gap-4 py-4 text-sm">
                    <span className="text-slate-400">{isZh ? "工作流预设" : "Workflow preset"}</span>
                    <span className="font-medium text-slate-900">{selected.workflowPreset ?? (isZh ? "无" : "None")}</span>
                  </div>
                  <div className="grid grid-cols-[11rem_minmax(0,1fr)] gap-4 py-4 text-sm">
                    <span className="text-slate-400">{isZh ? "主操作" : "Primary action"}</span>
                    <span className="font-medium text-slate-900">{actionLabel(selected, isZh)}</span>
                  </div>
                </div>
              </section>

              <section>
                <div className="border-b border-slate-200/80 pb-3">
                  <h3 className="text-sm font-semibold text-slate-900">{isZh ? "使用预期" : "What to expect"}</h3>
                  <p className="mt-1 text-sm text-slate-500">{isZh ? "保持 run flow 清晰可预测：配置、运行、查看日志、读取摘要。" : "Keep the run flow predictable: configure, run, inspect logs, read summary."}</p>
                </div>
                <div className="divide-y divide-slate-200/80 border-b border-slate-200/80">
                  {(isZh
                    ? [
                        "可以在工作台里逐个准备任务，也可以并排维护多个任务。",
                        "当本地工具链阻塞执行时，随时打开环境诊断。",
                        "预留能力会继续可见，但不会替代当前已跑通的 run flow。",
                      ]
                    : [
                        "Use the workbench to prepare one task at a time or queue multiple tasks.",
                        "Open diagnostics whenever a local toolchain issue blocks execution.",
                        "Reserved capabilities stay visible, but they do not replace the current run flow.",
                      ]).map((detail) => (
                    <div key={detail} className="py-4 text-sm leading-7 text-slate-500">
                      {detail}
                    </div>
                  ))}
                </div>
              </section>
            </div>
          </div>
        </div>

        <div className="border-t border-slate-200/80 bg-white px-10 py-5">
          <div className="mx-auto flex max-w-5xl items-center gap-3 border border-slate-200 bg-white px-4 py-3">
            <button
              type="button"
              className="ui-pressable rounded-lg border border-slate-200 px-3 py-2 text-xs font-medium text-slate-700 transition hover:bg-slate-50"
              onClick={() => onNavigate("/settings")}
            >
              {isZh ? "设置" : "Settings"}
            </button>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm text-slate-500">
                {capabilitySubtitle(selected, isZh)} - {capabilityStatusLabel(selected, isZh)} - {selected.route === "/analysis/new" ? (isZh ? "可进入工作台" : "Ready for the workbench") : isZh ? "打开诊断" : "Opens diagnostics"}
              </p>
            </div>
            <button
              type="button"
              className={
                selected.status === "connected"
                  ? "ui-pressable rounded-full bg-slate-900 px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-700"
                  : "rounded-full bg-slate-200 px-4 py-2 text-sm font-semibold text-slate-500"
              }
              disabled={selected.status !== "connected"}
              onClick={() => openCapability(selected)}
            >
              {actionLabel(selected, isZh)}
            </button>
          </div>
        </div>
      </main>

      <aside className="min-h-0 overflow-y-auto overflow-x-hidden border-l border-border bg-surface-raised px-5 py-6">
        <section>
          <h2 className="text-sm font-semibold text-slate-900">{isZh ? "已接入" : "Connected now"}</h2>
          <div className="mt-3 grid gap-2">
            {connected.map((entry) => (
              <button
                key={entry.id}
                type="button"
                className="ui-list-item flex items-center gap-3 rounded-lg px-2 py-2 text-left text-sm text-slate-600 transition hover:bg-slate-50 hover:text-slate-900"
                onClick={() => setSelectedId(entry.id)}
              >
                <GameIcon name={CAPABILITY_ICON[entry.id]} className="h-4 w-4" />
                <span className="truncate">{capabilitySubtitle(entry, isZh)}</span>
              </button>
            ))}
          </div>
        </section>

        <section className="mt-6 border-t border-slate-200/80 pt-6">
          <h2 className="text-sm font-semibold text-slate-900">{isZh ? "预留" : "Reserved"}</h2>
          <div className="mt-3 grid gap-2">
            {reserved.map((entry) => (
              <button
                key={entry.id}
                type="button"
                className="ui-list-item flex items-center gap-3 rounded-lg px-2 py-2 text-left text-sm text-slate-500 transition hover:bg-slate-50 hover:text-slate-900"
                onClick={() => setSelectedId(entry.id)}
              >
                <GameIcon name={CAPABILITY_ICON[entry.id]} className="h-4 w-4" />
                <span className="truncate">{capabilitySubtitle(entry, isZh)}</span>
              </button>
            ))}
          </div>
        </section>

        <section className="mt-6 border-t border-slate-200/80 pt-6">
          <h2 className="text-sm font-semibold text-slate-900">{isZh ? "动作" : "Action"}</h2>
          <div className="mt-3 grid gap-2 text-sm text-slate-500">
            <div className="grid grid-cols-[6rem_minmax(0,1fr)] gap-3">
              <span className="text-slate-400">{isZh ? "路由" : "Route"}</span>
              <span className="truncate text-slate-900">{selected.route}</span>
            </div>
            <div className="grid grid-cols-[6rem_minmax(0,1fr)] gap-3">
              <span className="text-slate-400">{isZh ? "预设" : "Preset"}</span>
              <span className="truncate text-slate-900">{selected.workflowPreset ?? (isZh ? "无" : "None")}</span>
            </div>
            <div className="grid grid-cols-[6rem_minmax(0,1fr)] gap-3">
              <span className="text-slate-400">{isZh ? "状态" : "Status"}</span>
              <span className="truncate text-slate-900">{capabilityStatusLabel(selected, isZh)}</span>
            </div>
          </div>
        </section>
      </aside>
    </div>
  );
}
