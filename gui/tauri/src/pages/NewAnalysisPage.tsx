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
import { validateAnalysisRequestDraft, type ValidationIssue } from "../models/validation";
import type { AppRoute } from "../routes/routes";
import { getAnalysisSchema, getTemplateDraft, type JsonObject } from "../services/analysis";

interface NewAnalysisPageProps {
  route: AppRoute;
}

const FIELD_CLASS =
  "mt-2 w-full rounded-lg border border-border bg-bg px-3 py-2 text-sm text-text-primary shadow-sm outline-none transition focus:border-ice-400 focus:ring-2 focus:ring-ice-200 dark:focus:ring-ice-900/60";
const LABEL_CLASS = "text-xs font-semibold uppercase tracking-[0.14em] text-text-tertiary";
const CHECKBOX_CLASS = "h-4 w-4 rounded border-border text-ice-500 focus:ring-ice-500";
const FIELD_GROUP_CLASS = "rounded-xl border border-border bg-surface/75 p-4 shadow-card";

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

export default function NewAnalysisPage({ route }: NewAnalysisPageProps) {
  const [draft, setDraft] = useState<AnalysisRequestDraft | null>(null);
  const [schema, setSchema] = useState<JsonObject | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

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
            <label className="mt-5 block">
              <span className={LABEL_CLASS}>输入目录</span>
              <input
                className={FIELD_CLASS}
                value={draft.directory}
                onChange={(event) => patchDraft({ directory: event.target.value })}
                placeholder="选择或输入包含 MCSCAN 输入文件的目录"
              />
              <IssueText issue={directoryIssue} />
            </label>
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
                          <input
                            className={FIELD_CLASS}
                            value={species.bed}
                            onChange={(event) => updateSpecies(index, { bed: event.target.value })}
                          />
                          <IssueText issue={issueFor(validation.issues, `input.species[${index}].bed`)} />
                        </label>
                        <label>
                          <span className={LABEL_CLASS}>CDS</span>
                          <input
                            className={FIELD_CLASS}
                            value={species.cds}
                            onChange={(event) => updateSpecies(index, { cds: event.target.value })}
                          />
                          <IssueText issue={issueFor(validation.issues, `input.species[${index}].cds`)} />
                        </label>
                      </>
                    ) : (
                      <>
                        <label>
                          <span className={LABEL_CLASS}>GFF</span>
                          <input
                            className={FIELD_CLASS}
                            value={species.gff}
                            onChange={(event) => updateSpecies(index, { gff: event.target.value })}
                          />
                          <IssueText issue={issueFor(validation.issues, `input.species[${index}].gff`)} />
                        </label>
                        <label>
                          <span className={LABEL_CLASS}>Genome FASTA</span>
                          <input
                            className={FIELD_CLASS}
                            value={species.genome}
                            onChange={(event) => updateSpecies(index, { genome: event.target.value })}
                          />
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
              <input
                className={FIELD_CLASS}
                value={draft.outputDirectory}
                onChange={(event) => patchDraft({ outputDirectory: event.target.value })}
              />
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
