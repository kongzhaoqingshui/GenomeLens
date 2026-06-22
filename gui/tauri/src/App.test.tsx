import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

const { invokeMock, dialogOpenMock, mkdirMock, writeTextFileMock } = vi.hoisted(() => ({
  invokeMock: vi.fn<(command: string, payload?: Record<string, unknown>) => Promise<unknown>>((command: string) => {
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
    if (command === "read_request_preview") {
      return Promise.resolve({
        requestPath: "/imports/request.json",
        json: {
          schema_version: 1,
          kind: "analysis_request",
          method: "mcscan",
          input: { mode: "auto_directory", directory: "/inputs/demo" },
          output: { directory: "/runs/from-request", force: false, formats: ["png"] },
          options: { preset: "auto", log_level: "INFO" },
          method_config: { workflow: "mcscan_pairwise", align_soft: "blast", dbtype: "nucl" },
        },
        method: "mcscan",
        workflow: "mcscan_pairwise",
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
    if (command === "list_artifacts") {
      return Promise.resolve([
        {
          path: "/runs/demo/report/pairwise.png",
          name: "pairwise.png",
          format: "png",
          source: "final_figures",
          preview: true,
        },
      ]);
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
    if (command === "list_projects") {
      return Promise.resolve([
        {
          name: "Demo Project",
          path: "/workspace/demo-project",
          configPath: "/workspace/demo-project/.genomelens/project.json",
          jcviConfigPath: "/workspace/demo-project/jcvi.yaml",
          updatedAt: "2026-06-22T00:00:00Z",
          createdAt: "2026-06-21T00:00:00Z",
          lastRunAt: "2026-06-22T01:00:00Z",
        },
      ]);
    }
    if (command === "create_project") {
      return Promise.resolve({
        name: "Created Project",
        path: "/workspace/Created Project",
        configPath: "/workspace/Created Project/.genomelens/project.json",
        jcviConfigPath: "/workspace/Created Project/jcvi.yaml",
        updatedAt: "2026-06-22T00:00:00Z",
        createdAt: "2026-06-22T00:00:00Z",
        lastRunAt: "",
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
  dialogOpenMock: vi.fn().mockResolvedValue(null),
  mkdirMock: vi.fn().mockResolvedValue(undefined),
  writeTextFileMock: vi.fn().mockResolvedValue(undefined),
}));

vi.mock("@tauri-apps/api/event", () => ({
  listen: vi.fn().mockResolvedValue(vi.fn()),
}));

vi.mock("@tauri-apps/api/core", () => ({
  invoke: invokeMock,
}));

vi.mock("@tauri-apps/plugin-dialog", () => ({
  open: dialogOpenMock,
}));

vi.mock("@tauri-apps/plugin-fs", () => ({
  mkdir: mkdirMock,
  writeTextFile: writeTextFileMock,
}));

import App from "./App";

afterEach(() => {
  cleanup();
  document.documentElement.className = "";
  window.localStorage.clear();
  window.location.hash = "";
  invokeMock.mockClear();
  dialogOpenMock.mockReset();
  dialogOpenMock.mockResolvedValue(null);
  mkdirMock.mockClear();
  writeTextFileMock.mockClear();
});

describe("App", () => {
  it("renders the JCVI meow desktop and startup overlay", async () => {
    render(<App />);

    expect(screen.getAllByText("JCVI meow").length).toBeGreaterThan(0);
    expect(screen.getByRole("heading", { name: "JCVI meow" })).toBeInTheDocument();
    expect(await screen.findByRole("button", { name: "双物种共线性" })).toBeInTheDocument();
  });

  it("switches theme modes", async () => {
    render(<App />);

    fireEvent.click(await screen.findByRole("button", { name: "深色" }));

    expect(document.documentElement).toHaveClass("dark");
    expect(window.localStorage.getItem("genomelens.theme")).toBe("dark");
  });

  it("defaults to Chinese and can switch language to English in settings", async () => {
    window.location.hash = "#/settings";
    render(<App />);

    expect(await screen.findByRole("heading", { name: "环境与参考" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "English" }));

    expect(window.localStorage.getItem("genomelens.language")).toBe("en");
    expect(await screen.findByRole("heading", { name: "Environment and references" })).toBeInTheDocument();
  });

  it("navigates from the home surface into the analysis workbench", async () => {
    render(<App />);

    const [primaryAction] = await screen.findAllByRole("button", { name: "打开工作台" });
    fireEvent.click(primaryAction);

    expect(window.location.hash).toBe("#/analysis/new?capability=pairwise-synteny");
    expect(await screen.findByRole("heading", { name: "任务" })).toBeInTheDocument();
    expect(screen.getByDisplayValue("Pairwise Synteny #1")).toBeInTheDocument();
    expect(screen.getByText("输入与输出")).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "运行" }).length).toBeGreaterThan(0);
  });

  it("renders the projects page with workspace controls and project rows", async () => {
    window.location.hash = "#/projects";
    render(<App />);

    expect(await screen.findByRole("heading", { name: "工作区项目" })).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("工作区路径"), {
      target: { value: "/workspace" },
    });
    fireEvent.click(screen.getByRole("button", { name: "刷新项目" }));

    expect(await screen.findByText("Demo Project")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "创建项目" })).toBeInTheDocument();
  });

  it("renders the results page with summary loading controls", async () => {
    window.location.hash = "#/results";
    render(<App />);

    expect(await screen.findByRole("heading", { name: "运行摘要浏览器" })).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("输出目录"), {
      target: { value: "/runs/demo" },
    });
    fireEvent.click(screen.getByRole("button", { name: "加载摘要" }));

    expect(await screen.findByText("主要图件")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "产物" })).toBeInTheDocument();
    expect(await screen.findByText("pairwise.png")).toBeInTheDocument();
  });

  it("imports an existing request JSON and runs it with the current outdir", async () => {
    dialogOpenMock.mockResolvedValueOnce("/imports/request.json");

    render(<App />);

    const [primaryAction] = await screen.findAllByRole("button", { name: "打开工作台" });
    fireEvent.click(primaryAction);

    expect(await screen.findByText("输入与输出")).toBeInTheDocument();
    fireEvent.change(screen.getByPlaceholderText("选择当前任务的输出位置"), {
      target: { value: "/runs/out" },
    });
    fireEvent.click(screen.getByRole("button", { name: "导入 request JSON" }));

    expect((await screen.findAllByText("/imports/request.json")).length).toBeGreaterThan(0);
    expect(screen.getAllByText("mcscan_pairwise").length).toBeGreaterThan(0);
    expect(screen.getAllByRole("button", { name: "运行" }).length).toBeGreaterThan(0);

    const runButtons = screen.getAllByRole("button", { name: "运行" });
    fireEvent.click(runButtons[runButtons.length - 1]!);
    fireEvent.click(await screen.findByRole("button", { name: "确认运行" }));

    await waitFor(() => {
      const runAnalysisCall = invokeMock.mock.calls.find(([command]) => command === "run_analysis");
      const runAnalysisPayload = runAnalysisCall?.[1];

      expect(runAnalysisPayload).toMatchObject({
        requestPath: "/imports/request.json",
        outdir: "/runs/out",
      });
    });
    expect(writeTextFileMock).not.toHaveBeenCalled();
  });
});
