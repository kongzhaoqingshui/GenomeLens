"""engine task(日志任务) 记录辅助函数"""

# region import
from __future__ import annotations

import json
import logging
import time
from collections.abc import Iterator
from contextlib import contextmanager

from jcvi_genomelens.runtime.logging_utils import LOGGER_NAME

# endregion


def _context_text(context: dict[str, object] | None) -> str:
    """把上下文压缩成单行 JSON 字符串"""

    if not context:
        return "{}"
    return json.dumps(context, ensure_ascii=False, sort_keys=True, default=str)


def task_started(*, task_id: str, step: str, context: dict[str, object] | None = None) -> None:
    """记录 engine task 开始"""

    logging.getLogger(LOGGER_NAME).info(
        "task_started task_id=%s step=%s status=STARTED elapsed_ms=0 context=%s",
        task_id,
        step,
        _context_text(context),
    )


def task_finished(
    *,
    task_id: str,
    step: str,
    elapsed_ms: int,
    status: str = "SUCCEEDED",
    context: dict[str, object] | None = None,
) -> None:
    """记录 engine task 结束"""

    logging.getLogger(LOGGER_NAME).info(
        "task_finished task_id=%s step=%s status=%s elapsed_ms=%s context=%s",
        task_id,
        step,
        status,
        elapsed_ms,
        _context_text(context),
    )


def task_failed(
    *,
    task_id: str,
    step: str,
    elapsed_ms: int,
    error: BaseException,
    context: dict[str, object] | None = None,
) -> None:
    """记录 engine task 失败"""

    error_context = dict(context or {})
    error_context.update({"error_type": error.__class__.__name__, "error_message": str(error)})
    logging.getLogger(LOGGER_NAME).exception(
        "task_failed task_id=%s step=%s status=FAILED elapsed_ms=%s context=%s",
        task_id,
        step,
        elapsed_ms,
        _context_text(error_context),
    )


@contextmanager
def task_scope(*, task_id: str, step: str, context: dict[str, object] | None = None) -> Iterator[None]:
    """在上下文中自动记录 engine task 开始、结束和失败"""

    started = time.perf_counter()
    task_started(task_id=task_id, step=step, context=context)
    try:
        yield
    except Exception as exc:
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        task_failed(task_id=task_id, step=step, elapsed_ms=elapsed_ms, error=exc, context=context)
        raise

    elapsed_ms = int((time.perf_counter() - started) * 1000)
    task_finished(task_id=task_id, step=step, elapsed_ms=elapsed_ms, context=context)
