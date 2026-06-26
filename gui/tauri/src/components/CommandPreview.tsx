import { Check, Copy, Terminal } from "lucide-react";
import { useEffect, useState } from "react";

import { useLanguage } from "../i18n/useLanguage";

type CommandState =
  | { status: "loading"; data?: undefined; error?: undefined }
  | { status: "ready"; data: unknown; error?: undefined }
  | { status: "error"; data?: undefined; error: string };

interface CommandPreviewProps<TData> {
  title: string;
  command: string;
  description: string;
  load: () => Promise<TData>;
}

export function CommandPreview<TData>({ title, command, description, load }: CommandPreviewProps<TData>) {
  const [state, setState] = useState<CommandState>({ status: "loading" });
  const [copied, setCopied] = useState(false);
  const { language } = useLanguage();
  const isZh = language === "zh-CN";

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

  const statusTone = state.status === "ready" ? "success" : state.status === "error" ? "error" : "default";
  const statusLabel = isZh
    ? state.status === "ready"
      ? "就绪"
      : state.status === "error"
        ? "错误"
        : "加载中"
    : state.status;

  const rawText = state.status === "ready" ? JSON.stringify(state.data, null, 2) : state.status === "error" ? state.error : isZh ? "加载中..." : "Loading...";

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(rawText);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // ignore
    }
  };

  return (
    <section className="overflow-hidden rounded-xl border border-border bg-surface">
      <div className="flex items-start justify-between gap-4 border-b border-border/90 px-4 py-4">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <Terminal className="h-4 w-4 text-text-tertiary" />
            <h2 className="text-sm font-semibold text-text-primary">{title}</h2>
          </div>
          <p className="mt-1 text-xs leading-5 text-text-secondary">{description}</p>
          <p className="mt-1 font-mono text-[11px] text-text-tertiary">{command}</p>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <span
            className={[
              "rounded-full px-2.5 py-1 text-[11px] font-semibold uppercase",
              statusTone === "success"
                ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-200"
                : statusTone === "error"
                  ? "bg-rose-50 text-rose-700 dark:bg-rose-950/30 dark:text-rose-200"
                  : "bg-surface text-text-secondary",
            ].join(" ")}
          >
            {statusLabel}
          </span>
          <button
            type="button"
            className="ui-icon-button"
            title={isZh ? "复制 JSON" : "Copy JSON"}
            disabled={state.status === "loading"}
            onClick={() => void handleCopy()}
          >
            {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
            {copied ? (isZh ? "已复制" : "Copied") : isZh ? "复制" : "Copy"}
          </button>
        </div>
      </div>

      <pre className="ui-terminal max-h-80 overflow-auto p-4 text-xs">{rawText}</pre>
    </section>
  );
}
