import type { AppRoute } from "../routes/routes";

interface PlaceholderPageProps {
  route: AppRoute;
  title: string;
  subtitle: string;
  details: string[];
}

export default function PlaceholderPage({ route, title, subtitle, details }: PlaceholderPageProps) {
  return (
    <section className="grid w-full gap-8 xl:grid-cols-[18rem_minmax(0,1fr)]">
      <aside className="overflow-hidden rounded-xl border border-slate-200 bg-slate-50">
        <div className="border-b border-slate-200/80 px-5 py-4">
          <p className="text-xs font-medium uppercase tracking-[0.18em] text-slate-400">{route.label}</p>
          <h1 className="mt-2 text-xl font-semibold text-slate-900">{title}</h1>
          <p className="mt-2 text-sm leading-6 text-slate-500">{subtitle}</p>
        </div>
        <div className="px-5 py-4 text-sm leading-6 text-slate-500">{route.description}</div>
      </aside>

      <section className="overflow-hidden rounded-xl border border-slate-200 bg-white">
        <div className="border-b border-slate-200/80 px-5 py-4">
          <h2 className="text-base font-semibold text-slate-900">Queued work</h2>
          <p className="mt-1 text-sm text-slate-500">This surface has been flattened to match the current Codex-like desktop language.</p>
        </div>
        <div className="divide-y divide-slate-200/80">
          {details.map((detail, index) => (
            <article key={detail} className="flex gap-4 px-5 py-4">
              <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-slate-100 text-xs font-semibold text-slate-600">
                {index + 1}
              </span>
              <p className="text-sm leading-7 text-slate-500">{detail}</p>
            </article>
          ))}
        </div>
      </section>
    </section>
  );
}
