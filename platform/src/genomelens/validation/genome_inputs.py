"""基因组输入声明校验工具"""

from __future__ import annotations

from genomelens.app.errors.exceptions import InputValidationError
from genomelens.contracts.species import GenomeInputSpec
from genomelens.validation.files import require_existing_file


def validate_genome_input(spec: GenomeInputSpec, label: str) -> None:
    """校验单个物种侧输入声明"""

    if bool(spec.prepared) == bool(spec.raw):
        raise InputValidationError(f"{label} must use exactly one input mode: bed_cds or gff_genome")

    if spec.prepared:
        require_existing_file(spec.prepared.bed, f"{label} BED")
        require_existing_file(spec.prepared.cds, f"{label} CDS")

    if spec.raw:
        require_existing_file(spec.raw.gff, f"{label} GFF/GTF")
        require_existing_file(spec.raw.genome, f"{label} genome FASTA")
