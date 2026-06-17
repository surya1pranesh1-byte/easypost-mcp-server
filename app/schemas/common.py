from __future__ import annotations

import re
from typing import Annotated, Union

from pydantic import BeforeValidator, Field

# Re-usable annotated types that mirror the Zod primitives in the JS implementation.

NonEmptyString = Annotated[str, Field(min_length=1, max_length=255)]

EasyPostId = Annotated[
    str,
    Field(pattern=r"^[a-z]+_[A-Za-z0-9]+$"),
]

_CURRENCY_PATTERN = re.compile(r"^\d+(\.\d{1,2})?$")


def _validate_currency_amount(v: object) -> object:
    """Mirror JS: z.union([z.string().regex(/^\d+(\.\d{1,2})?$/), z.number().nonnegative()])."""
    if isinstance(v, str):
        if not _CURRENCY_PATTERN.match(v.strip()):
            raise ValueError("currency amount string must be a non-negative decimal (e.g. '10' or '9.99')")
        return v.strip()
    if isinstance(v, (int, float)):
        if v < 0:
            raise ValueError("currency amount must be non-negative")
    return v


CurrencyAmount = Annotated[
    Union[str, float],
    BeforeValidator(_validate_currency_amount),
]

IdempotencyKey = Annotated[
    str,
    Field(min_length=8, max_length=128, pattern=r"^[A-Za-z0-9_.:-]+$"),
]


def _confirm_literal_true(v: object) -> object:
    """Mirror JS: z.literal(true).optional() — only accepts true or absent."""
    if v is None:
        return None
    if v is True:
        return True
    raise ValueError("confirm must be true if provided")


# Use this type for every 'confirm' field — matches JS z.literal(true).optional()
ConfirmFlag = Annotated[
    Union[bool, None],
    BeforeValidator(_confirm_literal_true),
]
