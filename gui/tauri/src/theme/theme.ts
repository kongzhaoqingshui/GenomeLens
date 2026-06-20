export type ThemeMode = "light" | "dark" | "system";

export const THEME_STORAGE_KEY = "genomelens.theme";

export function isThemeMode(value: string | null): value is ThemeMode {
  return value === "light" || value === "dark" || value === "system";
}

export function resolveThemeMode(value: string | null): ThemeMode {
  return isThemeMode(value) ? value : "system";
}

export function shouldUseDarkTheme(mode: ThemeMode, prefersDark: boolean): boolean {
  return mode === "dark" || (mode === "system" && prefersDark);
}

