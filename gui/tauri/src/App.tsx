import { useEffect, useMemo, useRef, useState } from "react";

import { AppShell } from "./components/AppShell";
import { LaunchScreen } from "./components/LaunchScreen";
import { useWorkbenchStartup } from "./hooks/useWorkbenchStartup";
import Home from "./pages/Home";
import NewAnalysisPage from "./pages/NewAnalysisPage";
import PlaceholderPage from "./pages/PlaceholderPage";
import ProjectsPage from "./pages/ProjectsPage";
import ResultsPage from "./pages/ResultsPage";
import SettingsPage from "./pages/SettingsPage";
import { useHashRouter } from "./routes/useHashRouter";
import { useTheme } from "./theme/useTheme";

function isTestRuntime(): boolean {
  return typeof navigator !== "undefined" && /jsdom/i.test(navigator.userAgent);
}

function renderRoute(
  route: ReturnType<typeof useHashRouter>["route"],
  navigate: (path: string) => void,
  hash: string,
) {
  if (route.id === "home") {
    return <Home route={route} onNavigate={navigate} />;
  }
  if (route.id === "projects") {
    return <ProjectsPage route={route} onNavigate={navigate} />;
  }
  if (route.id === "new-analysis") {
    return <NewAnalysisPage route={route} onNavigate={navigate} locationHash={hash} />;
  }
  if (route.id === "results") {
    return <ResultsPage route={route} onNavigate={navigate} />;
  }
  if (route.id === "settings") {
    return <SettingsPage route={route} onNavigate={navigate} />;
  }
  return (
    <PlaceholderPage
      route={route}
      title="Unavailable surface"
      subtitle="This route is not wired yet."
      details={["Keep the current workbench flow available.", "Wire a concrete page before removing this fallback."]}
    />
  );
}

function useLaunchOverlay(startupStatus: "loading" | "ready" | "error", hintCount: number) {
  const cycleStartedAt = useRef(Date.now());
  const [showOverlay, setShowOverlay] = useState(true);
  const [slow, setSlow] = useState(false);
  const [ready, setReady] = useState(false);
  const [hintIndex, setHintIndex] = useState(0);

  useEffect(() => {
    if (startupStatus === "loading") {
      cycleStartedAt.current = Date.now();
      setShowOverlay(true);
      setSlow(false);
      setReady(false);
      setHintIndex(0);
    }

    if (startupStatus === "error") {
      setShowOverlay(true);
      setReady(false);
    }
  }, [startupStatus]);

  useEffect(() => {
    let active = true;
    const messageTimer = window.setInterval(() => {
      if (active && hintCount > 0) {
        setHintIndex((current) => (current + 1) % hintCount);
      }
    }, 2200);

    return () => {
      active = false;
      window.clearInterval(messageTimer);
    };
  }, [hintCount]);

  useEffect(() => {
    if (startupStatus !== "loading") {
      return undefined;
    }

    const slowTimer = window.setTimeout(() => {
      setSlow(true);
    }, 10000);

    return () => {
      window.clearTimeout(slowTimer);
    };
  }, [startupStatus]);

  useEffect(() => {
    if (startupStatus !== "ready") {
      return undefined;
    }

    let active = true;
    const minDuration = isTestRuntime() ? 0 : 1800;
    const fadeDuration = isTestRuntime() ? 0 : 260;

    void (async () => {
      const elapsed = Date.now() - cycleStartedAt.current;
      if (elapsed < minDuration) {
        await new Promise((resolve) => window.setTimeout(resolve, minDuration - elapsed));
      }

      if (!active) {
        return;
      }

      setReady(true);
      window.setTimeout(() => {
        if (active) {
          setShowOverlay(false);
        }
      }, fadeDuration);
    })();

    return () => {
      active = false;
    };
  }, [startupStatus]);

  return useMemo(
    () => ({
      ready,
      showOverlay,
      slow,
      hintIndex,
    }),
    [hintIndex, ready, showOverlay, slow],
  );
}

export default function App() {
  const { hash, route, routes, navigate } = useHashRouter();
  const { mode, resolvedTheme, setMode } = useTheme();
  const startup = useWorkbenchStartup();
  const overlay = useLaunchOverlay(startup.status, startup.hints.length);
  const startupError =
    startup.failed.length > 0
      ? startup.failed
          .map((key) => startup[key].error)
          .filter((value): value is string => typeof value === "string" && value.length > 0)
          .join(" ")
      : null;
  const launchMessage =
    startup.hints.length > 0
      ? startup.hints[Math.min(overlay.hintIndex, Math.max(0, startup.hints.length - 1))]
      : startup.activeHint;
  const shouldRenderShell = !overlay.showOverlay || overlay.ready;

  return (
    <>
      {shouldRenderShell ? (
        <AppShell
          activeRoute={route}
          routes={routes}
          themeMode={mode}
          resolvedTheme={resolvedTheme}
          onNavigate={navigate}
          onThemeChange={setMode}
        >
          {renderRoute(route, navigate, hash)}
        </AppShell>
      ) : null}

      {overlay.showOverlay ? (
        <LaunchScreen
          message={launchMessage}
          error={startup.status === "error" ? startupError : null}
          slow={overlay.slow}
          closing={overlay.ready}
          onRetry={startup.reload}
          onOpenDiagnostics={() => navigate(startup.diagnosticsRoute)}
        />
      ) : null}
    </>
  );
}
