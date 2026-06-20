import { invoke } from "@tauri-apps/api/core";

import type { VersionInfo } from "../models/version";

export function getVersion(): Promise<VersionInfo> {
  return invoke<VersionInfo>("get_version");
}
