from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.constants.tool_categories import ToolCategory
from app.constants.tool_risk import ToolRisk
from app.schemas.resource_schemas import ListResourcesInput, ValidateCarrierInput, ValidateServiceInput
from app.tools.definition import ToolDefinition

if TYPE_CHECKING:
    from app.services.factory import Services


def resource_tools(services: "Services") -> list[ToolDefinition]:
    async def get_carriers(input: ListResourcesInput, context: dict) -> dict[str, Any]:
        if input.refresh:
            await services.resources.refresh(context)
        return {
            "ok": True,
            "carriers": services.resources.get_carriers(),
            "resource_context": services.resources.get_operational_context(),
        }

    async def validate_carrier(input: ValidateCarrierInput, context: dict) -> dict[str, Any]:
        result = services.resources.validate_carrier(input.carrier)
        return {
            "ok": result["valid"],
            "validation": result,
            "clarification_required": not result["valid"] and len(result["suggestions"]) > 0,
        }

    async def validate_service(input: ValidateServiceInput, context: dict) -> dict[str, Any]:
        result = services.resources.validate_service(input.carrier, input.service)
        return {
            "ok": result["valid"],
            "validation": result,
            "clarification_required": not result["valid"] and len(result["suggestions"]) > 0,
        }

    return [
        ToolDefinition(
            name="get_carriers",
            title="Get Carriers",
            category=ToolCategory.SHIPMENTS,
            risk=ToolRisk.LOW,
            description="Return compact authoritative carrier metadata from the server-side resource cache.",
            schema_cls=ListResourcesInput,
            handler=get_carriers,
        ),
        ToolDefinition(
            name="validate_carrier",
            title="Validate Carrier",
            category=ToolCategory.SHIPMENTS,
            risk=ToolRisk.LOW,
            description="Validate a carrier with exact matching. Fuzzy matches are returned only as suggestions.",
            schema_cls=ValidateCarrierInput,
            handler=validate_carrier,
        ),
        ToolDefinition(
            name="validate_service",
            title="Validate Service",
            category=ToolCategory.SHIPMENTS,
            risk=ToolRisk.LOW,
            description="Validate an exact carrier/service combination against cached authoritative resources.",
            schema_cls=ValidateServiceInput,
            handler=validate_service,
        ),
    ]
