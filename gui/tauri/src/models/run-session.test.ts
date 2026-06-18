import { describe, expect, it } from "vitest";

import { applyAnalysisEvent, createAnalysisRunState, type RunHandle } from "./run-session";

function makeHandle(): RunHandle {
  return {
    runId: "run-1",
    requestPath: "requests/demo.json",
    outdir: "runs/demo",
    status: "PENDING",
    startedAt: "unix-1.000",
  };
}

describe("run-session helpers", () => {
  it("collects and truncates log lines from analysis:stdout", () => {
    const initial = createAnalysisRunState(makeHandle());
    const first = applyAnalysisEvent(initial, {
      name: "analysis:stdout",
      payload: {
        runId: "run-1",
        outdir: "runs/demo",
        requestPath: "requests/demo.json",
        startedAt: "unix-1.000",
        line: "line-1",
      },
    });
    const second = applyAnalysisEvent(first, {
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
  });

  it("updates status and progress from analysis:state", () => {
    const initial = createAnalysisRunState(makeHandle());
    const next = applyAnalysisEvent(initial, {
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
    const initial = createAnalysisRunState(makeHandle());
    const next = applyAnalysisEvent(initial, {
      name: "analysis:finished",
      payload: {
        runId: "run-1",
        outdir: "runs/demo",
        requestPath: "requests/demo.json",
        startedAt: "unix-1.000",
        finishedAt: "unix-2.000",
        status: "SUCCEEDED",
        summary: {
          status: "SUCCEEDED",
          schema_version: 2,
          workflow: "mcscan",
          method: "mcscan",
          task: {},
          species: [],
          final_figures: ["/tmp/result.png"],
          artifact_index: [
            {
              artifact_id: "figure_1",
              artifact_type: "figure",
              path: "/tmp/result.png",
              produced_by: "mcscan",
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
    expect(next.status).toBe("SUCCEEDED");
    expect(next.summaryView?.figureAssets).toHaveLength(1);
    expect(next.summaryView?.runSummaryPath).toBe("/tmp/run_summary.json");
  });
});
