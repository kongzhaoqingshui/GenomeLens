import { useCallback } from "react";

import { CollapsibleSection } from "./CollapsibleSection";

import type { CapabilityEntry } from "../models/capability";
import type { SubmoduleRequestDraft } from "../models/submodule-request-draft";

const FIELD_CLASS =
  "mt-2 w-full rounded-lg border border-border bg-bg px-3 py-2 text-sm text-text-primary shadow-card outline-none transition focus:border-ice-400 focus:ring-2 focus:ring-ice-200 dark:focus:ring-ice-900/60";
const LABEL_CLASS = "text-xs font-semibold uppercase tracking-[0.14em] text-text-tertiary";
const CHECKBOX_CLASS = "h-4 w-4 rounded border-border text-ice-500 focus:ring-ice-500";
const SECONDARY_BUTTON_CLASS =
  "ui-pressable rounded-lg border border-border bg-surface-raised/80 px-3 py-2 text-xs font-semibold text-text-secondary transition hover:border-ice-200 hover:bg-ice-50 hover:text-ice-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ice-500 dark:hover:border-ice-800 dark:hover:bg-ice-900/30 dark:hover:text-ice-200 disabled:cursor-not-allowed disabled:opacity-45";

const FORMAT_OPTIONS = ["png", "pdf", "svg"] as const;
const LOG_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] as const;

interface SubmoduleFormProps {
  draft: SubmoduleRequestDraft;
  spec: CapabilityEntry;
  isZh: boolean;
  onChange: (draft: SubmoduleRequestDraft) => void;
  onPickFile: (onSelect: (path: string) => void) => Promise<void>;
  onPickDirectory: (onSelect: (path: string) => void) => Promise<void>;
}

function updateNumber(value: string): number | null {
  if (value.trim().length === 0) {
    return null;
  }
  const next = Number(value);
  return Number.isFinite(next) ? next : null;
}

