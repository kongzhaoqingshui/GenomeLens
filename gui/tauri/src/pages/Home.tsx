import { useMemo, useState } from "react";

import { GameIcon, type GameIconName } from "../components/GameIcon";
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

function actionLabel(entry: JcviCapabilityEntry): string {
  if (entry.route === "/settings") {
    return "Open diagnostics";
  }
  return entry.status === "connected" ? "Open workbench" : "Preview capability";
}

export default function Home({ onNavigate }: HomeProps) {
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
    <div className="ui-page-enter grid h-screen w-full grid-cols-[18rem_minmax(0,1fr)_20rem] overflow-hidden bg-white">
      <aside className="flex min-h-0 flex-col border-r border-slate-200/80 bg-[#eef6f8] px-3 py-4">
        <div className="flex items-center gap-3 rounded-xl px-3 py-2">
          <JcviMeowIcon className="h-9 w-9" />
          <span>
            <span className="jcvi-brand-title block text-sm font-semibold text-slate-900">JCVI meow</span>
            <span className="block text-xs text-slate-500">Desktop workbench</span>
          </span>
        </div>

        <button
          type="button"
          className="ui-pressable mt-4 rounded-lg bg-slate-900 px-3 py-2 text-left text-sm font-semibold text-white transition hover:bg-slate-700"
          onClick={() => openCapability(selected)}
        >
          {actionLabel(selected)}
        </button>

        <div className="mt-6 px-3 text-[11px] font-medium uppercase tracking-[0.18em] text-slate-400">Capabilities</div>
        <div className="mt-2 min-h-0 flex-1 overflow-auto">
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
                <span className="block truncate text-sm font-medium text-slate-900">{entry.subtitle}</span>
                <span className="block truncate text-xs text-slate-400">{entry.statusLabel}</span>
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
            Settings and diagnostics
          </button>
        </div>
      </aside>

      <main className="flex min-w-0 flex-col bg-white">
        <header className="flex h-16 items-center justify-between border-b border-slate-200/80 px-8">
          <div>
            <p className="text-xs font-medium uppercase tracking-[0.18em] text-slate-400">Home</p>
            <h1 className="mt-1 text-base font-semibold text-slate-900">{selected.subtitle}</h1>
          </div>
          <span
            className={
              selected.status === "connected"
                ? "rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700"
                : "rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600"
            }
          >
            {selected.statusLabel}
          </span>
        </header>

        <div className="min-h-0 flex-1 overflow-auto px-10 py-8">
          <div className="ui-surface-enter mx-auto max-w-5xl">
            <div className="flex items-start gap-5">
              <div className="flex h-16 w-16 items-center justify-center rounded-2xl border border-slate-200 bg-slate-50">
                <GameIcon name={CAPABILITY_ICON[selected.id]} className="h-7 w-7" />
              </div>
              <div className="min-w-0">
                <h2 className="text-3xl font-semibold tracking-tight text-slate-900">{selected.subtitle}</h2>
                <p className="mt-3 max-w-3xl text-sm leading-7 text-slate-500">{selected.description}</p>
              </div>
            </div>

            <div className="mt-8 grid gap-6 xl:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)]">
              <section>
                <div className="border-b border-slate-200/80 pb-3">
                  <h3 className="text-sm font-semibold text-slate-900">Current surface</h3>
                  <p className="mt-1 text-sm text-slate-500">This is where the selected capability opens inside the workbench.</p>
                </div>
                <div className="divide-y divide-slate-200/80 border-b border-slate-200/80">
                  <div className="grid grid-cols-[11rem_minmax(0,1fr)] gap-4 py-4 text-sm">
                    <span className="text-slate-400">Route</span>
                    <span className="font-medium text-slate-900">{selected.route}</span>
                  </div>
                  <div className="grid grid-cols-[11rem_minmax(0,1fr)] gap-4 py-4 text-sm">
                    <span className="text-slate-400">Workflow preset</span>
                    <span className="font-medium text-slate-900">{selected.workflowPreset ?? "None"}</span>
                  </div>
                  <div className="grid grid-cols-[11rem_minmax(0,1fr)] gap-4 py-4 text-sm">
                    <span className="text-slate-400">Primary action</span>
                    <span className="font-medium text-slate-900">{actionLabel(selected)}</span>
                  </div>
                </div>
              </section>

              <section>
                <div className="border-b border-slate-200/80 pb-3">
                  <h3 className="text-sm font-semibold text-slate-900">What to expect</h3>
                  <p className="mt-1 text-sm text-slate-500">Keep the run flow predictable: configure, run, inspect logs, read summary.</p>
                </div>
                <div className="divide-y divide-slate-200/80 border-b border-slate-200/80">
                  {[
                    "Use the workbench to prepare one task at a time or queue multiple tasks.",
                    "Open diagnostics whenever a local toolchain issue blocks execution.",
                    "Reserved capabilities stay visible, but they do not replace the current run flow.",
                  ].map((detail) => (
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
              Settings
            </button>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm text-slate-500">
                {selected.subtitle} - {selected.statusLabel} - {selected.route === "/analysis/new" ? "Ready for the workbench" : "Opens diagnostics"}
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
              {actionLabel(selected)}
            </button>
          </div>
        </div>
      </main>

      <aside className="min-h-0 overflow-auto border-l border-slate-200/80 bg-white px-5 py-6">
        <section>
          <h2 className="text-sm font-semibold text-slate-900">Connected now</h2>
          <div className="mt-3 grid gap-2">
            {connected.map((entry) => (
              <button
                key={entry.id}
                type="button"
                className="ui-list-item flex items-center gap-3 rounded-lg px-2 py-2 text-left text-sm text-slate-600 transition hover:bg-slate-50 hover:text-slate-900"
                onClick={() => setSelectedId(entry.id)}
              >
                <GameIcon name={CAPABILITY_ICON[entry.id]} className="h-4 w-4" />
                <span className="truncate">{entry.subtitle}</span>
              </button>
            ))}
          </div>
        </section>

        <section className="mt-6 border-t border-slate-200/80 pt-6">
          <h2 className="text-sm font-semibold text-slate-900">Reserved</h2>
          <div className="mt-3 grid gap-2">
            {reserved.map((entry) => (
              <button
                key={entry.id}
                type="button"
                className="ui-list-item flex items-center gap-3 rounded-lg px-2 py-2 text-left text-sm text-slate-500 transition hover:bg-slate-50 hover:text-slate-900"
                onClick={() => setSelectedId(entry.id)}
              >
                <GameIcon name={CAPABILITY_ICON[entry.id]} className="h-4 w-4" />
                <span className="truncate">{entry.subtitle}</span>
              </button>
            ))}
          </div>
        </section>

        <section className="mt-6 border-t border-slate-200/80 pt-6">
          <h2 className="text-sm font-semibold text-slate-900">Action</h2>
          <div className="mt-3 grid gap-2 text-sm text-slate-500">
            <div className="grid grid-cols-[6rem_minmax(0,1fr)] gap-3">
              <span className="text-slate-400">Route</span>
              <span className="truncate text-slate-900">{selected.route}</span>
            </div>
            <div className="grid grid-cols-[6rem_minmax(0,1fr)] gap-3">
              <span className="text-slate-400">Preset</span>
              <span className="truncate text-slate-900">{selected.workflowPreset ?? "None"}</span>
            </div>
            <div className="grid grid-cols-[6rem_minmax(0,1fr)] gap-3">
              <span className="text-slate-400">Status</span>
              <span className="truncate text-slate-900">{selected.statusLabel}</span>
            </div>
          </div>
        </section>
      </aside>
    </div>
  );
}
