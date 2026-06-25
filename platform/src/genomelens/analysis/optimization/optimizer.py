"""Optimization pipeline(优化流水线) between raw planning and execution"""

from __future__ import annotations

from dataclasses import replace

from genomelens.analysis.optimization.models import (
    SYNTENY_PAIRWISE_REUSE_PROFILE_ID,
    get_optimization_registry,
)
from genomelens.analysis.optimization.passes.shared_runtime import attach_shared_runtime_profile
from genomelens.analysis.planning.models import ExecutionPlan
from genomelens.analysis.requests.models import WorkflowRequest
from genomelens.analysis.workflows.onestop import get_onestop_registry


class PlanOptimizer:
    """Apply declarative optimization profiles(应用声明式优化配置) to a raw execution plan"""

    def optimize(self, request: WorkflowRequest, plan: ExecutionPlan) -> ExecutionPlan:
        """Return an optimized execution plan while preserving plan semantics
        (在保持计划语义的前提下返回优化后的执行计划)
        """

        profile_id = self._profile_id_for_request(request)
        if not profile_id:
            return plan

        profile = get_optimization_registry().get(profile_id)
        if profile is None:
            return plan

        optimized = replace(plan, optimizer_profile_id=profile.profile_id)
        if profile.shared_runtime_profile_id:
            optimized = attach_shared_runtime_profile(
                optimized,
                profile.shared_runtime_profile_id,
                composite_only=profile.composite_only,
            )
        return optimized

    @staticmethod
    def _profile_id_for_request(request: WorkflowRequest) -> str:
        """Resolve the optimization profile for a one-stop workflow request(为一站式工作流请求解析优化配置)"""

        spec = get_onestop_registry().get(request.workflow_id)
        if spec is not None and spec.optimizer_profile_id:
            return spec.optimizer_profile_id

        # 过渡回退：在全部一站式工作流注册完成前，按 workflow_id 硬编码匹配
        if request.workflow_id in {"synteny", "local_synteny"}:
            return SYNTENY_PAIRWISE_REUSE_PROFILE_ID
        return ""
