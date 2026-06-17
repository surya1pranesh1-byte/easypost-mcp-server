from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.schemas.common import NonEmptyString


class ListResourcesInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    refresh: Optional[bool] = None


class ValidateCarrierInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    carrier: NonEmptyString


class ValidateServiceInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    carrier: NonEmptyString
    service: NonEmptyString
