import { useLanguage } from "../i18n/useLanguage";
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
  const { language } = useLanguage();
  const isZh = language === "zh-CN";
  const isError = typeof error === "string" && error.length > 0;

  return (
    <div
      className={[
        "ui-app-frame fixed inset-0 z-50 flex items-center justify-center px-6 transition-opacity duration-300",
        closing ? "pointer-events-none opacity-0" : "opacity-100",
      ].join(" ")}
    >
      <div className="ui-surface-enter w-full max-w-lg overflow-hidden rounded-[1.35rem] border border-border bg-surface-raised shadow-[0_18px_45px_rgba(15,23,42,0.08)] dark:shadow-[0_18px_45px_rgba(2,6,23,0.45)]">
        <div className="border-b border-border/90 px-8 py-8 text-center">
          <div className="mx-auto flex h-24 w-24 items-center justify-center rounded-[1.25rem] bg-surface">
            <div className="ui-floating ui-breathing flex h-16 w-16 items-center justify-center">
              <JcviMeowIcon className="h-16 w-16" />
            </div>
          </div>
          <h1 className="jcvi-brand-title mt-5 text-[1.85rem] font-semibold tracking-tight text-text-primary">JCVI meow</h1>
          <div className="mt-3 min-h-[1.75rem]">
            <p key={message} className="ui-message-enter text-sm font-medium text-text-secondary">
              {message}
            </p>
          </div>
          <div className="mt-5 h-1.5 overflow-hidden rounded-full bg-surface">
            <div className="ui-running-progress h-full w-2/3 rounded-full bg-ice-500" />
          </div>
        </div>

        <div className="min-h-[8.75rem] px-8 py-6">
          {isError ? (
            <div className="ui-message-enter rounded-xl border border-rose-200 bg-rose-50 px-4 py-4 text-left text-sm text-rose-700 dark:border-rose-900/40 dark:bg-rose-950/20 dark:text-rose-200">
              <p className="font-semibold">{isZh ? "启动预热失败" : "Startup warmup failed"}</p>
              <p className="mt-2 max-h-24 overflow-auto leading-6">{error}</p>
              <div className="mt-4 flex flex-wrap gap-3">
                <button
                  type="button"
                  className="ui-pressable rounded-lg bg-ice-500 px-4 py-2 text-sm font-semibold text-white transition hover:bg-ice-400"
                  onClick={onRetry}
                >
                  {isZh ? "重试" : "Retry"}
                </button>
                <button
                  type="button"
                  className="ui-pressable rounded-lg border border-border bg-surface px-4 py-2 text-sm font-semibold text-text-secondary transition hover:bg-surface-raised hover:text-text-primary"
                  onClick={onOpenDiagnostics}
                >
                  {isZh ? "打开诊断" : "Open diagnostics"}
                </button>
              </div>
            </div>
          ) : slow ? (
            <div className="ui-message-enter ui-muted-strip flex items-center justify-between gap-4 rounded-xl border px-4 py-3 text-left">
              <div>
                <p className="text-sm font-medium text-text-primary">{isZh ? "启动时间比平时更久一些。" : "Warmup is taking longer than usual."}</p>
                <p className="mt-1 text-xs leading-5 text-text-secondary">
                  {isZh ? "工作台会继续在后台加载。" : "The workbench will continue loading in the background."}
                </p>
              </div>
              <button
                type="button"
                className="ui-pressable shrink-0 rounded-lg border border-border bg-surface-raised px-4 py-2 text-sm font-medium text-text-secondary transition hover:bg-surface hover:text-text-primary"
                onClick={onOpenDiagnostics}
              >
                {isZh ? "诊断" : "Diagnostics"}
              </button>
            </div>
          ) : (
            <div className="ui-message-enter text-sm text-text-secondary">
              {isZh ? "正在加载工作台界面与环境上下文。" : "Loading the workbench surface and environment context."}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
