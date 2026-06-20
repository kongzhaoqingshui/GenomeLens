import { useCallback, useEffect, useMemo, useState } from "react";

import {
  createLoadingWorkbenchStartupResources,
  deriveWorkbenchStartupState,
  type StartupResourceKey,
  type StartupResourceState,
  type WorkbenchStartupResources,
} from "../models/jcvi-meow";
import { getAnalysisSchema, getTemplate } from "../services/analysis";
import { getVersion } from "../services/version";

function toErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

function patchResource<TData>(
  resources: WorkbenchStartupResources,
  key: StartupResourceKey,
  nextResource: StartupResourceState<TData>,
): WorkbenchStartupResources {
  return {
    ...resources,
    [key]: nextResource,
  };
}

export function useWorkbenchStartup(method = "mcscan") {
  const [reloadToken, setReloadToken] = useState(0);
  const [resources, setResources] = useState<WorkbenchStartupResources>(createLoadingWorkbenchStartupResources);

  useEffect(() => {
    let cancelled = false;

    setResources(createLoadingWorkbenchStartupResources());

    void getVersion()
      .then((data) => {
        if (!cancelled) {
          setResources((current) => patchResource(current, "version", { status: "ready", data }));
        }
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setResources((current) =>
            patchResource(current, "version", { status: "error", error: toErrorMessage(error) }),
          );
        }
      });

    void getTemplate(method)
      .then((data) => {
        if (!cancelled) {
          setResources((current) => patchResource(current, "template", { status: "ready", data }));
        }
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setResources((current) =>
            patchResource(current, "template", { status: "error", error: toErrorMessage(error) }),
          );
        }
      });

    void getAnalysisSchema()
      .then((data) => {
        if (!cancelled) {
          setResources((current) => patchResource(current, "schema", { status: "ready", data }));
        }
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setResources((current) =>
            patchResource(current, "schema", { status: "error", error: toErrorMessage(error) }),
          );
        }
      });

    return () => {
      cancelled = true;
    };
  }, [method, reloadToken]);

  const state = useMemo(() => deriveWorkbenchStartupState(resources), [resources]);
  const reload = useCallback(() => setReloadToken((current) => current + 1), []);

  return {
    ...state,
    reload,
  };
}
