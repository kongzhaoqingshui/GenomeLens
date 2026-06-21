import logging
import shutil
import sys
from pathlib import Path

from jcvi_genomelens.runtime.command_runner import run_command, run_python_step
from jcvi_genomelens.runtime.logging_utils import close_engine_logging, setup_engine_logging


def _file_handler(logger: logging.Logger) -> logging.FileHandler:
    for handler in logger.handlers:
        if isinstance(handler, logging.FileHandler):
            return handler
    raise AssertionError("file handler not found")


def test_setup_engine_logging_closes_previous_file_handler(tmp_path: Path) -> None:
    first_dir = tmp_path / "first"
    logger = setup_engine_logging(first_dir / "run.log")
    first_handler = _file_handler(logger)

    setup_engine_logging(tmp_path / "second" / "run.log")

    assert first_handler.stream is None
    shutil.rmtree(first_dir)
    close_engine_logging()


def test_close_engine_logging_releases_log_directory(tmp_path: Path) -> None:
    log_dir = tmp_path / "logs"
    logger = setup_engine_logging(log_dir / "run.log")
    logger.info("write before closing")

    close_engine_logging()

    assert logger.handlers == []
    shutil.rmtree(log_dir)
    assert not log_dir.exists()


def test_engine_run_command_writes_task_log(tmp_path: Path) -> None:
    log_path = tmp_path / "logs" / "run.log"
    setup_engine_logging(log_path)

    result = run_command([sys.executable, "-c", "print('ok')"])

    close_engine_logging()
    text = log_path.read_text(encoding="utf-8")

    assert result.returncode == 0
    assert "task_started task_id=engine" in text
    assert "task_finished task_id=engine" in text
    assert "status=SUCCEEDED" in text
    assert "returncode" in text


def test_engine_python_step_logs_failed_returncode(tmp_path: Path) -> None:
    log_path = tmp_path / "logs" / "run.log"
    setup_engine_logging(log_path)

    def fail(_args: list[str]) -> None:
        raise RuntimeError("boom")

    result = run_python_step("demo.step", fail, [])

    close_engine_logging()
    text = log_path.read_text(encoding="utf-8")

    assert result.returncode == 1
    assert "step=demo.step status=FAILED" in text
    assert "RuntimeError: boom" in result.stderr
