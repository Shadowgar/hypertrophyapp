from __future__ import annotations

from datetime import date, datetime
from contextvars import ContextVar, Token
import json
import logging
from logging.handlers import RotatingFileHandler
import os
import sys
from typing import Any

LOGGER_NAME = "hypertrophy.app"
logger = logging.getLogger(LOGGER_NAME)

DEFAULT_STDOUT_LEVEL = "INFO"
DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_LOG_FILE_PATH = "logs/app-debug.log"
DEFAULT_LOG_MAX_BYTES = 5_000_000
DEFAULT_LOG_BACKUP_COUNT = 5

REQUIRED_EVENT_FIELDS: tuple[str, ...] = (
    "request_id",
    "route",
    "action",
    "user_id",
    "selected_program_id",
    "template_id",
    "runtime_template_id",
    "path_family",
    "generation_mode",
    "week_index",
    "authored_week_index",
    "target_days",
    "session_id",
    "error_class",
    "error_message",
)

REQUEST_ID_CONTEXT: ContextVar[str | None] = ContextVar("request_id", default=None)

SENSITIVE_KEY_FRAGMENTS: tuple[str, ...] = (
    "password",
    "secret",
    "token",
    "authorization",
    "auth_header",
    "api_key",
)


def _resolve_level(level_name: str, *, default: int = logging.INFO) -> int:
    return logging._nameToLevel.get(str(level_name or "").upper(), default)


def set_request_id(request_id: str | None) -> Token[str | None]:
    return REQUEST_ID_CONTEXT.set(request_id)


def reset_request_id(token: Token[str | None]) -> None:
    REQUEST_ID_CONTEXT.reset(token)


def get_request_id() -> str | None:
    return REQUEST_ID_CONTEXT.get()


def configure_logging(
    *,
    log_level: str = DEFAULT_LOG_LEVEL,
    log_file_path: str = DEFAULT_LOG_FILE_PATH,
    log_max_bytes: int = DEFAULT_LOG_MAX_BYTES,
    log_backup_count: int = DEFAULT_LOG_BACKUP_COUNT,
) -> None:
    """Configure structured stdout + rotating file logging.

    File logging respects LOG_LEVEL (e.g., DEBUG), while stdout remains INFO.
    """
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    formatter = logging.Formatter("%(message)s")

    # Reset existing handlers (avoids duplicates during reload/tests).
    logger.handlers.clear()

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(_resolve_level(DEFAULT_STDOUT_LEVEL, default=logging.INFO))
    stdout_handler.setFormatter(formatter)
    logger.addHandler(stdout_handler)

    normalized_path = str(log_file_path or DEFAULT_LOG_FILE_PATH)
    log_dir = os.path.dirname(normalized_path)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)

    rotating_handler = RotatingFileHandler(
        normalized_path,
        maxBytes=max(1, int(log_max_bytes)),
        backupCount=max(0, int(log_backup_count)),
        encoding="utf-8",
    )
    rotating_handler.setLevel(_resolve_level(log_level, default=logging.INFO))
    rotating_handler.setFormatter(formatter)
    logger.addHandler(rotating_handler)


def _is_sensitive_key(key_hint: str | None) -> bool:
    if not key_hint:
        return False
    lowered = key_hint.lower()
    return any(fragment in lowered for fragment in SENSITIVE_KEY_FRAGMENTS)


def _sanitize(value: Any, *, key_hint: str | None = None) -> Any:
    if _is_sensitive_key(key_hint):
        return "[REDACTED]"
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {
            str(key): sanitized
            for key, raw in value.items()
            if (sanitized := _sanitize(raw, key_hint=str(key))) is not None
        }
    if isinstance(value, (list, tuple, set)):
        return [
            sanitized
            for raw in value
            if (sanitized := _sanitize(raw, key_hint=key_hint)) is not None
        ]
    return str(value)


def log_event(event: str, level: str = "info", **fields: Any) -> None:
    payload = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "level": str(level or "info").upper(),
        "event": event,
        "request_id": get_request_id(),
    }
    payload.update({required_key: None for required_key in REQUIRED_EVENT_FIELDS})
    payload.update(
        {
            key: sanitized
            for key, raw in fields.items()
            if (sanitized := _sanitize(raw, key_hint=key)) is not None
        }
    )
    message = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    getattr(logger, level.lower(), logger.info)(message)


def validation_failure_event_name(path: str) -> str:
    if path == "/plan/adaptation/preview":
        return "frequency_adaptation_preview_failed_validation"
    if path == "/plan/adaptation/apply":
        return "frequency_adaptation_apply_failed_validation"
    if path == "/plan/generate-week":
        return "week_generate_failed_validation"
    if path == "/plan/next-week":
        return "week_next_failed_validation"
    return "request_validation_failed"
