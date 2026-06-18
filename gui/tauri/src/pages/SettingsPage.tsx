import { useCallback } from "react";

import { CommandPreview } from "../components/CommandPreview";
import type { AppRoute } from "../routes/routes";
import { getAnalysisSchema } from "../services/analysis";

interface SettingsPageProps {
  route: AppRoute;
}

export default function SettingsPage({ route }: SettingsPageProps) {
  const loadSchema = useCallback(() => getAnalysisSchema(), []);

  return (
    <section className="grid w-full gap-6 lg:grid-cols-[0.9fr_1.1fr]">
      <div className="flex flex-col justify-center">
        <p className="text-sm font-semibold uppercase tracking-[0.2em] text-ice-600 dark:text-ice-300">
          GenomeLens GUI · {route.description}
        </p>
        <h1 className="mt-5 text-4xl font-bold text-text-primary">设置与环境诊断</h1>
        <p className="mt-4 text-base leading-8 text-text-secondary">
          Phase 0 先展示平台 schema 接口，环境状态继续由首页的 `get_version()` 承载。后续会在这里汇总路径、
          主题和工具链定位。
        </p>
      </div>

      <CommandPreview
        title="AnalysisRequest Schema"
        command="get_analysis_schema()"
        description="来自 Tauri command，对应 CLI `genomelens analyze schema`。"
        load={loadSchema}
      />
    </section>
  );
}

