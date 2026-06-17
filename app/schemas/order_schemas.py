from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.address_schemas import AddressInput
from app.schemas.common import EasyPostId
from app.schemas.parcel_schemas import ParcelInput


class OrderShipmentInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    parcel: ParcelInput


class CreateOrderInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    from_address: AddressInput
    to_address: AddressInput
    shipments: list[OrderShipmentInput] = Field(min_length=1, max_length=100)


class GetOrderInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    order_id: EasyPostId
