import { open } from "@tauri-apps/plugin-dialog";
import { mkdir, writeTextFile } from "@tauri-apps/plugin-fs";
import { useEffect, useMemo, useState } from "react";

import type {
  AlignSoft,
  AnalysisInputMode,
  DbType,
  LogLevel,
  McscanWorkflow,
  OutputFormat,
  SpeciesInputMode,
} from "../models/analysis-request";
import type { AnalysisRequestDraft, SpeciesInputDraft } from "../models/analysis-request-draft";
import { draftToAnalysisRequest } from "../models/analysis-request-draft";
import {
  appendRunLogLines,
  applyAnalysisEvent,
  createAnalysisRunState,
  type AnalysisRunState,
} from "../models/run-session";
import { validateAnalysisRequestDraft, type ValidationIssue } from "../models/validation";
import type { AppRoute } from "../routes/routes";
import { getAnalysisSchema, getTemplateDraft, type JsonObject } from "../services/analysis";
import { listenToAnalysisEvents, openPath, readRunLog, readSummaryView, runAnalysis } from "../services/workbench";

interface NewAnalysisPageProps {
  route: AppRoute;
}

const FIELD_CLASS =
  "mt-2 w-full rounded-lg border border-border bg-bg px-3 py-2 text-sm text-text-primary shadow-sm outline-none transition focus:border-ice-400 focus:ring-2 focus:ring-ice-200 dark:focus:ring-ice-900/60";
const LABEL_CLASS = "text-xs font-semibold uppercase tracking-[0.14em] text-text-tertiary";
const CHECKBOX_CLASS = "h-4 w-4 rounded border-border text-ice-500 focus:ring-ice-500";
const FIELD_GROUP_CLASS = "rounded-xl border border-border bg-surface/75 p-4 shadow-card";
const SECONDARY_BUTTON_CLASS =
  "rounded-lg border border-border bg-surface-raised/80 px-3 py-2 text-xs font-semibold text-text-secondary transition hover:border-ice-200 hover:bg-ice-50 hover:text-ice-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ice-500 dark:hover:border-ice-800 dark:hover:bg-ice-900/30 dark:hover:text-ice-200";

const WORKFLOW_OPTIONS = [
  "mcscan_pairwise",
  "graphics_synteny",
  "graphics_dotplot",
  "graphics_karyotype",
  "catalog_ortholog",
  "local_synteny",
];
const LOG_LEVELS: LogLevel[] = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"];
const FORMAT_OPTIONS: OutputFormat[] = ["png", "pdf", "svg"];
type RunPanelStatus = "idle" | "confirming" | "starting" | "running" | "finished" | "error";
type McscanNumberField = "cscore" | "dist" | "iter" | "up" | "down" | "dpi";
const MCSCAN_NUMBER_FIELDS: Array<{
  key: McscanNumberField;
  label: string;
  min: number;
  max?: number;
  step: number;
}> = [
  { key: "cscore", label: "cscore", min: 0, max: 1, step: 0.05 },
  { key: "dist", label: "dist", min: 1, step: 1 },
  { key: "iter", label: "iter", min: 1, step: 1 },
  { key: "up", label: "upstream", min: 0, step: 1 },
  { key: "down", label: "downstream", min: 0, step: 1 },
  { key: "dpi", label: "dpi", min: 1, step: 1 },
];

function issueFor(issues: ValidationIssue[], field: string): ValidationIssue | undefined {
  return issues.find((item) => item.field === field);
}

function IssueText({ issue }: { issue?: ValidationIssue }) {
  if (issue === undefined) {
    return null;
  }

  return <p className="mt-2 text-xs font-medium text-rose-600 dark:text-rose-300">{issue.message}</p>;
}

function SectionTitle({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <div>
      <h2 className="text-lg font-semibold text-text-primary">{title}</h2>
      <p className="mt-1 text-sm leading-6 text-text-secondary">{subtitle}</p>
    </div>
  );
}

function updateNumber(value: string): number | null {
  if (value.trim().length === 0) {
    return null;
  }
  const next = Number(value);
  return Number.isFinite(next) ? next : null;
}

function emptySpecies(inputMode: SpeciesInputMode): SpeciesInputDraft {
  return {
    name: "",
    inputMode,
    bed: "",
    cds: "",
    gff: "",
    genome: "",
  };
}

