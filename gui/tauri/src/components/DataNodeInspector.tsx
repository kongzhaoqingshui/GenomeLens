import type { DataNode } from "../models/workbench-graph";
import type { SpeciesInputDraft } from "../models/workflow-request-draft";

const FIELD_CLASS =
  "mt-2 w-full rounded-lg border border-border bg-bg px-3 py-2 text-sm text-text-primary shadow-card outline-none transition focus:border-ice-400 focus:ring-2 focus:ring-ice-200 dark:focus:ring-ice-900/60";
const LABEL_CLASS = "text-xs font-semibold uppercase tracking-[0.14em] text-text-tertiary";
const SECONDARY_BUTTON_CLASS =
  "ui-pressable rounded-lg border border-border bg-surface-raised/80 px-3 py-2 text-xs font-semibold text-text-secondary transition hover:border-ice-200 hover:bg-ice-50 hover:text-ice-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ice-500 dark:hover:border-ice-800 dark:hover:bg-ice-900/30 dark:hover:text-ice-200 disabled:cursor-not-allowed disabled:opacity-45";

export interface DataNodeInspectorProps {
  node: DataNode;
  isZh: boolean;
  onChange: (node: DataNode) => void;
  onPickFile: (setter: (path: string) => void) => void;
}

function getSpeciesPairValue(value: unknown): { reference: SpeciesInputDraft; target: SpeciesInputDraft } {
  const empty: SpeciesInputDraft = { name: "", inputMode: "bed_cds", bed: "", cds: "", gff: "", genome: "" };
  if (typeof value === "object" && value !== null && "reference" in value && "target" in value) {
    const v = value as Record<string, unknown>;
    return {
      reference: (v.reference as SpeciesInputDraft) ?? { ...empty },
      target: (v.target as SpeciesInputDraft) ?? { ...empty },
    };
  }
  return { reference: { ...empty }, target: { ...empty } };
}

