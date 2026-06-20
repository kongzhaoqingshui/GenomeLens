export type AnalysisMethod = "mcscan";

export type AnalysisRequestKind = "analysis_request";

export type AnalysisInputMode = "auto_directory" | "bed_cds" | "gff_genome";

export type SpeciesInputMode = "bed_cds" | "gff_genome";

export type OutputFormat = "png" | "pdf" | "svg" | string;

export type LogLevel = "DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL";

export type McscanWorkflow =
  | "mcscan_pairwise"
  | "graphics_synteny"
  | "graphics_dotplot"
  | "graphics_karyotype"
  | "catalog_ortholog"
  | "local_synteny"
  | string;

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

export interface AnalysisInput {
  mode: AnalysisInputMode;
  directory?: string;
  species?: SpeciesInput[];
  reference_index?: number;
}

export interface AnalysisOutput {
  directory: string;
  force?: boolean;
  formats?: OutputFormat[];
}

export interface AnalysisConfigRef {
  project_config?: string;
  method_config?: string;
}

export interface AnalysisOptions {
  preset?: "auto" | string;
  threads?: number | null;
  min_block_size?: number | null;
  log_level?: LogLevel;
  verbose?: boolean;
  console_log?: boolean;
}

export interface McscanMethodConfig {
  workflow?: McscanWorkflow;
  jcvi_engine?: string;
  blastn?: string;
  makeblastdb?: string;
  jcvi_layout?: string;
  jcvi_seqids?: string;
  allow_simplified_fallback?: boolean;
  align_soft?: AlignSoft;
  dbtype?: DbType;
  cscore?: number;
  dist?: number;
  iter?: number;
  target_gene_ids?: string[];
  up?: number;
  down?: number;
  split_targets?: boolean;
  label_targets?: boolean;
  glyphstyle?: string;
  glyphcolor?: string;
  shadestyle?: string;
  figsize?: string;
  dpi?: number;
  optimize_figsize?: boolean;
  rewrite_layout_links?: boolean;
  trim_cross_chromosome_blocks?: boolean;
}

export interface AnalysisRequest {
  schema_version: 1;
  kind: AnalysisRequestKind;
  method: AnalysisMethod;
  input: AnalysisInput;
  output: AnalysisOutput;
  config?: AnalysisConfigRef;
  options?: AnalysisOptions;
  method_config?: McscanMethodConfig;
}

export interface AnalysisRequestFormModel {
  method: AnalysisMethod;
  inputMode: AnalysisInputMode;
  species: SpeciesInput[];
  referenceIndex: number;
  outputDirectory: string;
  forceOutput: boolean;
  formats: OutputFormat[];
  options: AnalysisOptions;
  mcscan: McscanMethodConfig;
}

