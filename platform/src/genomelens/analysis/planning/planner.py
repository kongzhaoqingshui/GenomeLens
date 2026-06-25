"""WorkflowPlanner(工作流规划器)：把公开请求展开为执行计划"""

# region import
from __future__ import annotations

from itertools import combinations
from pathlib import Path

from genomelens.analysis.execution.summary_builder import pair_id
from genomelens.analysis.execution.workflow_mapping import (
    build_synteny_request,
    validate_workflow_species,
)
from genomelens.analysis.optimization.optimizer import PlanOptimizer
from genomelens.analysis.planning.models import (
    ExecutionPlan,
    ExecutionStep,
    StepInputRef,
    StepOutputRef,
)
from genomelens.analysis.requests.models import WorkflowRequest
from genomelens.app.errors.exceptions import InputValidationError
from genomelens.contracts.species import GenomeInputSpec

# endregion


class WorkflowPlanner:
    """WorkflowPlanner：集中负责 workflow_id 到执行 DAG 的展开"""

    def build(self, request: WorkflowRequest) -> ExecutionPlan:
        """构建并优化执行计划"""

        raw_plan = self.build_raw_plan(request)
        return PlanOptimizer().optimize(request, raw_plan)

    def build_raw_plan(self, request: WorkflowRequest) -> ExecutionPlan:
        """构建未经优化的原始执行计划"""

        if request.workflow_id != "synteny":
            raise InputValidationError(f"unsupported workflow_id: {request.workflow_id}")
        return self._synteny_plan(request)

    def _synteny_plan(self, request: WorkflowRequest) -> ExecutionPlan:
        """构建 synteny / local synteny 执行计划"""

        species = validate_workflow_species(request)
        reference = species[request.reference_index]
        targets = species[: request.reference_index] + species[request.reference_index + 1 :]
        if len(species) == 2 and not request.target_gene_ids:
            return self._single_pair_plan(request, reference, targets[0])
        if request.target_gene_ids:
            return self._reference_vs_targets_plan(request, reference, targets)
        return self._all_vs_all_plan(request, species)

    def _single_pair_plan(
        self,
        request: WorkflowRequest,
        reference: GenomeInputSpec,
        target: GenomeInputSpec,
    ) -> ExecutionPlan:
        """构建双物种单步计划"""

        payload = build_synteny_request(
            request,
            reference=reference,
            target=target,
            outdir=Path(request.output.directory).expanduser().resolve(strict=False),
            engine_workflow="graphics_synteny",
            force=request.output.force,
        )
        step = ExecutionStep(
            step_id=pair_id(reference.name, target.name),
            kind="pairwise_synteny",
            payload=payload,
            outputs=self._pairwise_outputs("graphics_synteny"),
        )
        return ExecutionPlan(
            plan_id=step.step_id,
            workflow_id=request.workflow_id,
            outdir=payload.outdir,
            force=request.output.force,
            steps=[step],
        )

    @staticmethod
    def _pairwise_outputs(engine_workflow: str) -> list[StepOutputRef]:
        """根据底层 workflow 声明 pairwise step 预期产物"""

        outputs = [
            StepOutputRef("blast_table", "blast_table"),
            StepOutputRef("anchors", "anchors"),
            StepOutputRef("simple", "simple"),
            StepOutputRef("blocks", "blocks"),
        ]
        # 计算专用的 pairwise 工作流不产出图件；图形工作流才声明必需 figure
        if engine_workflow != "pairwise":
            outputs.append(StepOutputRef("figures", "figure", required=True))
        return outputs

    def _all_vs_all_plan(self, request: WorkflowRequest, species: list[GenomeInputSpec]) -> ExecutionPlan:
        """构建多物种 all-vs-all pairwise + global karyotype 计划"""

        outdir = Path(request.output.directory).expanduser().resolve(strict=False)
        steps: list[ExecutionStep] = []
        pair_steps: list[str] = []
        for reference, target in combinations(species, 2):
            step_id = pair_id(reference.name, target.name)
            pair_steps.append(step_id)
            steps.append(
                ExecutionStep(
                    step_id=step_id,
                    kind="pairwise_synteny",
                    payload=build_synteny_request(
                        request,
                        reference=reference,
                        target=target,
                        outdir=outdir / "intermediate" / "pairwise" / step_id,
                        engine_workflow="graphics_synteny",
                        force=True,
                    ),
                    outputs=[StepOutputRef("simple", "simple"), StepOutputRef("figures", "figure")],
                )
            )
        steps.append(
            ExecutionStep(
                step_id="global_karyotype",
                kind="global_karyotype",
                payload={
                    "request": build_synteny_request(
                        request,
                        reference=species[0],
                        target=species[1],
                        additional_species=species[2:],
                        outdir=outdir,
                        engine_workflow="graphics_synteny",
                        force=request.output.force,
                    )
                },
                depends_on=pair_steps,
                inputs=[StepInputRef(step_id=item, artifact_id="simple") for item in pair_steps],
                outputs=[StepOutputRef("global_karyotype_figures", "figure")],
            )
        )
        return ExecutionPlan(
            plan_id="all_vs_all_synteny",
            workflow_id=request.workflow_id,
            outdir=outdir,
            force=request.output.force,
            steps=steps,
        )

    def _reference_vs_targets_plan(
        self,
        request: WorkflowRequest,
        reference: GenomeInputSpec,
        targets: list[GenomeInputSpec],
    ) -> ExecutionPlan:
        """构建 reference-vs-targets 局部共线性计划"""

        outdir = Path(request.output.directory).expanduser().resolve(strict=False)
        steps: list[ExecutionStep] = []
        pair_steps: list[str] = []
        target_names = [item.name for item in targets]
        for target in targets:
            step_id = pair_id(reference.name, target.name)
            pair_steps.append(step_id)
            steps.append(
                ExecutionStep(
                    step_id=step_id,
                    kind="pairwise_synteny",
                    payload=build_synteny_request(
                        request,
                        reference=reference,
                        target=target,
                        outdir=outdir / "intermediate" / "pairwise" / step_id,
                        engine_workflow="local_synteny",
                        force=True,
                    ),
                    outputs=[
                        StepOutputRef("simple", "simple"),
                        StepOutputRef("blocks", "blocks"),
                        StepOutputRef("figures", "figure"),
                    ],
                )
            )
        steps.append(
            ExecutionStep(
                step_id="global_karyotype",
                kind="global_karyotype",
                payload={
                    "request": build_synteny_request(
                        request,
                        reference=reference,
                        target=targets[0],
                        additional_species=targets[1:],
                        outdir=outdir,
                        engine_workflow="local_synteny",
                        force=request.output.force,
                    )
                },
                depends_on=pair_steps,
                inputs=[StepInputRef(step_id=item, artifact_id="simple") for item in pair_steps],
                outputs=[StepOutputRef("global_karyotype_figures", "figure")],
            )
        )
        steps.append(
            ExecutionStep(
                step_id="multi_local_synteny",
                kind="multi_local_synteny",
                payload={
                    "request": build_synteny_request(
                        request,
                        reference=reference,
                        target=targets[0],
                        additional_species=targets[1:],
                        outdir=outdir,
                        engine_workflow="local_synteny",
                        force=request.output.force,
                    )
                },
                depends_on=pair_steps,
                inputs=[StepInputRef(step_id=item, artifact_id="blocks") for item in pair_steps],
                outputs=[StepOutputRef("multi_species_local_figures", "figure")],
            )
        )
        return ExecutionPlan(
            plan_id="reference_vs_targets_local_synteny",
            workflow_id=request.workflow_id,
            outdir=outdir,
            force=request.output.force,
            steps=steps,
            reference_name=reference.name,
            target_names=target_names,
        )
