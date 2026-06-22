import type { AppRoute } from "../routes/routes";

interface PlaceholderPageProps {
  route: AppRoute;
  title: string;
  subtitle: string;
  details: string[];
}

export default function PlaceholderPage({ route, title, subtitle, details }: PlaceholderPageProps) {
  return (
    <section className="mx-auto w-full max-w-5xl px-2">
      <header className="border-b border-border/90 pb-5">
        <p className="text-xs font-medium uppercase tracking-[0.16em] text-text-tertiary">{route.label}</p>
        <h1 className="mt-2 text-xl font-semibold text-text-primary">{title}</h1>
        <p className="mt-3 max-w-3xl text-sm leading-7 text-text-secondary">{subtitle}</p>
      </header>

      <div className="grid gap-8 pt-6 xl:grid-cols-[15rem_minmax(0,1fr)]">
        <aside>
          <p className="text-xs font-medium uppercase tracking-[0.16em] text-text-tertiary">Context</p>
          <p className="mt-3 text-sm leading-7 text-text-secondary">{route.description}</p>
        </aside>

        <section>
          <div className="border-b border-border/90 pb-3">
            <h2 className="text-sm font-semibold text-text-primary">Queued work</h2>
            <p className="mt-1 text-sm text-text-secondary">This area stays intentionally simple until the feature is reopened.</p>
          </div>

          <div className="divide-y divide-border/90 border-b border-border/90">
            {details.map((detail, index) => (
              <article key={detail} className="grid grid-cols-[2.5rem_minmax(0,1fr)] gap-4 py-4">
                <span className="text-sm font-semibold text-text-tertiary">{String(index + 1).padStart(2, "0")}</span>
                <p className="text-sm leading-7 text-text-secondary">{detail}</p>
              </article>
            ))}
          </div>
        </section>
      </div>
    </section>
  );
}
