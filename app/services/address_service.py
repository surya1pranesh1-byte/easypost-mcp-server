from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.adapters.easypost.response_mappers import map_address
from app.elicitation.fallback import create_fallback_response
from app.schemas.address_schemas import CreateAddressInput, VerifyAddressInput

if TYPE_CHECKING:
    from app.clients.easypost_client import EasyPostClient
    from app.services.confirmation_service import ConfirmationService


def _has_address_correction(original: dict, normalized: dict | None) -> bool:
    if not original or not normalized:
        return False
    for field in ("street1", "street2", "city", "state", "zip", "country"):
        before = str(original.get(field) or "").strip().upper()
        after = str(normalized.get(field) or "").strip().upper()
        if before and after and before != after:
            return True
    return False


class AddressService:
    def __init__(
        self,
        easypost_client: "EasyPostClient",
        *,
        confirmations: "ConfirmationService | None" = None,
    ) -> None:
        self._easypost = easypost_client
        self._confirmations = confirmations

    async def verify_address(self, input: VerifyAddressInput, context: dict) -> dict[str, Any]:
        address_dict = input.address.model_dump(exclude_none=True)

        address = await self._easypost.execute(
            "address.verify",
            lambda client: (
                client.address.create_and_verify(**address_dict)
                if hasattr(client.address, "create_and_verify")
                else client.address.create(**{**address_dict, "verify": input.verifications})
            ),
            context,
        )

        mapped = map_address(address)
        if _has_address_correction(address_dict, mapped) and input.confirm is not True:
            try:
                await self._confirmations.require_confirmed(
                    input,
                    action="confirm_normalized_address",
                    message="EasyPost returned a normalized address. Did you mean this corrected address?",
                    details={"original_address": address_dict, "normalized_address": mapped},
                    context=context,
                )
            except Exception:
                return create_fallback_response(
                    error_code="ADDRESS_CONFIRMATION_REQUIRED",
                    message="EasyPost returned a normalized address. Confirm before using it.",
                    available_options=[{"value": "normalized_address", "address": mapped}],
                    examples={"confirm": [True]},
                    next_action="Retry with confirm=true if the normalized address is correct.",
                    metadata={"original_address": address_dict, "normalized_address": mapped},
                )

        verifications = getattr(address, "verifications", None) or {}
        delivery = (
            verifications.get("delivery") if isinstance(verifications, dict)
            else getattr(verifications, "delivery", None)
        )
        delivery_success = (
            delivery.get("success") if isinstance(delivery, dict)
            else getattr(delivery, "success", None)
        )
        delivery_errors = (
            delivery.get("errors") if isinstance(delivery, dict)
            else getattr(delivery, "errors", None)
        ) or []

        return {
            "ok": True,
            "address": mapped,
            "verification_status": "verified" if delivery_success is True else "review_required",
            "messages": delivery_errors,
        }

    async def create_address(self, input: CreateAddressInput, context: dict) -> dict[str, Any]:
        address_dict = input.address.model_dump(exclude_none=True)

        address = await self._easypost.execute(
            "address.create",
            lambda client: client.address.create(**{**address_dict, "verify": input.verify}),
            context,
        )

        mapped = map_address(address)
        if input.verify and _has_address_correction(address_dict, mapped) and input.confirm is not True:
            return create_fallback_response(
                error_code="ADDRESS_CONFIRMATION_REQUIRED",
                message="EasyPost returned a normalized address. Confirm before using it.",
                available_options=[{"value": "normalized_address", "address": mapped}],
                examples={"confirm": [True]},
                next_action="Retry with confirm=true if the normalized address is correct.",
                metadata={"original_address": address_dict, "normalized_address": mapped},
            )

        return {"ok": True, "address": mapped}
