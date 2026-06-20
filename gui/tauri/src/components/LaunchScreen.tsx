import { JcviMeowIcon } from "./JcviMeowIcon";

interface LaunchScreenProps {
  message: string;
  error?: string | null;
  slow: boolean;
  closing: boolean;
  onRetry: () => void;
  onOpenDiagnostics: () => void;
}

export function LaunchScreen({
  message,
  error,
  slow,
  closing,
  onRetry,
  onOpenDiagnostics,
}: LaunchScreenProps) {
  const isError = typeof error === "string" && error.length > 0;

  return (
    <div
      className={[
        "fixed inset-0 z-50 flex items-center justify-center overflow-hidden bg-[radial-gradient(circle_at_50%_42%,rgb(186,230,253),rgb(248,250,252)_46%,rgb(255,255,255)_78%)] px-6 transition-opacity duration-300 dark:bg-[radial-gradient(circle_at_50%_42%,rgb(14,55,87),rgb(15,23,42)_52%,rgb(2,6,23)_86%)]",
        closing ? "pointer-events-none opacity-0" : "opacity-100",
      ].join(" ")}
    >
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute left-1/2 top-1/2 h-[30rem] w-[30rem] -translate-x-1/2 -translate-y-1/2 rounded-full border border-white/60 dark:border-white/5" />
        <div className="absolute left-1/2 top-1/2 h-[20rem] w-[20rem] -translate-x-1/2 -translate-y-1/2 rounded-full border border-ice-200/55 dark:border-ice-500/15" />
      </div>

      <div className="relative flex w-full max-w-xl flex-col items-center text-center">
        <div className="jcvi-launch-icon flex h-44 w-44 items-center justify-center">
          <JcviMeowIcon className="h-36 w-36 drop-shadow-[0_28px_56px_rgba(37,99,235,0.22)]" />
        </div>

        <h1 className="mt-5 text-3xl font-semibold tracking-tight text-text-primary">JCVI喵</h1>
        <p className="mt-4 h-7 text-sm font-medium leading-7 text-text-secondary">{message}</p>
        <p className="mt-1 text-xs text-text-tertiary">Powered by GenomeLens</p>

        {isError ? (
          <div className="mt-7 w-full max-w-md rounded-2xl border border-rose-200 bg-white/82 p-4 text-left text-sm text-rose-700 shadow-lg shadow-rose-500/5 backdrop-blur dark:border-rose-900/60 dark:bg-slate-950/72 dark:text-rose-200">
            <p className="font-semibold">启动预热失败</p>
            <p className="mt-2 leading-6">{error}</p>
            <div className="mt-4 flex flex-wrap gap-3">
              <button
                type="button"
                className="rounded-lg bg-ice-500 px-4 py-2 text-sm font-semibold text-white transition hover:bg-ice-400"
                onClick={onRetry}
              >
                重试
              </button>
              <button
                type="button"
                className="rounded-lg border border-border bg-white/70 px-4 py-2 text-sm font-semibold text-text-secondary transition hover:border-ice-200 hover:bg-ice-50 hover:text-ice-700 dark:bg-slate-900/70 dark:hover:border-ice-800 dark:hover:bg-ice-900/30 dark:hover:text-ice-200"
                onClick={onOpenDiagnostics}
              >
                查看诊断
              </button>
            </div>
          </div>
        ) : null}

        {!isError && slow ? (
          <button
            type="button"
            className="mt-7 rounded-full border border-ice-200/80 bg-white/70 px-4 py-2 text-xs font-semibold text-ice-700 shadow-sm backdrop-blur transition hover:border-ice-300 hover:bg-white dark:border-ice-800/70 dark:bg-slate-950/60 dark:text-ice-200 dark:hover:bg-ice-950/80"
            onClick={onOpenDiagnostics}
          >
            首次启动较慢，点击查看诊断
          </button>
        ) : null}
      </div>
    </div>
  );
}
