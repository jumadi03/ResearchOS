"""Structured logging with request correlation context."""

from contextvars import ContextVar
from datetime import datetime, timezone
import json
import logging
from pathlib import Path


correlation_id_context: ContextVar[str] = ContextVar(
    "correlation_id", default="unscoped"
)


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "event": getattr(record, "event", record.getMessage()),
            "correlation_id": correlation_id_context.get(),
            **getattr(record, "fields", {}),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def configure_logging(log_directory: Path | None = None) -> logging.Logger:
    logger = logging.getLogger("ResearchOS")
    logger.setLevel(logging.INFO)
    if logger.handlers:
        return logger
    directory = log_directory or Path("logs")
    directory.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(directory / "researchos.jsonl", encoding="utf-8")
    handler.setFormatter(JSONFormatter())
    logger.addHandler(handler)
    return logger


logger = configure_logging()
