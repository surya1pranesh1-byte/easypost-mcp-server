from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING, Any, Callable

import easypost

from app.exceptions.app_errors import ExternalServiceError
from app.utils.sanitize import redact_for_logs

if TYPE_CHECKING:
    from app.config.settings import AppConfig


def _map_easypost_error(error: Exception) -> ExternalServiceError:
    status_code = (
        getattr(error, "http_status", None)
        or getattr(error, "statusCode", None)
        or getattr(error, "status", None)
        or 502
    )
    code = getattr(error, "code", None) or "EASYPOST_ERROR"
    message = str(error) or "EasyPost request failed"
    retryable = status_code == 429 or status_code >= 500
    # Include the errors array from EasyPost response (mirrors JS responseMappers behavior)
    nested = getattr(error, "error", None)
    errors = getattr(error, "errors", None) or (getattr(nested, "errors", None) if nested else None)
    details: dict = {"status_code": status_code, "code": code}
    if errors:
        details["errors"] = errors
    return ExternalServiceError(
        message,
        code=code,
        status_code=status_code,
        retryable=retryable,
        details=details,
    )


class EasyPostClient:
    def __init__(self, config: AppConfig) -> None:
        self._config = config
        self._default_client = easypost.EasyPostClient(
            api_key=config.easypost.api_key or "",
        )
        self._timeout_s = config.easypost.timeout_ms / 1000.0
        self._retry_attempts = config.easypost.retry_attempts

    def _get_client(self, api_key_override: str | None) -> easypost.EasyPostClient:
        if api_key_override:
            return easypost.EasyPostClient(api_key=api_key_override)
        return self._default_client

    async def execute(
        self,
        operation: str,
        fn: Callable[[easypost.EasyPostClient], Any],
        context: dict | None = None,
        api_key_override: str | None = None,
    ) -> Any:
        from app.logging.logger import get_logger

        ctx = context or {}
        logger = get_logger().bind(
            correlation_id=ctx.get("correlation_id"),
            operation=operation,
            provider="easypost",
        )
        client = self._get_client(api_key_override)

        for attempt in range(self._retry_attempts + 1):
            started_at = time.monotonic()
            try:
                logger.debug("EasyPost request started", attempt=attempt)
                result = await asyncio.wait_for(
                    asyncio.to_thread(fn, client),
                    timeout=self._timeout_s,
                )
                logger.debug(
                    "EasyPost request completed",
                    attempt=attempt,
                    duration_ms=round((time.monotonic() - started_at) * 1000),
                )
                return result
            except asyncio.TimeoutError:
                # 504 >= 500 → always retryable, matching JS mapEasyPostError behavior
                mapped = ExternalServiceError(
                    "EasyPost request timed out",
                    code="EASYPOST_TIMEOUT",
                    status_code=504,
                    retryable=True,
                )
                logger.warning(
                    "EasyPost request timed out",
                    attempt=attempt,
                    retryable=mapped.retryable,
                )
                if attempt == self._retry_attempts:
                    raise mapped
                await asyncio.sleep(0.1 * (2 ** attempt))
            except Exception as exc:
                mapped = _map_easypost_error(exc)
                logger.warning(
                    "EasyPost request failed",
                    attempt=attempt,
                    retryable=mapped.retryable,
                    err=redact_for_logs(mapped.details or {}),
                )
                if not mapped.retryable or attempt == self._retry_attempts:
                    raise mapped from exc
                await asyncio.sleep(0.1 * (2 ** attempt))
