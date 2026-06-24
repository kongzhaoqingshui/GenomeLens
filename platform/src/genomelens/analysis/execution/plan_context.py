"""Backward-compatible re-export of shared runtime resources."""

from genomelens.analysis.execution.resources.shared_runtime import (
    PAIRWISE_CACHE_FIELDS,
    PAIRWISE_CACHE_REQUIRED_FIELDS,
    PAIRWISE_CACHE_VERSION,
    PREPROCESSING_CACHE_VERSION,
    PlanRunContext,
    PreparedSpeciesRecord,
    ResolvedPairwiseToolchain,
    SharedRuntimeResources,
    build_plan_run_context,
    build_shared_runtime_for_plan,
    build_shared_runtime_resources,
    pairwise_artifacts_from_json,
    pairwise_cache_key,
    species_fingerprint,
)

__all__ = [
    "PAIRWISE_CACHE_FIELDS",
    "PAIRWISE_CACHE_REQUIRED_FIELDS",
    "PAIRWISE_CACHE_VERSION",
    "PREPROCESSING_CACHE_VERSION",
    "PlanRunContext",
    "PreparedSpeciesRecord",
    "ResolvedPairwiseToolchain",
    "SharedRuntimeResources",
    "build_plan_run_context",
    "build_shared_runtime_for_plan",
    "build_shared_runtime_resources",
    "pairwise_artifacts_from_json",
    "pairwise_cache_key",
    "species_fingerprint",
]
