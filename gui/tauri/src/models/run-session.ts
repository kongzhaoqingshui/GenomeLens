import type { RunSummary } from "./run-summary";

export type WorkflowState =
  | "PENDING"
  | "VALIDATING_INPUTS"
  | "PREPROCESSING_ANNOTATIONS"
  | "PREPARING_WORKSPACE"
  | "CHECKING_TOOLCHAIN"
  | "WRITING_MANIFEST"
  | "RUNNING_ENGINE"
  | "PARSING_ENGINE_SUMMARY"
  | "FINALIZING"
  | "SUCCEEDED"
  | "FAILED"
  | "CANCELLED"
  | string;

export interface RunAnalysisInput extends Record<string, unknown> {
  requestPath: string;
  outdir: string;
}

export interface RunHandle {
  runId: string;
  requestPath: string;
  outdir: string;
  status: WorkflowState;
  pid?: number;
  startedAt?: string;
  [extraField: string]: unknown;
}

export interface ReadSummaryInput extends Record<string, unknown> {
  outdir: string;
}

export interface ReadRunLogInput extends Record<string, unknown> {
  outdir: string;
  tailLines?: number;
}

export interface RunLogSnapshot {
  outdir: string;
  logPath: string;
  text: string;
  lines: string[];
  truncated: boolean;
  updatedAt?: string;
  [extraField: string]: unknown;
}

export interface OpenPathInput extends Record<string, unknown> {
  path: string;
}

export interface AnalysisStdoutEventPayload {
  line: string;
}

export interface AnalysisStateEventPayload {
  state: WorkflowState;
  progress: number;
}

export interface AnalysisFinishedEventPayload {
  status: "SUCCEEDED" | "FAILED" | "CANCELLED";
  summary?: RunSummary;
}

export interface AnalysisErrorEventPayload {
  message: string;
  code?: string;
  details?: Record<string, unknown>;
}

export type AnalysisEvent =
  | { name: "analysis:stdout"; payload: AnalysisStdoutEventPayload }
  | { name: "analysis:state"; payload: AnalysisStateEventPayload }
  | { name: "analysis:finished"; payload: AnalysisFinishedEventPayload }
  | { name: "analysis:error"; payload: AnalysisErrorEventPayload };

export type AnalysisEventName = AnalysisEvent["name"];

export const ANALYSIS_EVENT_NAMES: AnalysisEventName[] = [
  "analysis:stdout",
  "analysis:state",
  "analysis:finished",
  "analysis:error",
];
