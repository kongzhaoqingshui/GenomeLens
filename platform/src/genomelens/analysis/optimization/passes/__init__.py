"""Composable optimization passes for execution plans"""

from genomelens.analysis.optimization.passes.shared_runtime import attach_shared_runtime_profile

__all__ = ["attach_shared_runtime_profile"]
