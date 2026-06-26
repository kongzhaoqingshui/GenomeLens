const SECONDARY_BUTTON_CLASS =
  "ui-pressable inline-flex items-center gap-1.5 rounded-xl border border-border bg-surface px-3 py-2 text-xs font-semibold text-text-secondary transition hover:border-ice-200 hover:bg-ice-50 hover:text-ice-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ice-500 dark:hover:border-ice-800 dark:hover:bg-ice-900/30 dark:hover:text-ice-200 disabled:cursor-not-allowed disabled:opacity-45";
const LABEL_CLASS = "text-xs font-semibold uppercase tracking-[0.14em] text-text-tertiary";

interface PathFieldProps {
  label: string;
  value: string;
  onChange: (path: string) => void;
  pickFile: (onSelect: (path: string) => void) => Promise<void>;
}

export function PathField({ label, value, onChange, pickFile }: PathFieldProps) {
  return (
    <label>
      <span className={LABEL_CLASS}>{label}</span>
      <div className="mt-2 flex gap-2">
        <input
          className="min-w-0 flex-1 rounded-lg border border-border bg-bg px-3 py-2 text-sm text-text-primary shadow-card outline-none transition focus:border-ice-400 focus:ring-2 focus:ring-ice-200 dark:focus:ring-ice-900/60"
          value={value}
          onChange={(event) => onChange(event.target.value)}
        />
        <button type="button" className={SECONDARY_BUTTON_CLASS} onClick={() => void pickFile(onChange)}>
          Browse
        </button>
      </div>
    </label>
  );
}
