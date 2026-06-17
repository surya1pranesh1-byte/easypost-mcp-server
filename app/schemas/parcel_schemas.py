from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.common import NonEmptyString


class ParcelInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    length: float = Field(gt=0, le=120)
    width: float = Field(gt=0, le=120)
    height: float = Field(gt=0, le=120)
    weight: float = Field(gt=0, le=1120)
    predefined_package: Optional[NonEmptyString] = None

    @model_validator(mode="after")
    def dimensions_positive(self) -> "ParcelInput":
        if self.length * self.width * self.height <= 0:
            raise ValueError("Parcel dimensions must be greater than zero")
        return self
