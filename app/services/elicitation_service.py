from __future__ import annotations

import copy
from typing import Any

from app.elicitation.field_catalog import schema_for_field


class ElicitationService:
    def supports_form(self, server: Any) -> bool:
        try:
            ctx = server.request_context if server else None
            caps = ctx.session.client_params.capabilities if ctx else None
            return getattr(caps, "elicitation", None) is not None
        except Exception:
            return False

    async def request_form(
        self,
        *,
        server: Any,
        message: str,
        properties: dict[str, Any],
        required: list[str] | None = None,
        timeout_ms: int = 120000,
    ) -> dict[str, Any]:
        if not server:
            return {"accepted": False, "reason": "FORM_ELICITATION_UNAVAILABLE"}
        try:
            ctx = server.request_context
            requested_schema: dict = {
                "type": "object",
                "properties": properties,
                "required": required or [],
            }
            result = await ctx.session.elicit_form(
                message,
                requested_schema,
                related_request_id=ctx.request_id,
            )
            if result.action != "accept":
                action = str(result.action or "UNKNOWN").upper()
                return {"accepted": False, "reason": f"ELICITATION_{action}"}
            return {"accepted": True, "content": result.content or {}}
        except Exception as exc:
            from app.logging.logger import get_logger
            get_logger().warning(
                "Elicitation failed",
                error_type=type(exc).__name__,
                error=str(exc),
            )
            return {
                "accepted": False,
                "reason": "ELICITATION_FAILED",
                "error": {"name": type(exc).__name__, "message": str(exc)},
            }

    async def single_select(
        self,
        *,
        server: Any,
        message: str,
        field: str = "selection",
        title: str = "Selection",
        description: str | None = None,
        options: list[dict[str, str]],
        required: bool = True,
        timeout_ms: int | None = None,
    ) -> dict[str, Any]:
        result = await self.request_form(
            server=server,
            message=message,
            timeout_ms=timeout_ms or 120000,
            properties={
                field: {
                    "type": "string",
                    "title": title,
                    "description": description,
                    "oneOf": [{"const": str(o["value"]), "title": o["label"]} for o in options],
                }
            },
            required=[field] if required else [],
        )
        if not result["accepted"]:
            return {"selected": False, **result}
        return {"selected": True, "value": result["content"].get(field), "content": result["content"]}

    async def confirm(
        self,
        *,
        server: Any,
        message: str,
        field: str = "confirm",
        title: str = "Confirm",
        description: str | None = None,
        typed_confirmation: str | None = None,
        timeout_ms: int | None = None,
    ) -> dict[str, Any]:
        properties: dict[str, Any] = {
            field: {
                "type": "boolean",
                "title": title,
                "description": description,
                "default": False,
            }
        }
        required = [field]
        if typed_confirmation:
            properties["confirmation_text"] = {
                "type": "string",
                "title": f"Type {typed_confirmation}",
                "description": f"Type {typed_confirmation} to confirm.",
                "minLength": len(typed_confirmation),
                "maxLength": len(typed_confirmation),
            }
            required.append("confirmation_text")

        result = await self.request_form(
            server=server, message=message, properties=properties, required=required, timeout_ms=timeout_ms or 120000
        )
        if not result["accepted"]:
            return {"confirmed": False, **result}

        typed_ok = (
            result["content"].get("confirmation_text") == typed_confirmation
            if typed_confirmation else True
        )
        return {
            "confirmed": result["content"].get(field) is True and typed_ok,
            "content": result["content"],
        }

    async def request_missing_fields(
        self,
        *,
        server: Any,
        tool_name: str,
        missing_fields: list[str],
        partial_input: dict[str, Any],
        timeout_ms: int | None = None,
    ) -> dict[str, Any]:
        properties = {path: schema_for_field(path) for path in missing_fields}
        result = await self.request_form(
            server=server,
            message=f"Provide the missing fields for {tool_name}. Already supplied values will be preserved.",
            properties=properties,
            required=missing_fields,
            timeout_ms=timeout_ms or 120000,
        )
        if not result["accepted"]:
            return {"completed": False, **result}
        return {"completed": True, "input": _apply_flat_paths(partial_input, result["content"])}

    async def multi_select(
        self,
        *,
        server: Any,
        message: str,
        field: str = "selection",
        title: str = "Selection",
        description: str | None = None,
        options: list[dict[str, str]],
        min_select: int = 1,
        max_select: int | None = None,
        required: bool = True,
        timeout_ms: int | None = None,
    ) -> dict[str, Any]:
        """Multi-value selection — mirrors JS ElicitationService.multiSelect()."""
        items_schema: dict[str, Any] = {
            "type": "string",
            "oneOf": [{"const": str(o["value"]), "title": o["label"]} for o in options],
        }
        field_schema: dict[str, Any] = {
            "type": "array",
            "title": title,
            "items": items_schema,
            "minItems": min_select,
        }
        if description:
            field_schema["description"] = description
        if max_select is not None:
            field_schema["maxItems"] = max_select

        result = await self.request_form(
            server=server,
            message=message,
            timeout_ms=timeout_ms or 120000,
            properties={field: field_schema},
            required=[field] if required else [],
        )
        if not result["accepted"]:
            return {"selected": False, **result}
        values = result["content"].get(field) or []
        return {"selected": True, "values": values, "content": result["content"]}

    async def clarify(
        self,
        *,
        server: Any,
        message: str,
        field: str,
        suggestions: list[dict],
        timeout_ms: int | None = None,
    ) -> dict[str, Any]:
        return await self.single_select(
            server=server,
            message=message,
            field=field,
            title="Clarification",
            description="Choose one exact suggested value, or cancel and provide a different exact value.",
            options=[
                {
                    "value": str(s.get("code") or s.get("value") or s.get("id") or s.get("name") or ""),
                    "label": _suggestion_label(s),
                }
                for s in suggestions
            ],
            timeout_ms=timeout_ms,
        )

    async def select_rate_for_label(
        self,
        *,
        server: Any,
        shipment_id: str,
        rates: list,
        confirm_default: bool = False,
        timeout_ms: int = 120000,
    ) -> dict[str, Any]:
        if not rates:
            return {"selected": False, "reason": "NO_RATES_AVAILABLE"}

        result = await self.request_form(
            server=server,
            timeout_ms=timeout_ms,
            message=f"Select the rate to buy for shipment {shipment_id}. This will purchase a shipping label only if you also confirm.",
            properties={
                "rate_option": {
                    "type": "string",
                    "title": "Rate",
                    "description": "Choose one exact returned shipment rate.",
                    "oneOf": [
                        {
                            "const": str(i + 1),
                            "title": _rate_label(r),
                        }
                        for i, r in enumerate(rates)
                    ],
                },
                "confirm": {
                    "type": "boolean",
                    "title": "Confirm label purchase",
                    "description": "Required to buy the selected label.",
                    "default": confirm_default,
                },
            },
            required=["rate_option", "confirm"],
        )
        if not result["accepted"]:
            return {"selected": False, "reason": result.get("reason"), "error": result.get("error")}

        option_str = result["content"].get("rate_option")
        try:
            option = int(option_str)
        except (TypeError, ValueError):
            return {"selected": False, "reason": "INVALID_RATE_OPTION"}

        return {
            "selected": True,
            "rate_option": option,
            "confirm": result["content"].get("confirm") is True,
        }


