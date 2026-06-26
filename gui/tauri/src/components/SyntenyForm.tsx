import { useCallback, useMemo } from "react";
import { Sliders, Play, LayoutList } from "lucide-react";
import { CollapsibleSection } from "./CollapsibleSection";
import { SectionHeader } from "./ui";
import { PathField } from "./PathField";
import type { CapabilityEntry } from "../models/capability";
import type { WorkflowRequestDraft, SpeciesInputDraft, WorkflowRequestInputMode } from "../models/workflow-request-draft";

const FIELD_CLASS =
  "mt-2 w-full rounded-xl border border-border bg-bg px-3 py-2 text-sm text-text-primary shadow-card outline-none transition focus:border-ice-400 focus:ring-2 focus:ring-ice-200 dark:focus:ring-ice-900/60";
const LABEL_CLASS = "text-xs font-semibold uppercase tracking-[0.14em] text-text-tertiary";
const CHECKBOX_CLASS = "h-4 w-4 rounded border-border text-ice-500 focus:ring-ice-500";
const SECONDARY_BUTTON_CLASS =
  "ui-pressable inline-flex items-center gap-1.5 rounded-xl border border-border bg-surface px-3 py-2 text-xs font-semibold text-text-secondary transition hover:border-ice-200 hover:bg-ice-50 hover:text-ice-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ice-500 dark:hover:border-ice-800 dark:hover:bg-ice-900/30 dark:hover:text-ice-200 disabled:cursor-not-allowed disabled:opacity-45";

const LOG_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"];
const FORMAT_OPTIONS = ["png", "pdf", "svg"] as const;

const SYNTENY_NUMBER_FIELDS: Array<{
  key: "cscore" | "dist" | "iter";
  label: string;
  min: number;
  max?: number;
  step: number;
}> = [
  { key: "cscore", label: "cscore", min: 0, max: 1, step: 0.05 },
  { key: "dist", label: "dist", min: 1, step: 1 },
  { key: "iter", label: "iter", min: 1, step: 1 },
];

const PLOT_NUMBER_FIELDS: Array<{
  key: "dpi";
  label: string;
  min: number;
  step: number;
}> = [{ key: "dpi", label: "dpi", min: 1, step: 1 }];

const LOCAL_NUMBER_FIELDS: Array<{
  key: "up" | "down";
  label: string;
  min: number;
  step: number;
}> = [
  { key: "up", label: "upstream", min: 0, step: 1 },
  { key: "down", label: "downstream", min: 0, step: 1 },
];

type InputMode = WorkflowRequestInputMode;

function updateNumber(value: string): number | null {
  if (value.trim().length === 0) {
    return null;
  }
  const next = Number(value);
  return Number.isFinite(next) ? next : null;
}

