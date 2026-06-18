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
    label: "工作台",
    description: "GenomeLens 首页与主要入口",
  },
  {
    id: "projects",
    path: "/projects",
    label: "项目",
    description: "项目列表与最近任务",
  },
  {
    id: "new-analysis",
    path: "/analysis/new",
    label: "新建分析",
    description: "任务创建向导入口",
  },
  {
    id: "results",
    path: "/results",
    label: "结果",
    description: "运行摘要与图件预览",
  },
  {
    id: "settings",
    path: "/settings",
    label: "设置",
    description: "主题、路径与环境诊断",
  },
];

export function findRouteByPath(pathname: string): AppRoute {
  return APP_ROUTES.find((route) => route.path === pathname) ?? APP_ROUTES[0];
}
