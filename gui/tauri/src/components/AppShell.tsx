import type { ReactNode } from "react";

import { useLanguage } from "../i18n/useLanguage";
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
  const { language } = useLanguage();
  const isZh = language === "zh-CN";

  if (activeRoute.id === "home") {
    return (
      <div className="min-h-screen bg-bg text-text-primary transition-colors duration-200">
        <div className="fixed bottom-5 right-5 z-30 w-[17rem] max-w-[calc(100vw-2.5rem)]">
          <ThemeToggle mode={themeMode} resolvedTheme={resolvedTheme} onChange={onThemeChange} />
        </div>
        <main className="ui-page-enter min-h-screen">{children}</main>
      </div>
    );
  }

  if (activeRoute.id === "new-analysis") {
    return <div className="ui-page-enter min-h-screen bg-[#f4f7f8] text-text-primary transition-colors duration-200">{children}</div>;
  }

  const sidebarRoutes = routes.filter((route) => route.id !== "new-analysis");

  return (
    <div className="min-h-screen bg-[#f4f7f8] text-text-primary transition-colors duration-200">
      <div className="mx-auto grid min-h-screen w-full max-w-[1600px] grid-cols-[15rem_minmax(0,1fr)] overflow-hidden">
        <aside className="flex min-h-0 flex-col border-r border-slate-200/80 bg-[#eef6f8] px-3 py-4">
          <button
            type="button"
            className="ui-pressable flex items-center gap-3 rounded-xl px-3 py-2 text-left transition hover:bg-white/70 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ice-500"
            onClick={() => onNavigate("/")}
          >
            <JcviMeowIcon className="h-8 w-8" />
            <span>
              <span className="jcvi-brand-title block text-sm font-semibold text-slate-900">JCVI meow</span>
            </span>
          </button>

          <nav className="mt-6 grid gap-1">
            {sidebarRoutes.map((route) => (
              <button
                key={route.id}
                type="button"
                className={
                  route.id === activeRoute.id
                    ? "ui-list-item flex items-center rounded-lg bg-white px-3 py-2 text-left text-sm font-medium text-slate-900 shadow-sm"
                    : "ui-list-item flex items-center rounded-lg px-3 py-2 text-left text-sm text-slate-600 transition hover:bg-white/70 hover:text-slate-900"
                }
                onClick={() => onNavigate(route.path)}
              >
                {route.label}
              </button>
            ))}
          </nav>

          <div className="mt-auto border-t border-slate-200/80 pt-4">
            <div className="px-3 text-[11px] font-medium uppercase tracking-[0.18em] text-slate-400">
              {isZh ? "外观" : "Appearance"}
            </div>
            <div className="mt-3 px-1">
              <ThemeToggle mode={themeMode} resolvedTheme={resolvedTheme} onChange={onThemeChange} />
            </div>
          </div>
        </aside>

        <div className="flex min-w-0 flex-col bg-white">
          <header className="flex h-14 items-center justify-between border-b border-slate-200/80 bg-white px-6">
            <div className="min-w-0">
              <p className="text-sm font-semibold text-slate-900">{activeRoute.label}</p>
              <p className="truncate text-xs text-slate-500">{activeRoute.description}</p>
            </div>
            <button
              type="button"
              className="ui-pressable rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-medium text-slate-600 transition hover:bg-slate-50 hover:text-slate-900"
              onClick={() => onNavigate("/analysis/new")}
            >
              {isZh ? "打开工作台" : "Open workbench"}
            </button>
          </header>

          <main className="ui-page-enter min-h-0 flex-1 overflow-auto bg-white px-8 py-8">{children}</main>
        </div>
      </div>
    </div>
  );
}