function SpeciesPairEditor({
  value,
  isZh,
  onChange,
  onPickFile,
}: {
  value: unknown;
  isZh: boolean;
  onChange: (value: unknown) => void;
  onPickFile: (setter: (path: string) => void) => void;
}) {
  const pair = getSpeciesPairValue(value);

  function updateSpecies(key: "reference" | "target", patch: Partial<SpeciesInputDraft>) {
    onChange({
      ...pair,
      [key]: { ...pair[key], ...patch },
    });
  }

  function renderSpeciesEditor(key: "reference" | "target", species: SpeciesInputDraft) {
    const title = key === "reference" ? (isZh ? "参考物种" : "Reference species") : isZh ? "目标物种" : "Target species";
    return (
      <div className="rounded-lg border border-border bg-bg p-3">
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-text-tertiary">{title}</p>
        <div className="mt-2 grid gap-3">
          <label>
            <span className={LABEL_CLASS}>name</span>
            <input
              className={FIELD_CLASS}
              value={species.name}
              onChange={(event) => updateSpecies(key, { name: event.target.value })}
            />
          </label>
          <label>
            <span className={LABEL_CLASS}>input mode</span>
            <select
              className={FIELD_CLASS}
              value={species.inputMode}
              onChange={(event) =>
                updateSpecies(key, { inputMode: event.target.value as SpeciesInputDraft["inputMode"] })
              }
            >
              <option value="bed_cds">BED + CDS</option>
              <option value="gff_genome">GFF + Genome</option>
            </select>
          </label>
          {species.inputMode === "bed_cds" ? (
            <div className="grid gap-3 lg:grid-cols-2">
              <label>
                <span className={LABEL_CLASS}>BED</span>
                <div className="mt-2 flex gap-2">
                  <input
                    className="min-w-0 flex-1 rounded-lg border border-border bg-bg px-3 py-2 text-sm text-text-primary shadow-card outline-none transition focus:border-ice-400 focus:ring-2 focus:ring-ice-200 dark:focus:ring-ice-900/60"
                    value={species.bed}
                    onChange={(event) => updateSpecies(key, { bed: event.target.value })}
                  />
                  <button
                    type="button"
                    className={SECONDARY_BUTTON_CLASS}
                    onClick={() => onPickFile((path) => updateSpecies(key, { bed: path }))}
                  >
                    Browse
                  </button>
                </div>
              </label>
              <label>
                <span className={LABEL_CLASS}>CDS</span>
                <div className="mt-2 flex gap-2">
                  <input
                    className="min-w-0 flex-1 rounded-lg border border-border bg-bg px-3 py-2 text-sm text-text-primary shadow-card outline-none transition focus:border-ice-400 focus:ring-2 focus:ring-ice-200 dark:focus:ring-ice-900/60"
                    value={species.cds}
                    onChange={(event) => updateSpecies(key, { cds: event.target.value })}
                  />
                  <button
                    type="button"
                    className={SECONDARY_BUTTON_CLASS}
                    onClick={() => onPickFile((path) => updateSpecies(key, { cds: path }))}
                  >
                    Browse
                  </button>
                </div>
              </label>
            </div>
          ) : (
            <div className="grid gap-3 lg:grid-cols-2">
              <label>
                <span className={LABEL_CLASS}>GFF</span>
                <div className="mt-2 flex gap-2">
                  <input
                    className="min-w-0 flex-1 rounded-lg border border-border bg-bg px-3 py-2 text-sm text-text-primary shadow-card outline-none transition focus:border-ice-400 focus:ring-2 focus:ring-ice-200 dark:focus:ring-ice-900/60"
                    value={species.gff}
                    onChange={(event) => updateSpecies(key, { gff: event.target.value })}
                  />
                  <button
                    type="button"
                    className={SECONDARY_BUTTON_CLASS}
                    onClick={() => onPickFile((path) => updateSpecies(key, { gff: path }))}
                  >
                    Browse
                  </button>
                </div>
              </label>
              <label>
                <span className={LABEL_CLASS}>Genome</span>
                <div className="mt-2 flex gap-2">
                  <input
                    className="min-w-0 flex-1 rounded-lg border border-border bg-bg px-3 py-2 text-sm text-text-primary shadow-card outline-none transition focus:border-ice-400 focus:ring-2 focus:ring-ice-200 dark:focus:ring-ice-900/60"
                    value={species.genome}
                    onChange={(event) => updateSpecies(key, { genome: event.target.value })}
                  />
                  <button
                    type="button"
                    className={SECONDARY_BUTTON_CLASS}
                    onClick={() => onPickFile((path) => updateSpecies(key, { genome: path }))}
                  >
                    Browse
                  </button>
                </div>
              </label>
            </div>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="grid gap-4">
      {renderSpeciesEditor("reference", pair.reference)}
      {renderSpeciesEditor("target", pair.target)}
    </div>
  );
}

function ArtifactEditor({
  value,
  isZh,
  onChange,
  onPickFile,
}: {
  value: unknown;
  isZh: boolean;
  onChange: (value: unknown) => void;
  onPickFile: (setter: (path: string) => void) => void;
}) {
  const path = typeof value === "object" && value !== null ? (value as Record<string, unknown>).path ?? "" : "";
  const artifactType =
    typeof value === "object" && value !== null ? (value as Record<string, unknown>).artifactType ?? "" : "";

  function update(patch: Record<string, unknown>) {
    const base = typeof value === "object" && value !== null ? { ...(value as Record<string, unknown>) } : {};
    onChange({ ...base, ...patch });
  }

  return (
    <div className="grid gap-4">
      <label>
        <span className={LABEL_CLASS}>{isZh ? "Artifact file" : "Artifact file"}</span>
        <div className="mt-2 flex gap-2">
          <input
            className="min-w-0 flex-1 rounded-lg border border-border bg-bg px-3 py-2 text-sm text-text-primary shadow-card outline-none transition focus:border-ice-400 focus:ring-2 focus:ring-ice-200 dark:focus:ring-ice-900/60"
            value={String(path)}
            onChange={(event) => update({ path: event.target.value })}
            placeholder={isZh ? "选择或输入文件路径" : "Select or enter a file path"}
          />
          <button
            type="button"
            className={SECONDARY_BUTTON_CLASS}
            onClick={() => onPickFile((selected) => update({ path: selected }))}
          >
            {isZh ? "浏览" : "Browse"}
          </button>
        </div>
      </label>
      <label>
        <span className={LABEL_CLASS}>{isZh ? "Artifact type" : "Artifact type"}</span>
        <input
          className={FIELD_CLASS}
          value={String(artifactType)}
          onChange={(event) => update({ artifactType: event.target.value })}
          placeholder={isZh ? "例如 anchors, blocks, pdf, png" : "e.g. anchors, blocks, pdf, png"}
        />
      </label>
    </div>
  );
}

function ValueEditor({
  value,
  isZh,
  onChange,
}: {
  value: unknown;
  isZh: boolean;
  onChange: (value: unknown) => void;
}) {
  const text = Array.isArray(value) ? value.join("\n") : typeof value === "string" ? value : "";
  return (
    <label>
      <span className={LABEL_CLASS}>{isZh ? "Value" : "Value"}</span>
      <textarea
        className={`${FIELD_CLASS} min-h-32`}
        value={text}
        onChange={(event) => {
          const lines = event.target.value.split("\n");
          const trimmed = lines.map((line) => line.trim()).filter(Boolean);
          onChange(trimmed.length > 0 ? trimmed : event.target.value);
        }}
        placeholder={isZh ? "每行一个值，或输入单个字符串" : "One value per line, or a single string"}
      />
    </label>
  );
}

export function DataNodeInspector({
  node,
  isZh,
  onChange,
  onPickFile,
}: DataNodeInspectorProps) {
  function patchLabel(label: string) {
    onChange({ ...node, label });
  }

  function patchValue(value: unknown) {
    onChange({ ...node, value });
  }

  return (
    <div className="mx-auto grid w-full max-w-4xl gap-6">
      <div className="rounded-lg border border-border bg-bg p-3">
        <label>
          <span className={LABEL_CLASS}>{isZh ? "节点标签" : "Node label"}</span>
          <input className={FIELD_CLASS} value={node.label} onChange={(event) => patchLabel(event.target.value)} />
        </label>
      </div>

      {node.dataKind === "species_pair" && (
        <SpeciesPairEditor value={node.value} isZh={isZh} onChange={patchValue} onPickFile={onPickFile} />
      )}
      {node.dataKind === "artifact" && (
        <ArtifactEditor value={node.value} isZh={isZh} onChange={patchValue} onPickFile={onPickFile} />
      )}
      {node.dataKind === "value" && <ValueEditor value={node.value} isZh={isZh} onChange={patchValue} />}

      {node.dataKind === "species_pair" ? (
        <p className="text-xs text-text-tertiary">
          {isZh
            ? "注：species_pair 节点的 value 应为 { reference: SpeciesInputDraft, target: SpeciesInputDraft }"
            : "Note: species_pair node value should be { reference: SpeciesInputDraft, target: SpeciesInputDraft }"}
        </p>
      ) : null}
    </div>
  );
}
