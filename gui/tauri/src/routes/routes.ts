export type RouteId = "home" | "projects" | "new-analysis" | "results" | "settings";

export interface AppRoute {
  id: RouteId;
  path: string;
  label: string;
  description: string;
}

type RouteLanguage = "zh-CN" | "en";

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

export function localizeRoute(route: AppRoute, language: RouteLanguage): AppRoute {
  if (language === "en") {
    return route;
  }

  switch (route.id) {
    case "home":
      return { ...route, label: "首页", description: "桌面总览与能力入口。" };
    case "projects":
      return { ...route, label: "项目", description: "工作区项目与最近任务。" };
    case "new-analysis":
      return { ...route, label: "工作台", description: "JCVI 任务工作台与运行流程。" };
    case "results":
      return { ...route, label: "结果", description: "运行摘要与图件入口。" };
    case "settings":
      return { ...route, label: "设置", description: "主题、语言、环境诊断与契约参考。" };
    default:
      return route;
  }
}

export function localizeRoutes(routes: AppRoute[], language: RouteLanguage): AppRoute[] {
  return routes.map((route) => localizeRoute(route, language));
}
