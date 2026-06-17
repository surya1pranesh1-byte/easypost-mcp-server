from __future__ import annotations

from typing import Optional, Union

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import ConfirmFlag, EasyPostId
from app.schemas.shipment_schemas import CreateShipmentInput


class BatchShipmentByIdInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    shipment_id: EasyPostId


class BatchShipmentCreateInput(CreateShipmentInput):
    carrier: Optional[str] = Field(default=None, min_length=1)
    service: Optional[str] = Field(default=None, min_length=1)


BatchShipmentInput = Union[BatchShipmentByIdInput, BatchShipmentCreateInput]


class CreateBatchInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    shipments: list[BatchShipmentInput] = Field(min_length=1, max_length=100)


class BuyBatchInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    batch_id: EasyPostId
    confirm: ConfirmFlag = None


BatchStatusInput = BuyBatchInput