function splitList(value: string): string[] {
  return value
    .split(/[\n,]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function renderInputControl(
  draft: SubmoduleRequestDraft,
  spec: CapabilityEntry,
  isZh: boolean,
  onChange: (draft: SubmoduleRequestDraft) => void,
  onPickFile: (onSelect: (path: string) => void) => Promise<void>,
) {
  return spec.inputs.map((input) => {
    const value = draft.inputs[input.port_id];
    const label = input.description ? `${input.port_id} · ${input.description}` : input.port_id;
    const required = input.required;

    if (input.port_kind === "artifact") {
      const currentValue = typeof value === "string" ? value : "";
      return (
        <label key={input.port_id}>
          <span className={LABEL_CLASS}>
            {input.port_id}
            {required ? " *" : null}
          </span>
          <div className="mt-2 flex gap-2">
            <input
              className="min-w-0 flex-1 rounded-lg border border-border bg-bg px-3 py-2 text-sm text-text-primary shadow-card outline-none transition focus:border-ice-400 focus:ring-2 focus:ring-ice-200 dark:focus:ring-ice-900/60"
              value={currentValue}
              onChange={(event) =>
                onChange({
                  ...draft,
                  inputs: { ...draft.inputs, [input.port_id]: event.target.value },
                })
              }
              placeholder={isZh ? "选择输入文件" : "Select an input file"}
            />
            <button
              type="button"
              className={SECONDARY_BUTTON_CLASS}
              onClick={() =>
                void onPickFile((path) =>
                  onChange({
                    ...draft,
                    inputs: { ...draft.inputs, [input.port_id]: path },
                  }),
                )
              }
            >
              Browse
            </button>
          </div>
          {input.description ? (
            <p className="mt-1 text-xs text-text-tertiary">{input.description}</p>
          ) : null}
        </label>
      );
    }

    if (input.port_kind === "species_pair") {
      const currentValue = Array.isArray(value) ? value.join(", ") : typeof value === "string" ? value : "";
      return (
        <label key={input.port_id}>
          <span className={LABEL_CLASS}>
            {input.port_id}
            {required ? " *" : null}
          </span>
          <input
            className={FIELD_CLASS}
            value={currentValue}
            onChange={(event) => {
              const text = event.target.value;
              const values = splitList(text);
              onChange({
                ...draft,
                inputs: { ...draft.inputs, [input.port_id]: values.length > 0 ? values : text },
              });
            }}
            placeholder={isZh ? "物种 A, 物种 B" : "species A, species B"}
          />
          {input.description ? (
            <p className="mt-1 text-xs text-text-tertiary">{input.description}</p>
          ) : null}
        </label>
      );
    }

    const currentValue = typeof value === "string" ? value : "";
    return (
      <label key={input.port_id}>
        <span className={LABEL_CLASS}>
          {input.port_id}
          {required ? " *" : null}
        </span>
        <input
          className={FIELD_CLASS}
          value={currentValue}
          onChange={(event) =>
            onChange({
              ...draft,
              inputs: { ...draft.inputs, [input.port_id]: event.target.value },
            })
          }
          placeholder={label}
        />
        {input.description ? (
          <p className="mt-1 text-xs text-text-tertiary">{input.description}</p>
        ) : null}
      </label>
    );
  });
}

function renderParameterControls(
  draft: SubmoduleRequestDraft,
  spec: CapabilityEntry,
  isZh: boolean,
  onChange: (draft: SubmoduleRequestDraft) => void,
) {
  return spec.parameters.map((parameter) => {
    const value = draft.parameters[parameter.param_id];
    const label = parameter.description
      ? `${parameter.param_id} · ${parameter.description}`
      : parameter.param_id;
    const required = parameter.required;

    switch (parameter.param_type) {
      case "boolean": {
        const checked = typeof value === "boolean" ? value : false;
        return (
          <label key={parameter.param_id} className="inline-flex items-center gap-2 text-sm font-medium text-text-secondary">
            <input
              className={CHECKBOX_CLASS}
              type="checkbox"
              checked={checked}
              onChange={(event) =>
                onChange({
                  ...draft,
                  parameters: { ...draft.parameters, [parameter.param_id]: event.target.checked },
                })
              }
            />
            {parameter.param_id}
            {required ? " *" : null}
          </label>
        );
      }
      case "integer":
      case "number": {
        const currentValue = typeof value === "number" ? value : "";
        return (
          <label key={parameter.param_id}>
            <span className={LABEL_CLASS}>
              {parameter.param_id}
              {required ? " *" : null}
            </span>
            <input
              className={FIELD_CLASS}
              type="number"
              value={currentValue}
              onChange={(event) => {
                const next = updateNumber(event.target.value);
                onChange({
                  ...draft,
                  parameters: {
                    ...draft.parameters,
                    [parameter.param_id]: next === null ? undefined : next,
                  },
                });
              }}
              placeholder={label}
            />
          </label>
        );
      }
      case "array": {
        const currentValue = Array.isArray(value) ? value.join("\n") : "";
        return (
          <label key={parameter.param_id} className="block">
            <span className={LABEL_CLASS}>
              {parameter.param_id}
              {required ? " *" : null}
            </span>
            <textarea
              className={`${FIELD_CLASS} min-h-24`}
              value={currentValue}
              onChange={(event) =>
                onChange({
                  ...draft,
                  parameters: {
                    ...draft.parameters,
                    [parameter.param_id]: splitList(event.target.value),
                  },
                })
              }
              placeholder={isZh ? "每行一个值" : "One value per line"}
            />
          </label>
        );
      }
      default: {
        const currentValue = typeof value === "string" ? value : "";
        return (
          <label key={parameter.param_id}>
            <span className={LABEL_CLASS}>
              {parameter.param_id}
              {required ? " *" : null}
            </span>
            <input
              className={FIELD_CLASS}
              value={currentValue}
              onChange={(event) =>
                onChange({
                  ...draft,
                  parameters: { ...draft.parameters, [parameter.param_id]: event.target.value },
                })
              }
              placeholder={label}
            />
          </label>
        );
      }
    }
  });
}

export function SubmoduleForm({
  draft,
  spec,
  isZh,
  onChange,
  onPickFile,
  onPickDirectory,
}: SubmoduleFormProps) {
  const toggleFormat = useCallback(
    (format: string) => {
      const formats = draft.formats.includes(format)
        ? draft.formats.filter((item) => item !== format)
        : [...draft.formats, format];
      onChange({ ...draft, formats });
    },
    [draft, onChange],
  );

  return (
    <div className="mx-auto grid w-full max-w-4xl gap-6">
      {spec.inputs.length > 0 ? (
        <CollapsibleSection
          title={isZh ? "子模块输入" : "Submodule inputs"}
          subtitle={isZh ? "根据能力描述动态渲染的输入端口。" : "Dynamically rendered input ports from the capability description."}
          className="ui-surface-enter w-full"
          defaultOpen
        >
          <div className="grid gap-4">
            {renderInputControl(draft, spec, isZh, onChange, onPickFile)}
          </div>
        </CollapsibleSection>
      ) : null}

      {spec.parameters.length > 0 ? (
        <CollapsibleSection
          title={isZh ? "子模块参数" : "Submodule parameters"}
          subtitle={isZh ? "根据能力描述动态渲染的运行参数。" : "Dynamically rendered runtime parameters from the capability description."}
          className="ui-surface-enter w-full"
        >
          <div className="grid gap-4 lg:grid-cols-2">
            {renderParameterControls(draft, spec, isZh, onChange)}
          </div>
        </CollapsibleSection>
      ) : null}

      <CollapsibleSection
        title={isZh ? "输出与运行" : "Output and runtime"}
        subtitle={isZh ? "配置子模块的输出目录和运行时选项。" : "Configure the output directory and runtime options for the submodule."}
        className="ui-surface-enter w-full"
        defaultOpen
      >
        <label>
          <span className={LABEL_CLASS}>{isZh ? "输出目录" : "output directory"}</span>
          <div className="mt-2 flex gap-2">
            <input
              className="min-w-0 flex-1 rounded-lg border border-border bg-bg px-3 py-2 text-sm text-text-primary shadow-card outline-none transition focus:border-ice-400 focus:ring-2 focus:ring-ice-200 dark:focus:ring-ice-900/60"
              value={draft.outputDirectory}
              onChange={(event) => onChange({ ...draft, outputDirectory: event.target.value })}
              placeholder={isZh ? "选择当前子模块任务的输出位置" : "Select where this submodule task should write outputs"}
            />
            <button
              type="button"
              className={SECONDARY_BUTTON_CLASS}
              onClick={() => void onPickDirectory((path) => onChange({ ...draft, outputDirectory: path }))}
            >
              {isZh ? "浏览" : "Browse"}
            </button>
          </div>
        </label>

        <div className="mt-4 grid gap-4 lg:grid-cols-3">
          <label>
            <span className={LABEL_CLASS}>threads</span>
            <input
              className={FIELD_CLASS}
              type="number"
              min={1}
              value={draft.runtime.threads ?? ""}
              onChange={(event) =>
                onChange({
                  ...draft,
                  runtime: { ...draft.runtime, threads: updateNumber(event.target.value) },
                })
              }
            />
          </label>
          <label>
            <span className={LABEL_CLASS}>log level</span>
            <select
              className={FIELD_CLASS}
              value={draft.runtime.logLevel}
              onChange={(event) =>
                onChange({
                  ...draft,
                  runtime: { ...draft.runtime, logLevel: event.target.value },
                })
              }
            >
              {LOG_LEVELS.map((level) => (
                <option key={level} value={level}>
                  {level}
                </option>
              ))}
            </select>
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
                    onChange({ ...draft, forceOutput: event.target.checked });
                  } else if (key === "verbose") {
                    onChange({
                      ...draft,
                      runtime: { ...draft.runtime, verbose: event.target.checked },
                    });
                  } else {
                    onChange({
                      ...draft,
                      runtime: { ...draft.runtime, consoleLog: event.target.checked },
                    });
                  }
                }}
              />
              {label}
            </label>
          ))}
        </div>
      </CollapsibleSection>
    </div>
  );
}