function splitTargets(value: string): string[] {
  return value
    .split(/[\n,]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function stringifyJson(value: unknown): string {
  return JSON.stringify(value, null, 2);
}

function joinPath(directory: string, filename: string): string {
  const separator = directory.includes("\\") ? "\\" : "/";
  return `${directory.replace(/[\\/]+$/, "")}${separator}${filename}`;
}

function timestampForFilename(): string {
  return new Date().toISOString().replace(/[:.]/g, "-");
}

function toProgressPercent(value: number): number {
  if (!Number.isFinite(value)) {
    return 0;
  }
  return value <= 1 ? value * 100 : value;
}

function coerceDialogPath(value: string | string[] | null): string | null {
  if (Array.isArray(value)) {
    return value[0] ?? null;
  }
  return value;
}

export default function NewAnalysisPage({ route }: NewAnalysisPageProps) {
  const [draft, setDraft] = useState<AnalysisRequestDraft | null>(null);
  const [schema, setSchema] = useState<JsonObject | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [runStatus, setRunStatus] = useState<RunPanelStatus>("idle");
  const [runState, setRunState] = useState<AnalysisRunState | null>(null);
  const [runError, setRunError] = useState<string | null>(null);
  const [pendingRequestJson, setPendingRequestJson] = useState("");

  useEffect(() => {
    let cancelled = false;

    setLoading(true);
    setLoadError(null);
    void Promise.all([getTemplateDraft("mcscan"), getAnalysisSchema()])
      .then(([templateDraft, analysisSchema]) => {
        if (!cancelled) {
          setDraft(templateDraft);
          setSchema(analysisSchema);
        }
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setLoadError(error instanceof Error ? error.message : String(error));
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const validation = useMemo(() => (draft ? validateAnalysisRequestDraft(draft) : null), [draft]);
  const requestJson = useMemo(() => (draft ? stringifyJson(draftToAnalysisRequest(draft)) : ""), [draft]);
  const schemaJson = useMemo(() => (schema ? stringifyJson(schema) : ""), [schema]);
  const targetGeneText = draft?.mcscan.targetGeneIds.join("\n") ?? "";
  const activeRunId = runState?.runId;

  useEffect(() => {
    let active = true;
    let stopListening: (() => void) | null = null;

    void listenToAnalysisEvents((event) => {
      if (!active) {
        return;
      }

      if (activeRunId && event.payload.runId !== activeRunId) {
        return;
      }

      setRunState((current) => (current ? applyAnalysisEvent(current, event) : current));

      if (event.name === "analysis:stdout") {
        setRunStatus((current) =>
          current === "idle" || current === "confirming" || current === "starting" ? "running" : current,
        );
      } else if (event.name === "analysis:state") {
        setRunStatus((current) => (current === "finished" || current === "error" ? current : "running"));
      } else if (event.name === "analysis:finished") {
        setRunStatus(event.payload.status === "SUCCEEDED" ? "finished" : "error");
      } else {
        setRunStatus("error");
        setRunError(event.payload.message);
      }
    }).then((unlisten) => {
      if (active) {
        stopListening = unlisten;
      } else {
        unlisten();
      }
    });

    return () => {
      active = false;
      stopListening?.();
    };
  }, [activeRunId]);

  useEffect(() => {
    if (!runState || !runState.finished || runState.summaryView !== undefined) {
      return;
    }

    void readSummaryView({ outdir: runState.outdir })
      .then((nextSummaryView) => {
        setRunState((current) => (current ? { ...current, summaryView: nextSummaryView } : current));
      })
      .catch((error: unknown) => {
        setRunError(error instanceof Error ? error.message : String(error));
      });
  }, [runState]);

  function patchDraft(patch: Partial<AnalysisRequestDraft>) {
    setDraft((current) => (current ? { ...current, ...patch } : current));
  }

  function patchOptions(patch: Partial<AnalysisRequestDraft["options"]>) {
    setDraft((current) => (current ? { ...current, options: { ...current.options, ...patch } } : current));
  }

  function patchMcscan(patch: Partial<AnalysisRequestDraft["mcscan"]>) {
    setDraft((current) => (current ? { ...current, mcscan: { ...current.mcscan, ...patch } } : current));
  }

  function updateSpecies(index: number, patch: Partial<SpeciesInputDraft>) {
    setDraft((current) => {
      if (!current) {
        return current;
      }
      const species = current.species.map((item, itemIndex) => (itemIndex === index ? { ...item, ...patch } : item));
      return { ...current, species };
    });
  }

  function addSpecies() {
    setDraft((current) => {
      if (!current) {
        return current;
      }
      const inputMode: SpeciesInputMode = current.inputMode === "gff_genome" ? "gff_genome" : "bed_cds";
      return { ...current, species: [...current.species, emptySpecies(inputMode)] };
    });
  }

  function removeSpecies(index: number) {
    setDraft((current) =>
      current ? { ...current, species: current.species.filter((_, itemIndex) => itemIndex !== index) } : current,
    );
  }

  function toggleFormat(format: OutputFormat) {
    setDraft((current) => {
      if (!current) {
        return current;
      }
      const formats = current.formats.includes(format)
        ? current.formats.filter((item) => item !== format)
        : [...current.formats, format];
      return { ...current, formats };
    });
  }

  async function pickDirectory(onSelect: (path: string) => void) {
    const selected = coerceDialogPath(await open({ directory: true, multiple: false }));
    if (selected) {
      onSelect(selected);
    }
  }

  async function pickFile(onSelect: (path: string) => void) {
    const selected = coerceDialogPath(await open({ directory: false, multiple: false }));
    if (selected) {
      onSelect(selected);
    }
  }

  async function handlePrepareRun() {
    if (!draft || !validation) {
      return;
    }
    if (!validation.ok) {
      setRunStatus("error");
      setRunError("请先处理校验结果中的错误，再启动分析。");
      return;
    }

    setRunError(null);
    setPendingRequestJson(requestJson);
    setRunStatus("confirming");
  }

  async function handleConfirmRun() {
    if (!draft) {
      return;
    }

    const request = draftToAnalysisRequest(draft);
    const json = stringifyJson(request);
    const requestPath = joinPath(draft.outputDirectory, `genomelens-request-${timestampForFilename()}.json`);

    setRunStatus("starting");
    setRunError(null);
    setRunState(null);

    try {
      await mkdir(draft.outputDirectory, { recursive: true });
      await writeTextFile(requestPath, `${json}\n`);
      const handle = await runAnalysis({ requestPath, outdir: draft.outputDirectory });
      setRunState(createAnalysisRunState(handle));
      setRunStatus("running");
      setPendingRequestJson("");
    } catch (error: unknown) {
      setRunStatus("error");
      setRunError(error instanceof Error ? error.message : String(error));
    }
  }

  async function handleReadSummary() {
    if (!draft && !runState) {
      return;
    }
    const outdir = runState?.outdir ?? draft?.outputDirectory ?? "";
    if (!outdir) {
      return;
    }
    try {
      const nextSummaryView = await readSummaryView({ outdir });
      setRunState((current) => (current ? { ...current, summaryView: nextSummaryView } : current));
    } catch (error: unknown) {
      setRunError(error instanceof Error ? error.message : String(error));
    }
  }

  async function handleReadLog() {
    if (!draft && !runState) {
      return;
    }
    const outdir = runState?.outdir ?? draft?.outputDirectory ?? "";
    if (!outdir) {
      return;
    }
    try {
      const snapshot = await readRunLog({ outdir, tailLines: 80 });
      setRunState((current) => {
        if (!current) {
          return current;
        }
        return appendRunLogLines({ ...current, logLines: [], lastLogLine: undefined }, snapshot.lines);
      });
    } catch (error: unknown) {
      setRunError(error instanceof Error ? error.message : String(error));
    }
  }

  async function handleOpenOutput() {
    const outdir = runState?.outdir ?? draft?.outputDirectory ?? "";
    if (outdir) {
      await openPath({ path: outdir });
    }
  }

  if (loading) {
    return (
      <section className="grid w-full content-center gap-4">
        <p className="text-sm font-semibold uppercase tracking-[0.2em] text-ice-600 dark:text-ice-300">
          GenomeLens GUI · {route.description}
        </p>
        <h1 className="text-3xl font-bold text-text-primary">正在读取 MCSCAN 模板</h1>
        <p className="text-sm text-text-secondary">Tauri command: get_template(&quot;mcscan&quot;)</p>
      </section>
    );
  }

  if (loadError || draft === null || validation === null) {
    return (
      <section className="grid w-full content-center gap-4">
        <p className="text-sm font-semibold uppercase tracking-[0.2em] text-ice-600 dark:text-ice-300">
          GenomeLens GUI · {route.description}
        </p>
        <h1 className="text-3xl font-bold text-text-primary">模板读取失败</h1>
        <p className="max-w-2xl rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700 dark:border-rose-900/50 dark:bg-rose-950/30 dark:text-rose-200">
          {loadError ?? "无法初始化 AnalysisRequestDraft"}
        </p>
      </section>
    );
  }

  const directoryIssue = issueFor(validation.issues, "input.directory");
  const outputIssue = issueFor(validation.issues, "output.directory");
  const threadsIssue = issueFor(validation.issues, "options.threads");
  const minBlockIssue = issueFor(validation.issues, "options.min_block_size");
  const workflowState = runState?.status ?? "PENDING";
  const progress = toProgressPercent(runState?.progress ?? 0);
  const logLines = runState?.logLines ?? [];
  const summaryView = runState?.summaryView ?? null;

  return (
    <div className="grid w-full gap-6 xl:grid-cols-[minmax(0,1.15fr)_minmax(23rem,0.85fr)]">
      <section className="grid gap-5">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-ice-600 dark:text-ice-300">
            GenomeLens GUI · {route.description}
          </p>
          <div className="mt-4 flex flex-wrap items-end justify-between gap-4">
            <div>
              <h1 className="text-4xl font-bold text-text-primary">MCSCAN 分析向导</h1>
              <p className="mt-3 max-w-3xl text-sm leading-7 text-text-secondary">
                默认值来自平台模板，当前表单直接编辑 AnalysisRequestDraft，并通过统一校验器反馈字段问题。
              </p>
            </div>
            <span
              className={
                validation.ok
                  ? "rounded-full bg-emerald-100 px-3 py-1 text-xs font-semibold text-emerald-700 dark:bg-emerald-400/15 dark:text-emerald-200"
                  : "rounded-full bg-amber-100 px-3 py-1 text-xs font-semibold text-amber-700 dark:bg-amber-400/15 dark:text-amber-200"
              }
            >
              {validation.ok ? "校验通过" : `${validation.issues.length} 个待处理项`}
            </span>
          </div>
        </div>

        <section className={FIELD_GROUP_CLASS}>
          <SectionTitle title="输入模式" subtitle="自动目录模式用于读取规范化项目目录；显式模式用于逐物种填入输入文件。" />
          <div className="mt-4 grid gap-4 md:grid-cols-3">
            {(["auto_directory", "bed_cds", "gff_genome"] as AnalysisInputMode[]).map((mode) => (
              <button
                key={mode}
                type="button"
                className={
                  draft.inputMode === mode
                    ? "rounded-xl border border-ice-300 bg-ice-50 p-4 text-left text-sm font-semibold text-ice-800 shadow-card dark:border-ice-700 dark:bg-ice-900/30 dark:text-ice-100"
                    : "rounded-xl border border-border bg-bg p-4 text-left text-sm font-semibold text-text-secondary transition hover:border-ice-200 hover:bg-ice-50 dark:hover:border-ice-800 dark:hover:bg-ice-900/20"
                }
                onClick={() => patchDraft({ inputMode: mode })}
              >
                {mode}
              </button>
            ))}
          </div>

          {draft.inputMode === "auto_directory" ? (
            <div className="mt-5">
              <span className={LABEL_CLASS}>输入目录</span>
              <div className="mt-2 flex gap-2">
                <input
                  className="w-full rounded-lg border border-border bg-bg px-3 py-2 text-sm text-text-primary shadow-sm outline-none transition focus:border-ice-400 focus:ring-2 focus:ring-ice-200 dark:focus:ring-ice-900/60"
                  value={draft.directory}
                  onChange={(event) => patchDraft({ directory: event.target.value })}
                  placeholder="选择包含 MCSCAN 输入文件的目录"
                />
                <button type="button" className={SECONDARY_BUTTON_CLASS} onClick={() => pickDirectory((path) => patchDraft({ directory: path }))}>
                  选择
                </button>
              </div>
              <IssueText issue={directoryIssue} />
            </div>
          ) : (
            <div className="mt-5 grid gap-4">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <h3 className="text-sm font-semibold text-text-primary">物种输入</h3>
                  <p className="mt-1 text-xs text-text-secondary">显式输入至少需要两个物种，参考物种索引从 0 开始。</p>
                </div>
                <button
                  type="button"
                  className="rounded-lg bg-ice-500 px-3 py-2 text-xs font-semibold text-white shadow-lg shadow-ice-500/20 transition hover:bg-ice-400"
                  onClick={addSpecies}
                >
                  添加物种
                </button>
              </div>

              {draft.species.map((species, index) => (
                <article key={index} className="rounded-xl border border-border bg-bg p-4">
                  <div className="flex items-center justify-between gap-3">
                    <h4 className="text-sm font-semibold text-text-primary">Species {index + 1}</h4>
                    <button
                      type="button"
                      className="rounded-lg border border-border px-3 py-1.5 text-xs font-semibold text-text-secondary transition hover:border-rose-200 hover:text-rose-600"
                      onClick={() => removeSpecies(index)}
                    >
                      移除
                    </button>
                  </div>
                  <div className="mt-4 grid gap-4 md:grid-cols-2">
                    <label>
                      <span className={LABEL_CLASS}>名称</span>
                      <input
                        className={FIELD_CLASS}
                        value={species.name}
                        onChange={(event) => updateSpecies(index, { name: event.target.value })}
                      />
                      <IssueText issue={issueFor(validation.issues, `input.species[${index}].name`)} />
                    </label>
                    <label>
                      <span className={LABEL_CLASS}>输入类型</span>
                      <select
                        className={FIELD_CLASS}
                        value={species.inputMode}
                        onChange={(event) =>
                          updateSpecies(index, { inputMode: event.target.value as SpeciesInputMode })
                        }
                      >
                        <option value="bed_cds">bed_cds</option>
                        <option value="gff_genome">gff_genome</option>
                      </select>
                    </label>
                    {species.inputMode === "bed_cds" ? (
                      <>
                        <label>
                          <span className={LABEL_CLASS}>BED</span>
                          <div className="mt-2 flex gap-2">
                            <input
                              className="w-full rounded-lg border border-border bg-bg px-3 py-2 text-sm text-text-primary shadow-sm outline-none transition focus:border-ice-400 focus:ring-2 focus:ring-ice-200 dark:focus:ring-ice-900/60"
                              value={species.bed}
                              onChange={(event) => updateSpecies(index, { bed: event.target.value })}
                            />
                            <button type="button" className={SECONDARY_BUTTON_CLASS} onClick={() => pickFile((path) => updateSpecies(index, { bed: path }))}>
                              选择
                            </button>
                          </div>
                          <IssueText issue={issueFor(validation.issues, `input.species[${index}].bed`)} />
                        </label>
                        <label>
                          <span className={LABEL_CLASS}>CDS</span>
                          <div className="mt-2 flex gap-2">
                            <input
                              className="w-full rounded-lg border border-border bg-bg px-3 py-2 text-sm text-text-primary shadow-sm outline-none transition focus:border-ice-400 focus:ring-2 focus:ring-ice-200 dark:focus:ring-ice-900/60"
                              value={species.cds}
                              onChange={(event) => updateSpecies(index, { cds: event.target.value })}
                            />
                            <button type="button" className={SECONDARY_BUTTON_CLASS} onClick={() => pickFile((path) => updateSpecies(index, { cds: path }))}>
                              选择
                            </button>
                          </div>
                          <IssueText issue={issueFor(validation.issues, `input.species[${index}].cds`)} />
                        </label>
                      </>
                    ) : (
                      <>
                        <label>
                          <span className={LABEL_CLASS}>GFF</span>
                          <div className="mt-2 flex gap-2">
                            <input
                              className="w-full rounded-lg border border-border bg-bg px-3 py-2 text-sm text-text-primary shadow-sm outline-none transition focus:border-ice-400 focus:ring-2 focus:ring-ice-200 dark:focus:ring-ice-900/60"
                              value={species.gff}
                              onChange={(event) => updateSpecies(index, { gff: event.target.value })}
                            />
                            <button type="button" className={SECONDARY_BUTTON_CLASS} onClick={() => pickFile((path) => updateSpecies(index, { gff: path }))}>
                              选择
                            </button>
                          </div>
                          <IssueText issue={issueFor(validation.issues, `input.species[${index}].gff`)} />
                        </label>
                        <label>
                          <span className={LABEL_CLASS}>Genome FASTA</span>
                          <div className="mt-2 flex gap-2">
                            <input
                              className="w-full rounded-lg border border-border bg-bg px-3 py-2 text-sm text-text-primary shadow-sm outline-none transition focus:border-ice-400 focus:ring-2 focus:ring-ice-200 dark:focus:ring-ice-900/60"
                              value={species.genome}
                              onChange={(event) => updateSpecies(index, { genome: event.target.value })}
                            />
                            <button type="button" className={SECONDARY_BUTTON_CLASS} onClick={() => pickFile((path) => updateSpecies(index, { genome: path }))}>
                              选择
                            </button>
                          </div>
                          <IssueText issue={issueFor(validation.issues, `input.species[${index}].genome`)} />
                        </label>
                      </>
                    )}
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>

        <section className={FIELD_GROUP_CLASS}>
          <SectionTitle title="输出与运行选项" subtitle="这些字段会映射到 output、options 和 config，不在页面中展开私有路径。" />
          <div className="mt-4 grid gap-4 md:grid-cols-2">
            <label>
              <span className={LABEL_CLASS}>输出目录</span>
              <div className="mt-2 flex gap-2">
                <input
                  className="w-full rounded-lg border border-border bg-bg px-3 py-2 text-sm text-text-primary shadow-sm outline-none transition focus:border-ice-400 focus:ring-2 focus:ring-ice-200 dark:focus:ring-ice-900/60"
                  value={draft.outputDirectory}
                  onChange={(event) => patchDraft({ outputDirectory: event.target.value })}
                />
                <button type="button" className={SECONDARY_BUTTON_CLASS} onClick={() => pickDirectory((path) => patchDraft({ outputDirectory: path }))}>
                  选择
                </button>
              </div>
              <IssueText issue={outputIssue} />
            </label>
            <label>
              <span className={LABEL_CLASS}>参考物种索引</span>
              <input
                className={FIELD_CLASS}
                type="number"
                min={0}
                value={draft.referenceIndex}
                onChange={(event) => patchDraft({ referenceIndex: Number(event.target.value) })}
              />
              <IssueText issue={issueFor(validation.issues, "input.reference_index")} />
            </label>
            <label>
              <span className={LABEL_CLASS}>线程数</span>
              <input
                className={FIELD_CLASS}
                type="number"
                min={1}
                value={draft.options.threads ?? ""}
                onChange={(event) => patchOptions({ threads: updateNumber(event.target.value) })}
              />
              <IssueText issue={threadsIssue} />
            </label>
            <label>
              <span className={LABEL_CLASS}>最小 block 大小</span>
              <input
                className={FIELD_CLASS}
                type="number"
                min={1}
                value={draft.options.minBlockSize ?? ""}
                onChange={(event) => patchOptions({ minBlockSize: updateNumber(event.target.value) })}
              />
              <IssueText issue={minBlockIssue} />
            </label>
            <label>
              <span className={LABEL_CLASS}>日志级别</span>
              <select
                className={FIELD_CLASS}
                value={draft.options.logLevel}
                onChange={(event) => patchOptions({ logLevel: event.target.value as LogLevel })}
              >
                {LOG_LEVELS.map((level) => (
                  <option key={level} value={level}>
                    {level}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <span className={LABEL_CLASS}>Preset</span>
              <input
                className={FIELD_CLASS}
                value={draft.options.preset}
                onChange={(event) => patchOptions({ preset: event.target.value })}
              />
            </label>
          </div>

          <div className="mt-5 flex flex-wrap gap-4">
            {FORMAT_OPTIONS.map((format) => (
              <label key={format} className="inline-flex items-center gap-2 text-sm font-medium text-text-secondary">
                <input
                  className={CHECKBOX_CLASS}
                  type="checkbox"
                  checked={draft.formats.includes(format)}
                  onChange={() => toggleFormat(format)}
                />
                {format}
              </label>
            ))}
            {[
              ["forceOutput", "覆盖输出"],
              ["verbose", "verbose"],
              ["consoleLog", "console log"],
            ].map(([key, label]) => (
              <label key={key} className="inline-flex items-center gap-2 text-sm font-medium text-text-secondary">
                <input
                  className={CHECKBOX_CLASS}
                  type="checkbox"
                  checked={
                    key === "forceOutput"
                      ? draft.forceOutput
                      : key === "verbose"
                        ? draft.options.verbose
                        : draft.options.consoleLog
                  }
                  onChange={(event) => {
                    if (key === "forceOutput") {
                      patchDraft({ forceOutput: event.target.checked });
                    } else if (key === "verbose") {
                      patchOptions({ verbose: event.target.checked });
                    } else {
                      patchOptions({ consoleLog: event.target.checked });
                    }
                  }}
                />
                {label}
              </label>
            ))}
          </div>
        </section>

        <section className={FIELD_GROUP_CLASS}>
          <SectionTitle title="MCSCAN 参数" subtitle="字段名保持和平台契约一致，默认值来自模板转换后的 draft。" />
          <div className="mt-4 grid gap-4 md:grid-cols-3">
            <label>
              <span className={LABEL_CLASS}>workflow</span>
              <select
                className={FIELD_CLASS}
                value={draft.mcscan.workflow}
                onChange={(event) => patchMcscan({ workflow: event.target.value as McscanWorkflow })}
              >
                {WORKFLOW_OPTIONS.map((workflow) => (
                  <option key={workflow} value={workflow}>
                    {workflow}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <span className={LABEL_CLASS}>align_soft</span>
              <select
                className={FIELD_CLASS}
                value={draft.mcscan.alignSoft}
                onChange={(event) => patchMcscan({ alignSoft: event.target.value as AlignSoft })}
              >
                <option value="blast">blast</option>
                <option value="last">last</option>
                <option value="diamond_blastp">diamond_blastp</option>
              </select>
            </label>
            <label>
              <span className={LABEL_CLASS}>dbtype</span>
              <select
                className={FIELD_CLASS}
                value={draft.mcscan.dbtype}
                onChange={(event) => patchMcscan({ dbtype: event.target.value as DbType })}
              >
                <option value="nucl">nucl</option>
                <option value="prot">prot</option>
              </select>
            </label>
            {MCSCAN_NUMBER_FIELDS.map(({ key, label, min, max, step }) => (
              <label key={key}>
                <span className={LABEL_CLASS}>{label}</span>
                <input
                  className={FIELD_CLASS}
                  type="number"
                  min={min}
                  max={max}
                  step={step}
                  value={draft.mcscan[key]}
                  onChange={(event) => patchMcscan({ [key]: Number(event.target.value) })}
                />
              </label>
            ))}
            <label>
              <span className={LABEL_CLASS}>figsize</span>
              <input
                className={FIELD_CLASS}
                value={draft.mcscan.figsize}
                onChange={(event) => patchMcscan({ figsize: event.target.value })}
              />
            </label>
            <label>
              <span className={LABEL_CLASS}>glyphstyle</span>
              <input
                className={FIELD_CLASS}
                value={draft.mcscan.glyphstyle}
                onChange={(event) => patchMcscan({ glyphstyle: event.target.value })}
              />
            </label>
            <label>
              <span className={LABEL_CLASS}>glyphcolor</span>
              <input
                className={FIELD_CLASS}
                value={draft.mcscan.glyphcolor}
                onChange={(event) => patchMcscan({ glyphcolor: event.target.value })}
              />
            </label>
          </div>

          <label className="mt-4 block">
            <span className={LABEL_CLASS}>target_gene_ids</span>
            <textarea
              className={`${FIELD_CLASS} min-h-28`}
              value={targetGeneText}
              onChange={(event) => patchMcscan({ targetGeneIds: splitTargets(event.target.value) })}
              placeholder="每行或逗号分隔一个目标基因 ID"
            />
            <IssueText issue={issueFor(validation.issues, "method_config.target_gene_ids")} />
          </label>

          <div className="mt-5 grid gap-3 md:grid-cols-2">
            {[
              ["allowSimplifiedFallback", "allow_simplified_fallback"],
              ["splitTargets", "split_targets"],
              ["labelTargets", "label_targets"],
              ["optimizeFigsize", "optimize_figsize"],
              ["rewriteLayoutLinks", "rewrite_layout_links"],
              ["trimCrossChromosomeBlocks", "trim_cross_chromosome_blocks"],
            ].map(([key, label]) => (
              <label key={key} className="inline-flex items-center gap-2 text-sm font-medium text-text-secondary">
                <input
                  className={CHECKBOX_CLASS}
                  type="checkbox"
                  checked={draft.mcscan[key as keyof AnalysisRequestDraft["mcscan"]] as boolean}
                  onChange={(event) => patchMcscan({ [key]: event.target.checked })}
                />
                {label}
              </label>
            ))}
          </div>
        </section>
      </section>

      <aside className="grid content-start gap-5">
        <section className={FIELD_GROUP_CLASS}>
          <SectionTitle title="运行面板" subtitle="runAnalysis() + listenToAnalysisEvents()" />
          <div className="mt-4 flex flex-wrap items-center gap-3">
            <button
              type="button"
              className="rounded-lg bg-ice-500 px-4 py-2 text-sm font-semibold text-white shadow-lg shadow-ice-500/20 transition hover:bg-ice-400 disabled:cursor-not-allowed disabled:opacity-50"
              disabled={runStatus === "starting" || runStatus === "running"}
              onClick={handlePrepareRun}
            >
              Run
            </button>
            <button type="button" className={SECONDARY_BUTTON_CLASS} onClick={handleReadSummary}>
              读取 summary
            </button>
            <button type="button" className={SECONDARY_BUTTON_CLASS} onClick={handleReadLog}>
              读取日志
            </button>
            <button type="button" className={SECONDARY_BUTTON_CLASS} onClick={handleOpenOutput}>
              打开输出目录
            </button>
          </div>

          <div className="mt-4 grid gap-3 rounded-xl border border-border bg-bg p-4">
            <div className="flex items-center justify-between gap-3">
              <span className="text-xs font-semibold uppercase tracking-[0.14em] text-text-tertiary">当前状态</span>
              <span className="rounded-full bg-ice-100 px-3 py-1 text-xs font-semibold text-ice-700 dark:bg-ice-900/40 dark:text-ice-200">
                {runStatus} / {workflowState}
              </span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-ice-100 dark:bg-ice-900/40">
              <div className="h-full rounded-full bg-ice-500 transition-all" style={{ width: `${Math.max(0, Math.min(progress, 100))}%` }} />
            </div>
            {runState ? (
              <div className="grid gap-1 font-mono text-xs text-text-tertiary">
                <span>runId: {runState.runId}</span>
                <span>outdir: {runState.outdir}</span>
              </div>
            ) : null}
            {runError ? <p className="text-sm font-medium text-rose-600 dark:text-rose-300">{runError}</p> : null}
          </div>

          {runStatus === "confirming" ? (
            <div className="mt-4 rounded-xl border border-amber-200 bg-amber-50 p-4 dark:border-amber-900/40 dark:bg-amber-950/20">
              <h3 className="text-sm font-semibold text-text-primary">确认 AnalysisRequest JSON</h3>
              <pre className="mt-3 max-h-64 overflow-auto rounded-lg border border-border bg-bg p-3 font-mono text-xs leading-6 text-text-secondary">
                {pendingRequestJson}
              </pre>
              <div className="mt-3 flex gap-2">
                <button type="button" className="rounded-lg bg-ice-500 px-3 py-2 text-xs font-semibold text-white" onClick={handleConfirmRun}>
                  确认运行
                </button>
                <button type="button" className={SECONDARY_BUTTON_CLASS} onClick={() => setRunStatus("idle")}>
                  取消
                </button>
              </div>
            </div>
          ) : null}

          <div className="mt-4">
            <h3 className="text-sm font-semibold text-text-primary">最近日志</h3>
            <pre className="mt-3 max-h-56 overflow-auto rounded-xl border border-border bg-bg p-4 font-mono text-xs leading-6 text-text-secondary">
              {logLines.length > 0 ? logLines.join("\n") : "等待 analysis:stdout 或 read_run_log()"}
            </pre>
          </div>
        </section>

        <section className={FIELD_GROUP_CLASS}>
          <SectionTitle title="结果轻展示" subtitle="read_summary() -> RunSummaryViewModel" />
          {summaryView ? (
            <div className="mt-4 grid gap-4">
              <div className="grid gap-2 rounded-xl border border-border bg-bg p-4 text-sm text-text-secondary">
                <div className="flex justify-between gap-3">
                  <span>status</span>
                  <span className="font-semibold text-text-primary">{summaryView.status}</span>
                </div>
                <div className="flex justify-between gap-3">
                  <span>workflow</span>
                  <span className="font-semibold text-text-primary">{summaryView.workflow}</span>
                </div>
                <div className="flex justify-between gap-3">
                  <span>progress</span>
                  <span className="font-semibold text-text-primary">{toProgressPercent(summaryView.progress)}%</span>
                </div>
              </div>
              <div>
                <h3 className="text-sm font-semibold text-text-primary">主要图件</h3>
                <div className="mt-3 grid gap-2">
                  {summaryView.figureAssets.length > 0 ? (
                    summaryView.figureAssets.slice(0, 8).map((asset) => (
                      <div key={asset.path} className="rounded-lg border border-border bg-bg p-3">
                        <p className="text-sm font-semibold text-text-primary">{asset.name}</p>
                        <p className="mt-1 break-all font-mono text-xs text-text-tertiary">{asset.path}</p>
                      </div>
                    ))
                  ) : (
                    <p className="rounded-lg border border-border bg-bg p-3 text-sm text-text-secondary">summary 暂无图件索引。</p>
                  )}
                </div>
              </div>
            </div>
          ) : (
            <p className="mt-4 rounded-lg border border-border bg-bg p-3 text-sm text-text-secondary">
              运行结束后会自动读取 summary，也可以手动点击“读取 summary”。
            </p>
          )}
        </section>

        <section className={FIELD_GROUP_CLASS}>
          <SectionTitle title="校验结果" subtitle="validateAnalysisRequestDraft()" />
          {validation.issues.length === 0 ? (
            <p className="mt-4 rounded-lg bg-emerald-50 p-3 text-sm font-medium text-emerald-700 dark:bg-emerald-400/10 dark:text-emerald-200">
              当前 draft 可以转换为 AnalysisRequest。
            </p>
          ) : (
            <div className="mt-4 grid gap-2">
              {validation.issues.map((item) => (
                <div key={`${item.field}-${item.code}`} className="rounded-lg border border-border bg-bg p-3">
                  <p className="font-mono text-[11px] text-text-tertiary">{item.field}</p>
                  <p className="mt-1 text-sm font-medium text-text-primary">{item.message}</p>
                </div>
              ))}
            </div>
          )}
        </section>

        <section className={FIELD_GROUP_CLASS}>
          <SectionTitle title="请求预览" subtitle="draftToAnalysisRequest()" />
          <pre className="mt-4 max-h-[26rem] overflow-auto rounded-xl border border-border bg-bg p-4 font-mono text-xs leading-6 text-text-secondary">
            {requestJson}
          </pre>
        </section>

        <section className={FIELD_GROUP_CLASS}>
          <SectionTitle title="Schema 参考" subtitle="get_analysis_schema()" />
          <pre className="mt-4 max-h-72 overflow-auto rounded-xl border border-border bg-bg p-4 font-mono text-xs leading-6 text-text-secondary">
            {schemaJson || "Schema 未返回"}
          </pre>
        </section>
      </aside>
    </div>
  );
}
