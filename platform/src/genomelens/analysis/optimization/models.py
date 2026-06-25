"""Optimization profile models for execution-plan rewriting"""

from __future__ import annotations

from dataclasses import dataclass

SYNTENY_PAIRWISE_REUSE_PROFILE_ID = "synteny_pairwise_reuse_v1"
PAIRWISE_SHARED_RUNTIME_PROFILE_ID = "pairwise_synteny_v1"


@dataclass(frozen=True)
class OptimizationProfileSpec:
    """Declarative optimization profile applied between planning and execution"""

    profile_id: str
    shared_runtime_profile_id: str = ""
    composite_only: bool = True


class OptimizationProfileRegistry:
    """Registry of built-in optimization profiles"""

    def __init__(self) -> None:
        self._profiles = {
            SYNTENY_PAIRWISE_REUSE_PROFILE_ID: OptimizationProfileSpec(
                profile_id=SYNTENY_PAIRWISE_REUSE_PROFILE_ID,
                shared_runtime_profile_id=PAIRWISE_SHARED_RUNTIME_PROFILE_ID,
                composite_only=True,
            )
        }

    def get(self, profile_id: str) -> OptimizationProfileSpec | None:
        """Return a registered optimization profile"""

        return self._profiles.get(profile_id)


_OPTIMIZATION_REGISTRY: OptimizationProfileRegistry | None = None


def get_optimization_registry() -> OptimizationProfileRegistry:
    """Return the process-wide optimization registry"""

    global _OPTIMIZATION_REGISTRY
    if _OPTIMIZATION_REGISTRY is None:
        _OPTIMIZATION_REGISTRY = OptimizationProfileRegistry()
    assert _OPTIMIZATION_REGISTRY is not None
    return _OPTIMIZATION_REGISTRY
