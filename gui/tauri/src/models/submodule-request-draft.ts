import type { SubmoduleRequest, SubmoduleRequestOutput, SubmoduleRequestRuntime } from "./submodule-request";

export interface SubmoduleRequestDraft {
  schemaVersion: 3;
  kind: "submodule_request";
  moduleId: string;
  inputs: Record<string, unknown>;
  parameters: Record<string, unknown>;
  outputDirectory: string;
  forceOutput: boolean;
  formats: string[];
  runtime: {
    projectConfig: string;
    engineConfig: string;
    jcviEngine: string;
    blastn: string;
    makeblastdb: string;
    lastal: string;
    lastdb: string;
    threads: number | null;
    minBlockSize: number | null;
    logLevel: string;
    verbose: boolean;
    consoleLog: boolean;
  };
}

function runtimeToDraft(runtime: SubmoduleRequestRuntime): SubmoduleRequestDraft["runtime"] {
  return {
    projectConfig: runtime.project_config ?? "",
    engineConfig: runtime.engine_config ?? "",
    jcviEngine: runtime.jcvi_engine ?? "",
    blastn: runtime.blastn ?? "",
    makeblastdb: runtime.makeblastdb ?? "",
    lastal: runtime.lastal ?? "",
    lastdb: runtime.lastdb ?? "",
    threads: runtime.threads ?? null,
    minBlockSize: runtime.min_block_size ?? null,
    logLevel: runtime.log_level ?? "INFO",
    verbose: runtime.verbose ?? false,
    consoleLog: runtime.console_log ?? false,
  };
}

function runtimeFromDraft(draft: SubmoduleRequestDraft["runtime"]): SubmoduleRequestRuntime {
  return {
    project_config: draft.projectConfig,
    engine_config: draft.engineConfig,
    jcvi_engine: draft.jcviEngine,
    blastn: draft.blastn,
    makeblastdb: draft.makeblastdb,
    lastal: draft.lastal,
    lastdb: draft.lastdb,
    threads: draft.threads,
    min_block_size: draft.minBlockSize,
    log_level: draft.logLevel,
    verbose: draft.verbose,
    console_log: draft.consoleLog,
  };
}

export function submoduleRequestToDraft(request: SubmoduleRequest): SubmoduleRequestDraft {
  const output: SubmoduleRequestOutput = request.output ?? { directory: "" };
  return {
    schemaVersion: request.schema_version,
    kind: request.kind,
    moduleId: request.module_id,
    inputs: { ...(request.inputs ?? {}) },
    parameters: { ...(request.parameters ?? {}) },
    outputDirectory: output.directory,
    forceOutput: output.force ?? false,
    formats: output.formats ?? ["svg"],
    runtime: runtimeToDraft(request.runtime ?? {}),
  };
}

export function draftToSubmoduleRequest(draft: SubmoduleRequestDraft): SubmoduleRequest {
  const output: SubmoduleRequestOutput = {
    directory: draft.outputDirectory,
    force: draft.forceOutput,
    formats: [...draft.formats],
  };

  return {
    schema_version: 3,
    kind: "submodule_request",
    module_id: draft.moduleId,
    inputs: { ...draft.inputs },
    parameters: { ...draft.parameters },
    output,
    runtime: runtimeFromDraft(draft.runtime),
  };
}

export function createDefaultSubmoduleRequestDraft(moduleId: string): SubmoduleRequestDraft {
  return {
    schemaVersion: 3,
    kind: "submodule_request",
    moduleId,
    inputs: {},
    parameters: {},
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
  };
}
