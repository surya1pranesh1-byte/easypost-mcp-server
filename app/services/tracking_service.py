from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.adapters.easypost.response_mappers import map_tracker
from app.schemas.tracking_schemas import GetTrackingHistoryInput, TrackPackageInput

if TYPE_CHECKING:
    from app.clients.easypost_client import EasyPostClient


class TrackingService:
    def __init__(self, easypost_client: "EasyPostClient") -> None:
        self._easypost = easypost_client

    async def track_package(self, input: TrackPackageInput, context: dict) -> dict[str, Any]:
        tracker = await self._easypost.execute(
            "tracker.create",
            lambda client: client.tracker.create(
                tracking_code=input.tracking_code,
                carrier=input.carrier,
            ),
            context,
        )
        return {"ok": True, "tracker": map_tracker(tracker)}

    async def get_tracking_history(self, input: GetTrackingHistoryInput, context: dict) -> dict[str, Any]:
        if input.tracker_id:
            tracker = await self._easypost.execute(
                "tracker.retrieve",
                lambda client: client.tracker.retrieve(input.tracker_id),
                context,
            )
        else:
            tracker = await self._easypost.execute(
                "tracker.create",
                lambda client: client.tracker.create(
                    tracking_code=input.tracking_code,
                    carrier=input.carrier,
                ),
                context,
            )
        mapped = map_tracker(tracker)
        history = (mapped or {}).get("tracking_details", []) if mapped else []
        return {"ok": True, "tracker": mapped, "history": history}
