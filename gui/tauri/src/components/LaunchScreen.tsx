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
        "fixed inset-0 z-50 flex items-center justify-center bg-bg/94 px-6 backdrop-blur-xl transition-opacity duration-300",
        closing ? "pointer-events-none opacity-0" : "opacity-100",
      ].join(" ")}
    >
      <div className="jcvi-launch-shell relative w-full max-w-2xl overflow-hidden rounded-[28px] border border-ice-200/60 bg-surface-raised/90 p-8 shadow-2xl shadow-ice-500/10 dark:border-ice-900/60">
        <div className="pointer-events-none absolute inset-0">
          <div className="absolute left-1/2 top-0 h-48 w-48 -translate-x-1/2 rounded-full bg-ice-100/70 blur-3xl dark:bg-ice-900/30" />
          <div className="jcvi-launch-line absolute left-10 top-14 h-px w-24 bg-gradient-to-r from-transparent via-ice-300/70 to-transparent" />
          <div className="jcvi-launch-line absolute right-12 top-24 h-px w-28 bg-gradient-to-r from-transparent via-ice-300/70 to-transparent [animation-delay:180ms]" />
          <div className="jcvi-launch-line absolute bottom-20 left-1/2 h-px w-20 -translate-x-1/2 bg-gradient-to-r from-transparent via-ice-300/70 to-transparent [animation-delay:320ms]" />
        </div>

        <div className="relative flex flex-col items-center text-center">
          <div className="jcvi-launch-icon flex h-44 w-44 items-center justify-center rounded-full bg-gradient-to-b from-ice-50 to-white shadow-lg shadow-ice-500/10 dark:from-ice-950/60 dark:to-slate-950">
            <JcviMeowIcon className="h-28 w-28 text-ice-500" />
          </div>

          <p className="mt-6 text-sm font-semibold uppercase tracking-[0.3em] text-ice-600 dark:text-ice-300">
            JCVI喵
          </p>
          <h1 className="mt-3 text-3xl font-semibold tracking-tight text-text-primary">正在唤醒你的 JCVI 工作台</h1>
          <p className="mt-3 max-w-xl text-sm leading-7 text-text-secondary">{message}</p>
          <p className="mt-2 text-xs text-text-tertiary">Powered by GenomeLens</p>

          {isError ? (
            <div className="mt-6 w-full max-w-xl rounded-2xl border border-rose-200 bg-rose-50/90 p-4 text-left text-sm text-rose-700 dark:border-rose-900/60 dark:bg-rose-950/30 dark:text-rose-200">
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
                  className="rounded-lg border border-border bg-surface px-4 py-2 text-sm font-semibold text-text-secondary transition hover:border-ice-200 hover:bg-ice-50 hover:text-ice-700 dark:hover:border-ice-800 dark:hover:bg-ice-900/30 dark:hover:text-ice-200"
                  onClick={onOpenDiagnostics}
                >
                  查看诊断
                </button>
              </div>
            </div>
          ) : null}

          {!isError && slow ? (
            <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
              <span className="rounded-full bg-amber-100 px-3 py-1 text-xs font-semibold text-amber-700 dark:bg-amber-400/15 dark:text-amber-200">
                如果第一次启动稍慢，通常是在预热本地工具链
              </span>
              <button
                type="button"
                className="rounded-lg border border-border bg-surface px-3 py-2 text-xs font-semibold text-text-secondary transition hover:border-ice-200 hover:bg-ice-50 hover:text-ice-700 dark:hover:border-ice-800 dark:hover:bg-ice-900/30 dark:hover:text-ice-200"
                onClick={onOpenDiagnostics}
              >
                查看诊断
              </button>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
