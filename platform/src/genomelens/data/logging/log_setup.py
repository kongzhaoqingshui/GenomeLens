"""CLI(命令行接口) 与 workflow(工作流) 运行的日志初始化"""

# region import
from __future__ import annotations

import hashlib
import logging
import sys
from pathlib import Path

# endregion


LOGGER_NAME = "genomelens"
RUN_LOGGER_PREFIX = f"{LOGGER_NAME}.run"


class ConciseConsoleFilter(logging.Filter):
    """控制台默认静默，只输出初始启动信息与警告/错误"""

    # 仅允许以该前缀开头的 INFO/DEBUG 消息输出到控制台
    _allowed_info_prefix: str = "Starting GenomeLens"

    def filter(self, record: logging.LogRecord) -> bool:
        # WARNING/ERROR/CRITICAL 始终输出到控制台，方便用户及时看到问题
        if record.levelno >= logging.WARNING:
            return True

        # 其余级别只保留初始启动句段，避免 task_started/task_finished 等大段日志刷屏
        message = record.getMessage()
        return message.startswith(self._allowed_info_prefix)


def normalize_log_level(level: str) -> str:
    """把日志级别规范化为 logging 支持的名称"""

    normalized = str(level or "INFO").upper()
    if normalized not in {"DEBUG", "INFO", "WARNING", "ERROR"}:
        return "INFO"
    return normalized


def logger_name_for_path(path: str | Path) -> str:
    """为某个 run.log 生成稳定且互不干扰的 logger 名称"""

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
    """Flush and close GenomeLens logging handlers"""

    _close_handlers(logging.getLogger(logger_name))


def setup_logging(
    log_file: str | Path | None = None,
    *,
    level: str = "INFO",
    logger_name: str = LOGGER_NAME,
) -> logging.Logger:
    """配置 root logging(根日志)，可选写出 UTF-8 日志文件"""

    logger = logging.getLogger(logger_name)
    logger.setLevel(getattr(logging, normalize_log_level(level), logging.INFO))
    logger.propagate = False
    # 反复初始化时先清空旧 handler，避免同一条日志被重复输出。
    _close_handlers(logger)
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    stream = logging.StreamHandler(sys.stderr)
    stream.setFormatter(formatter)
    stream.addFilter(ConciseConsoleFilter())
    logger.addHandler(stream)
    if log_file is not None:
        path = Path(log_file)
        # 文件日志目录在这里兜底创建，调用方不必额外关心父目录是否存在。
        path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(path, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    return logger
