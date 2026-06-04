from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from datetime import UTC, datetime

import pytest

from backend.app.observability import (
    StructuredFormatter,
    categorize_connector_error,
    configure_logging,
    get_logger,
    log_partial_fetch,
    partial_data_notice,
)
from backend.app.providers.base import (
    ConnectorDataError,
    ConnectorError,
    ConnectorUnavailable,
    FetchResult,
)


def _fetch_result(**kwargs: object) -> FetchResult:
    defaults: dict[str, object] = {
        "bundle": {"resourceType": "Bundle"},
        "source": "mock-fhir",
        "fetched_at": datetime.now(UTC),
    }
    defaults.update(kwargs)
    return FetchResult(**defaults)  # type: ignore[arg-type]


class _CaptureHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


@pytest.fixture
def capture_medflow() -> Iterator[_CaptureHandler]:
    handler = _CaptureHandler()
    logger = logging.getLogger("medflow")
    logger.addHandler(handler)
    try:
        yield handler
    finally:
        logger.removeHandler(handler)


# --- structured logging -----------------------------------------------------


def test_structured_formatter_emits_valid_json_with_context():
    formatter = StructuredFormatter()
    record = logging.LogRecord(
        name="medflow.api",
        level=logging.WARNING,
        pathname=__file__,
        lineno=1,
        msg="hello %s",
        args=("world",),
        exc_info=None,
    )
    record.context = {"path": "/health", "status": 200}

    parsed = json.loads(formatter.format(record))

    assert parsed["level"] == "WARNING"
    assert parsed["logger"] == "medflow.api"
    assert parsed["message"] == "hello world"
    assert parsed["context"] == {"path": "/health", "status": 200}


def test_configure_logging_is_idempotent():
    logger = configure_logging()
    handler_count = len(logger.handlers)
    again = configure_logging(logging.DEBUG)

    assert again is logger
    assert len(again.handlers) == handler_count
    assert again.level == logging.DEBUG


def test_get_logger_is_namespaced_under_medflow():
    assert get_logger("api").name == "medflow.api"


# --- connector error categorization -----------------------------------------


def test_unavailable_error_is_retryable():
    result = categorize_connector_error(ConnectorUnavailable("down"))
    assert result.category == "source_unavailable"
    assert result.retryable is True


def test_data_error_is_not_retryable():
    result = categorize_connector_error(ConnectorDataError("bad payload"))
    assert result.category == "source_data_error"
    assert result.retryable is False


def test_base_connector_error_falls_back_to_message():
    result = categorize_connector_error(ConnectorError("something odd"))
    assert result.category == "connector_error"
    assert result.message == "something odd"
    assert result.retryable is False


def test_base_connector_error_without_message_has_default():
    result = categorize_connector_error(ConnectorError())
    assert result.message == "A data source error occurred."


# --- partial-data notice ----------------------------------------------------


def test_complete_fetch_produces_no_notice():
    result = _fetch_result(partial=False, warnings=[])
    assert partial_data_notice(result) is None


def test_partial_fetch_surfaces_warnings_and_missing_categories():
    result = _fetch_result(
        partial=True,
        warnings=["conditions endpoint timed out"],
        coverage={
            "patient": {"requested": True, "returned": True},
            "conditions": {"requested": True, "returned": False},
        },
    )

    notice = partial_data_notice(result)

    assert notice is not None
    assert notice["partial"] is True
    assert notice["source"] == "mock-fhir"
    assert notice["warnings"] == ["conditions endpoint timed out"]
    assert notice["missing"] == ["conditions"]


def test_warnings_without_partial_flag_still_surface():
    result = _fetch_result(partial=False, warnings=["one record skipped"])
    notice = partial_data_notice(result)
    assert notice is not None
    assert notice["warnings"] == ["one record skipped"]


def test_log_partial_fetch_emits_structured_warning(capture_medflow: _CaptureHandler):
    logger = get_logger("test")
    result = _fetch_result(partial=True, warnings=["partial"])

    notice = log_partial_fetch(logger, result)

    assert notice is not None
    assert len(capture_medflow.records) == 1
    record = capture_medflow.records[0]
    assert record.levelno == logging.WARNING
    assert record.context["partial"] is True


def test_log_partial_fetch_stays_silent_when_complete(capture_medflow: _CaptureHandler):
    logger = get_logger("test")
    result = _fetch_result(partial=False, warnings=[])

    notice = log_partial_fetch(logger, result)

    assert notice is None
    assert capture_medflow.records == []
