import { describe, expect, it } from "vitest";

import {
  applyCapabilityPresetToDraft,
  applyWorkflowPresetToDraft,
  createDraftForCapability,
  createLoadingWorkbenchStartupResources,
  deriveWorkbenchStartupState,
  getJcviCapabilityById,
  listJcviCapabilities,
} from "./jcvi-meow";
import type { AnalysisRequestDraft } from "./analysis-request-draft";

const BASE_DRAFT: AnalysisRequestDraft = {
  schemaVersion: 1,
  kind: "analysis_request",
  method: "mcscan",
  inputMode: "auto_directory",
  directory: "",
  species: [],
  referenceIndex: 0,
  outputDirectory: "",
  forceOutput: false,
  formats: ["png"],
  projectConfig: "",
  methodConfigPath: "",
  options: {
    preset: "auto",
    threads: null,
    minBlockSize: null,
    logLevel: "INFO",
    verbose: false,
    consoleLog: false,
  },
  mcscan: {
    workflow: "graphics_synteny",
    jcviEngine: "",
    blastn: "",
    makeblastdb: "",
    jcviLayout: "",
    jcviSeqids: "",
    allowSimplifiedFallback: false,
    alignSoft: "blast",
    dbtype: "nucl",
    cscore: 0.7,
    dist: 20,
    iter: 1,
    targetGeneIds: [],
    up: 20,
    down: 20,
    splitTargets: false,
    labelTargets: false,
    glyphstyle: "",
    glyphcolor: "",
    shadestyle: "",
    figsize: "",
    dpi: 300,
    optimizeFigsize: false,
    rewriteLayoutLinks: false,
    trimCrossChromosomeBlocks: false,
  },
};

describe("jcvi meow startup state", () => {
  it("tracks pending warmup resources until all three are ready", () => {
    const loading = deriveWorkbenchStartupState(createLoadingWorkbenchStartupResources());
    expect(loading.status).toBe("loading");
    expect(loading.pending).toEqual(["version", "template", "schema"]);
    expect(loading.activeHint).toBe("Checking GenomeLens and JCVI engine availability...");

    const ready = deriveWorkbenchStartupState({
      version: { status: "ready", data: { platform: { ok: true, command: "", version: "" }, engine: { ok: true, command: "", version: "" } } },
      template: { status: "ready", data: { schema_version: 1, kind: "analysis_request", method: "mcscan", input: { mode: "auto_directory" }, output: { directory: "" } } },
      schema: { status: "ready", data: { title: "AnalysisRequest" } },
    });

    expect(ready.status).toBe("ready");
    expect(ready.readyCount).toBe(3);
    expect(ready.pending).toEqual([]);
    expect(ready.activeHint).toBe("Workbench resources are ready.");
  });

  it("enters error state when any warmup resource fails", () => {
    const state = deriveWorkbenchStartupState({
      version: { status: "ready", data: { platform: { ok: true, command: "", version: "" }, engine: { ok: true, command: "", version: "" } } },
      template: { status: "error", error: "template failed" },
      schema: { status: "loading" },
    });

    expect(state.status).toBe("error");
    expect(state.failed).toEqual(["template"]);
    expect(state.pending).toEqual(["schema"]);
  });
});

describe("jcvi meow capability registry", () => {
  it("lists connected and reserved capability entries with stable routes", () => {
    const capabilities = listJcviCapabilities();
    expect(capabilities.map((entry) => entry.id)).toEqual([
      "pairwise-synteny",
      "multi-species-synteny",
      "local-synteny",
      "dotplot",
      "karyotype",
      "ortholog-catalog",
      "environment-check",
    ]);
    expect(getJcviCapabilityById("environment-check")).toMatchObject({
      route: "/settings",
      status: "connected",
      statusLabel: "Connected",
    });
    expect(getJcviCapabilityById("dotplot")).toMatchObject({
      route: "/analysis/new",
      status: "reserved",
      statusLabel: "Reserved",
      workflowPreset: "graphics_dotplot",
    });
  });
});

describe("jcvi meow workflow presets", () => {
  it("updates only the local draft workflow field", () => {
    const updated = applyWorkflowPresetToDraft(BASE_DRAFT, "local_synteny");
    expect(updated.mcscan.workflow).toBe("local_synteny");
    expect(updated.outputDirectory).toBe(BASE_DRAFT.outputDirectory);
    expect(BASE_DRAFT.mcscan.workflow).toBe("graphics_synteny");
  });

  it("applies capability presets when present", () => {
    const capability = getJcviCapabilityById("pairwise-synteny");
    expect(capability).toBeDefined();

    const updated = applyCapabilityPresetToDraft(BASE_DRAFT, capability!);
    expect(updated.mcscan.workflow).toBe("mcscan_pairwise");
  });

  it("leaves the draft unchanged for non-workflow capability entries", () => {
    const updated = createDraftForCapability(BASE_DRAFT, "environment-check");
    expect(updated).toEqual(BASE_DRAFT);
  });
});
