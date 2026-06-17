from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.address_schemas import AddressInput
from app.schemas.common import ConfirmFlag, EasyPostId, IdempotencyKey, NonEmptyString


class SchedulePickupInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    shipment_ids: list[EasyPostId] = Field(min_length=1)
    address: AddressInput
    min_datetime: NonEmptyString
    max_datetime: NonEmptyString
    instructions: Optional[str] = Field(default=None, max_length=500)
    carrier_accounts: Optional[list[NonEmptyString]] = None
    idempotency_key: Optional[IdempotencyKey] = None
    confirm: ConfirmFlag = None


class CancelPickupInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pickup_id: EasyPostId
    confirm: ConfirmFlag = None
