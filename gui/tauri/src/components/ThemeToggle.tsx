import type { ThemeMode } from "../theme/theme";

const THEME_OPTIONS: Array<{ mode: ThemeMode; label: string }> = [
  { mode: "system", label: "系统" },
  { mode: "light", label: "浅色" },
  { mode: "dark", label: "深色" },
];

interface ThemeToggleProps {
  mode: ThemeMode;
  resolvedTheme: "light" | "dark";
  onChange: (mode: ThemeMode) => void;
}

export function ThemeToggle({ mode, resolvedTheme, onChange }: ThemeToggleProps) {
  return (
    <div className="flex items-center gap-2">
      <span className="hidden text-xs font-medium text-text-tertiary lg:inline">
        {resolvedTheme === "dark" ? "Dark" : "Light"}
      </span>
      <div className="flex rounded-full border border-border bg-surface/80 p-1 shadow-card backdrop-blur">
        {THEME_OPTIONS.map((option) => (
          <button
            key={option.mode}
            type="button"
            className={
              mode === option.mode
                ? "rounded-full bg-ice-500 px-3 py-1.5 text-xs font-semibold text-white shadow-sm transition"
                : "rounded-full px-3 py-1.5 text-xs font-semibold text-text-secondary transition hover:bg-ice-50 hover:text-ice-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ice-500 dark:hover:bg-ice-900/30 dark:hover:text-ice-200"
            }
            aria-pressed={mode === option.mode}
            onClick={() => onChange(option.mode)}
          >
            {option.label}
          </button>
        ))}
      </div>
    </div>
  );
}

