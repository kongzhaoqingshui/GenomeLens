export type CheckToolStatus = "ok" | "missing" | "error" | "unknown" | string;

export interface CheckToolItem {
  status: CheckToolStatus;
  path?: string;
  message?: string;
  [extraField: string]: unknown;
}

export interface CheckReport {
  status: CheckToolStatus;
  blastn: CheckToolItem;
  makeblastdb: CheckToolItem;
  magick: CheckToolItem;
  jcvi_engine: CheckToolItem;
  install_attempts?: Array<Record<string, unknown>>;
  engine_candidate_names?: string[];
}

export interface EngineProbeInfo {
  engineName: string;
  engineVersion: string;
  jcviUpstreamVersion: string;
  patchset: string;
  python: string;
  platform: string;
  distribution: string;
  status: string;
  capabilities: string[];
  dispatchableWorkflows: string[];
  bundledJcviModules: string[];
}

export interface CheckToolViewModel {
  id: "blastn" | "makeblastdb" | "magick" | "jcvi_engine";
  label: string;
  status: CheckToolStatus;
  path: string;
  message: string;
  extra: Record<string, unknown>;
}

export function getCheckToolItems(report: CheckReport): CheckToolViewModel[] {
  return [
    { id: "blastn", label: "BLAST+ blastn", ...toCheckToolViewModel("blastn", report.blastn) },
    { id: "makeblastdb", label: "BLAST+ makeblastdb", ...toCheckToolViewModel("makeblastdb", report.makeblastdb) },
    { id: "magick", label: "ImageMagick", ...toCheckToolViewModel("magick", report.magick) },
    { id: "jcvi_engine", label: "JCVI Engine", ...toCheckToolViewModel("jcvi_engine", report.jcvi_engine) },
  ];
}

export function getEngineProbeInfo(report: CheckReport): EngineProbeInfo | null {
  const extra = report.jcvi_engine;
  if (!extra || typeof extra !== "object") {
    return null;
  }

  const raw = extra as Record<string, unknown>;
  if (!raw.engine_version && !raw.engine_name) {
    return null;
  }

  return {
    engineName: String(raw.engine_name ?? "JCVI Engine"),
    engineVersion: String(raw.engine_version ?? ""),
    jcviUpstreamVersion: String(raw.jcvi_upstream_version ?? ""),
    patchset: String(raw.patchset ?? ""),
    python: String(raw.python ?? ""),
    platform: String(raw.platform ?? ""),
    distribution: String(raw.distribution ?? ""),
    status: String(raw.status ?? extra.status ?? "unknown"),
    capabilities: Array.isArray(raw.capabilities) ? (raw.capabilities as string[]) : [],
    dispatchableWorkflows: Array.isArray(raw.dispatchable_workflows)
      ? (raw.dispatchable_workflows as string[])
      : [],
    bundledJcviModules: Array.isArray(raw.bundled_jcvi_modules)
      ? (raw.bundled_jcvi_modules as string[])
      : [],
  };
}

function toCheckToolViewModel(
  id: CheckToolViewModel["id"],
  item: CheckToolItem | undefined,
): Omit<CheckToolViewModel, "id" | "label"> {
  if (item === undefined) {
    return {
      status: "unknown",
      path: "",
      message: "",
      extra: {},
    };
  }

  const { status, path, message, ...extra } = item;
  return {
    status,
    path: typeof path === "string" ? path : "",
    message: typeof message === "string" ? message : "",
    extra,
  };
}