function emptySpecies(inputMode: InputMode): SpeciesInputDraft {
  const speciesMode = inputMode === "gff_genome" ? "gff_genome" : "bed_cds";
  return {
    name: "",
    inputMode: speciesMode,
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

interface SyntenyFormProps {
  draft: WorkflowRequestDraft;
  isZh: boolean;
  onChange: (draft: WorkflowRequestDraft) => void;
  onPickFile: (onSelect: (path: string) => void) => Promise<void>;
  onPickDirectory: (onSelect: (path: string) => void) => Promise<void>;
}

export function SyntenyForm({ draft, isZh, onChange, onPickFile, onPickDirectory }: SyntenyFormProps) {
  const patchDraft = useCallback(
    (patch: Partial<WorkflowRequestDraft>) => {
      onChange({ ...draft, ...patch });
    },
    [draft, onChange],
  );

  const patchRuntime = useCallback(
    (patch: Partial<WorkflowRequestDraft["runtime"]>) => {
      onChange({ ...draft, runtime: { ...draft.runtime, ...patch } });
    },
    [draft, onChange],
  );

  const patchSynteny = useCallback(
    (patch: Partial<WorkflowRequestDraft["parameters"]["synteny"]>) => {
      onChange({
        ...draft,
        parameters: { ...draft.parameters, synteny: { ...draft.parameters.synteny, ...patch } },
      });
    },
    [draft, onChange],
  );

  const patchPlot = useCallback(
    (patch: Partial<WorkflowRequestDraft["parameters"]["plot"]>) => {
      onChange({
        ...draft,
        parameters: { ...draft.parameters, plot: { ...draft.parameters.plot, ...patch } },
      });
    },
    [draft, onChange],
  );

  const patchLocalSynteny = useCallback(
    (patch: Partial<WorkflowRequestDraft["parameters"]["localSynteny"]>) => {
      onChange({
        ...draft,
        parameters: { ...draft.parameters, localSynteny: { ...draft.parameters.localSynteny, ...patch } },
      });
    },
    [draft, onChange],
  );

  const updateSpecies = useCallback(
    (index: number, patch: Partial<SpeciesInputDraft>) => {
      const species = draft.species.map((item, itemIndex) =>
        itemIndex === index ? { ...item, ...patch } : item,
      );
      onChange({ ...draft, species });
    },
    [draft, onChange],
  );

  const addSpecies = useCallback(() => {
    onChange({ ...draft, species: [...draft.species, emptySpecies(draft.inputMode)] });
  }, [draft, onChange]);

  const removeSpecies = useCallback(
    (index: number) => {
      onChange({ ...draft, species: draft.species.filter((_, itemIndex) => itemIndex !== index) });
    },
    [draft, onChange],
  );

  const toggleFormat = useCallback(
    (format: string) => {
      const formats = draft.formats.includes(format)
        ? draft.formats.filter((item) => item !== format)
        : [...draft.formats, format];
      onChange({ ...draft, formats });
    },
    [draft, onChange],
  );

  const targetGeneText = useMemo(
    () => draft.parameters.localSynteny.targetGeneIds.join("\n"),
    [draft.parameters.localSynteny.targetGeneIds],
  );

  return (
    <div className="mx-auto grid w-full max-w-4xl gap-6">
      <CollapsibleSection
        title={isZh ? "输入与输出" : "Inputs and output"}
        subtitle={isZh ? "选择数据来源、输出目录和任务级选项。" : "Choose the data source, output directory, and task-level options."}
        className="ui-surface-enter mx-auto w-full max-w-4xl"
        defaultOpen
      >
        <div className="mt-4 grid gap-4 lg:grid-cols-2">
          <label>
            <span className={LABEL_CLASS}>input mode</span>
            <select
              className={FIELD_CLASS}
              value={draft.inputMode}
              onChange={(event) => patchDraft({ inputMode: event.target.value as InputMode })}
            >
              <option value="auto_directory">auto_directory</option>
              <option value="bed_cds">bed_cds</option>
              <option value="gff_genome">gff_genome</option>
            </select>
          </label>
          <label>
            <span className={LABEL_CLASS}>workflow</span>
            <input className={FIELD_CLASS} value={draft.workflowId} readOnly disabled />
          </label>
        </div>

        <div className="mt-4 grid gap-4">
          <label>
            <span className={LABEL_CLASS}>{isZh ? "输入目录" : "input directory"}</span>
            <div className="mt-2 flex gap-2">
              <input
                className="min-w-0 flex-1 rounded-lg border border-border bg-bg px-3 py-2 text-sm text-text-primary shadow-card outline-none transition focus:border-ice-400 focus:ring-2 focus:ring-ice-200 dark:focus:ring-ice-900/60"
                value={draft.directory}
                onChange={(event) => patchDraft({ directory: event.target.value })}
                placeholder={isZh ? "选择工作区或 request 输入目录" : "Select a workspace or request input directory"}
              />
              <button
                type="button"
                className={SECONDARY_BUTTON_CLASS}
                onClick={() => onPickDirectory((path) => patchDraft({ directory: path }))}
              >
                Browse
              </button>
            </div>
          </label>

          <label>
            <span className={LABEL_CLASS}>{isZh ? "输出目录" : "output directory"}</span>
            <div className="mt-2 flex gap-2">
              <input
                className="min-w-0 flex-1 rounded-lg border border-border bg-bg px-3 py-2 text-sm text-text-primary shadow-card outline-none transition focus:border-ice-400 focus:ring-2 focus:ring-ice-200 dark:focus:ring-ice-900/60"
                value={draft.outputDirectory}
                onChange={(event) => patchDraft({ outputDirectory: event.target.value })}
                placeholder={isZh ? "选择当前任务的输出位置" : "Select where this task should write outputs"}
              />
              <button
                type="button"
                className={SECONDARY_BUTTON_CLASS}
                onClick={() => onPickDirectory((path) => patchDraft({ outputDirectory: path }))}
              >
                {isZh ? "浏览" : "Browse"}
              </button>
            </div>
          </label>
        </div>
      </CollapsibleSection>

      {draft.inputMode !== "auto_directory" ? (
        <CollapsibleSection
          title={isZh ? "物种输入" : "Species inputs"}
          subtitle={isZh ? "当 workflow 不使用 auto_directory 时，可以改用显式物种输入。" : "Explicit species mode is available for workflows that do not use auto_directory."}
          className="ui-surface-enter mx-auto w-full max-w-4xl"
          defaultOpen
          badge={
            <button type="button" className={SECONDARY_BUTTON_CLASS} onClick={addSpecies}>
              {isZh ? "添加物种" : "Add species"}
            </button>
          }
        >
          <div className="mt-4 grid gap-3">
            {draft.species.map((species, index) => (
              <div key={index} className="rounded-lg border border-border bg-bg p-3">
                <div className="flex items-start justify-between gap-3">
                  <label className="min-w-0 flex-1">
                    <span className={LABEL_CLASS}>species name</span>
                    <input
                      className={FIELD_CLASS}
                      value={species.name}
                      onChange={(event) => updateSpecies(index, { name: event.target.value })}
                    />
                  </label>
                  <button type="button" className={SECONDARY_BUTTON_CLASS} onClick={() => removeSpecies(index)}>
                    Remove
                  </button>
                </div>
                {species.inputMode === "bed_cds" ? (
                  <div className="mt-3 grid gap-3 lg:grid-cols-2">
                    <PathField
                      label="BED"
                      value={species.bed}
                      onChange={(path) => updateSpecies(index, { bed: path })}
                      pickFile={onPickFile}
                    />
                    <PathField
                      label="CDS"
                      value={species.cds}
                      onChange={(path) => updateSpecies(index, { cds: path })}
                      pickFile={onPickFile}
                    />
                  </div>
                ) : (
                  <div className="mt-3 grid gap-3 lg:grid-cols-2">
                    <PathField
                      label="GFF"
                      value={species.gff}
                      onChange={(path) => updateSpecies(index, { gff: path })}
                      pickFile={onPickFile}
                    />
                    <PathField
                      label="Genome"
                      value={species.genome}
                      onChange={(path) => updateSpecies(index, { genome: path })}
                      pickFile={onPickFile}
                    />
                  </div>
                )}
              </div>
            ))}
          </div>
        </CollapsibleSection>
      ) : null}

      <CollapsibleSection
        title={isZh ? "工作流选项" : "Workflow options"}
        subtitle={isZh ? "保持 transport 字段与 GenomeLens WorkflowRequest 契约一致。" : "Keep transport fields aligned with the GenomeLens WorkflowRequest contract."}
        className="ui-surface-enter mx-auto w-full max-w-4xl"
        defaultOpen
      >
        <div className="mt-4 grid gap-4 lg:grid-cols-3">
          <label>
            <span className={LABEL_CLASS}>threads</span>
            <input
              className={FIELD_CLASS}
              type="number"
              min={1}
              value={draft.runtime.threads ?? ""}
              onChange={(event) => patchRuntime({ threads: updateNumber(event.target.value) })}
            />
          </label>
          <label>
            <span className={LABEL_CLASS}>log level</span>
            <select
              className={FIELD_CLASS}
              value={draft.runtime.logLevel}
              onChange={(event) =>
                patchRuntime({ logLevel: event.target.value as WorkflowRequestDraft["runtime"]["logLevel"] })
              }
            >
              {LOG_LEVELS.map((level) => (
                <option key={level} value={level}>
                  {level}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span className={LABEL_CLASS}>reference index</span>
            <input
              className={FIELD_CLASS}
              type="number"
              min={0}
              value={draft.referenceIndex}
              onChange={(event) => patchDraft({ referenceIndex: Number(event.target.value) })}
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
            ["forceOutput", "force output"],
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
                      ? draft.runtime.verbose
                      : draft.runtime.consoleLog
                }
                onChange={(event) => {
                  if (key === "forceOutput") {
                    patchDraft({ forceOutput: event.target.checked });
                  } else if (key === "verbose") {
                    patchRuntime({ verbose: event.target.checked });
                  } else {
                    patchRuntime({ consoleLog: event.target.checked });
                  }
                }}
              />
              {label}
            </label>
          ))}
        </div>
      </CollapsibleSection>

      <CollapsibleSection
        title={isZh ? "Synteny 参数" : "Synteny parameters"}
        subtitle={isZh ? "Synteny 算法与图件参数，保留为任务本地设置。" : "Synteny algorithm and figure parameters remain task-local."}
        className="ui-surface-enter mx-auto w-full max-w-4xl"
      >
        <div className="mt-4 grid gap-4 lg:grid-cols-3">
          <label>
            <span className={LABEL_CLASS}>align_soft</span>
            <select
              className={FIELD_CLASS}
              value={draft.parameters.synteny.alignSoft}
              onChange={(event) =>
                patchSynteny({ alignSoft: event.target.value as WorkflowRequestDraft["parameters"]["synteny"]["alignSoft"] })
              }
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
              value={draft.parameters.synteny.dbtype}
              onChange={(event) =>
                patchSynteny({ dbtype: event.target.value as WorkflowRequestDraft["parameters"]["synteny"]["dbtype"] })
              }
            >
              <option value="nucl">nucl</option>
              <option value="prot">prot</option>
            </select>
          </label>
          <label>
            <span className={LABEL_CLASS}>figsize</span>
            <input
              className={FIELD_CLASS}
              value={draft.parameters.plot.figsize}
              onChange={(event) => patchPlot({ figsize: event.target.value })}
            />
          </label>
          {SYNTENY_NUMBER_FIELDS.map(({ key, label, min, max, step }) => (
            <label key={key}>
              <span className={LABEL_CLASS}>{label}</span>
              <input
                className={FIELD_CLASS}
                type="number"
                min={min}
                max={max}
                step={step}
                value={draft.parameters.synteny[key]}
                onChange={(event) => patchSynteny({ [key]: Number(event.target.value) })}
              />
            </label>
          ))}
          <label>
            <span className={LABEL_CLASS}>min block size</span>
            <input
              className={FIELD_CLASS}
              type="number"
              min={1}
              value={draft.parameters.synteny.minBlockSize}
              onChange={(event) => patchSynteny({ minBlockSize: updateNumber(event.target.value) ?? undefined })}
            />
          </label>
        </div>

        <div className="mt-5 grid gap-3 lg:grid-cols-2">
          {[["allowSimplifiedFallback", "allow_simplified_fallback"]].map(([key, label]) => (
            <label key={key} className="inline-flex items-center gap-2 text-sm font-medium text-text-secondary">
              <input
                className={CHECKBOX_CLASS}
                type="checkbox"
                checked={draft.parameters.synteny[key as keyof typeof draft.parameters.synteny] as boolean}
                onChange={(event) => patchSynteny({ [key]: event.target.checked })}
              />
              {label}
            </label>
          ))}
        </div>
      </CollapsibleSection>

      <CollapsibleSection
        title={isZh ? "图件参数" : "Plot parameters"}
        subtitle={isZh ? "图件样式与 DPI 设置。" : "Figure styling and DPI settings."}
        className="ui-surface-enter mx-auto w-full max-w-4xl"
      >
        <div className="mt-4 grid gap-4 lg:grid-cols-3">
          <label>
            <span className={LABEL_CLASS}>glyphstyle</span>
            <select
              className={FIELD_CLASS}
              value={draft.parameters.plot.glyphstyle}
              onChange={(event) => patchPlot({ glyphstyle: event.target.value })}
            >
              <option value=""></option>
              <option value="box">box</option>
              <option value="arrow">arrow</option>
            </select>
          </label>
          <label>
            <span className={LABEL_CLASS}>glyphcolor</span>
            <select
              className={FIELD_CLASS}
              value={draft.parameters.plot.glyphcolor}
              onChange={(event) => patchPlot({ glyphcolor: event.target.value })}
            >
              <option value=""></option>
              <option value="orientation">orientation</option>
              <option value="orthogroup">orthogroup</option>
            </select>
          </label>
          <label>
            <span className={LABEL_CLASS}>shadestyle</span>
            <select
              className={FIELD_CLASS}
              value={draft.parameters.plot.shadestyle}
              onChange={(event) => patchPlot({ shadestyle: event.target.value })}
            >
              <option value=""></option>
              <option value="curve">curve</option>
              <option value="line">line</option>
            </select>
          </label>
          {PLOT_NUMBER_FIELDS.map(({ key, label, min, step }) => (
            <label key={key}>
              <span className={LABEL_CLASS}>{label}</span>
              <input
                className={FIELD_CLASS}
                type="number"
                min={min}
                step={step}
                value={draft.parameters.plot[key]}
                onChange={(event) => patchPlot({ [key]: Number(event.target.value) })}
              />
            </label>
          ))}
        </div>
      </CollapsibleSection>

      <CollapsibleSection
        title={isZh ? "局部共线性参数" : "Local synteny parameters"}
        subtitle={isZh ? "目标基因与上下游窗口设置。" : "Target gene and flanking window settings."}
        className="ui-surface-enter mx-auto w-full max-w-4xl"
      >
        <div className="mt-4 grid gap-4 lg:grid-cols-3">
          {LOCAL_NUMBER_FIELDS.map(({ key, label, min, step }) => (
            <label key={key}>
              <span className={LABEL_CLASS}>{label}</span>
              <input
                className={FIELD_CLASS}
                type="number"
                min={min}
                step={step}
                value={draft.parameters.localSynteny[key]}
                onChange={(event) => patchLocalSynteny({ [key]: Number(event.target.value) })}
              />
            </label>
          ))}
        </div>

        <label className="mt-4 block">
          <span className={LABEL_CLASS}>target_gene_ids</span>
          <textarea
            className={`${FIELD_CLASS} min-h-24`}
            value={targetGeneText}
            onChange={(event) => patchLocalSynteny({ targetGeneIds: splitTargets(event.target.value) })}
            placeholder="One gene id per line, or comma-separated"
          />
        </label>

        <div className="mt-5 grid gap-3 lg:grid-cols-2">
          {[
            ["splitTargets", "split_targets"],
            ["labelTargets", "label_targets"],
            ["useNativeRenderer", "use_native_renderer"],
          ].map(([key, label]) => (
            <label key={key} className="inline-flex items-center gap-2 text-sm font-medium text-text-secondary">
              <input
                className={CHECKBOX_CLASS}
                type="checkbox"
                checked={draft.parameters.localSynteny[key as keyof typeof draft.parameters.localSynteny] as boolean}
                onChange={(event) => patchLocalSynteny({ [key]: event.target.checked })}
              />
              {label}
            </label>
          ))}
        </div>
      </CollapsibleSection>
    </div>
  );
}
