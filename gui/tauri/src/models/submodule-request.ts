export interface SubmoduleRequestOutput {
  directory: string;
  force?: boolean;
  formats?: string[];
}

export interface SubmoduleRequestRuntime {
  project_config?: string;
  engine_config?: string;
  jcvi_engine?: string;
  blastn?: string;
  makeblastdb?: string;
  lastal?: string;
  lastdb?: string;
  threads?: number | null;
  min_block_size?: number | null;
  log_level?: string;
  verbose?: boolean;
  console_log?: boolean;
}

export interface SubmoduleRequest {
  schema_version: 3;
  kind: "submodule_request";
  module_id: string;
  inputs: Record<string, unknown>;
  parameters: Record<string, unknown>;
  output: SubmoduleRequestOutput;
  runtime: SubmoduleRequestRuntime;
}
