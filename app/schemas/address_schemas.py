from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.schemas.common import ConfirmFlag, NonEmptyString


class AddressInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Optional[NonEmptyString] = None
    company: Optional[NonEmptyString] = None
    street1: NonEmptyString
    street2: Optional[NonEmptyString] = None
    city: NonEmptyString
    state: NonEmptyString
    zip: NonEmptyString
    country: str = Field(min_length=2, max_length=2)
    phone: Optional[NonEmptyString] = None
    email: Optional[EmailStr] = None
    residential: Optional[bool] = None

    @field_validator("country", mode="before")
    @classmethod
    def uppercase_country(cls, v: str) -> str:
        return v.strip().upper()


class VerifyAddressInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    address: AddressInput
    verifications: list[str] = Field(default_factory=lambda: ["delivery"])
    confirm: ConfirmFlag = None


class CreateAddressInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    address: AddressInput
    verify: bool = False
    confirm: ConfirmFlag = None
