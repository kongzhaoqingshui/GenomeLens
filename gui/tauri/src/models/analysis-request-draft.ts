import type {
  AlignSoft,
  AnalysisInputMode,
  AnalysisMethod,
  AnalysisRequest,
  AnalysisRequestKind,
  DbType,
  LogLevel,
  McscanWorkflow,
  OutputFormat,
  SpeciesInput,
  SpeciesInputMode,
} from "./analysis-request";

export interface SpeciesInputDraft {
  name: string;
  inputMode: SpeciesInputMode;
  bed: string;
  cds: string;
  gff: string;
  genome: string;
}

export interface AnalysisOptionsDraft {
  preset: "auto" | string;
  threads: number | null;
  minBlockSize: number | null;
  logLevel: LogLevel;
  verbose: boolean;
  consoleLog: boolean;
}

export interface McscanMethodConfigDraft {
  workflow: McscanWorkflow;
  jcviEngine: string;
  blastn: string;
  makeblastdb: string;
  jcviLayout: string;
  jcviSeqids: string;
  allowSimplifiedFallback: boolean;
  alignSoft: AlignSoft;
  dbtype: DbType;
  cscore: number;
  dist: number;
  iter: number;
  targetGeneIds: string[];
  up: number;
  down: number;
  splitTargets: boolean;
  labelTargets: boolean;
  glyphstyle: string;
  glyphcolor: string;
  shadestyle: string;
  figsize: string;
  dpi: number;
  optimizeFigsize: boolean;
  rewriteLayoutLinks: boolean;
  trimCrossChromosomeBlocks: boolean;
}

export interface AnalysisRequestDraft {
  schemaVersion: 1;
  kind: AnalysisRequestKind;
  method: AnalysisMethod;
  inputMode: AnalysisInputMode;
  directory: string;
  species: SpeciesInputDraft[];
  referenceIndex: number;
  outputDirectory: string;
  forceOutput: boolean;
  formats: OutputFormat[];
  projectConfig: string;
  methodConfigPath: string;
  options: AnalysisOptionsDraft;
  mcscan: McscanMethodConfigDraft;
}

function speciesInputToDraft(species: SpeciesInput): SpeciesInputDraft {
  return {
    name: species.name,
    inputMode: species.input_mode,
    bed: species.bed ?? "",
    cds: species.cds ?? "",
    gff: species.gff ?? "",
    genome: species.genome ?? "",
  };
}

function speciesInputFromDraft(species: SpeciesInputDraft): SpeciesInput {
  return {
    name: species.name,
    input_mode: species.inputMode,
    bed: species.bed,
    cds: species.cds,
    gff: species.gff,
    genome: species.genome,
  };
}

export function analysisRequestToDraft(request: AnalysisRequest): AnalysisRequestDraft {
  return {
    schemaVersion: request.schema_version,
    kind: request.kind,
    method: request.method,
    inputMode: request.input.mode,
    directory: request.input.directory ?? "",
    species: (request.input.species ?? []).map(speciesInputToDraft),
    referenceIndex: request.input.reference_index ?? 0,
    outputDirectory: request.output.directory,
    forceOutput: request.output.force ?? false,
    formats: request.output.formats ?? ["png"],
    projectConfig: request.config?.project_config ?? "",
    methodConfigPath: request.config?.method_config ?? "",
    options: {
      preset: request.options?.preset ?? "auto",
      threads: request.options?.threads ?? null,
      minBlockSize: request.options?.min_block_size ?? null,
      logLevel: request.options?.log_level ?? "INFO",
      verbose: request.options?.verbose ?? false,
      consoleLog: request.options?.console_log ?? false,
    },
    mcscan: {
      workflow: request.method_config?.workflow ?? "graphics_synteny",
      jcviEngine: request.method_config?.jcvi_engine ?? "",
      blastn: request.method_config?.blastn ?? "",
      makeblastdb: request.method_config?.makeblastdb ?? "",
      jcviLayout: request.method_config?.jcvi_layout ?? "",
      jcviSeqids: request.method_config?.jcvi_seqids ?? "",
      allowSimplifiedFallback: request.method_config?.allow_simplified_fallback ?? false,
      alignSoft: request.method_config?.align_soft ?? "blast",
      dbtype: request.method_config?.dbtype ?? "nucl",
      cscore: request.method_config?.cscore ?? 0.7,
      dist: request.method_config?.dist ?? 20,
      iter: request.method_config?.iter ?? 1,
      targetGeneIds: request.method_config?.target_gene_ids ?? [],
      up: request.method_config?.up ?? 20,
      down: request.method_config?.down ?? 20,
      splitTargets: request.method_config?.split_targets ?? false,
      labelTargets: request.method_config?.label_targets ?? false,
      glyphstyle: request.method_config?.glyphstyle ?? "",
      glyphcolor: request.method_config?.glyphcolor ?? "",
      shadestyle: request.method_config?.shadestyle ?? "",
      figsize: request.method_config?.figsize ?? "",
      dpi: request.method_config?.dpi ?? 300,
      optimizeFigsize: request.method_config?.optimize_figsize ?? false,
      rewriteLayoutLinks: request.method_config?.rewrite_layout_links ?? false,
      trimCrossChromosomeBlocks: request.method_config?.trim_cross_chromosome_blocks ?? false,
    },
  };
}

export function draftToAnalysisRequest(draft: AnalysisRequestDraft): AnalysisRequest {
  return {
    schema_version: draft.schemaVersion,
    kind: draft.kind,
    method: draft.method,
    input: {
      mode: draft.inputMode,
      directory: draft.directory,
      species: draft.species.map(speciesInputFromDraft),
      reference_index: draft.referenceIndex,
    },
    output: {
      directory: draft.outputDirectory,
      force: draft.forceOutput,
      formats: [...draft.formats],
    },
    config: {
      project_config: draft.projectConfig,
      method_config: draft.methodConfigPath,
    },
    options: {
      preset: draft.options.preset,
      threads: draft.options.threads,
      min_block_size: draft.options.minBlockSize,
      log_level: draft.options.logLevel,
      verbose: draft.options.verbose,
      console_log: draft.options.consoleLog,
    },
    method_config: {
      workflow: draft.mcscan.workflow,
      jcvi_engine: draft.mcscan.jcviEngine,
      blastn: draft.mcscan.blastn,
      makeblastdb: draft.mcscan.makeblastdb,
      jcvi_layout: draft.mcscan.jcviLayout,
      jcvi_seqids: draft.mcscan.jcviSeqids,
      allow_simplified_fallback: draft.mcscan.allowSimplifiedFallback,
      align_soft: draft.mcscan.alignSoft,
      dbtype: draft.mcscan.dbtype,
      cscore: draft.mcscan.cscore,
      dist: draft.mcscan.dist,
      iter: draft.mcscan.iter,
      target_gene_ids: [...draft.mcscan.targetGeneIds],
      up: draft.mcscan.up,
      down: draft.mcscan.down,
      split_targets: draft.mcscan.splitTargets,
      label_targets: draft.mcscan.labelTargets,
      glyphstyle: draft.mcscan.glyphstyle,
      glyphcolor: draft.mcscan.glyphcolor,
      shadestyle: draft.mcscan.shadestyle,
      figsize: draft.mcscan.figsize,
      dpi: draft.mcscan.dpi,
      optimize_figsize: draft.mcscan.optimizeFigsize,
      rewrite_layout_links: draft.mcscan.rewriteLayoutLinks,
      trim_cross_chromosome_blocks: draft.mcscan.trimCrossChromosomeBlocks,
    },
  };
}
