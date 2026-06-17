from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.utils.sanitize import redact_for_logs

if TYPE_CHECKING:
    import structlog


class AuditLogger:
    def __init__(self, logger: structlog.stdlib.BoundLogger) -> None:
        self._logger = logger

    def record(self, event: str, payload: dict[str, Any] | None = None) -> None:
        self._logger.info(
            event=event,
            audit=True,
            **redact_for_logs(payload or {}),
        )
