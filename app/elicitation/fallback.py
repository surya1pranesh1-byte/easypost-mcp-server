from __future__ import annotations

from typing import Any

from app.elicitation.field_catalog import examples_for_fields, get_field_metadata


def create_fallback_response(
    *,
    error_code: str,
    message: str,
    missing_fields: list[str] | None = None,
    ambiguous_fields: list | None = None,
    available_options: list | None = None,
    examples: dict | None = None,
    next_action: str | None = None,
    workflow_id: str | None = None,
    valid_values: dict | None = None,
    metadata: dict | None = None,
) -> dict[str, Any]:
    missing = missing_fields or []
    ambiguous = ambiguous_fields or []

    all_paths = [*missing, *(f.get("path") or f.get("field") for f in ambiguous if isinstance(f, dict))]
    all_paths = [p for p in all_paths if p]

    return {
        "ok": False,
        "success": False,
        "error_code": error_code,
        "message": message,
        "workflow_id": workflow_id,
        "missing_fields": missing,
        "ambiguous_fields": ambiguous,
        "available_options": available_options or [],
        "examples": examples if examples is not None else examples_for_fields(missing),
        "valid_values": valid_values or {},
        "field_metadata": {
            **{path: get_field_metadata(path) for path in all_paths},
            **(metadata or {}),
        },
        "next_action": next_action,
    }
