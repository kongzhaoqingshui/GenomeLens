import { useEffect, useState } from "react";

import type { JsonObject } from "../services/analysis";

type CommandState =
  | { status: "loading"; data?: undefined; error?: undefined }
  | { status: "ready"; data: JsonObject; error?: undefined }
  | { status: "error"; data?: undefined; error: string };

interface CommandPreviewProps {
  title: string;
  command: string;
  description: string;
  load: () => Promise<JsonObject>;
}

export function CommandPreview({ title, command, description, load }: CommandPreviewProps) {
  const [state, setState] = useState<CommandState>({ status: "loading" });

  useEffect(() => {
    let cancelled = false;

    setState({ status: "loading" });
    void load()
      .then((data) => {
        if (!cancelled) {
          setState({ status: "ready", data });
        }
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setState({ status: "error", error: error instanceof Error ? error.message : String(error) });
        }
      });

    return () => {
      cancelled = true;
    };
  }, [load]);

  return (
    <section className="rounded-2xl border border-border bg-surface/80 p-5 shadow-card">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-text-primary">{title}</h2>
          <p className="mt-1 text-sm leading-6 text-text-secondary">{description}</p>
          <p className="mt-2 font-mono text-xs text-text-tertiary">{command}</p>
        </div>
        <span
          className={
            state.status === "ready"
              ? "rounded-full bg-emerald-100 px-3 py-1 text-[11px] font-semibold text-emerald-700 dark:bg-emerald-400/15 dark:text-emerald-200"
              : "rounded-full bg-ice-100 px-3 py-1 text-[11px] font-semibold text-ice-700 dark:bg-ice-900/40 dark:text-ice-200"
          }
        >
          {state.status === "ready" ? "READY" : state.status === "error" ? "ERROR" : "LOADING"}
        </span>
      </div>

      <pre className="mt-4 max-h-56 overflow-auto rounded-xl border border-border bg-bg p-4 font-mono text-xs leading-6 text-text-secondary">
        {state.status === "ready"
          ? JSON.stringify(state.data, null, 2)
          : state.status === "error"
            ? state.error
            : "Loading..."}
      </pre>
    </section>
  );
}

