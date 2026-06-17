from __future__ import annotations

from typing import TYPE_CHECKING

from app.constants.tool_categories import ToolCategory
from app.schemas.tracking_schemas import GetTrackingHistoryInput, TrackPackageInput
from app.tools.definition import ToolDefinition

if TYPE_CHECKING:
    from app.services.factory import Services


def tracking_tools(services: "Services") -> list[ToolDefinition]:
    return [
        ToolDefinition(
            name="track_package",
            title="Track Package",
            category=ToolCategory.TRACKING,
            description="Create or refresh tracking for a package using a tracking code and optional carrier.",
            schema_cls=TrackPackageInput,
            handler=services.tracking.track_package,
        ),
        ToolDefinition(
            name="get_tracking_history",
            title="Get Tracking History",
            category=ToolCategory.TRACKING,
            description="Return normalized tracking events by tracker id or tracking code.",
            schema_cls=GetTrackingHistoryInput,
            handler=services.tracking.get_tracking_history,
        ),
    ]
