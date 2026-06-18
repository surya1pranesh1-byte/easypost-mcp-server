from __future__ import annotations

from typing import Any, Type, TYPE_CHECKING

from pydantic import BaseModel, ValidationError as PydanticValidationError

from app.exceptions.app_errors import ValidationError
from app.utils.sanitize import sanitize_input
from app.validators.anti_hallucination import assert_not_hallucinated

if TYPE_CHECKING:
    from app.resources.resource_manager import ResourceManager


def validate_input(
    schema_cls: Type[BaseModel],
    raw_input: dict[str, Any] | None,
    *,
    resource_manager: "ResourceManager | None" = None,
    tool_name: str | None = None,
    risk: str | None = None,
) -> BaseModel:
    sanitized = sanitize_input(raw_input or {})

    try:
        parsed = schema_cls.model_validate(sanitized)
    except PydanticValidationError as exc:
        issues = [
            {
                "path": ".".join(str(loc) for loc in e["loc"]),
                "message": e["msg"],
                "code": e["type"],
                "received": e.get("input"),
            }
            for e in exc.errors()
        ]
        raise ValidationError("Tool input validation failed", details=issues) from exc

    assert_not_hallucinated(
        parsed.model_dump(exclude_none=True),
        tool_name=tool_name,
        resource_manager=resource_manager,
    )
    return parsed


def model_to_json_schema(
    schema_cls: Type[BaseModel],
    name: str | None = None,
    exclude_fields: list[str] | None = None,
) -> dict[str, Any]:
    """Convert a Pydantic model to a JSON Schema dict for MCP tool registration."""
    schema = schema_cls.model_json_schema()
    schema.pop("title", None)
    if name:
        schema["title"] = name
    if exclude_fields:
        props = schema.get("properties", {})
        required = schema.get("required", [])
        for f in exclude_fields:
            props.pop(f, None)
            if f in required:
                required.remove(f)
    return schema
