"""Passes that attach shared-runtime directives(共享运行时指令) to an execution plan"""

from __future__ import annotations

from dataclasses import replace

from genomelens.analysis.planning.models import ExecutionPlan


def attach_shared_runtime_profile(
    plan: ExecutionPlan,
    shared_runtime_profile_id: str,
    *,
    step_kinds: tuple[str, ...] = ("pairwise_synteny",),
    composite_only: bool = True,
) -> ExecutionPlan:
    """Attach a shared-runtime profile when the plan structure can benefit from it
    (当计划结构可从共享运行时受益时附加 shared-runtime profile)
    """

    if composite_only and len(plan.steps) < 2:
        return plan
    if not any(step.kind in step_kinds for step in plan.steps):
        return plan
    return replace(
        plan,
        shared_runtime_profile_id=shared_runtime_profile_id,
        shared_runtime_step_kinds=list(step_kinds),
    )
