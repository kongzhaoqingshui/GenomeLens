import { useCallback, useEffect, useMemo, useState } from "react";

import { APP_ROUTES, findRouteByPath, type AppRoute } from "./routes";

function normalizeHash(hash: string): string {
  const value = hash.replace(/^#/, "");
  const pathname = value.split("?")[0] ?? "/";
  return pathname.startsWith("/") ? pathname : "/";
}

function readCurrentRoute(): AppRoute {
  return findRouteByPath(normalizeHash(window.location.hash));
}

export function useHashRouter() {
  const [route, setRoute] = useState<AppRoute>(readCurrentRoute);
  const [hash, setHash] = useState(window.location.hash || "#/");

  useEffect(() => {
    function handleHashChange(): void {
      setHash(window.location.hash || "#/");
      setRoute(readCurrentRoute());
    }

    window.addEventListener("hashchange", handleHashChange);
    return () => window.removeEventListener("hashchange", handleHashChange);
  }, []);

  const navigate = useCallback((path: string) => {
    window.location.hash = path;
    setHash(`#${path}`);
    setRoute(findRouteByPath(normalizeHash(path)));
  }, []);

  return useMemo(
    () => ({
      hash,
      route,
      routes: APP_ROUTES,
      navigate,
    }),
    [hash, navigate, route],
  );
}

