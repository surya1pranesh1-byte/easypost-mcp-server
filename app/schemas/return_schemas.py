from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.address_schemas import AddressInput
from app.schemas.common import ConfirmFlag, EasyPostId, IdempotencyKey
from app.schemas.parcel_schemas import ParcelInput


class CreateReturnLabelInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    original_shipment_id: Optional[EasyPostId] = None
    from_address: AddressInput
    to_address: AddressInput
    parcel: ParcelInput
    carrier: Optional[str] = None
    service: Optional[str] = None
    rate_id: Optional[EasyPostId] = None
    rate_option: Optional[int] = Field(default=None, ge=1)
    idempotency_key: Optional[IdempotencyKey] = None
    confirm: ConfirmFlag = None
