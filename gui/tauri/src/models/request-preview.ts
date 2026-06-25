import type { WorkflowRequest } from "./workflow-request";

export interface ReadRequestPreviewInput extends Record<string, unknown> {
  requestPath: string;
}

export interface RequestPreview {
  requestPath: string;
  json: WorkflowRequest | Record<string, unknown>;
  workflowId?: string;
  kind?: string;
}
