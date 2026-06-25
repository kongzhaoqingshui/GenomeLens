import { describe, expect, it } from "vitest";

import { applyWorkflowEvent, createWorkflowRunState, type RunHandle } from "./run-session";

function makeHandle(): RunHandle {
  return {
    runId: "run-1",
    requestPath: "requests/demo.json",
    outdir: "runs/demo",
    status: "PENDING",
    pid: 4123,
    startedAt: "unix-1.000",
    logPath: "runs/demo/logs/run.log",
    summaryPath: "runs/demo/report/run_summary.json",
  };
}

describe("run-session helpers", () => {
  it("collects and truncates log lines from analysis:stdout", () => {
    const initial = createWorkflowRunState(makeHandle());
    const first = applyWorkflowEvent(initial, {
      name: "analysis:stdout",
      payload: {
        runId: "run-1",
        outdir: "runs/demo",
        requestPath: "requests/demo.json",
        startedAt: "unix-1.000",
        line: "line-1",
      },
    });
    const second = applyWorkflowEvent(first, {
      name: "analysis:stdout",
      payload: {
        runId: "run-1",
        outdir: "runs/demo",
        requestPath: "requests/demo.json",
        startedAt: "unix-1.000",
        line: "line-2",
      },
    });

    expect(second.logLines).toEqual(["line-1", "line-2"]);
    expect(second.lastLogLine).toBe("line-2");
    expect(second.logPath).toBe("runs/demo/logs/run.log");
  });

  it("updates status and progress from analysis:state", () => {
    const initial = createWorkflowRunState(makeHandle());
    const next = applyWorkflowEvent(initial, {
      name: "analysis:state",
      payload: {
        runId: "run-1",
        outdir: "runs/demo",
        requestPath: "requests/demo.json",
        startedAt: "unix-1.000",
        state: "RUNNING_ENGINE",
        progress: 0.78,
      },
    });

    expect(next.status).toBe("RUNNING_ENGINE");
    expect(next.progress).toBe(0.78);
  });

  it("materializes summary view on analysis:finished", () => {
    const initial = createWorkflowRunState(makeHandle());
    const next = applyWorkflowEvent(initial, {
      name: "analysis:finished",
      payload: {
        runId: "run-1",
        outdir: "runs/demo",
        requestPath: "requests/demo.json",
        startedAt: "unix-1.000",
        exitCode: 0,
        logPath: "runs/demo/logs/run.log",
        summaryPath: "runs/demo/report/run_summary.json",
        finishedAt: "unix-2.000",
        status: "SUCCEEDED",
        summary: {
          status: "SUCCEEDED",
          schema_version: 3,
          workflow: "synteny",
          method: "synteny",
          task: {},
          species: [],
          final_figures: ["/tmp/result.png"],
          artifact_index: [
            {
              artifact_id: "figure_1",
              artifact_type: "figure",
              path: "/tmp/result.png",
              produced_by: "synteny",
              format: "png",
              preview: true,
              input_refs: [],
              metadata: {},
            },
          ],
          logs: { run_log: "/tmp/run.log" },
          ui: {
            state: "SUCCEEDED",
            progress: 1,
            primary_figures: ["/tmp/result.png"],
            summary_path: "/tmp/run_summary.json",
            log_path: "/tmp/run.log",
          },
          scoring: {
            status: "not_run",
            scores: [],
            ranking: [],
            message: "pending",
          },
        },
      },
    });

    expect(next.finished).toBe(true);
    expect(next.finishedAt).toBe("unix-2.000");
    expect(next.exitCode).toBe(0);
    expect(next.summaryPath).toBe("runs/demo/report/run_summary.json");
    expect(next.status).toBe("SUCCEEDED");
    expect(next.summaryView?.figureAssets).toHaveLength(1);
    expect(next.summaryView?.runSummaryPath).toBe("/tmp/run_summary.json");
  });

  it("captures terminal metadata from analysis:error", () => {
    const initial = createWorkflowRunState(makeHandle());
    const next = applyWorkflowEvent(initial, {
      name: "analysis:error",
      payload: {
        runId: "run-1",
        outdir: "runs/demo",
        requestPath: "requests/demo.json",
        startedAt: "unix-1.000",
        finishedAt: "unix-2.500",
        exitCode: 17,
        logPath: "runs/demo/logs/run.log",
        summaryPath: "runs/demo/report/run_summary.json",
        message: "run failed",
        code: "non_zero_exit",
      },
    });

    expect(next.error?.code).toBe("non_zero_exit");
    expect(next.finishedAt).toBe("unix-2.500");
    expect(next.exitCode).toBe(17);
    expect(next.summaryPath).toBe("runs/demo/report/run_summary.json");
  });
});
