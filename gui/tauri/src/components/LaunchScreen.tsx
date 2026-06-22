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
        "fixed inset-0 z-50 flex items-center justify-center bg-[#f4f7f8] px-6 transition-opacity duration-300",
        closing ? "pointer-events-none opacity-0" : "opacity-100",
      ].join(" ")}
    >
      <div className="ui-surface-enter w-full max-w-lg overflow-hidden rounded-[1.5rem] border border-slate-200 bg-white shadow-[0_18px_45px_rgba(15,23,42,0.08)]">
        <div className="border-b border-slate-200/80 px-8 py-8 text-center">
          <div className="mx-auto flex h-24 w-24 items-center justify-center rounded-[1.25rem] bg-slate-50">
            <div className="ui-floating ui-breathing flex h-16 w-16 items-center justify-center">
              <JcviMeowIcon className="h-16 w-16" />
            </div>
          </div>
          <h1 className="jcvi-brand-title mt-5 text-3xl font-semibold tracking-tight text-slate-900">JCVI meow</h1>
          <div className="mt-3 min-h-[1.75rem]">
            <p key={message} className="ui-message-enter text-sm font-medium text-slate-500">
              {message}
            </p>
          </div>
          <div className="mt-5 h-1.5 overflow-hidden rounded-full bg-slate-100">
            <div className="ui-running-progress h-full w-2/3 rounded-full bg-slate-900/85" />
          </div>
        </div>

        <div className="min-h-[8.75rem] px-8 py-6">
          {isError ? (
            <div className="ui-message-enter rounded-xl border border-rose-200 bg-rose-50 px-4 py-4 text-left text-sm text-rose-700">
              <p className="font-semibold">Startup warmup failed</p>
              <p className="mt-2 max-h-24 overflow-auto leading-6">{error}</p>
              <div className="mt-4 flex flex-wrap gap-3">
                <button
                  type="button"
                  className="ui-pressable rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-700"
                  onClick={onRetry}
                >
                  Retry
                </button>
                <button
                  type="button"
                  className="ui-pressable rounded-lg border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-600 transition hover:bg-slate-50 hover:text-slate-900"
                  onClick={onOpenDiagnostics}
                >
                  Open diagnostics
                </button>
              </div>
            </div>
          ) : slow ? (
            <div className="ui-message-enter flex items-center justify-between gap-4 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-left">
              <div>
                <p className="text-sm font-medium text-slate-700">Warmup is taking longer than usual.</p>
                <p className="mt-1 text-xs leading-5 text-slate-500">The workbench will continue loading in the background.</p>
              </div>
              <button
                type="button"
                className="ui-pressable shrink-0 rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-600 transition hover:bg-slate-50 hover:text-slate-900"
                onClick={onOpenDiagnostics}
              >
                Diagnostics
              </button>
            </div>
          ) : (
            <div className="ui-message-enter text-sm text-slate-500">Loading the workbench surface and environment context.</div>
          )}
        </div>
      </div>
    </div>
  );
}
