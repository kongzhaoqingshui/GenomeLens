import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

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

    return Promise.resolve({
      platform: { ok: true, command: "genomelens --version", version: "GenomeLens Shell 0.0.0" },
      engine: { ok: false, command: "jcvi-genomelens --version", version: "", error: "not found" },
    });
  }),
}));

import App from "./App";

afterEach(() => {
  cleanup();
  document.documentElement.className = "";
  window.localStorage.clear();
  window.location.hash = "";
});

describe("App", () => {
  it("renders the Phase 0 workbench", async () => {
    render(<App />);

    expect(screen.getByText("比较基因组学分析工作台")).toBeInTheDocument();
    expect(await screen.findByText("GenomeLens Shell 0.0.0")).toBeInTheDocument();
    const analysisRequestEntries = await screen.findAllByText(/analysis_request/);
    expect(analysisRequestEntries.length).toBeGreaterThan(0);
  });

  it("switches theme modes", async () => {
    render(<App />);

    fireEvent.click(screen.getByRole("button", { name: "深色" }));

    expect(document.documentElement).toHaveClass("dark");
    expect(window.localStorage.getItem("genomelens.theme")).toBe("dark");
  });

  it("navigates through primary entries", async () => {
    render(<App />);

    fireEvent.click(screen.getByRole("button", { name: "新建分析任务" }));

    expect(window.location.hash).toBe("#/analysis/new");
    expect(screen.getByText(/任务创建向导入口/)).toBeInTheDocument();
    expect(await screen.findByText("MCSCAN 分析向导")).toBeInTheDocument();
    expect(screen.getByText("validateAnalysisRequestDraft()")).toBeInTheDocument();
    expect(screen.getByText("draftToAnalysisRequest()")).toBeInTheDocument();
  });
});
