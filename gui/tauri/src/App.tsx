import { AppShell } from "./components/AppShell";
import Home from "./pages/Home";
import NewAnalysisPage from "./pages/NewAnalysisPage";
import PlaceholderPage from "./pages/PlaceholderPage";
import SettingsPage from "./pages/SettingsPage";
import { useHashRouter } from "./routes/useHashRouter";
import { useTheme } from "./theme/useTheme";

function renderRoute(route: ReturnType<typeof useHashRouter>["route"], navigate: (path: string) => void) {
  if (route.id === "home") {
    return <Home route={route} onNavigate={navigate} />;
  }
  if (route.id === "new-analysis") {
    return <NewAnalysisPage route={route} />;
  }
  if (route.id === "settings") {
    return <SettingsPage route={route} />;
  }
  if (route.id === "projects") {
    return (
      <PlaceholderPage
        route={route}
        title="项目列表"
        subtitle="项目浏览、创建和最近任务入口将在 Phase 1 接入 A 的项目持久化命令。"
        details={["最近项目列表", "创建项目弹窗", "工作区路径选择"]}
      />
    );
  }
  return (
    <PlaceholderPage
      route={route}
      title="结果与图件预览"
      subtitle="结果摘要、文件树和图件预览将在 Phase 3 接入 summary 与 artifact 读取命令。"
      details={["运行摘要卡片", "结果文件树", "图件网格与放大预览"]}
    />
  );
}

export default function App() {
  const { route, routes, navigate } = useHashRouter();
  const { mode, resolvedTheme, setMode } = useTheme();

  return (
    <AppShell
      activeRoute={route}
      routes={routes}
      themeMode={mode}
      resolvedTheme={resolvedTheme}
      onNavigate={navigate}
      onThemeChange={setMode}
    >
      {renderRoute(route, navigate)}
    </AppShell>
  );
}

