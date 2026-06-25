import type { WorkflowRequestDraft, SpeciesInputDraft } from "./workflow-request-draft";
import type { CapabilityEntry, CapabilityInputDeclaration, CapabilityParameterDeclaration } from "./capability";
import type { SubmoduleRequestDraft } from "./submodule-request-draft";

export type ValidationSeverity = "error" | "warning";

export interface ValidationIssue {
  field: string;
  code: string;
  message: string;
  severity: ValidationSeverity;
}

export interface ValidationResult {
  ok: boolean;
  issues: ValidationIssue[];
}

function issue(field: string, code: string, message: string, severity: ValidationSeverity = "error"): ValidationIssue {
  return { field, code, message, severity };
}

function isBlank(value: string | undefined): boolean {
  return value === undefined || value.trim().length === 0;
}

function validateBedCdsSpecies(species: SpeciesInputDraft, index: number): ValidationIssue[] {
  const prefix = `species[${index}]`;
  const issues: ValidationIssue[] = [];

  if (isBlank(species.bed)) {
    issues.push(issue(`${prefix}.bed`, "species.bed.required", "BED+CDS 输入需要 BED 文件路径"));
  }
  if (isBlank(species.cds)) {
    issues.push(issue(`${prefix}.cds`, "species.cds.required", "BED+CDS 输入需要 CDS 文件路径"));
  }

  return issues;
}

function validateGffGenomeSpecies(species: SpeciesInputDraft, index: number): ValidationIssue[] {
  const prefix = `species[${index}]`;
  const issues: ValidationIssue[] = [];

  if (isBlank(species.gff)) {
    issues.push(issue(`${prefix}.gff`, "species.gff.required", "GFF+FASTA 输入需要 GFF 文件路径"));
  }
  if (isBlank(species.genome)) {
    issues.push(issue(`${prefix}.genome`, "species.genome.required", "GFF+FASTA 输入需要 genome 文件路径"));
  }

  return issues;
}

function validateSpecies(species: SpeciesInputDraft | undefined, index: number): ValidationIssue[] {
  const prefix = `species[${index}]`;
  const issues: ValidationIssue[] = [];

  if (species === undefined) {
    return [issue(prefix, "species.required", "物种输入不能为空")];
  }
  if (isBlank(species.name)) {
    issues.push(issue(`${prefix}.name`, "species.name.required", "物种名称不能为空"));
  }
  if (species.inputMode === "bed_cds") {
    issues.push(...validateBedCdsSpecies(species, index));
  } else if (species.inputMode === "gff_genome") {
    issues.push(...validateGffGenomeSpecies(species, index));
  } else {
    issues.push(issue(`${prefix}.inputMode`, "species.inputMode.unsupported", "不支持的物种输入模式"));
  }

  return issues;
}

function validateTargetGenes(draft: WorkflowRequestDraft): ValidationIssue[] {
  const targetGeneIds = draft.parameters.localSynteny.targetGeneIds ?? [];
  if (targetGeneIds.length === 0) {
    return [];
  }

  const species = draft.species ?? [];
  const referenceIndex = draft.referenceIndex ?? 0;
  const reference = species[referenceIndex];
  const issues: ValidationIssue[] = [];

  if (species.length < 2) {
    issues.push(issue("parameters.localSynteny.targetGeneIds", "target_genes.species.too_few", "局部共线性至少需要两个物种"));
  }
  if (reference === undefined) {
    issues.push(issue("referenceIndex", "reference_index.missing", "目标基因需要有效参考物种"));
  }
  for (const [index, geneId] of targetGeneIds.entries()) {
    if (geneId.trim().length === 0) {
      issues.push(issue(`parameters.localSynteny.targetGeneIds[${index}]`, "target_gene.blank", "目标基因 ID 不能为空"));
    }
  }

  return issues;
}

function validateSubmoduleInput(
  port: CapabilityInputDeclaration,
  value: unknown,
): ValidationIssue | undefined {
  if (port.required) {
    if (value === undefined || value === null || (typeof value === "string" && isBlank(value))) {
      return issue(`inputs.${port.port_id}`, "input.required", `${port.port_id} 是必填端口`);
    }
    if (port.port_kind === "artifact") {
      if (Array.isArray(value) && value.length === 0) {
        return issue(`inputs.${port.port_id}`, "input.empty", `${port.port_id} 至少需要提供一个文件`);
      }
    }
  }
  return undefined;
}

