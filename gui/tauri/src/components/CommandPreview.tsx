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

  const statusClass =
    state.status === "ready"
      ? "bg-emerald-50 text-emerald-700"
      : state.status === "error"
        ? "bg-rose-50 text-rose-700"
        : "bg-slate-100 text-slate-600";

  return (
    <section className="border-t border-slate-200/80">
      <div className="flex items-start justify-between gap-4 px-6 py-5">
        <div className="min-w-0">
          <h2 className="text-base font-semibold text-slate-900">{title}</h2>
          <p className="mt-1 text-sm leading-6 text-slate-500">{description}</p>
          <p className="mt-2 font-mono text-xs text-slate-400">{command}</p>
        </div>
        <span className={`rounded-full px-3 py-1 text-[11px] font-semibold uppercase ${statusClass}`}>
          {isZh
            ? state.status === "ready"
              ? "就绪"
              : state.status === "error"
                ? "错误"
                : "加载中"
            : state.status}
        </span>
      </div>

      <pre className="max-h-80 overflow-auto border-t border-slate-200/80 bg-slate-50 px-6 py-5 font-mono text-xs leading-6 text-slate-600">
        {state.status === "ready"
          ? JSON.stringify(state.data, null, 2)
          : state.status === "error"
            ? state.error
            : isZh
              ? "加载中..."
              : "Loading..."}
      </pre>
    </section>
  );
}
