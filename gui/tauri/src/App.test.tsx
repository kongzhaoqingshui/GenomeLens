import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("@tauri-apps/api/core", () => ({
  invoke: vi.fn().mockResolvedValue({
    platform: { ok: true, command: "genomelens --version", version: "GenomeLens Shell 0.0.0" },
    engine: { ok: false, command: "jcvi-genomelens --version", version: "", error: "not found" },
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
  });
});
