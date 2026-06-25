import type {
  AlignSoft,
  DbType,
  LogLevel,
  OutputFormat,
  SpeciesInput,
  SpeciesInputMode,
  WorkflowId,
  WorkflowOutput,
  WorkflowParameters,
  WorkflowRequest,
  WorkflowRequestKind,
  WorkflowRuntime,
} from "./workflow-request";

export interface SpeciesInputDraft {
  name: string;
  inputMode: SpeciesInputMode;
  bed: string;
  cds: string;
  gff: string;
  genome: string;
}

export interface RuntimeDraft {
  projectConfig: string;
  engineConfig: string;
  jcviEngine: string;
  blastn: string;
  makeblastdb: string;
  lastal: string;
  lastdb: string;
  threads: number | null;
  minBlockSize: number | null;
  logLevel: LogLevel;
  verbose: boolean;
  consoleLog: boolean;
}

export interface SyntenyParametersDraft {
  alignSoft: AlignSoft;
  dbtype: DbType;
  cscore: number;
  dist: number;
  iter: number;
  allowSimplifiedFallback: boolean;
  minBlockSize: number;
}

export interface LocalSyntenyParametersDraft {
  targetGeneIds: string[];
  up: number;
  down: number;
  splitTargets: boolean;
  labelTargets: boolean;
  useNativeRenderer: boolean;
}

export interface PlotParametersDraft {
  glyphstyle: string;
  glyphcolor: string;
  shadestyle: string;
  figsize: string;
  dpi: number;
  autoOptimization: Record<string, unknown>;
}

export interface HistogramParametersDraft {
  inputs: string[];
  columns: number[];
  skip: number;
  bins: number;
  vmin: number | null;
  vmax: number | null;
  xlabel: string;
  title: string;
  base: number;
  facet: boolean;
  fill: string;
}

export interface HeatmapParametersDraft {
  matrix: string;
  rowgroups: string;
  cmap: string;
  groups: boolean;
  horizontalbar: boolean;
}

export interface ParametersDraft {
  synteny: SyntenyParametersDraft;
  localSynteny: LocalSyntenyParametersDraft;
  plot: PlotParametersDraft;
  histogram: HistogramParametersDraft;
  heatmap: HeatmapParametersDraft;
  extras: Record<string, unknown>;
}

export type WorkflowRequestInputMode = SpeciesInputMode | "auto_directory";

