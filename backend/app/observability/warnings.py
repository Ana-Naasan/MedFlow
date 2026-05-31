from __future__ import annotations

import logging
from dataclasses import dataclass

from backend.app.providers.base import (
    ConnectorDataError,
    ConnectorError,
    ConnectorUnavailable,
    FetchResult,
)

_UNAVAILABLE = "source_unavailable"
_DATA_ERROR = "source_data_error"
_UNKNOWN = "connector_error"


@dataclass(slots=True)
class ErrorCategory:
    category: str
    message: str
    retryable: bool


def categorize_connector_error(exc: ConnectorError) -> ErrorCategory:
    """Map a ConnectorError onto a clear, user-facing category."""
    if isinstance(exc, ConnectorUnavailable):
        return ErrorCategory(
            category=_UNAVAILABLE,
            message="The data source is temporarily unreachable. Showing what we already have.",
            retryable=True,
        )
    if isinstance(exc, ConnectorDataError):
        return ErrorCategory(
            category=_DATA_ERROR,
            message="The data source returned records we could not read. Showing what we have.",
            retryable=False,
        )
    return ErrorCategory(
        category=_UNKNOWN,
        message=str(exc) or "A data source error occurred.",
        retryable=False,
    )


def _missing_categories(coverage: dict[str, dict[str, bool]]) -> list[str]:
    return sorted(
        name
        for name, flags in coverage.items()
        if flags.get("requested") and not flags.get("returned")
    )


def partial_data_notice(result: FetchResult) -> dict[str, object] | None:
    """Build a non-blocking notice for a partial fetch, or None when complete.

    A complete fetch (not partial, no warnings) returns None so callers can
    attach the notice only when there is something honest to surface.
    """
    if not result.partial and not result.warnings:
        return None
    return {
        "level": "warning",
        "source": result.source,
        "partial": result.partial,
        "message": "Some data could not be retrieved from this source.",
        "warnings": list(result.warnings),
        "missing": _missing_categories(result.coverage),
    }


def log_partial_fetch(logger: logging.Logger, result: FetchResult) -> dict[str, object] | None:
    """Emit a structured warning when a fetch is partial; return the notice."""
    notice = partial_data_notice(result)
    if notice is not None:
        logger.warning("partial fetch from %s", result.source, extra={"context": notice})
    return notice
