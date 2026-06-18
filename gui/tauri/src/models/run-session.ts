import type { RunSummary } from "./run-summary";
import { runSummaryToViewModel, type RunSummaryViewModel } from "./run-summary-view";

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
  logPath?: string;
  summaryPath?: string;
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
  runId: string;
  outdir: string;
  requestPath: string;
  startedAt?: string;
  line: string;
}

export interface AnalysisStateEventPayload {
  runId: string;
  outdir: string;
  requestPath: string;
  startedAt?: string;
  state: WorkflowState;
  progress: number;
}

export interface AnalysisFinishedEventPayload {
  runId: string;
  outdir: string;
  requestPath: string;
  startedAt?: string;
  finishedAt?: string;
  exitCode?: number | null;
  logPath?: string;
  summaryPath?: string;
  status: "SUCCEEDED" | "FAILED" | "CANCELLED";
  summary?: RunSummary;
}

export interface AnalysisErrorEventPayload {
  runId: string;
  outdir: string;
  requestPath: string;
  startedAt?: string;
  finishedAt?: string;
  exitCode?: number | null;
  logPath?: string;
  summaryPath?: string;
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

export interface AnalysisRunState {
  runId: string;
  outdir: string;
  requestPath: string;
  pid?: number;
  logPath?: string;
  summaryPath?: string;
  status: WorkflowState;
  progress: number;
  startedAt?: string;
  finishedAt?: string;
  exitCode?: number | null;
  finished: boolean;
  error?: AnalysisErrorEventPayload;
  summary?: RunSummary;
  summaryView?: RunSummaryViewModel;
  logLines: string[];
  lastLogLine?: string;
}

export function createAnalysisRunState(handle: RunHandle): AnalysisRunState {
  return {
    runId: handle.runId,
    outdir: handle.outdir,
    requestPath: handle.requestPath,
    pid: handle.pid,
    logPath: handle.logPath,
    summaryPath: handle.summaryPath,
    status: handle.status,
    progress: 0,
    startedAt: handle.startedAt,
    finished: false,
    logLines: [],
  };
}

export function appendRunLogLines(
  state: AnalysisRunState,
  incomingLines: string[],
  maxLines = 200,
): AnalysisRunState {
  const normalized = incomingLines.filter((line) => line.trim().length > 0);
  if (normalized.length === 0) {
    return state;
  }

  const nextLines = [...state.logLines, ...normalized];
  const keptLines = nextLines.length > maxLines ? nextLines.slice(nextLines.length - maxLines) : nextLines;

  return {
    ...state,
    logLines: keptLines,
    lastLogLine: normalized[normalized.length - 1],
  };
}

export function applyAnalysisEvent(state: AnalysisRunState, event: AnalysisEvent): AnalysisRunState {
  switch (event.name) {
    case "analysis:stdout":
      return appendRunLogLines(state, [event.payload.line]);
    case "analysis:state":
      return {
        ...state,
        status: event.payload.state,
        progress: event.payload.progress,
      };
    case "analysis:finished":
      return {
        ...state,
        logPath: event.payload.logPath ?? state.logPath,
        summaryPath: event.payload.summaryPath ?? state.summaryPath,
        status: event.payload.status,
        progress: 1,
        finishedAt: event.payload.finishedAt,
        exitCode: event.payload.exitCode ?? state.exitCode,
        finished: true,
        summary: event.payload.summary,
        summaryView:
          event.payload.summary === undefined ? state.summaryView : runSummaryToViewModel(event.payload.summary),
      };
    case "analysis:error":
      return {
        ...state,
        logPath: event.payload.logPath ?? state.logPath,
        summaryPath: event.payload.summaryPath ?? state.summaryPath,
        finishedAt: event.payload.finishedAt ?? state.finishedAt,
        exitCode: event.payload.exitCode ?? state.exitCode,
        error: event.payload,
      };
    default:
      return state;
  }
}
