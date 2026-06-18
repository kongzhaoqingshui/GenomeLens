import { useEffect, useMemo, useState } from "react";

import { resolveThemeMode, shouldUseDarkTheme, THEME_STORAGE_KEY, type ThemeMode } from "./theme";

function systemPrefersDark(): boolean {
  return window.matchMedia("(prefers-color-scheme: dark)").matches;
}

function readInitialThemeMode(): ThemeMode {
  return resolveThemeMode(window.localStorage.getItem(THEME_STORAGE_KEY));
}

function applyThemeMode(mode: ThemeMode, prefersDark: boolean): void {
  document.documentElement.dataset.themeMode = mode;
  document.documentElement.classList.toggle("dark", shouldUseDarkTheme(mode, prefersDark));
}

export function useTheme() {
  const [mode, setMode] = useState<ThemeMode>(readInitialThemeMode);
  const [prefersDark, setPrefersDark] = useState(systemPrefersDark);

  useEffect(() => {
    const media = window.matchMedia("(prefers-color-scheme: dark)");

    function handleChange(event: MediaQueryListEvent): void {
      setPrefersDark(event.matches);
    }

    media.addEventListener("change", handleChange);
    return () => media.removeEventListener("change", handleChange);
  }, []);

  useEffect(() => {
    window.localStorage.setItem(THEME_STORAGE_KEY, mode);
    applyThemeMode(mode, prefersDark);
  }, [mode, prefersDark]);

  return useMemo(
    () => ({
      mode,
      resolvedTheme: (shouldUseDarkTheme(mode, prefersDark) ? "dark" : "light") as "light" | "dark",
      setMode,
    }),
    [mode, prefersDark],
  );
}
