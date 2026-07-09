# backend/src/utils/logging_config.py
"""
Centralized logging configuration for LLMAIx Web backend.

Usage:
    from .utils.logging_config import setup_logging

    setup_logging()  # call once at application startup (web + each Celery worker)

Log level is configurable via the LOG_LEVEL environment variable (default: INFO).
Valid values: DEBUG, INFO, WARNING, ERROR, CRITICAL

Output format is configurable via LOG_FORMAT (``text`` default, or ``json`` for
a structured line a SIEM/Loki can parse). Every record carries the per-request
correlation id (``request_id``) when one is set, so app logs, the audit trail,
and the central error log all join on the same id.
"""

import json
import logging
import os
import sys
from logging.handlers import RotatingFileHandler

from .request_context import get_request_id

# Default text format: timestamp, level, module:line, correlation id, message
_DEFAULT_FORMAT = (
    "[%(asctime)s] %(levelname)-8s %(name)s:%(lineno)d [%(request_id)s] — %(message)s"
)
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


class _RequestIdFilter(logging.Filter):
    """Attach the current request's correlation id to every record.

    Uses ``-`` outside a request (startup, Celery task bodies that haven't set a
    context) so the format string never fails.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id() or "-"
        return True


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": self.formatTime(record, _DATE_FORMAT),
            "level": record.levelname,
            "logger": record.name,
            "line": record.lineno,
            "request_id": getattr(record, "request_id", "-"),
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


def setup_logging(
    *,
    level: str | None = None,
    log_format: str | None = None,
    text_format: str = _DEFAULT_FORMAT,
    date_format: str = _DATE_FORMAT,
    log_file: str | None = None,
    max_bytes: int = 10 * 1024 * 1024,
    backup_count: int = 3,
) -> None:
    """Configure root logger with a consistent format and level.

    Parameters
    ----------
    level : str, optional
        Log level string. Falls back to ``LOG_LEVEL`` env var, then ``INFO``.
    log_format : str, optional
        ``text`` (human-readable, default) or ``json`` (structured). Falls back
        to the ``LOG_FORMAT`` env var, then ``text``.
    text_format : str
        Format string used when ``log_format`` is ``text``.
    date_format : str
        Date format for ``asctime``.
    log_file : str, optional
        Path to a log file. If set, logs are written both to stdout and to
        this file (with rotation).
    max_bytes : int
        Max size per log file before rotation (default 10 MB).
    backup_count : int
        Number of rotated log files to keep (default 3).
    """
    log_level = (level or os.getenv("LOG_LEVEL", "INFO")).upper()

    valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
    if log_level not in valid_levels:
        print(
            f"Invalid LOG_LEVEL '{log_level}', falling back to INFO. "
            f"Valid values: {', '.join(sorted(valid_levels))}",
            file=sys.stderr,
        )
        log_level = "INFO"

    fmt_kind = (log_format or os.getenv("LOG_FORMAT", "text")).lower()
    if fmt_kind == "json":
        formatter: logging.Formatter = _JsonFormatter()
    else:
        formatter = logging.Formatter(text_format, date_format)

    request_id_filter = _RequestIdFilter()

    # Remove any pre-existing handlers on the root logger (e.g. from Celery)
    root = logging.getLogger()
    for h in root.handlers[:]:
        root.removeHandler(h)
        try:
            h.close()
        except Exception:
            pass

    root.setLevel(log_level)

    # --- Stream handler (stdout) ---
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(log_level)
    stream_handler.setFormatter(formatter)
    stream_handler.addFilter(request_id_filter)
    root.addHandler(stream_handler)

    # --- Optional rotating file handler ---
    if log_file:
        try:
            file_handler = RotatingFileHandler(
                log_file, maxBytes=max_bytes, backupCount=backup_count
            )
            file_handler.setLevel(log_level)
            file_handler.setFormatter(formatter)
            file_handler.addFilter(request_id_filter)
            root.addHandler(file_handler)
        except OSError as exc:
            root.warning("Could not open log file %s: %s", log_file, exc)

    # Quiet noisy third-party loggers (optional)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("botocore").setLevel(logging.WARNING)
    logging.getLogger("PIL").setLevel(logging.WARNING)
    logging.getLogger("openai._base_client").setLevel(logging.WARNING)

    root.info(
        "Logging configured: level=%s, format=%s, file=%s",
        log_level,
        fmt_kind,
        log_file or "(stdout only)",
    )
