import type { LucideIcon } from "lucide-react";
import {
  FileBarChart,
  FlaskConical,
  FolderOpen,
  Home,
  Settings2,
} from "lucide-react";
import type { ReactNode } from "react";

import { useLanguage } from "../i18n/useLanguage";
import type { AppRoute, RouteId } from "../routes/routes";
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

const ROUTE_ICONS: Record<RouteId, LucideIcon> = {
  home: Home,
  projects: FolderOpen,
  "new-analysis": FlaskConical,
  results: FileBarChart,
  settings: Settings2,
};

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
      <div className="ui-app-frame min-h-screen transition-colors duration-200">
        <div className="fixed bottom-5 right-5 z-30 w-[17rem] max-w-[calc(100vw-2.5rem)]">
          <ThemeToggle mode={themeMode} resolvedTheme={resolvedTheme} onChange={onThemeChange} />
        </div>
        <main className="ui-page-enter min-h-screen">{children}</main>
      </div>
    );
  }

  if (activeRoute.id === "new-analysis") {
    return <div className="ui-app-frame ui-page-enter min-h-screen transition-colors duration-200">{children}</div>;
  }

  const sidebarRoutes = routes.filter((route) => route.id !== "new-analysis");

  return (
    <div className="ui-app-frame min-h-screen transition-colors duration-200">
      <div className="mx-auto grid min-h-screen w-full max-w-[1600px] grid-cols-[15rem_minmax(0,1fr)] overflow-hidden">
        <aside className="ui-shell-sidebar flex min-h-0 flex-col border-r px-3 py-4">
          <button
            type="button"
            className="ui-pressable flex items-center gap-3 rounded-xl px-3 py-2 text-left transition hover:bg-surface-raised/80 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ice-500"
            onClick={() => onNavigate("/")}
          >
            <JcviMeowIcon className="h-8 w-8" />
            <span>
              <span className="jcvi-brand-title block text-sm font-semibold text-text-primary">JCVI meow</span>
            </span>
          </button>

          <nav className="mt-6 grid gap-1">
            {sidebarRoutes.map((route) => {
              const Icon = ROUTE_ICONS[route.id];
              const isActive = route.id === activeRoute.id;
              return (
                <button
                  key={route.id}
                  type="button"
                  className={[
                    "ui-list-item group flex items-center gap-3 rounded-xl px-3 py-2.5 text-left text-sm transition",
                    isActive
                      ? "border border-border bg-surface-raised font-semibold text-text-primary shadow-card"
                      : "text-text-secondary hover:bg-surface-raised/75 hover:text-text-primary",
                  ].join(" ")}
                  onClick={() => onNavigate(route.path)}
                >
                  <span
                    className={[
                      "flex h-7 w-7 shrink-0 items-center justify-center rounded-lg transition",
                      isActive
                        ? "bg-ice-500 text-white"
                        : "bg-surface text-text-tertiary group-hover:text-text-primary",
                    ].join(" ")}
                  >
                    <Icon className="h-4 w-4" />
                  </span>
                  {route.label}
                </button>
              );
            })}
          </nav>

          <div className="mt-auto border-t border-border/90 pt-4">
            <div className="px-3 text-[11px] font-medium uppercase tracking-[0.16em] text-text-tertiary">
              {isZh ? "外观" : "Appearance"}
            </div>
            <div className="mt-3 px-1">
              <ThemeToggle mode={themeMode} resolvedTheme={resolvedTheme} onChange={onThemeChange} />
            </div>
          </div>
        </aside>

        <div className="ui-shell-main flex min-w-0 flex-col">
          <header className="flex h-14 items-center justify-between border-b px-6">
            <div className="min-w-0">
              <p className="text-sm font-semibold text-text-primary">{activeRoute.label}</p>
              <p className="truncate text-xs text-text-secondary">{activeRoute.description}</p>
            </div>
            <button
              type="button"
              className="ui-pressable inline-flex items-center gap-2 rounded-lg border border-border bg-surface px-3 py-1.5 text-xs font-medium text-text-secondary transition hover:border-ice-200 hover:bg-surface-raised hover:text-text-primary dark:hover:border-ice-800 dark:hover:bg-surface"
              onClick={() => onNavigate("/analysis/new")}
            >
              <FlaskConical className="h-3.5 w-3.5" />
              {isZh ? "打开工作台" : "Open workbench"}
            </button>
          </header>

          <main className="ui-page-enter min-h-0 flex-1 overflow-auto bg-surface-raised px-8 py-8">{children}</main>
        </div>
      </div>
    </div>
  );
}
