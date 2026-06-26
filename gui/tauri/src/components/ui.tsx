import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

interface CardProps {
  children: ReactNode;
  className?: string;
  hover?: boolean;
  padded?: boolean;
}

export function Card({ children, className = "", hover = true, padded = true }: CardProps) {
  return (
    <div
      className={[
        "ui-card",
        hover ? "" : "hover:transform-none hover:shadow-card",
        padded ? "p-5" : "",
        className,
      ].join(" ")}
    >
      {children}
    </div>
  );
}

interface BadgeProps {
  children: ReactNode;
  tone?: "default" | "success" | "warning" | "error" | "info" | "active";
  dot?: boolean;
  pulse?: boolean;
}

const BADGE_TONES: Record<NonNullable<BadgeProps["tone"]>, string> = {
  default: "bg-surface text-text-secondary",
  success: "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-200",
  warning: "bg-amber-50 text-amber-700 dark:bg-amber-950/30 dark:text-amber-200",
  error: "bg-rose-50 text-rose-700 dark:bg-rose-950/30 dark:text-rose-200",
  info: "bg-sky-50 text-sky-700 dark:bg-sky-950/30 dark:text-sky-200",
  active: "bg-ice-50 text-ice-700 dark:bg-ice-900/30 dark:text-ice-200",
};

const DOT_TONES: Record<NonNullable<BadgeProps["tone"]>, string> = {
  default: "bg-text-tertiary",
  success: "bg-emerald-500",
  warning: "bg-amber-500",
  error: "bg-rose-500",
  info: "bg-sky-500",
  active: "bg-ice-500",
};

export function Badge({ children, tone = "default", dot = false, pulse = false }: BadgeProps) {
  return (
    <span className={`ui-badge ${BADGE_TONES[tone]}`}>
      {dot ? <span className={`ui-status-dot ${pulse ? "live" : ""} ${DOT_TONES[tone]}`} /> : null}
      {children}
    </span>
  );
}

interface IconButtonProps {
  icon: LucideIcon;
  label?: string;
  onClick?: () => void;
  disabled?: boolean;
  title?: string;
  variant?: "default" | "primary" | "ghost";
  className?: string;
}

export function IconButton({
  icon: Icon,
  label,
  onClick,
  disabled,
  title,
  variant = "default",
  className = "",
}: IconButtonProps) {
  const variantClass =
    variant === "primary"
      ? "border-ice-500 bg-ice-500 text-white hover:bg-ice-400 hover:border-ice-400"
      : variant === "ghost"
        ? "border-transparent bg-transparent hover:bg-surface"
        : "";

  return (
    <button
      type="button"
      className={["ui-icon-button", variantClass, className].join(" ")}
      disabled={disabled}
      title={title}
      onClick={onClick}
    >
      <Icon className="h-4 w-4" />
      {label ? <span>{label}</span> : null}
    </button>
  );
}

interface EmptyStateProps {
  icon?: LucideIcon;
  title: string;
  description?: string;
  action?: ReactNode;
}

export function EmptyState({ icon: Icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="ui-empty-state">
      {Icon ? <Icon className="h-8 w-8 text-text-tertiary" /> : null}
      <p className="text-sm font-semibold text-text-primary">{title}</p>
      {description ? <p className="max-w-xs text-xs leading-5 text-text-secondary">{description}</p> : null}
      {action ? <div className="mt-1">{action}</div> : null}
    </div>
  );
}

interface StatCardProps {
  label: string;
  value: ReactNode;
  tone?: BadgeProps["tone"];
  icon?: LucideIcon;
}

export function StatCard({ label, value, tone = "default", icon: Icon }: StatCardProps) {
  return (
    <Card className="flex items-center justify-between gap-3" hover>
      <div>
        <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-text-tertiary">{label}</p>
        <p className="mt-1 text-xl font-semibold text-text-primary">{value}</p>
      </div>
      {Icon ? (
        <span
          className={[
            "flex h-9 w-9 shrink-0 items-center justify-center rounded-xl",
            tone === "success"
              ? "bg-emerald-50 text-emerald-600 dark:bg-emerald-950/30 dark:text-emerald-200"
              : tone === "warning"
                ? "bg-amber-50 text-amber-600 dark:bg-amber-950/30 dark:text-amber-200"
                : tone === "error"
                  ? "bg-rose-50 text-rose-600 dark:bg-rose-950/30 dark:text-rose-200"
                  : tone === "info"
                    ? "bg-sky-50 text-sky-600 dark:bg-sky-950/30 dark:text-sky-200"
                    : "bg-ice-50 text-ice-600 dark:bg-ice-900/30 dark:text-ice-200",
          ].join(" ")}
        >
          <Icon className="h-5 w-5" />
        </span>
      ) : null}
    </Card>
  );
}

interface QuickActionProps {
  icon: LucideIcon;
  label: string;
  description?: string;
  onClick?: () => void;
  disabled?: boolean;
}

export function QuickAction({ icon: Icon, label, description, onClick, disabled }: QuickActionProps) {
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onClick}
      className="ui-card flex w-full items-center gap-3 p-3 text-left disabled:cursor-not-allowed disabled:opacity-50"
    >
      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-ice-50 text-ice-600 dark:bg-ice-900/30 dark:text-ice-200">
        <Icon className="h-5 w-5" />
      </span>
      <div className="min-w-0">
        <p className="text-sm font-semibold text-text-primary">{label}</p>
        {description ? <p className="truncate text-xs text-text-secondary">{description}</p> : null}
      </div>
    </button>
  );
}

interface SectionHeaderProps {
  title: string;
  subtitle?: string;
  action?: ReactNode;
}

export function SectionHeader({ title, subtitle, action }: SectionHeaderProps) {
  return (
    <div className="ui-section-header">
      <div>
        <h3 className="text-sm font-semibold text-text-primary">{title}</h3>
        {subtitle ? <p className="mt-1 text-xs leading-5 text-text-secondary">{subtitle}</p> : null}
      </div>
      {action ? <div className="shrink-0">{action}</div> : null}
    </div>
  );
}

interface StaggerListProps {
  children: ReactNode;
  className?: string;
}

export function StaggerList({ children, className = "" }: StaggerListProps) {
  return <div className={`ui-stagger-list ${className}`}>{children}</div>;
}
