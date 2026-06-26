import { listen, type UnlistenFn } from "@tauri-apps/api/event";
import { invoke } from "@tauri-apps/api/core";

import type { ArtifactSummary, ListArtifactsInput } from "../models/artifact";
import type { CheckReport } from "../models/check-report";
import type { CreateProjectInput, ListProjectsInput, ProjectSummary } from "../models/project";
import type {
  WorkflowEvent,
  WorkflowEventName,
  CancelRunInput,
  CancelRunResult,
  OpenPathInput,
  ReadRunLogInput,
  ReadRunSnapshotInput,
  ReadSummaryInput,
  RunAnalysisInput,
  RunHandle,
  RunLogSnapshot,
  RunSnapshot,
} from "../models/run-session";
import type { RunSummary } from "../models/run-summary";
import { runSummaryToViewModel, type RunSummaryViewModel } from "../models/run-summary-view";

export function checkEnvironment(): Promise<CheckReport> {
  return invoke<CheckReport>("check_environment");
}

export function listProjects(input: ListProjectsInput): Promise<ProjectSummary[]> {
  return invoke<ProjectSummary[]>("list_projects", { input });
}

export function createProject(input: CreateProjectInput): Promise<ProjectSummary> {
  return invoke<ProjectSummary>("create_project", { input });
}

export function listArtifacts(input: ListArtifactsInput): Promise<ArtifactSummary[]> {
  return invoke<ArtifactSummary[]>("list_artifacts", { input });
}

export function runAnalysis(input: RunAnalysisInput): Promise<RunHandle> {
  return invoke<RunHandle>("run_analysis", { input });
}

export function cancelRun(input: CancelRunInput): Promise<CancelRunResult> {
  return invoke<CancelRunResult>("cancel_run", { input });
}

export function readSummary(input: ReadSummaryInput): Promise<RunSummary> {
  return invoke<RunSummary>("read_summary", { input });
}

export async function readSummaryView(input: ReadSummaryInput): Promise<RunSummaryViewModel> {
  return runSummaryToViewModel(await readSummary(input));
}

export function readRunLog(input: ReadRunLogInput): Promise<RunLogSnapshot> {
  return invoke<RunLogSnapshot>("read_run_log", { input });
}

export function readRunSnapshot(input: ReadRunSnapshotInput): Promise<RunSnapshot> {
  return invoke<RunSnapshot>("read_run_snapshot", { input });
}

export function openPath(input: OpenPathInput): Promise<void> {
  return invoke<void>("open_path", { input });
}

export async function listenToWorkflowEvent<Name extends WorkflowEventName>(
  name: Name,
  handler: (event: Extract<WorkflowEvent, { name: Name }>) => void,
): Promise<UnlistenFn> {
  return listen<Extract<WorkflowEvent, { name: Name }>["payload"]>(name, (event) => {
    handler({ name, payload: event.payload } as Extract<WorkflowEvent, { name: Name }>);
  });
}

export async function listenToWorkflowEvents(
  handler: (event: WorkflowEvent) => void,
): Promise<UnlistenFn> {
  const unlisten = await Promise.all([
    listenToWorkflowEvent("analysis:stdout", handler),
    listenToWorkflowEvent("analysis:state", handler),
    listenToWorkflowEvent("analysis:finished", handler),
    listenToWorkflowEvent("analysis:error", handler),
  ]);

  return () => {
    unlisten.forEach((stop) => stop());
  };
}
