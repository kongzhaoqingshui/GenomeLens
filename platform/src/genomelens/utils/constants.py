"""GenomeLens platform-wide constants(平台级全局常量)

Constants that cross module boundaries (timeouts, default paths) live here so
that runners, adapters, and CLI commands do not hard-code the same magic numbers.
"""

from __future__ import annotations

from pathlib import Path

PROBE_TIMEOUT_SECONDS = 120
"""jcvi-genomelens probe 调用超时(秒)"""

ENGINE_RUN_TIMEOUT_SECONDS = 3600
"""完整 jcvi-genomelens run 引擎调用超时(秒)"""

DEFAULT_WORKSPACE_PATH = Path.home() / "GenomeLensWork"
"""CLI 使用的默认临时/缓存工作区根目录"""
