import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("@tauri-apps/api/event", () => ({
  listen: vi.fn().mockResolvedValue(vi.fn()),
}));

vi.mock("@tauri-apps/api/core", () => ({
  invoke: vi.fn((command: string) => {
    if (command === "get_template") {
      return Promise.resolve({
        schema_version: 1,
        kind: "analysis_request",
        method: "mcscan",
        input: { mode: "auto_directory", directory: "" },
        output: { directory: "", force: false, formats: ["png"] },
        options: { preset: "auto", threads: null, min_block_size: null, log_level: "INFO" },
        method_config: { workflow: "graphics_synteny", align_soft: "blast", dbtype: "nucl" },
      });
    }
    if (command === "get_analysis_schema") {
      return Promise.resolve({
        title: "GenomeLens AnalysisRequest",
        properties: { kind: { const: "analysis_request" } },
      });
    }
    if (command === "run_analysis") {
      return Promise.resolve({
        runId: "run-test",
        requestPath: "request.json",
        outdir: "out",
        status: "PENDING",
      });
    }
    if (command === "read_summary") {
      return Promise.resolve({
        status: "SUCCEEDED",
        schema_version: 1,
        workflow: "graphics_synteny",
        method: "mcscan",
        task: {},
        species: [],
        final_figures: [],
        artifact_index: [],
        logs: {},
        ui: { state: "SUCCEEDED", progress: 100, primary_figures: [], summary_path: "", log_path: "" },
        scoring: { status: "", scores: [], ranking: [], message: "" },
      });
    }
    if (command === "read_run_log") {
      return Promise.resolve({
        outdir: "out",
        logPath: "out/logs/run.log",
        text: "",
        lines: [],
        truncated: false,
      });
    }
    if (command === "check_environment") {
      return Promise.resolve({
        status: "ok",
        blastn: { status: "ok", path: "blastn", message: "ready" },
        makeblastdb: { status: "ok", path: "makeblastdb", message: "ready" },
        magick: { status: "ok", path: "magick", message: "ready" },
        jcvi_engine: { status: "ok", path: "jcvi-genomelens", message: "ready" },
      });
    }
    if (command === "open_path") {
      return Promise.resolve();
    }

    return Promise.resolve({
      platform: { ok: true, command: "genomelens --version", version: "GenomeLens Shell 0.0.0" },
      engine: { ok: false, command: "jcvi-genomelens probe", version: "", error: "not found" },
    });
  }),
}));

vi.mock("@tauri-apps/plugin-dialog", () => ({
  open: vi.fn().mockResolvedValue(null),
}));

vi.mock("@tauri-apps/plugin-fs", () => ({
  mkdir: vi.fn().mockResolvedValue(undefined),
  writeTextFile: vi.fn().mockResolvedValue(undefined),
}));

import App from "./App";

afterEach(() => {
  cleanup();
  document.documentElement.className = "";
  window.localStorage.clear();
  window.location.hash = "";
});

describe("App", () => {
  it("renders the JCVI喵 desktop and startup overlay", async () => {
    render(<App />);

    expect(screen.getAllByText("JCVI喵").length).toBeGreaterThan(0);
    expect(screen.getByRole("heading", { name: "JCVI喵" })).toBeInTheDocument();
    expect(await screen.findByRole("button", { name: /双物种共线性/ })).toBeInTheDocument();
  });

  it("switches theme modes", async () => {
    render(<App />);

    fireEvent.click(await screen.findByRole("button", { name: "深色" }));

    expect(document.documentElement).toHaveClass("dark");
    expect(window.localStorage.getItem("genomelens.theme")).toBe("dark");
  });

  it("navigates from the home ring into the analysis workbench", async () => {
    render(<App />);

    fireEvent.click(await screen.findByRole("button", { name: /双物种共线性/ }));

    expect(window.location.hash).toBe("#/analysis/new?capability=pairwise-synteny");
    expect(screen.getByText(/JCVI 任务工作台/)).toBeInTheDocument();
    expect(await screen.findByText("MCSCAN 分析工作台")).toBeInTheDocument();
    expect(screen.getByText("validateAnalysisRequestDraft()")).toBeInTheDocument();
  });
});
