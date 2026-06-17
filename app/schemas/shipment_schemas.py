from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.address_schemas import AddressInput
from app.schemas.common import ConfirmFlag, CurrencyAmount, EasyPostId, IdempotencyKey, NonEmptyString
from app.schemas.parcel_schemas import ParcelInput


class ShipmentOptionsInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label_format: Optional[str] = Field(default=None, pattern=r"^(PDF|PNG|ZPL|EPL2)$")
    delivery_confirmation: Optional[str] = None
    print_custom_1: Optional[str] = Field(default=None, max_length=255)
    print_custom_2: Optional[str] = Field(default=None, max_length=255)


class CreateShipmentInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    from_address: AddressInput
    to_address: AddressInput
    parcel: ParcelInput
    carrier_accounts: Optional[list[NonEmptyString]] = None
    customs_info: Optional[dict[str, Any]] = None
    options: Optional[ShipmentOptionsInput] = None
    reference: Optional[str] = Field(default=None, max_length=255)
    idempotency_key: Optional[IdempotencyKey] = None


class BuyShippingLabelInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    shipment_id: EasyPostId
    rate_id: Optional[EasyPostId] = None
    rate_option: Optional[int] = Field(default=None, ge=1)
    insurance: Optional[CurrencyAmount] = None
    idempotency_key: IdempotencyKey
    confirm: ConfirmFlag = None


class GetShipmentInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    shipment_id: EasyPostId


class ListShipmentsInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    page_size: Optional[int] = Field(default=None, ge=1, le=100)
    before_id: Optional[str] = None
    after_id: Optional[str] = None
    purchased: Optional[bool] = None
    include_children: Optional[bool] = None


EstimateRatesInput = CreateShipmentInput


class RefundShipmentInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    shipment_id: EasyPostId
    confirm: ConfirmFlag = None


CancelShipmentInput = RefundShipmentInput


class InsureShipmentInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    shipment_id: EasyPostId
    amount: CurrencyAmount
    confirm: ConfirmFlag = None
