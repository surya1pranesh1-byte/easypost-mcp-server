from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, model_validator

from app.schemas.common import EasyPostId, NonEmptyString


class TrackPackageInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tracking_code: NonEmptyString
    carrier: Optional[NonEmptyString] = None


class GetTrackingHistoryInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tracker_id: Optional[EasyPostId] = None
    tracking_code: Optional[NonEmptyString] = None
    carrier: Optional[NonEmptyString] = None

    @model_validator(mode="after")
    def require_tracker_id_or_tracking_code(self) -> "GetTrackingHistoryInput":
        if not self.tracker_id and not self.tracking_code:
            raise ValueError("Provide tracker_id or tracking_code")
        return self
