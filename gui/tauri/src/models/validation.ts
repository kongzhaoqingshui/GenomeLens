import type { AnalysisRequest, SpeciesInput } from "./analysis-request";
import type { AnalysisRequestDraft } from "./analysis-request-draft";
import { draftToAnalysisRequest } from "./analysis-request-draft";

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

function validateBedCdsSpecies(species: SpeciesInput, index: number): ValidationIssue[] {
  const prefix = `input.species[${index}]`;
  const issues: ValidationIssue[] = [];

  if (isBlank(species.bed)) {
    issues.push(issue(`${prefix}.bed`, "species.bed.required", "BED+CDS 输入需要 BED 文件路径"));
  }
  if (isBlank(species.cds)) {
    issues.push(issue(`${prefix}.cds`, "species.cds.required", "BED+CDS 输入需要 CDS 文件路径"));
  }

  return issues;
}

function validateGffGenomeSpecies(species: SpeciesInput, index: number): ValidationIssue[] {
  const prefix = `input.species[${index}]`;
  const issues: ValidationIssue[] = [];

  if (isBlank(species.gff)) {
    issues.push(issue(`${prefix}.gff`, "species.gff.required", "GFF+FASTA 输入需要 GFF 文件路径"));
  }
  if (isBlank(species.genome)) {
    issues.push(issue(`${prefix}.genome`, "species.genome.required", "GFF+FASTA 输入需要 genome 文件路径"));
  }

  return issues;
}

function validateSpecies(species: SpeciesInput | undefined, index: number): ValidationIssue[] {
  const prefix = `input.species[${index}]`;
  const issues: ValidationIssue[] = [];

  if (species === undefined) {
    return [issue(prefix, "species.required", "物种输入不能为空")];
  }
  if (isBlank(species.name)) {
    issues.push(issue(`${prefix}.name`, "species.name.required", "物种名称不能为空"));
  }
  if (species.input_mode === "bed_cds") {
    issues.push(...validateBedCdsSpecies(species, index));
  } else if (species.input_mode === "gff_genome") {
    issues.push(...validateGffGenomeSpecies(species, index));
  } else {
    issues.push(issue(`${prefix}.input_mode`, "species.input_mode.unsupported", "不支持的物种输入模式"));
  }

  return issues;
}

function validateTargetGenes(request: AnalysisRequest): ValidationIssue[] {
  const targetGeneIds = request.method_config?.target_gene_ids ?? [];
  if (targetGeneIds.length === 0) {
    return [];
  }

  const species = request.input.species ?? [];
  const referenceIndex = request.input.reference_index ?? 0;
  const reference = species[referenceIndex];
  const issues: ValidationIssue[] = [];

  if (species.length < 2) {
    issues.push(issue("method_config.target_gene_ids", "target_genes.species.too_few", "局部共线性至少需要两个物种"));
  }
  if (reference === undefined) {
    issues.push(issue("input.reference_index", "reference_index.missing", "目标基因需要有效参考物种"));
  }
  for (const [index, geneId] of targetGeneIds.entries()) {
    if (geneId.trim().length === 0) {
      issues.push(issue(`method_config.target_gene_ids[${index}]`, "target_gene.blank", "目标基因 ID 不能为空"));
    }
  }

  return issues;
}

export function validateAnalysisRequest(request: AnalysisRequest): ValidationResult {
  const issues: ValidationIssue[] = [];

  if (request.schema_version !== 1) {
    issues.push(issue("schema_version", "schema_version.unsupported", "GUI 先行版仅支持 AnalysisRequest schema_version=1"));
  }
  if (request.kind !== "analysis_request") {
    issues.push(issue("kind", "kind.unsupported", "请求 kind 必须是 analysis_request"));
  }
  if (request.method !== "mcscan") {
    issues.push(issue("method", "method.unsupported", "GUI 先行版仅支持 mcscan 方法"));
  }

  if (request.input.mode === "auto_directory") {
    if (isBlank(request.input.directory)) {
      issues.push(issue("input.directory", "input.directory.required", "自动目录模式需要输入目录"));
    }
  } else {
    const species = request.input.species ?? [];
    if (species.length < 2) {
      issues.push(issue("input.species", "species.too_few", "显式物种输入至少需要两个物种"));
    }
    species.forEach((item, index) => issues.push(...validateSpecies(item, index)));
  }

  const referenceIndex = request.input.reference_index ?? 0;
  const speciesCount = request.input.species?.length ?? 0;
  if (referenceIndex < 0 || (speciesCount > 0 && referenceIndex >= speciesCount)) {
    issues.push(issue("input.reference_index", "reference_index.out_of_range", "参考物种索引超出物种列表范围"));
  }

  if (isBlank(request.output.directory)) {
    issues.push(issue("output.directory", "output.directory.required", "输出目录不能为空"));
  }
  if (request.options?.threads !== undefined && request.options.threads !== null && request.options.threads < 1) {
    issues.push(issue("options.threads", "threads.minimum", "线程数必须大于等于 1"));
  }
  if (
    request.options?.min_block_size !== undefined &&
    request.options.min_block_size !== null &&
    request.options.min_block_size < 1
  ) {
    issues.push(issue("options.min_block_size", "min_block_size.minimum", "最小 block 大小必须大于等于 1"));
  }

  issues.push(...validateTargetGenes(request));

  return {
    ok: issues.every((item) => item.severity !== "error"),
    issues,
  };
}

export function validateAnalysisRequestDraft(draft: AnalysisRequestDraft): ValidationResult {
  return validateAnalysisRequest(draftToAnalysisRequest(draft));
}

