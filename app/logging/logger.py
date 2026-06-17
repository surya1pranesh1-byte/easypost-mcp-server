from __future__ import annotations

import logging
import sys
from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from app.config.settings import AppConfig

_LEVEL_MAP = {
    "trace": 5,
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warn": logging.WARNING,
    "error": logging.ERROR,
    "fatal": logging.CRITICAL,
    "silent": logging.CRITICAL + 10,
}

logging.addLevelName(5, "TRACE")

# Fields that must never appear in plaintext in logs (mirrors Pino redact paths)
_REDACT_KEYS = frozenset({
    "authorization", "api_key", "apiKey", "token", "password",
    "EASYPOST_API_KEY", "secret", "client_secret",
    # PII
    "street1", "street2", "name", "company", "phone", "email",
})


def _auto_redact(logger: Any, method: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    """Automatically mask sensitive fields at the structlog processor level.

    Mirrors Pino's built-in `redact` option — if any developer logs a sensitive
    key without manually calling redact_for_logs(), this processor catches it.
    """
    for key in list(event_dict.keys()):
        if key in _REDACT_KEYS:
            raw = str(event_dict[key])
            if len(raw) <= 4:
                event_dict[key] = "***"
            else:
                event_dict[key] = f"{raw[:2]}***{raw[-2:]}"
    return event_dict


_logger: structlog.stdlib.BoundLogger | None = None


def init_logger(config: "AppConfig") -> structlog.stdlib.BoundLogger:
    global _logger

    level_name = config.logging.level
    numeric_level = _LEVEL_MAP.get(level_name, logging.INFO)

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stderr,
        level=numeric_level,
    )

    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            _auto_redact,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    _logger = structlog.get_logger().bind(
        service="easypost-mcp",
        environment=config.env,
        easypost_mode=config.easypost.mode,
    )
    return _logger


def get_logger() -> structlog.stdlib.BoundLogger:
    if _logger is None:
        raise RuntimeError("Logger not initialized. Call init_logger() during server startup.")
    return _logger
