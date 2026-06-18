import { useCallback, useEffect, useMemo, useState } from "react";

import { APP_ROUTES, findRouteByPath, type AppRoute } from "./routes";

function normalizeHash(hash: string): string {
  const value = hash.replace(/^#/, "");
  return value.startsWith("/") ? value : "/";
}

function readCurrentRoute(): AppRoute {
  return findRouteByPath(normalizeHash(window.location.hash));
}

export function useHashRouter() {
  const [route, setRoute] = useState<AppRoute>(readCurrentRoute);

  useEffect(() => {
    function handleHashChange(): void {
      setRoute(readCurrentRoute());
    }

    window.addEventListener("hashchange", handleHashChange);
    return () => window.removeEventListener("hashchange", handleHashChange);
  }, []);

  const navigate = useCallback((path: string) => {
    window.location.hash = path;
    setRoute(findRouteByPath(path));
  }, []);

  return useMemo(
    () => ({
      route,
      routes: APP_ROUTES,
      navigate,
    }),
    [navigate, route],
  );
}

