"""Composable optimization passes(可组合优化遍) for execution plans"""

from genomelens.analysis.optimization.passes.shared_runtime import attach_shared_runtime_profile

__all__ = ["attach_shared_runtime_profile"]
