import { describe, expect, it } from "vitest";

import {
  applyCapabilityPresetToDraft,
  createDraftForCapability,
  createLoadingWorkbenchStartupResources,
  deriveWorkbenchStartupState,
  getJcviCapabilityById,
  listJcviCapabilities,
} from "./jcvi-meow";
import type { WorkflowRequestDraft } from "./workflow-request-draft";

const BASE_DRAFT: WorkflowRequestDraft = {
  schemaVersion: 3,
  kind: "workflow_request",
  workflowId: "synteny",
  inputMode: "bed_cds",
  directory: "",
  species: [
    {
      name: "species_a",
      inputMode: "bed_cds",
      bed: "",
      cds: "",
      gff: "",
      genome: "",
    },
    {
      name: "species_b",
      inputMode: "bed_cds",
      bed: "",
      cds: "",
      gff: "",
      genome: "",
    },
  ],
  referenceIndex: 0,
  outputDirectory: "",
  forceOutput: false,
  formats: ["svg"],
  runtime: {
    projectConfig: "",
    engineConfig: "",
    jcviEngine: "",
    blastn: "",
    makeblastdb: "",
    lastal: "",
    lastdb: "",
    threads: null,
    minBlockSize: null,
    logLevel: "INFO",
    verbose: false,
    consoleLog: false,
  },
  parameters: {
    synteny: {
      alignSoft: "blast",
      dbtype: "nucl",
      cscore: 0.7,
      dist: 20,
      iter: 1,
      allowSimplifiedFallback: false,
      minBlockSize: 5,
    },
    localSynteny: {
      targetGeneIds: [],
      up: 20,
      down: 20,
      splitTargets: false,
      labelTargets: false,
      useNativeRenderer: false,
    },
    plot: {
      glyphstyle: "",
      glyphcolor: "",
      shadestyle: "",
      figsize: "",
      dpi: 300,
      autoOptimization: {},
    },
    histogram: {
      inputs: [],
      columns: [0],
      skip: 0,
      bins: 20,
      vmin: 0,
      vmax: null,
      xlabel: "value",
      title: "",
      base: 0,
      facet: false,
      fill: "white",
    },
    heatmap: {
      matrix: "",
      rowgroups: "",
      cmap: "",
      groups: false,
      horizontalbar: false,
    },
    extras: {},
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
      template: { status: "ready", data: { schema_version: 3, kind: "workflow_request", workflow_id: "synteny", species: [], output: { directory: "" } } },
      schema: { status: "ready", data: { title: "WorkflowRequest" } },
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
    });
  });
});

describe("jcvi meow capability presets", () => {
  it("applies pairwise preset by setting two species", () => {
    const capability = getJcviCapabilityById("pairwise-synteny");
    expect(capability).toBeDefined();

    const updated = applyCapabilityPresetToDraft(BASE_DRAFT, capability!);
    expect(updated.species).toHaveLength(2);
    expect(updated.workflowId).toBe("synteny");
  });

  it("applies multi-species preset by setting three species", () => {
    const capability = getJcviCapabilityById("multi-species-synteny");
    expect(capability).toBeDefined();

    const updated = applyCapabilityPresetToDraft(BASE_DRAFT, capability!);
    expect(updated.species).toHaveLength(3);
  });

  it("applies local synteny preset with target gene hint", () => {
    const capability = getJcviCapabilityById("local-synteny");
    expect(capability).toBeDefined();

    const updated = applyCapabilityPresetToDraft(BASE_DRAFT, capability!);
    expect(updated.parameters.localSynteny.targetGeneIds.length).toBeGreaterThan(0);
  });

  it("leaves the draft unchanged for non-workflow capability entries", () => {
    const updated = createDraftForCapability(BASE_DRAFT, "environment-check");
    expect(updated).toEqual(BASE_DRAFT);
  });
});
