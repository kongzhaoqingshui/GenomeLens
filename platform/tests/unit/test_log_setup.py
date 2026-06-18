import logging
import shutil
from pathlib import Path

from genomelens.data.logging.log_setup import close_logging, logger_name_for_path, normalize_log_level, setup_logging
from genomelens.data.logging.task_log import task_scope


def _file_handler(logger: logging.Logger) -> logging.FileHandler:
    for handler in logger.handlers:
        if isinstance(handler, logging.FileHandler):
            return handler
    raise AssertionError("file handler not found")


def test_setup_logging_closes_previous_file_handler(tmp_path: Path) -> None:
    first_dir = tmp_path / "first" / "logs"
    logger = setup_logging(first_dir / "run.log")
    first_handler = _file_handler(logger)

    setup_logging(tmp_path / "second" / "logs" / "run.log")

    assert first_handler.stream is None
    shutil.rmtree(first_dir)
    close_logging()


def test_close_logging_releases_log_directory(tmp_path: Path) -> None:
    log_dir = tmp_path / "logs"
    logger = setup_logging(log_dir / "run.log")
    logger.info("write before closing")

    close_logging()

    assert logger.handlers == []
    shutil.rmtree(log_dir)
    assert not log_dir.exists()


def test_normalize_log_level_falls_back_to_info() -> None:
    assert normalize_log_level("debug") == "DEBUG"
    assert normalize_log_level("nope") == "INFO"


def test_setup_logging_supports_isolated_run_loggers(tmp_path: Path) -> None:
    first = tmp_path / "first" / "logs" / "run.log"
    second = tmp_path / "second" / "logs" / "run.log"
    first_logger = setup_logging(first, logger_name=logger_name_for_path(first))
    second_logger = setup_logging(second, logger_name=logger_name_for_path(second))

    first_logger.info("first only")
    second_logger.info("second only")

    close_logging(logger_name_for_path(first))
    close_logging(logger_name_for_path(second))

    assert "first only" in first.read_text(encoding="utf-8")
    assert "second only" not in first.read_text(encoding="utf-8")
    assert "second only" in second.read_text(encoding="utf-8")


def test_task_scope_writes_structured_fields(tmp_path: Path) -> None:
    log_path = tmp_path / "logs" / "run.log"
    logger_name = logger_name_for_path(log_path)
    logger = setup_logging(log_path, logger_name=logger_name)

    with task_scope(logger, task_id="query__subject", step="prepare_inputs", context={"species_count": 2}):
        pass

    close_logging(logger_name)
    text = log_path.read_text(encoding="utf-8")

    assert "task_started task_id=query__subject step=prepare_inputs status=STARTED" in text
    assert "task_finished task_id=query__subject step=prepare_inputs status=SUCCEEDED" in text
    assert "elapsed_ms=" in text
    assert '"species_count": 2' in text
