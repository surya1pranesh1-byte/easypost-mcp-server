from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.adapters.easypost.response_mappers import map_rate, map_shipment
from app.schemas.return_schemas import CreateReturnLabelInput

if TYPE_CHECKING:
    from app.clients.easypost_client import EasyPostClient
    from app.services.confirmation_service import ConfirmationService
    from app.services.elicitation_service import ElicitationService


class ReturnService:
    def __init__(
        self,
        easypost_client: "EasyPostClient",
        *,
        confirmations: "ConfirmationService | None" = None,
        elicitation: "ElicitationService | None" = None,
    ) -> None:
        self._easypost = easypost_client
        self._confirmations = confirmations
        self._elicitation = elicitation

    async def create_return_label(self, input: CreateReturnLabelInput, context: dict) -> dict[str, Any]:
        api_key = (context.get("auth") or {}).get("api_key")
        options = {"original_shipment_id": input.original_shipment_id} if input.original_shipment_id else None

        shipment = await self._easypost.execute(
            "return.create",
            lambda client: client.shipment.create(
                from_address=input.from_address.model_dump(exclude_none=True),
                to_address=input.to_address.model_dump(exclude_none=True),
                parcel=input.parcel.model_dump(exclude_none=True),
                is_return=True,
                options=options,
            ),
            context,
            api_key,
        )

        rates = getattr(shipment, "rates", []) or []
        if not input.rate_id and not input.rate_option:
            return {
                "ok": True,
                "shipment": map_shipment(shipment),
                "rates": [{"option": i + 1, **(map_rate(r) or {})} for i, r in enumerate(rates)],
                "next_step": "Choose a numbered rate_option or exact rate_id to buy the return label. The server will not auto-select a return rate.",
            }

        rate = None
        if input.rate_id:
            rate = next((r for r in rates if getattr(r, "id", None) == input.rate_id), None)
        elif input.rate_option is not None:
            idx = input.rate_option - 1
            rate = rates[idx] if 0 <= idx < len(rates) else None

        if not rate:
            return {
                "ok": False,
                "success": False,
                "error_code": "RETURN_RATE_SELECTION_REQUIRED",
                "message": "The requested return rate selection is unavailable. Select one returned option.",
                "missing_fields": [],
                "ambiguous_fields": [],
                "available_options": [{"option": i + 1, **(map_rate(r) or {})} for i, r in enumerate(rates)],
                "examples": {"rate_option": [1]},
                "next_action": "Retry with a valid rate_option or rate_id from available_options.",
            }

        mapped_rate = map_rate(rate)
        await self._confirmations.require_confirmed(
            input,
            action="create_return_label",
            message=f"You are about to buy a return label using {mapped_rate['carrier']} {mapped_rate['service']} for {mapped_rate['rate']} {mapped_rate.get('currency') or 'USD'}. Proceed?",
            details={"rate": mapped_rate, "shipment_id": getattr(shipment, "id", None)},
            context=context,
        )

        bought = await self._easypost.execute(
            "return.buy",
            lambda client: client.shipment.buy(getattr(shipment, "id"), rate),
            context,
            api_key,
        )
        return {"ok": True, "shipment": map_shipment(bought), "purchased_rate": mapped_rate}
