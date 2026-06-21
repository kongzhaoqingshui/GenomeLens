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
      <div className="w-full max-w-lg overflow-hidden rounded-[1.5rem] border border-slate-200 bg-white shadow-[0_18px_45px_rgba(15,23,42,0.08)]">
        <div className="border-b border-slate-200/80 px-8 py-8 text-center">
          <div className="mx-auto flex h-24 w-24 items-center justify-center rounded-[1.25rem] bg-slate-50">
            <JcviMeowIcon className="h-16 w-16" />
          </div>
          <h1 className="jcvi-brand-title mt-5 text-3xl font-semibold tracking-tight text-slate-900">JCVI meow</h1>
          <p className="mt-3 text-sm font-medium text-slate-500">{message}</p>
        </div>

        <div className="px-8 py-6">
          {isError ? (
            <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-4 text-left text-sm text-rose-700">
              <p className="font-semibold">Startup warmup failed</p>
              <p className="mt-2 max-h-24 overflow-auto leading-6">{error}</p>
              <div className="mt-4 flex flex-wrap gap-3">
                <button
                  type="button"
                  className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-700"
                  onClick={onRetry}
                >
                  Retry
                </button>
                <button
                  type="button"
                  className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-600 transition hover:bg-slate-50 hover:text-slate-900"
                  onClick={onOpenDiagnostics}
                >
                  Open diagnostics
                </button>
              </div>
            </div>
          ) : slow ? (
            <button
              type="button"
              className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-600 transition hover:bg-slate-50 hover:text-slate-900"
              onClick={onOpenDiagnostics}
            >
              First launch can take longer. Open diagnostics
            </button>
          ) : (
            <div className="text-sm text-slate-500">Loading the workbench surface and environment context.</div>
          )}
        </div>
      </div>
    </div>
  );
}
