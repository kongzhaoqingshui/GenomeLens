import { invoke } from "@tauri-apps/api/core";
import type { AnalysisRequest } from "../models/analysis-request";
import { analysisRequestToDraft, type AnalysisRequestDraft } from "../models/analysis-request-draft";
import type { ReadRequestPreviewInput, RequestPreview } from "../models/request-preview";

export type JsonObject = Record<string, unknown>;

const templateCache = new Map<string, AnalysisRequest>();
const templatePromiseCache = new Map<string, Promise<AnalysisRequest>>();
const templateDraftCache = new Map<string, AnalysisRequestDraft>();
let analysisSchemaCache: JsonObject | null = null;
let analysisSchemaPromiseCache: Promise<JsonObject> | null = null;

export function getTemplate(method = "mcscan"): Promise<AnalysisRequest> {
  const cached = templateCache.get(method);
  if (cached) {
    return Promise.resolve(cached);
  }

  const pending = templatePromiseCache.get(method);
  if (pending) {
    return pending;
  }

  const nextPromise = invoke<AnalysisRequest>("get_template", { method })
    .then((template) => {
      templateCache.set(method, template);
      templatePromiseCache.delete(method);
      return template;
    })
    .catch((error: unknown) => {
      templatePromiseCache.delete(method);
      throw error;
    });
  templatePromiseCache.set(method, nextPromise);
  return nextPromise;
}

export async function getTemplateDraft(method = "mcscan"): Promise<AnalysisRequestDraft> {
  const cached = templateDraftCache.get(method);
  if (cached) {
    return cached;
  }

  const nextDraft = analysisRequestToDraft(await getTemplate(method));
  templateDraftCache.set(method, nextDraft);
  return nextDraft;
}

export function getAnalysisSchema(): Promise<JsonObject> {
  if (analysisSchemaCache) {
    return Promise.resolve(analysisSchemaCache);
  }
  if (analysisSchemaPromiseCache) {
    return analysisSchemaPromiseCache;
  }

  analysisSchemaPromiseCache = invoke<JsonObject>("get_analysis_schema")
    .then((schema) => {
      analysisSchemaCache = schema;
      analysisSchemaPromiseCache = null;
      return schema;
    })
    .catch((error: unknown) => {
      analysisSchemaPromiseCache = null;
      throw error;
    });
  return analysisSchemaPromiseCache;
}

export function readRequestPreview(input: ReadRequestPreviewInput): Promise<RequestPreview> {
  return invoke<RequestPreview>("read_request_preview", input);
}

export function getCachedTemplateDraft(method = "mcscan"): AnalysisRequestDraft | null {
  const cachedDraft = templateDraftCache.get(method);
  if (cachedDraft) {
    return cachedDraft;
  }

  const cachedTemplate = templateCache.get(method);
  if (!cachedTemplate) {
    return null;
  }

  const nextDraft = analysisRequestToDraft(cachedTemplate);
  templateDraftCache.set(method, nextDraft);
  return nextDraft;
}

export function getCachedAnalysisSchema(): JsonObject | null {
  return analysisSchemaCache;
}
