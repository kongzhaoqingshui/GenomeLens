"""Workflow run log(日志) 的 CLI 日志配置工具"""

# region import
from __future__ import annotations

import hashlib
import logging
import sys
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

# endregion


LOGGER_NAME = "genomelens"
RUN_LOGGER_PREFIX = f"{LOGGER_NAME}.run"


class ConciseConsoleFilter(logging.Filter):
    """Keep the console concise by default."""

    _allowed_info_prefix: str = "Starting GenomeLens"

    def filter(self, record: logging.LogRecord) -> bool:
        """仅允许 WARNING 及以上，或前缀为启动信息的日志通过"""

        if record.levelno >= logging.WARNING:
            return True

        return record.getMessage().startswith(self._allowed_info_prefix)


def normalize_log_level(level: str) -> str:
    """Normalize user log levels to supported logging names."""

    normalized = str(level or "INFO").upper()
    if normalized not in {"DEBUG", "INFO", "WARNING", "ERROR"}:
        return "INFO"
    return normalized


def logger_name_for_path(path: str | Path) -> str:
    """Build a stable logger name for a run.log path."""

    resolved = str(Path(path).expanduser().resolve(strict=False))
    digest = hashlib.sha1(resolved.encode("utf-8")).hexdigest()[:12]
    return f"{RUN_LOGGER_PREFIX}.{digest}"


def _close_handlers(logger: logging.Logger) -> None:
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        try:
            handler.flush()
        finally:
            handler.close()


def close_logging(logger_name: str = LOGGER_NAME) -> None:
    """Flush and close GenomeLens logging handlers."""

    _close_handlers(logging.getLogger(logger_name))


def setup_logging(
    log_file: str | Path | None = None,
    *,
    level: str = "INFO",
    logger_name: str = LOGGER_NAME,
    console: bool = True,
    concise: bool = True,
) -> logging.Logger:
    """Configure run logging and optionally attach console/file handlers."""

    logger = logging.getLogger(logger_name)
    logger.setLevel(getattr(logging, normalize_log_level(level), logging.INFO))
    logger.propagate = False
    _close_handlers(logger)

    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")

    if console:
        stream = logging.StreamHandler(sys.stderr)
        stream.setFormatter(formatter)
        if concise:
            stream.addFilter(ConciseConsoleFilter())
        logger.addHandler(stream)

    if log_file is not None:
        path = Path(log_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(path, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


@contextmanager
def run_with_logging(
    log_file: str | Path,
    *,
    level: str = "INFO",
    console: bool = True,
    concise: bool = True,
) -> Generator[logging.Logger, None, None]:
    """Setup logging for a run and guarantee cleanup via a context manager."""

    logger_name = logger_name_for_path(log_file)
    logger = setup_logging(
        log_file,
        level=level,
        logger_name=logger_name,
        console=console,
        concise=concise,
    )
    try:
        yield logger
    finally:
        close_logging(logger_name)