function validateSubmoduleParameter(
  param: CapabilityParameterDeclaration,
  value: unknown,
): ValidationIssue | undefined {
  if (param.required && (value === undefined || value === null || (typeof value === "string" && isBlank(value)))) {
    return issue(`parameters.${param.param_id}`, "parameter.required", `${param.param_id} 是必填参数`);
  }
  if (value === undefined || value === null) {
    return undefined;
  }
  switch (param.param_type) {
    case "integer":
      if (!Number.isInteger(value)) {
        return issue(`parameters.${param.param_id}`, "parameter.type", `${param.param_id} 必须是整数`);
      }
      break;
    case "number":
      if (typeof value !== "number" || Number.isNaN(value)) {
        return issue(`parameters.${param.param_id}`, "parameter.type", `${param.param_id} 必须是数字`);
      }
      break;
    case "boolean":
      if (typeof value !== "boolean") {
        return issue(`parameters.${param.param_id}`, "parameter.type", `${param.param_id} 必须是布尔值`);
      }
      break;
    case "string":
      if (typeof value !== "string") {
        return issue(`parameters.${param.param_id}`, "parameter.type", `${param.param_id} 必须是字符串`);
      }
      break;
    case "array":
      if (!Array.isArray(value)) {
        return issue(`parameters.${param.param_id}`, "parameter.type", `${param.param_id} 必须是数组`);
      }
      break;
  }
  return undefined;
}

export function validateWorkflowRequestDraft(draft: WorkflowRequestDraft): ValidationResult {
  const issues: ValidationIssue[] = [];

  if (draft.schemaVersion !== 3) {
    issues.push(issue("schemaVersion", "schema_version.unsupported", "GUI 仅支持 WorkflowRequest schema_version=3"));
  }
  if (draft.kind !== "workflow_request") {
    issues.push(issue("kind", "kind.unsupported", "请求 kind 必须是 workflow_request"));
  }
  if (draft.workflowId !== "synteny") {
    issues.push(issue("workflowId", "workflow.unsupported", "GUI 先行版仅支持 synteny 工作流"));
  }

  if (draft.inputMode === "auto_directory") {
    if (isBlank(draft.directory)) {
      issues.push(issue("directory", "directory.required", "自动目录模式需要输入目录"));
    }
  } else {
    const species = draft.species ?? [];
    if (species.length < 2) {
      issues.push(issue("species", "species.too_few", "显式物种输入至少需要两个物种"));
    }
    species.forEach((item, index) => issues.push(...validateSpecies(item, index)));
  }

  const referenceIndex = draft.referenceIndex ?? 0;
  const speciesCount = draft.species?.length ?? 0;
  if (referenceIndex < 0 || (speciesCount > 0 && referenceIndex >= speciesCount)) {
    issues.push(issue("referenceIndex", "reference_index.out_of_range", "参考物种索引超出物种列表范围"));
  }

  if (isBlank(draft.outputDirectory)) {
    issues.push(issue("outputDirectory", "output.directory.required", "输出目录不能为空"));
  }

  const runtime = draft.runtime;
  if (runtime.threads !== undefined && runtime.threads !== null && runtime.threads < 1) {
    issues.push(issue("runtime.threads", "threads.minimum", "线程数必须大于等于 1"));
  }

  const syntenyMinBlockSize = draft.parameters.synteny?.minBlockSize;
  if (syntenyMinBlockSize !== undefined && syntenyMinBlockSize !== null && syntenyMinBlockSize < 1) {
    issues.push(issue("parameters.synteny.minBlockSize", "min_block_size.minimum", "最小 block 大小必须大于等于 1"));
  }

  issues.push(...validateTargetGenes(draft));

  return {
    ok: issues.every((item) => item.severity !== "error"),
    issues,
  };
}

export function validateSubmoduleRequestDraft(
  draft: SubmoduleRequestDraft,
  spec: CapabilityEntry,
): ValidationResult {
  const issues: ValidationIssue[] = [];

  if (draft.schemaVersion !== 3) {
    issues.push(issue("schemaVersion", "schema_version.unsupported", "GUI 仅支持 SubmoduleRequest schema_version=3"));
  }
  if (draft.kind !== "submodule_request") {
    issues.push(issue("kind", "kind.unsupported", "请求 kind 必须是 submodule_request"));
  }
  if (draft.moduleId !== spec.id) {
    issues.push(issue("moduleId", "module_id.mismatch", "请求 module_id 与所选能力不匹配"));
  }

  for (const input of spec.inputs) {
    const error = validateSubmoduleInput(input, draft.inputs[input.port_id]);
    if (error) {
      issues.push(error);
    }
  }

  for (const parameter of spec.parameters) {
    const error = validateSubmoduleParameter(parameter, draft.parameters[parameter.param_id]);
    if (error) {
      issues.push(error);
    }
  }

  if (isBlank(draft.outputDirectory)) {
    issues.push(issue("outputDirectory", "output.directory.required", "输出目录不能为空"));
  }

  const runtime = draft.runtime;
  if (runtime.threads !== undefined && runtime.threads !== null && runtime.threads < 1) {
    issues.push(issue("runtime.threads", "threads.minimum", "线程数必须大于等于 1"));
  }

  return {
    ok: issues.every((item) => item.severity !== "error"),
    issues,
  };
}
