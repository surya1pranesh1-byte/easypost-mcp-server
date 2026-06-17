from __future__ import annotations

from typing import TYPE_CHECKING, Any

import httpx

if TYPE_CHECKING:
    import structlog

_EASYPOST_API_BASE_URL = "https://api.easypost.com"
_EASYPOST_API_KEYS_ENDPOINT = "/v2/api_keys"
_TEST_KEY_PREFIX = "EZTK"
_PRODUCTION_KEY_PREFIX = "EZAK"


async def validate_easypost_api_key(
    api_key: str,
    logger: structlog.stdlib.BoundLogger | None = None,
) -> dict[str, Any]:
    """Validate an EasyPost API key by calling the /v2/api_keys endpoint.

    Validation rules:
    1. HTTP 200 → valid
    2. MODE.UNAUTHORIZED + test key (EZTK...) → valid (endpoint requires production key)
    3. Other auth failures → invalid
    """
    if not api_key:
        return {"valid": False, "reason": "API key is required"}

    url = f"{_EASYPOST_API_BASE_URL}{_EASYPOST_API_KEYS_ENDPOINT}"
    key_format = api_key[:10] + "***" if len(api_key) >= 10 else "***"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                timeout=10.0,
            )

        if response.status_code == 200:
            if logger:
                logger.debug(
                    "EasyPost API key validation successful",
                    key_format=key_format,
                    endpoint=_EASYPOST_API_KEYS_ENDPOINT,
                )
            return {"valid": True}

        try:
            error_body = response.json()
        except Exception:
            error_body = {"error": {"code": "PARSE_ERROR", "message": response.reason_phrase}}

        error_code = (error_body.get("error") or {}).get("code")
        error_message = (error_body.get("error") or {}).get("message")

        if error_code == "MODE.UNAUTHORIZED" and api_key.startswith(_TEST_KEY_PREFIX):
            if logger:
                logger.debug(
                    "Test API key validation: MODE.UNAUTHORIZED (expected for test keys)",
                    key_format=key_format,
                    error_code=error_code,
                )
            return {"valid": True}

        auth_failure_codes = {"UNAUTHORIZED", "INVALID_API_KEY", "UNAUTHENTICATED"}
        if error_code in auth_failure_codes or response.status_code in (401, 403):
            if logger:
                logger.warning(
                    "Invalid EasyPost API key validation attempt",
                    key_format=key_format,
                    error_code=error_code,
                    error_message=error_message,
                    status=response.status_code,
                )
            return {"valid": False, "reason": error_message or "Invalid API key"}

        if logger:
            logger.warning(
                "EasyPost API key validation failed with unexpected error",
                key_format=key_format,
                error_code=error_code,
                status=response.status_code,
            )
        return {"valid": False, "reason": error_message or f"Validation failed with status {response.status_code}"}

    except Exception as exc:
        if logger:
            logger.warning(
                "EasyPost API key validation error",
                key_format=key_format,
                error_name=type(exc).__name__,
                error_message=str(exc),
            )
        return {"valid": False, "reason": str(exc) or "Validation request failed"}
