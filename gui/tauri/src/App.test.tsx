import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("@tauri-apps/api/core", () => ({
  invoke: vi.fn().mockResolvedValue({
    platform: { ok: true, command: "genomelens --version", version: "GenomeLens Shell 0.0.0" },
    engine: { ok: false, command: "jcvi-genomelens --version", version: "", error: "not found" },
  }),
}));

import App from "./App";

describe("App", () => {
  it("renders the Phase 0 workbench", async () => {
    render(<App />);

    expect(screen.getByText("比较基因组学分析工作台")).toBeInTheDocument();
    expect(await screen.findByText("GenomeLens Shell 0.0.0")).toBeInTheDocument();
  });
});
