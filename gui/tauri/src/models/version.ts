export interface CommandVersion {
  ok: boolean;
  command: string;
  version: string;
  error?: string;
}

export interface VersionInfo {
  platform: CommandVersion;
  engine: CommandVersion;
}
