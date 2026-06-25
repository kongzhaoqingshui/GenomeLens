export type WorkflowRequestKind = "workflow_request";

export type WorkflowId = "synteny";

export type SpeciesInputMode = "bed_cds" | "gff_genome";

export type OutputFormat = "png" | "pdf" | "svg" | string;

export type LogLevel = "DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL";

export type AlignSoft = "blast" | "last" | "diamond_blastp";

export type DbType = "nucl" | "prot";

export interface SpeciesInput {
  name: string;
  input_mode: SpeciesInputMode;
  bed?: string;
  cds?: string;
  gff?: string;
  genome?: string;
}

export interface SyntenyParameters {
  align_soft?: AlignSoft;
  dbtype?: DbType;
  cscore?: number;
  dist?: number;
  iter?: number;
  allow_simplified_fallback?: boolean;
  min_block_size?: number;
}

export interface LocalSyntenyParameters {
  target_gene_ids?: string[];
  up?: number;
  down?: number;
  split_targets?: boolean;
  label_targets?: boolean;
  use_native_renderer?: boolean;
}

export interface PlotParameters {
  glyphstyle?: string;
  glyphcolor?: string;
  shadestyle?: string;
  figsize?: string;
  dpi?: number;
  auto_optimization?: Record<string, unknown>;
}

export interface HistogramParameters {
  inputs?: string[];
  columns?: number[];
  skip?: number;
  bins?: number;
  vmin?: number | null;
  vmax?: number | null;
  xlabel?: string;
  title?: string;
  base?: number;
  facet?: boolean;
  fill?: string;
}

export interface HeatmapParameters {
  matrix?: string;
  rowgroups?: string;
  cmap?: string;
  groups?: boolean;
  horizontalbar?: boolean;
}

export interface WorkflowParameters {
  synteny?: SyntenyParameters;
  local_synteny?: LocalSyntenyParameters;
  plot?: PlotParameters;
  histogram?: HistogramParameters;
  heatmap?: HeatmapParameters;
  extras?: Record<string, unknown>;
}

export interface WorkflowOutput {
  directory: string;
  force?: boolean;
  formats?: OutputFormat[];
}

export interface WorkflowRuntime {
  project_config?: string;
  engine_config?: string;
  jcvi_engine?: string;
  blastn?: string;
  makeblastdb?: string;
  lastal?: string;
  lastdb?: string;
  threads?: number | null;
  min_block_size?: number | null;
  log_level?: LogLevel;
  verbose?: boolean;
  console_log?: boolean;
}

export interface WorkflowRequest {
  schema_version: 3;
  kind: WorkflowRequestKind;
  workflow_id: WorkflowId;
  species: SpeciesInput[];
  reference_index: number;
  inputs: Record<string, unknown>;
  parameters: WorkflowParameters;
  output: WorkflowOutput;
  runtime: WorkflowRuntime;
}
