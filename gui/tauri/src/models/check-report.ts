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
