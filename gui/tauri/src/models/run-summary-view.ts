import type { ArtifactRecord, FigureAsset, PairwiseJobSummary, RunSummary, RunStatus } from "./run-summary";

const KNOWN_RUN_SUMMARY_KEYS = new Set<string>([
  "status",
  "schema_version",
  "workflow",
  "method",
  "task",
  "species",
  "final_figures",
  "artifact_index",
  "logs",
  "ui",
  "scoring",
  "analysis_request_path",
  "species_count",
  "pairing_strategy",
  "pairwise_jobs",
  "pairwise_job_count",
  "global_figures",
  "reference_name",
  "native_multi_species",
  "native_edges",
  "native_layout",
]);

export interface RunSummaryViewModel {
  status: RunStatus;
  schemaVersion: number;
  workflow: string;
  method: string;
  progress: number;
  analysisRequestPath: string;
  runSummaryPath: string;
  runLogPath: string;
  primaryFigurePaths: string[];
  finalFigures: string[];
  globalFigures: string[];
  figureAssets: FigureAsset[];
  artifactIndex: ArtifactRecord[];
  pairwiseJobs: PairwiseJobSummary[];
  pairwiseJobCount: number;
  pairingStrategy: string;
  referenceName: string;
  methodData: Record<string, unknown>;
}

function basename(path: string): string {
  const parts = path.split(/[\\/]/);
  return parts.length > 0 ? parts[parts.length - 1] : path;
}

function inferFormat(path: string, fallback = "unknown"): string {
  const name = basename(path);
  const dotIndex = name.lastIndexOf(".");
  if (dotIndex < 0 || dotIndex === name.length - 1) {
    return fallback;
  }
  return name.slice(dotIndex + 1).toLowerCase();
}

function addFigureAsset(
  assets: Map<string, FigureAsset>,
  path: string,
  source: FigureAsset["source"],
  preview: boolean,
  format?: string,
): void {
  if (!path || assets.has(path)) {
    return;
  }
  assets.set(path, {
    path,
    name: basename(path),
    format: format ?? inferFormat(path),
    source,
    preview,
  });
}

export function getRunSummaryMethodData(summary: RunSummary): Record<string, unknown> {
  const methodData: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(summary)) {
    if (!KNOWN_RUN_SUMMARY_KEYS.has(key)) {
      methodData[key] = value;
    }
  }
  return methodData;
}

export function collectFigureAssets(summary: RunSummary): FigureAsset[] {
  const assets = new Map<string, FigureAsset>();

  for (const path of summary.final_figures) {
    addFigureAsset(assets, path, "final_figures", true);
  }

  for (const path of summary.global_figures ?? []) {
    addFigureAsset(assets, path, "global_figures", true);
  }

  for (const artifact of summary.artifact_index) {
    addFigureAsset(
      assets,
      artifact.path,
      "artifact_index",
      artifact.preview ?? false,
      artifact.format ?? inferFormat(artifact.path, artifact.artifact_type),
    );
  }

  return [...assets.values()];
}

export function runSummaryToViewModel(summary: RunSummary): RunSummaryViewModel {
  return {
    status: summary.status,
    schemaVersion: summary.schema_version,
    workflow: summary.workflow,
    method: summary.method ?? "",
    progress: summary.ui.progress,
    analysisRequestPath: summary.analysis_request_path ?? "",
    runSummaryPath: summary.ui.summary_path,
    runLogPath: summary.ui.log_path,
    primaryFigurePaths: [...summary.ui.primary_figures],
    finalFigures: [...summary.final_figures],
    globalFigures: [...(summary.global_figures ?? [])],
    figureAssets: collectFigureAssets(summary),
    artifactIndex: [...summary.artifact_index],
    pairwiseJobs: [...(summary.pairwise_jobs ?? [])],
    pairwiseJobCount: summary.pairwise_job_count ?? summary.pairwise_jobs?.length ?? 0,
    pairingStrategy: summary.pairing_strategy ?? "",
    referenceName: summary.reference_name ?? "",
    methodData: getRunSummaryMethodData(summary),
  };
}