export interface WorkflowRequestDraft {
  schemaVersion: 3;
  kind: WorkflowRequestKind;
  workflowId: WorkflowId;
  inputMode: WorkflowRequestInputMode;
  directory: string;
  species: SpeciesInputDraft[];
  referenceIndex: number;
  outputDirectory: string;
  forceOutput: boolean;
  formats: OutputFormat[];
  runtime: RuntimeDraft;
  parameters: ParametersDraft;
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

function defaultSpeciesInputs(): SpeciesInputDraft[] {
  return [
    {
      name: "species_a",
      inputMode: "bed_cds",
      bed: "",
      cds: "",
      gff: "",
      genome: "",
    },
    {
      name: "species_b",
      inputMode: "bed_cds",
      bed: "",
      cds: "",
      gff: "",
      genome: "",
    },
  ];
}

export function workflowRequestToDraft(request: WorkflowRequest): WorkflowRequestDraft {
  const synteny = request.parameters?.synteny ?? {};
  const localSynteny = request.parameters?.local_synteny ?? {};
  const plot = request.parameters?.plot ?? {};
  const histogram = request.parameters?.histogram ?? {};
  const heatmap = request.parameters?.heatmap ?? {};

  return {
    schemaVersion: request.schema_version,
    kind: request.kind,
    workflowId: request.workflow_id,
    inputMode: "bed_cds",
    directory: "",
    species: (request.species ?? []).map(speciesInputToDraft),
    referenceIndex: request.reference_index ?? 0,
    outputDirectory: request.output.directory,
    forceOutput: request.output.force ?? false,
    formats: request.output.formats ?? ["svg"],
    runtime: {
      projectConfig: request.runtime?.project_config ?? "",
      engineConfig: request.runtime?.engine_config ?? "",
      jcviEngine: request.runtime?.jcvi_engine ?? "",
      blastn: request.runtime?.blastn ?? "",
      makeblastdb: request.runtime?.makeblastdb ?? "",
      lastal: request.runtime?.lastal ?? "",
      lastdb: request.runtime?.lastdb ?? "",
      threads: request.runtime?.threads ?? null,
      minBlockSize: request.runtime?.min_block_size ?? null,
      logLevel: request.runtime?.log_level ?? "INFO",
      verbose: request.runtime?.verbose ?? false,
      consoleLog: request.runtime?.console_log ?? false,
    },
    parameters: {
      synteny: {
        alignSoft: synteny.align_soft ?? "blast",
        dbtype: synteny.dbtype ?? "nucl",
        cscore: synteny.cscore ?? 0.7,
        dist: synteny.dist ?? 20,
        iter: synteny.iter ?? 1,
        allowSimplifiedFallback: synteny.allow_simplified_fallback ?? false,
        minBlockSize: synteny.min_block_size ?? 5,
      },
      localSynteny: {
        targetGeneIds: localSynteny.target_gene_ids ?? [],
        up: localSynteny.up ?? 20,
        down: localSynteny.down ?? 20,
        splitTargets: localSynteny.split_targets ?? false,
        labelTargets: localSynteny.label_targets ?? false,
        useNativeRenderer: localSynteny.use_native_renderer ?? false,
      },
      plot: {
        glyphstyle: plot.glyphstyle ?? "",
        glyphcolor: plot.glyphcolor ?? "",
        shadestyle: plot.shadestyle ?? "",
        figsize: plot.figsize ?? "",
        dpi: plot.dpi ?? 300,
        autoOptimization: plot.auto_optimization ?? {},
      },
      histogram: {
        inputs: histogram.inputs ?? [],
        columns: histogram.columns ?? [0],
        skip: histogram.skip ?? 0,
        bins: histogram.bins ?? 20,
        vmin: histogram.vmin ?? 0,
        vmax: histogram.vmax ?? null,
        xlabel: histogram.xlabel ?? "value",
        title: histogram.title ?? "",
        base: histogram.base ?? 0,
        facet: histogram.facet ?? false,
        fill: histogram.fill ?? "white",
      },
      heatmap: {
        matrix: heatmap.matrix ?? "",
        rowgroups: heatmap.rowgroups ?? "",
        cmap: heatmap.cmap ?? "",
        groups: heatmap.groups ?? false,
        horizontalbar: heatmap.horizontalbar ?? false,
      },
      extras: request.parameters?.extras ?? {},
    },
  };
}

export function draftToWorkflowRequest(draft: WorkflowRequestDraft): WorkflowRequest {
  const species = draft.species.map(speciesInputFromDraft);

  const output: WorkflowOutput = {
    directory: draft.outputDirectory,
    force: draft.forceOutput,
    formats: [...draft.formats],
  };

  const runtime: WorkflowRuntime = {
    project_config: draft.runtime.projectConfig,
    engine_config: draft.runtime.engineConfig,
    jcvi_engine: draft.runtime.jcviEngine,
    blastn: draft.runtime.blastn,
    makeblastdb: draft.runtime.makeblastdb,
    lastal: draft.runtime.lastal,
    lastdb: draft.runtime.lastdb,
    threads: draft.runtime.threads,
    min_block_size: draft.runtime.minBlockSize,
    log_level: draft.runtime.logLevel,
    verbose: draft.runtime.verbose,
    console_log: draft.runtime.consoleLog,
  };

  const parameters: WorkflowParameters = {
    synteny: {
      align_soft: draft.parameters.synteny.alignSoft,
      dbtype: draft.parameters.synteny.dbtype,
      cscore: draft.parameters.synteny.cscore,
      dist: draft.parameters.synteny.dist,
      iter: draft.parameters.synteny.iter,
      allow_simplified_fallback: draft.parameters.synteny.allowSimplifiedFallback,
      min_block_size: draft.parameters.synteny.minBlockSize,
    },
    local_synteny: {
      target_gene_ids: [...draft.parameters.localSynteny.targetGeneIds],
      up: draft.parameters.localSynteny.up,
      down: draft.parameters.localSynteny.down,
      split_targets: draft.parameters.localSynteny.splitTargets,
      label_targets: draft.parameters.localSynteny.labelTargets,
      use_native_renderer: draft.parameters.localSynteny.useNativeRenderer,
    },
    plot: {
      glyphstyle: draft.parameters.plot.glyphstyle,
      glyphcolor: draft.parameters.plot.glyphcolor,
      shadestyle: draft.parameters.plot.shadestyle,
      figsize: draft.parameters.plot.figsize,
      dpi: draft.parameters.plot.dpi,
      auto_optimization: { ...draft.parameters.plot.autoOptimization },
    },
    histogram: {
      inputs: [...draft.parameters.histogram.inputs],
      columns: [...draft.parameters.histogram.columns],
      skip: draft.parameters.histogram.skip,
      bins: draft.parameters.histogram.bins,
      vmin: draft.parameters.histogram.vmin,
      vmax: draft.parameters.histogram.vmax,
      xlabel: draft.parameters.histogram.xlabel,
      title: draft.parameters.histogram.title,
      base: draft.parameters.histogram.base,
      facet: draft.parameters.histogram.facet,
      fill: draft.parameters.histogram.fill,
    },
    heatmap: {
      matrix: draft.parameters.heatmap.matrix,
      rowgroups: draft.parameters.heatmap.rowgroups,
      cmap: draft.parameters.heatmap.cmap,
      groups: draft.parameters.heatmap.groups,
      horizontalbar: draft.parameters.heatmap.horizontalbar,
    },
    extras: { ...draft.parameters.extras },
  };

  return {
    schema_version: 3,
    kind: "workflow_request",
    workflow_id: draft.workflowId,
    species,
    reference_index: draft.referenceIndex,
    inputs: {},
    parameters,
    output,
    runtime,
  };
}

export function createDefaultWorkflowRequestDraft(): WorkflowRequestDraft {
  return {
    schemaVersion: 3,
    kind: "workflow_request",
    workflowId: "synteny",
    inputMode: "bed_cds",
    directory: "",
    species: defaultSpeciesInputs(),
    referenceIndex: 0,
    outputDirectory: "",
    forceOutput: false,
    formats: ["svg"],
    runtime: {
      projectConfig: "",
      engineConfig: "",
      jcviEngine: "",
      blastn: "",
      makeblastdb: "",
      lastal: "",
      lastdb: "",
      threads: null,
      minBlockSize: null,
      logLevel: "INFO",
      verbose: false,
      consoleLog: false,
    },
    parameters: {
      synteny: {
        alignSoft: "blast",
        dbtype: "nucl",
        cscore: 0.7,
        dist: 20,
        iter: 1,
        allowSimplifiedFallback: false,
        minBlockSize: 5,
      },
      localSynteny: {
        targetGeneIds: [],
        up: 20,
        down: 20,
        splitTargets: false,
        labelTargets: false,
        useNativeRenderer: false,
      },
      plot: {
        glyphstyle: "",
        glyphcolor: "",
        shadestyle: "",
        figsize: "",
        dpi: 300,
        autoOptimization: {},
      },
      histogram: {
        inputs: [],
        columns: [0],
        skip: 0,
        bins: 20,
        vmin: 0,
        vmax: null,
        xlabel: "value",
        title: "",
        base: 0,
        facet: false,
        fill: "white",
      },
      heatmap: {
        matrix: "",
        rowgroups: "",
        cmap: "",
        groups: false,
        horizontalbar: false,
      },
      extras: {},
    },
  };
}
