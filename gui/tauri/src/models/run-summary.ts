export type RunStatus = "SUCCEEDED" | "FAILED" | "RUNNING" | "PENDING" | string;

export interface ArtifactRecord {
  artifact_id: string;
  artifact_type: string;
  path: string;
  produced_by: string;
  format?: string;
  preview?: boolean;
  input_refs?: string[];
  metadata?: Record<string, unknown>;
}

export interface UiBlock {
  state: RunStatus;
  progress: number;
  primary_figures: string[];
  summary_path: string;
  log_path: string;
}

export interface ScoringBlock {
  status: string;
  scores: unknown[];
  ranking: unknown[];
  message: string;
  artifact_path?: string;
  model_version?: string;
}

export interface ChildRunRecord {
  child_id: string;
  pair_id: string;
  species_a_name: string;
  species_b_name: string;
  status: RunStatus;
  outdir: string;
  run_summary_path?: string;
  engine_summary_path?: string;
  blast_table?: string;
  anchors_path?: string;
  simple_path?: string;
  blocks_path?: string;
  query_bed?: string;
  subject_bed?: string;
  final_figures?: string[];
  error?: {
    type: string;
    message: string;
  };
}

export interface RunSummary {
  status: RunStatus;
  schema_version: number;
  workflow: string;
  method?: string;
  task: Record<string, unknown>;
  species: Array<Record<string, unknown>>;
  final_figures: string[];
  artifact_index: ArtifactRecord[];
  logs: Record<string, string>;
  ui: UiBlock;
  scoring: ScoringBlock;
  extensions?: Record<string, unknown>;
  child_runs?: ChildRunRecord[];
  analysis_request_path?: string;
  [extensionKey: string]: unknown;
}

export interface FigureAsset {
  path: string;
  name: string;
  format: string;
  source: "final_figures" | "child_runs" | "artifact_index";
  preview: boolean;
}
