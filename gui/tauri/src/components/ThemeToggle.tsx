import type { ThemeMode } from "../theme/theme";

const THEME_OPTIONS: Array<{ mode: ThemeMode; label: string }> = [
  { mode: "system", label: "System" },
  { mode: "light", label: "Light" },
  { mode: "dark", label: "Dark" },
];

interface ThemeToggleProps {
  mode: ThemeMode;
  resolvedTheme: "light" | "dark";
  onChange: (mode: ThemeMode) => void;
}

export function ThemeToggle({ mode, resolvedTheme, onChange }: ThemeToggleProps) {
  return (
    <div className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-2 py-2">
      <span className="hidden text-[11px] font-medium uppercase tracking-[0.16em] text-slate-400 lg:inline">
        {resolvedTheme}
      </span>
      <div className="flex items-center gap-1 rounded-lg bg-slate-100 p-1">
        {THEME_OPTIONS.map((option) => (
          <button
            key={option.mode}
            type="button"
            className={
              mode === option.mode
                ? "rounded-md bg-white px-3 py-1.5 text-xs font-semibold text-slate-900 shadow-sm transition"
                : "rounded-md px-3 py-1.5 text-xs font-medium text-slate-500 transition hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ice-500"
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
