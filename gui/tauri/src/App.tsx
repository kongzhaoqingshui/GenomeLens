import { AppShell } from "./components/AppShell";
import Home from "./pages/Home";
import { useHashRouter } from "./routes/useHashRouter";
import { useTheme } from "./theme/useTheme";

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
      <Home route={route} onNavigate={navigate} />
    </AppShell>
  );
}

