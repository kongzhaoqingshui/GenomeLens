import { invoke } from "@tauri-apps/api/core";

export type JsonObject = Record<string, unknown>;

export function getTemplate(method = "mcscan"): Promise<JsonObject> {
  return invoke<JsonObject>("get_template", { method });
}

export function getAnalysisSchema(): Promise<JsonObject> {
  return invoke<JsonObject>("get_analysis_schema");
}
