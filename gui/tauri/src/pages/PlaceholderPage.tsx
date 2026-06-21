import type { AppRoute } from "../routes/routes";

interface PlaceholderPageProps {
  route: AppRoute;
  title: string;
  subtitle: string;
  details: string[];
}

export default function PlaceholderPage({ route, title, subtitle, details }: PlaceholderPageProps) {
  return (
    <section className="grid w-full content-center gap-6">
      <div className="max-w-3xl">
        <p className="text-sm font-semibold uppercase tracking-[0.2em] text-ice-600 dark:text-ice-300">
          JCVI meow · {route.description}
        </p>
        <h1 className="mt-5 text-4xl font-bold text-text-primary">{title}</h1>
        <p className="mt-4 text-base leading-8 text-text-secondary">{subtitle}</p>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        {details.map((detail) => (
          <article key={detail} className="rounded-xl border border-border bg-surface/80 p-4 shadow-card">
            <div className="mb-4 h-1 w-12 rounded-full bg-ice-400" />
            <p className="text-sm leading-6 text-text-secondary">{detail}</p>
          </article>
        ))}
      </div>
    </section>
  );
}

