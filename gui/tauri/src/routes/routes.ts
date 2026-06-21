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
    label: "桌面",
    description: "JCVI meow 桌面与能力入口",
  },
  {
    id: "projects",
    path: "/projects",
    label: "项目",
    description: "项目与最近任务",
  },
  {
    id: "new-analysis",
    path: "/analysis/new",
    label: "分析",
    description: "JCVI 任务工作台",
  },
  {
    id: "results",
    path: "/results",
    label: "结果",
    description: "运行摘要与图件入口",
  },
  {
    id: "settings",
    path: "/settings",
    label: "设置",
    description: "主题、环境诊断与契约参考",
  },
];

export function findRouteByPath(pathname: string): AppRoute {
  return APP_ROUTES.find((route) => route.path === pathname) ?? APP_ROUTES[0];
}
