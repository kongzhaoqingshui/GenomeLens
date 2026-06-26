import { invoke } from "@tauri-apps/api/core";
import type { WorkflowRequest } from "../models/workflow-request";
import { workflowRequestToDraft, type WorkflowRequestDraft } from "../models/workflow-request-draft";
import type { ReadRequestPreviewInput, RequestPreview } from "../models/request-preview";

export type JsonObject = Record<string, unknown>;

const templateCache = new Map<string, WorkflowRequest>();
const templatePromiseCache = new Map<string, Promise<WorkflowRequest>>();
const templateDraftCache = new Map<string, WorkflowRequestDraft>();
let workflowSchemaCache: JsonObject | null = null;
let workflowSchemaPromiseCache: Promise<JsonObject> | null = null;

export function getTemplate(kind = "workflow", id = "synteny"): Promise<WorkflowRequest> {
  const cacheKey = `${kind}:${id}`;
  const cached = templateCache.get(cacheKey);
  if (cached) {
    return Promise.resolve(cached);
  }

  const pending = templatePromiseCache.get(cacheKey);
  if (pending) {
    return pending;
  }

  const nextPromise = invoke<WorkflowRequest>("get_template", { kind, id })
    .then((template) => {
      templateCache.set(cacheKey, template);
      templatePromiseCache.delete(cacheKey);
      return template;
    })
    .catch((error: unknown) => {
      templatePromiseCache.delete(cacheKey);
      throw error;
    });
  templatePromiseCache.set(cacheKey, nextPromise);
  return nextPromise;
}

export async function getTemplateDraft(kind = "workflow", id = "synteny"): Promise<WorkflowRequestDraft> {
  const cacheKey = `${kind}:${id}`;
  const cached = templateDraftCache.get(cacheKey);
  if (cached) {
    return cached;
  }

  const nextDraft = workflowRequestToDraft(await getTemplate(kind, id));
  templateDraftCache.set(cacheKey, nextDraft);
  return nextDraft;
}

export function getWorkflowSchema(): Promise<JsonObject> {
  if (workflowSchemaCache) {
    return Promise.resolve(workflowSchemaCache);
  }
  if (workflowSchemaPromiseCache) {
    return workflowSchemaPromiseCache;
  }

  workflowSchemaPromiseCache = invoke<JsonObject>("get_workflow_schema")
    .then((schema) => {
      workflowSchemaCache = schema;
      workflowSchemaPromiseCache = null;
      return schema;
    })
    .catch((error: unknown) => {
      workflowSchemaPromiseCache = null;
      throw error;
    });
  return workflowSchemaPromiseCache;
}

export function getSubmoduleSchema(): Promise<JsonObject> {
  return invoke<JsonObject>("get_workflow_schema", { input: { kind: "submodule" } });
}

export function getUnionSchema(): Promise<JsonObject> {
  return invoke<JsonObject>("get_workflow_schema", { input: { kind: "union" } });
}

export function readRequestPreview(input: ReadRequestPreviewInput): Promise<RequestPreview> {
  return invoke<RequestPreview>("read_request_preview", { input });
}

export function getCachedTemplateDraft(kind = "workflow", id = "synteny"): WorkflowRequestDraft | null {
  const cacheKey = `${kind}:${id}`;
  const cachedDraft = templateDraftCache.get(cacheKey);
  if (cachedDraft) {
    return cachedDraft;
  }

  const cachedTemplate = templateCache.get(cacheKey);
  if (!cachedTemplate) {
    return null;
  }

  const nextDraft = workflowRequestToDraft(cachedTemplate);
  templateDraftCache.set(cacheKey, nextDraft);
  return nextDraft;
}

export function getCachedWorkflowSchema(): JsonObject | null {
  return workflowSchemaCache;
}