def _rate_label(r: Any) -> str:
    carrier = getattr(r, "carrier", None) or (r.get("carrier") if isinstance(r, dict) else "") or ""
    service = getattr(r, "service", None) or (r.get("service") if isinstance(r, dict) else "") or ""
    rate = getattr(r, "rate", None) or (r.get("rate") if isinstance(r, dict) else "") or ""
    currency = getattr(r, "currency", None) or (r.get("currency") if isinstance(r, dict) else "") or "USD"
    days = getattr(r, "delivery_days", None) or (r.get("delivery_days") if isinstance(r, dict) else None)
    days_str = f" · {days}d" if days else ""
    return f"{carrier} {service} — ${rate} {currency}{days_str}".strip()


def _suggestion_label(suggestion: dict) -> str:
    primary = suggestion.get("name") or suggestion.get("code") or suggestion.get("value") or suggestion.get("id") or ""
    score = suggestion.get("score")
    return f"{primary} ({score})" if score is not None else str(primary)


def _apply_flat_paths(base: dict, flat_values: dict) -> dict:
    output = copy.deepcopy(base or {})
    for path, value in (flat_values or {}).items():
        parts = path.split(".")
        target = output
        for part in parts[:-1]:
            if not isinstance(target.get(part), dict):
                target[part] = {}
            target = target[part]
        target[parts[-1]] = value
    return output
