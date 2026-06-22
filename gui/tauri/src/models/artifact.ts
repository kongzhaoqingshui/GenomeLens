export interface ListArtifactsInput extends Record<string, unknown> {
  outdir: string;
}

export type ArtifactSummarySource = "final_figures" | "global_figures" | "artifact_index" | string;

export interface ArtifactSummary {
  path: string;
  name: string;
  format: string;
  source: ArtifactSummarySource;
  preview: boolean;
}
