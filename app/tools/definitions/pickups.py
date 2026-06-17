from __future__ import annotations

from typing import TYPE_CHECKING

from app.constants.tool_categories import ToolCategory
from app.schemas.pickup_schemas import CancelPickupInput, SchedulePickupInput
from app.tools.definition import ToolDefinition

if TYPE_CHECKING:
    from app.services.factory import Services


def pickup_tools(services: "Services") -> list[ToolDefinition]:
    return [
        ToolDefinition(
            name="schedule_pickup",
            title="Schedule Pickup",
            category=ToolCategory.PICKUPS,
            description="Create a carrier pickup request for one or more shipments. Requires confirm=true and never auto-buys a pickup rate.",
            schema_cls=SchedulePickupInput,
            handler=services.pickups.schedule_pickup,
        ),
        ToolDefinition(
            name="cancel_pickup",
            title="Cancel Pickup",
            category=ToolCategory.PICKUPS,
            description="Cancel a scheduled carrier pickup. Requires confirm=true.",
            schema_cls=CancelPickupInput,
            handler=services.pickups.cancel_pickup,
        ),
    ]
