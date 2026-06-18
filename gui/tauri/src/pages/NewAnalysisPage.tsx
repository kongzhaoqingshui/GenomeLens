import { useCallback } from "react";

import { CommandPreview } from "../components/CommandPreview";
import type { AppRoute } from "../routes/routes";
import { getTemplate } from "../services/analysis";

interface NewAnalysisPageProps {
  route: AppRoute;
}

export default function NewAnalysisPage({ route }: NewAnalysisPageProps) {
  const loadTemplate = useCallback(() => getTemplate("mcscan"), []);

  return (
    <section className="grid w-full gap-6 lg:grid-cols-[0.9fr_1.1fr]">
      <div className="flex flex-col justify-center">
        <p className="text-sm font-semibold uppercase tracking-[0.2em] text-ice-600 dark:text-ice-300">
          GenomeLens GUI · {route.description}
        </p>
        <h1 className="mt-5 text-4xl font-bold text-text-primary">任务创建向导</h1>
        <p className="mt-4 text-base leading-8 text-text-secondary">
          Phase 0 先接通平台提供的 `get_template(method)`，后续 C 的表单模型会基于这个模板生成
          AnalysisRequest，而不是在前端维护私有 schema。
        </p>
      </div>

      <CommandPreview
        title="AnalysisRequest 模板"
        command="get_template('mcscan')"
        description="来自 Tauri command，对应 CLI `genomelens analyze template mcscan`。"
        load={loadTemplate}
      />
    </section>
  );
}

