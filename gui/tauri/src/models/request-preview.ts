import type { AnalysisRequest } from "./analysis-request";

export interface ReadRequestPreviewInput extends Record<string, unknown> {
  requestPath: string;
}

export interface RequestPreview {
  requestPath: string;
  json: AnalysisRequest | Record<string, unknown>;
  method?: string;
  workflow?: string;
}
