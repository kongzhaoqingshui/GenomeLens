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
      <header className="border-b border-slate-200/80 pb-5">
        <p className="text-xs font-medium uppercase tracking-[0.18em] text-slate-400">{route.label}</p>
        <h1 className="mt-2 text-2xl font-semibold text-slate-900">{title}</h1>
        <p className="mt-3 max-w-3xl text-sm leading-7 text-slate-500">{subtitle}</p>
      </header>

      <div className="grid gap-8 pt-6 xl:grid-cols-[15rem_minmax(0,1fr)]">
        <aside>
          <p className="text-xs font-medium uppercase tracking-[0.18em] text-slate-400">Context</p>
          <p className="mt-3 text-sm leading-7 text-slate-500">{route.description}</p>
        </aside>

        <section>
          <div className="border-b border-slate-200/80 pb-3">
            <h2 className="text-sm font-semibold text-slate-900">Queued work</h2>
            <p className="mt-1 text-sm text-slate-500">This area stays intentionally simple until the feature is reopened.</p>
          </div>

          <div className="divide-y divide-slate-200/80 border-b border-slate-200/80">
            {details.map((detail, index) => (
              <article key={detail} className="grid grid-cols-[2.5rem_minmax(0,1fr)] gap-4 py-4">
                <span className="text-sm font-semibold text-slate-400">{String(index + 1).padStart(2, "0")}</span>
                <p className="text-sm leading-7 text-slate-500">{detail}</p>
              </article>
            ))}
          </div>
        </section>
      </div>
    </section>
  );
}
