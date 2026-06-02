from __future__ import annotations

import json
import logging
from datetime import UTC, datetime

_ROOT_LOGGER_NAME = "umraa"
_configured = False


class StructuredFormatter(logging.Formatter):
    """Render log records as single-line JSON for machine-readable logs."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "ts": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        context = getattr(record, "context", None)
        if isinstance(context, dict):
            payload["context"] = context
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str, sort_keys=True)


def configure_logging(level: int | str = logging.INFO) -> logging.Logger:
    """Attach a single structured handler to the umraa root logger.

    Idempotent: repeated calls update the level but never stack handlers.
    """
    global _configured
    root = logging.getLogger(_ROOT_LOGGER_NAME)
    root.setLevel(level)
    if not _configured:
        handler = logging.StreamHandler()
        handler.setFormatter(StructuredFormatter())
        root.addHandler(handler)
        root.propagate = False
        _configured = True
    return root


def get_logger(name: str) -> logging.Logger:
    """Return a namespaced child of the umraa logger (e.g. ``umraa.api``)."""
    return logging.getLogger(f"{_ROOT_LOGGER_NAME}.{name}")
