import type { ReactNode } from "react";

import type { AppRoute } from "../routes/routes";
import type { ThemeMode } from "../theme/theme";
import { JcviMeowIcon } from "./JcviMeowIcon";
import { ThemeToggle } from "./ThemeToggle";

interface AppShellProps {
  activeRoute: AppRoute;
  routes: AppRoute[];
  themeMode: ThemeMode;
  resolvedTheme: "light" | "dark";
  onNavigate: (path: string) => void;
  onThemeChange: (mode: ThemeMode) => void;
  children: ReactNode;
}

export function AppShell({
  activeRoute,
  routes,
  themeMode,
  resolvedTheme,
  onNavigate,
  onThemeChange,
  children,
}: AppShellProps) {
  if (activeRoute.id === "home") {
    return (
      <div className="min-h-screen bg-bg text-text-primary transition-colors duration-200">
        <div className="fixed right-5 top-5 z-10">
          <ThemeToggle mode={themeMode} resolvedTheme={resolvedTheme} onChange={onThemeChange} />
        </div>
        <main className="min-h-screen p-5">{children}</main>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-bg text-text-primary transition-colors duration-200">
      <div className="pointer-events-none fixed inset-0 overflow-hidden">
        <div className="absolute inset-x-0 top-0 h-72 bg-gradient-to-b from-ice-100/80 via-ice-50/40 to-transparent dark:from-ice-900/30 dark:via-ice-800/10" />
        <div className="absolute left-1/2 top-16 h-64 w-[42rem] -translate-x-1/2 rounded-full border border-ice-200/50 opacity-50 blur-3xl dark:border-ice-700/30" />
      </div>

      <div className="relative mx-auto flex min-h-screen w-full max-w-[1600px] flex-col px-6 py-5 lg:px-8">
        <header className="flex flex-wrap items-center justify-between gap-4 border-b border-border/80 pb-4">
          <button
            type="button"
            className="flex items-center gap-3 rounded-xl text-left outline-none transition focus-visible:ring-2 focus-visible:ring-ice-500 focus-visible:ring-offset-2 focus-visible:ring-offset-bg"
            onClick={() => onNavigate("/")}
          >
            <span className="flex h-11 w-11 items-center justify-center rounded-2xl bg-ice-50 text-ice-500 shadow-lg shadow-ice-500/10 ring-1 ring-ice-100 dark:bg-ice-950/60 dark:ring-ice-900/60">
              <JcviMeowIcon className="h-8 w-8" showLensText={false} />
            </span>
            <span>
              <span className="jcvi-brand-title block text-xl font-semibold tracking-tight">JCVI喵</span>
              <span className="block text-xs text-text-secondary">Comparative genomics workbench · Powered by GenomeLens</span>
            </span>
          </button>

          <nav className="hidden items-center gap-1 rounded-full border border-border bg-surface/80 p-1 shadow-card backdrop-blur lg:flex">
            {routes.map((route) => (
              <button
                key={route.id}
                type="button"
                className={
                  route.id === activeRoute.id
                    ? "rounded-full bg-ice-500 px-4 py-2 text-xs font-semibold text-white shadow-sm transition"
                    : "rounded-full px-4 py-2 text-xs font-semibold text-text-secondary transition hover:bg-ice-50 hover:text-ice-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ice-500 dark:hover:bg-ice-900/30 dark:hover:text-ice-200"
                }
                onClick={() => onNavigate(route.path)}
              >
                {route.label}
              </button>
            ))}
          </nav>

          <div className="flex items-center gap-3">
            <span className="hidden rounded-full border border-border bg-surface/80 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-text-tertiary lg:inline-flex">
              {activeRoute.label}
            </span>
            <ThemeToggle mode={themeMode} resolvedTheme={resolvedTheme} onChange={onThemeChange} />
          </div>
        </header>

        <main className="flex flex-1 py-8">{children}</main>
      </div>
    </div>
  );
}
