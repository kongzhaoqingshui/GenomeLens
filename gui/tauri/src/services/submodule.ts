import { invoke } from "@tauri-apps/api/core";
import type { SubmoduleRequest } from "../models/submodule-request";
import {
  createDefaultSubmoduleRequestDraft,
  submoduleRequestToDraft,
  type SubmoduleRequestDraft,
} from "../models/submodule-request-draft";

const templateDraftCache = new Map<string, SubmoduleRequestDraft>();
const templatePromiseCache = new Map<string, Promise<SubmoduleRequest>>();

export function getSubmoduleTemplate(moduleId: string): Promise<SubmoduleRequest> {
  const pending = templatePromiseCache.get(moduleId);
  if (pending) {
    return pending;
  }

  const nextPromise = invoke<SubmoduleRequest>("get_submodule_template", { input: { moduleId } })
    .then((template) => {
      templatePromiseCache.delete(moduleId);
      return template;
    })
    .catch((error: unknown) => {
      templatePromiseCache.delete(moduleId);
      throw error;
    });

  templatePromiseCache.set(moduleId, nextPromise);
  return nextPromise;
}

export async function getSubmoduleTemplateDraft(moduleId: string): Promise<SubmoduleRequestDraft> {
  const cached = templateDraftCache.get(moduleId);
  if (cached) {
    return cached;
  }

  try {
    const draft = submoduleRequestToDraft(await getSubmoduleTemplate(moduleId));
    templateDraftCache.set(moduleId, draft);
    return draft;
  } catch {
    const fallback = createDefaultSubmoduleRequestDraft(moduleId);
    templateDraftCache.set(moduleId, fallback);
    return fallback;
  }
}

export function getCachedSubmoduleTemplateDraft(moduleId: string): SubmoduleRequestDraft | null {
  return templateDraftCache.get(moduleId) ?? null;
}

export function validateSubmodulePorts(
  moduleId: string,
  ports: Record<string, unknown>,
): Promise<{ valid: boolean; errors: string[] }> {
  return invoke<{ valid: boolean; errors: string[] }>("validate_submodule_ports", { input: { moduleId, ports } });
}
