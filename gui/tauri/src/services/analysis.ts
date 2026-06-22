import { invoke } from "@tauri-apps/api/core";
import type { AnalysisRequest } from "../models/analysis-request";
import { analysisRequestToDraft, type AnalysisRequestDraft } from "../models/analysis-request-draft";
import type { ReadRequestPreviewInput, RequestPreview } from "../models/request-preview";

export type JsonObject = Record<string, unknown>;

export function getTemplate(method = "mcscan"): Promise<AnalysisRequest> {
  return invoke<AnalysisRequest>("get_template", { method });
}

export async function getTemplateDraft(method = "mcscan"): Promise<AnalysisRequestDraft> {
  return analysisRequestToDraft(await getTemplate(method));
}

export function getAnalysisSchema(): Promise<JsonObject> {
  return invoke<JsonObject>("get_analysis_schema");
}

export function readRequestPreview(input: ReadRequestPreviewInput): Promise<RequestPreview> {
  return invoke<RequestPreview>("read_request_preview", input);
}
