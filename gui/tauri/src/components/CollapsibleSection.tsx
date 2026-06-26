import { ChevronDown } from "lucide-react";
import { useState, type ReactNode } from "react";

interface CollapsibleSectionProps {
  title: string;
  subtitle?: string;
  children: ReactNode;
  defaultOpen?: boolean;
  className?: string;
  badge?: ReactNode;
}

export function CollapsibleSection({
  title,
  subtitle,
  children,
  defaultOpen = true,
  className = "",
  badge,
}: CollapsibleSectionProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <section className={`ui-card overflow-hidden ${className}`}>
      <div className="flex items-start justify-between gap-3 border-b border-border/90 bg-surface">
        <button
          type="button"
          className="ui-pressable min-w-0 flex-1 px-5 py-4 text-left"
          onClick={() => setIsOpen((current) => !current)}
          aria-expanded={isOpen}
        >
          <div className="min-w-0">
            <h3 className="text-sm font-semibold text-text-primary">{title}</h3>
            {subtitle ? <p className="mt-1 text-xs leading-5 text-text-secondary">{subtitle}</p> : null}
          </div>
        </button>
        <div className="flex shrink-0 items-center gap-2 px-5 py-4">
          {badge ? <span>{badge}</span> : null}
          <span
            className={[
              "flex h-6 w-6 items-center justify-center rounded-md border border-border bg-surface-raised text-text-tertiary transition",
              isOpen ? "rotate-180" : "",
            ].join(" ")}
          >
            <ChevronDown className="h-4 w-4" />
          </span>
        </div>
      </div>
      <div
        className={[
          "grid transition-all duration-200 ease-out",
          isOpen ? "grid-rows-[1fr] opacity-100" : "grid-rows-[0fr] opacity-0",
        ].join(" ")}
      >
        <div className="overflow-hidden">
          <div className="px-5 py-5">{children}</div>
        </div>
      </div>
    </section>
  );
}
