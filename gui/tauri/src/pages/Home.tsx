import { useMemo } from "react";

import { JcviMeowIcon } from "../components/JcviMeowIcon";
import { listJcviCapabilities } from "../models";
import type { AppRoute } from "../routes/routes";

const CAPABILITY_LAYOUT = {
  "pairwise-synteny": { offsetX: -184, offsetY: -92, shortLabel: "Pairwise" },
  "multi-species-synteny": { offsetX: 166, offsetY: -118, shortLabel: "Multi" },
  "local-synteny": { offsetX: -206, offsetY: 54, shortLabel: "Local" },
  dotplot: { offsetX: 202, offsetY: 38, shortLabel: "Dotplot" },
  karyotype: { offsetX: -118, offsetY: 164, shortLabel: "Karyotype" },
  "ortholog-catalog": { offsetX: 132, offsetY: 166, shortLabel: "Ortholog" },
  "environment-check": { offsetX: 4, offsetY: -198, shortLabel: "Check" },
} as const;

interface HomeProps {
  route: AppRoute;
  onNavigate: (path: string) => void;
}

export default function Home({ onNavigate }: HomeProps) {
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
    <div className="relative flex min-h-[calc(100vh-4rem)] w-full items-center justify-center overflow-hidden rounded-[36px] bg-[radial-gradient(circle_at_50%_45%,rgba(186,230,253,0.58),rgba(248,250,252,0.88)_44%,rgba(255,255,255,0.96)_75%)] px-6 py-16 dark:bg-[radial-gradient(circle_at_50%_45%,rgba(14,165,233,0.18),rgba(15,23,42,0.86)_52%,rgba(2,6,23,0.96)_82%)]">
      <div className="pointer-events-none absolute left-1/2 top-1/2 h-[42rem] w-[42rem] -translate-x-1/2 -translate-y-1/2 rounded-full border border-white/70 dark:border-white/5" />
      <div className="pointer-events-none absolute left-1/2 top-1/2 h-[30rem] w-[30rem] -translate-x-1/2 -translate-y-1/2 rounded-full border border-ice-200/70 dark:border-ice-500/15" />
      <div className="pointer-events-none absolute left-1/2 top-1/2 h-[18rem] w-[18rem] -translate-x-1/2 -translate-y-1/2 rounded-full border border-dashed border-ice-200/70 dark:border-ice-500/15" />

      <div className="relative h-[38rem] w-[46rem] max-w-full">
        {capabilities.map((entry) => {
          const isConnected = entry.status === "connected";
          const tooltip = `${entry.title} / ${entry.subtitle}。${entry.description}`;

          return (
            <button
              key={entry.id}
              type="button"
              aria-label={tooltip}
              title={tooltip}
              className={[
                "group absolute left-1/2 top-1/2 flex -translate-x-1/2 -translate-y-1/2 flex-col items-center gap-2 text-center transition duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ice-500 focus-visible:ring-offset-4 focus-visible:ring-offset-bg",
                isConnected ? "cursor-pointer" : "cursor-default opacity-50",
              ].join(" ")}
              style={{
                transform: `translate(calc(-50% + ${entry.offsetX}px), calc(-50% + ${entry.offsetY}px))`,
              }}
              onClick={() => handleCapabilityClick(entry.route, entry.id, entry.status)}
            >
              <span
                className={[
                  "relative flex h-20 w-20 items-center justify-center rounded-full text-xs font-semibold shadow-lg transition duration-200",
                  isConnected
                    ? "bg-white/88 text-ice-700 shadow-ice-500/10 ring-1 ring-ice-200/80 group-hover:scale-105 group-hover:bg-white group-hover:shadow-ice-500/20 dark:bg-slate-950/72 dark:text-ice-200 dark:ring-ice-700/40"
                    : "bg-white/48 text-text-tertiary ring-1 ring-border/60 dark:bg-slate-950/42",
                ].join(" ")}
              >
                {entry.shortLabel}
                <span className="absolute -right-1 -top-1 h-3 w-3 rounded-full bg-ice-400 opacity-0 transition group-hover:opacity-100" />
              </span>
              <span className="text-xs font-semibold text-text-secondary">{entry.title}</span>
              <span className="pointer-events-none absolute left-1/2 top-full z-20 mt-3 w-64 -translate-x-1/2 rounded-2xl border border-border bg-white/92 p-3 text-left text-xs leading-5 text-text-secondary opacity-0 shadow-xl shadow-slate-900/8 backdrop-blur transition duration-150 group-hover:translate-y-1 group-hover:opacity-100 group-focus-visible:translate-y-1 group-focus-visible:opacity-100 dark:bg-slate-950/90">
                <span className="block font-semibold text-text-primary">{entry.subtitle}</span>
                <span className="mt-1 block">{entry.description}</span>
                <span className="mt-2 block text-[10px] font-semibold uppercase tracking-[0.14em] text-ice-600 dark:text-ice-300">
                  {entry.statusLabel}
                </span>
              </span>
            </button>
          );
        })}

        <button
          type="button"
          className="group absolute left-1/2 top-1/2 flex h-64 w-64 -translate-x-1/2 -translate-y-1/2 flex-col items-center justify-center rounded-full border border-white/70 bg-white/64 text-center shadow-2xl shadow-ice-500/12 backdrop-blur transition hover:bg-white/78 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ice-500 focus-visible:ring-offset-4 focus-visible:ring-offset-bg dark:border-white/10 dark:bg-slate-950/58 dark:hover:bg-slate-950/72"
          onClick={() => onNavigate("/analysis/new")}
        >
          <JcviMeowIcon className="h-32 w-32 drop-shadow-[0_24px_48px_rgba(37,99,235,0.2)] transition group-hover:scale-[1.03]" />
          <span className="mt-4 text-3xl font-semibold tracking-tight text-text-primary">JCVI喵</span>
          <span className="mt-2 text-xs font-medium text-text-tertiary">Powered by GenomeLens</span>
          <span className="sr-only">进入分析工作台</span>
        </button>
      </div>
    </div>
  );
}
