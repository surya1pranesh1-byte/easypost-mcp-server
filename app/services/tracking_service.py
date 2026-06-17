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
        api_key = (context.get("auth") or {}).get("api_key")
        tracker = await self._easypost.execute(
            "tracker.create",
            lambda client: client.tracker.create(
                tracking_code=input.tracking_code,
                carrier=input.carrier,
            ),
            context,
            api_key,
        )
        return {"ok": True, "tracker": map_tracker(tracker)}

    async def get_tracking_history(self, input: GetTrackingHistoryInput, context: dict) -> dict[str, Any]:
        api_key = (context.get("auth") or {}).get("api_key")
        if input.tracker_id:
            tracker = await self._easypost.execute(
                "tracker.retrieve",
                lambda client: client.tracker.retrieve(input.tracker_id),
                context,
                api_key,
            )
        else:
            tracker = await self._easypost.execute(
                "tracker.create",
                lambda client: client.tracker.create(
                    tracking_code=input.tracking_code,
                    carrier=input.carrier,
                ),
                context,
                api_key,
            )
        mapped = map_tracker(tracker)
        history = (mapped or {}).get("tracking_details", []) if mapped else []
        return {"ok": True, "tracker": mapped, "history": history}
