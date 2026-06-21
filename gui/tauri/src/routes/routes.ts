export type RouteId = "home" | "projects" | "new-analysis" | "results" | "settings";

export interface AppRoute {
  id: RouteId;
  path: string;
  label: string;
  description: string;
}

export const APP_ROUTES: AppRoute[] = [
  {
    id: "home",
    path: "/",
    label: "Home",
    description: "Desktop overview and capability entry points.",
  },
  {
    id: "projects",
    path: "/projects",
    label: "Projects",
    description: "Project history and recent tasks.",
  },
  {
    id: "new-analysis",
    path: "/analysis/new",
    label: "Analysis",
    description: "JCVI task workbench and run flow.",
  },
  {
    id: "results",
    path: "/results",
    label: "Results",
    description: "Run summaries and figure entry points.",
  },
  {
    id: "settings",
    path: "/settings",
    label: "Settings",
    description: "Theme, environment checks, and contract references.",
  },
];

export function findRouteByPath(pathname: string): AppRoute {
  return APP_ROUTES.find((route) => route.path === pathname) ?? APP_ROUTES[0];
}
