from __future__ import annotations

from typing import Any

_SECRET_KEYS = frozenset({"authorization", "api_key", "apiKey", "token", "password", "EASYPOST_API_KEY"})
_PII_KEYS = frozenset({"street1", "street2", "name", "company", "phone", "email"})


def _mask_value(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    if len(value) <= 4:
        return "***"
    return f"{value[:2]}***{value[-2:]}"


def _sanitize_string(value: str) -> str:
    import re
    return re.sub(r"\s+", " ", value.strip())


def sanitize_input(value: Any) -> Any:
    if isinstance(value, list):
        return [sanitize_input(item) for item in value]
    if isinstance(value, str):
        return _sanitize_string(value)
    if not isinstance(value, dict):
        return value
    return {k: sanitize_input(v) for k, v in value.items()}


def redact_for_logs(value: Any) -> Any:
    if isinstance(value, list):
        return [redact_for_logs(item) for item in value]
    if not isinstance(value, dict):
        return value
    result: dict[str, Any] = {}
    for key, nested in value.items():
        if key in _SECRET_KEYS:
            result[key] = "***REDACTED***"
        elif key in _PII_KEYS:
            result[key] = _mask_value(nested)
        else:
            result[key] = redact_for_logs(nested)
    return result
