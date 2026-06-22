import { useLanguage } from "../i18n/useLanguage";
import type { ThemeMode } from "../theme/theme";

interface ThemeToggleProps {
  mode: ThemeMode;
  resolvedTheme: "light" | "dark";
  onChange: (mode: ThemeMode) => void;
}

export function ThemeToggle({ mode, resolvedTheme, onChange }: ThemeToggleProps) {
  const { language } = useLanguage();
  const isZh = language === "zh-CN";
  const options: Array<{ mode: ThemeMode; label: string }> = [
    { mode: "system", label: isZh ? "跟随系统" : "System" },
    { mode: "light", label: isZh ? "浅色" : "Light" },
    { mode: "dark", label: isZh ? "深色" : "Dark" },
  ];

  return (
    <div
      className="w-full min-w-0 rounded-lg border border-border bg-surface-raised/95 p-1 shadow-card backdrop-blur"
      aria-label={isZh ? `颜色模式：${resolvedTheme === "dark" ? "深色" : "浅色"}` : `Color mode: ${resolvedTheme}`}
    >
      <div className="grid min-w-0 grid-cols-3 gap-1 rounded-lg bg-surface p-1">
        {options.map((option) => (
          <button
            key={option.mode}
            type="button"
            className={
              mode === option.mode
                ? "ui-pressable min-w-0 rounded-md border border-border bg-surface-raised px-2 py-1.5 text-xs font-semibold text-text-primary shadow-card transition"
                : "ui-pressable min-w-0 rounded-md px-2 py-1.5 text-xs font-medium text-text-secondary transition hover:bg-surface-raised/70 hover:text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ice-500"
            }
            aria-pressed={mode === option.mode}
            onClick={() => onChange(option.mode)}
          >
            <span className="block truncate">{option.label}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
