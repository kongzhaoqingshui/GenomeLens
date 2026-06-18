export interface ListProjectsInput extends Record<string, unknown> {
  workspace: string;
}

export interface CreateProjectInput extends Record<string, unknown> {
  workspace: string;
  name: string;
}

export interface ProjectSummary {
  name: string;
  path: string;
  configPath?: string;
  jcviConfigPath?: string;
  updatedAt?: string;
  createdAt?: string;
  lastRunAt?: string;
  [extraField: string]: unknown;
}
