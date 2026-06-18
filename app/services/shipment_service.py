from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.adapters.easypost.response_mappers import map_collection, map_rate, map_shipment
from app.elicitation.fallback import create_fallback_response
from app.exceptions.app_errors import NotFoundError
from app.schemas.shipment_schemas import (
    BuyShippingLabelInput,
    CreateShipmentInput,
    GetShipmentInput,
    InsureShipmentInput,
    ListShipmentsInput,
    RefundShipmentInput,
)

if TYPE_CHECKING:
    from app.clients.easypost_client import EasyPostClient
    from app.services.confirmation_service import ConfirmationService
    from app.services.elicitation_service import ElicitationService
    from app.services.idempotency_store import IdempotencyStore


def _map_selectable_rates(rates: list) -> list[dict]:
    return [{"option": i + 1, **(map_rate(r) or {})} for i, r in enumerate(rates)]


def _strip_rate_ids(rates: list[dict]) -> list[dict]:
    return [{k: v for k, v in r.items() if k != "id"} for r in rates]


class ShipmentService:
    def __init__(
        self,
        easypost_client: "EasyPostClient",
        *,
        confirmations: "ConfirmationService | None" = None,
        elicitation: "ElicitationService | None" = None,
        idempotency: "IdempotencyStore | None" = None,
    ) -> None:
        self._easypost = easypost_client
        self._confirmations = confirmations
        self._elicitation = elicitation
        self._idempotency = idempotency

    async def create_shipment(self, input: CreateShipmentInput, context: dict) -> dict[str, Any]:
        input_dict = input.model_dump(exclude_none=True)

        async def operation() -> dict:
            shipment = await self._easypost.execute(
                "shipment.create",
                lambda client: client.shipment.create(**input_dict),
                context,
            )
            raw_rates = getattr(shipment, "rates", []) or []
            rates = _map_selectable_rates(raw_rates)
            audit = context.get("audit")
            if audit:
                audit.record("rates_returned", {
                    "correlation_id": context.get("correlation_id"),
                    "shipment_id": getattr(shipment, "id", None),
                    "rate_count": len(rates),
                    "rate_ids": [r.get("id") for r in rates],
                })
            shipment_data = map_shipment(shipment)
            # Strip rate IDs from the response so the AI cannot pass them directly
            # to buy_shipping_label; rate selection must go through interactive flow.
            display_rates = _strip_rate_ids(rates)
            if isinstance(shipment_data.get("rates"), list):
                shipment_data["rates"] = _strip_rate_ids(shipment_data["rates"])
            return {
                "ok": True,
                "shipment": shipment_data,
                "rates": display_rates,
                "next_step": (
                    "Present the rates table to the user and ask them which carrier and service they prefer. "
                    "Do NOT choose a rate on the user's behalf. "
                    "Only call buy_shipping_label after the user has explicitly stated their choice."
                    if rates else
                    "No rates were returned by the carrier accounts for this shipment."
                ),
            }

        if not self._idempotency or not input.idempotency_key:
            return await operation()
        outcome = await self._idempotency.run(f"create_shipment:{input.idempotency_key}", operation)
        return {**outcome["result"], "idempotent_replay": True} if outcome["reused"] else outcome["result"]

    async def buy_shipping_label(self, input: BuyShippingLabelInput, context: dict) -> dict[str, Any]:
        shipment = await self._easypost.execute(
            "shipment.retrieve",
            lambda client: client.shipment.retrieve(input.shipment_id),
            context,
        )
        if not shipment:
            raise NotFoundError("shipment", input.shipment_id)

        rates = getattr(shipment, "rates", []) or []
        rate_id = input.rate_id
        rate_option = input.rate_option

        if not rate_id and not rate_option:
            elicited = None
            if self._elicitation:
                elicited = await self._elicitation.select_rate_for_label(
                    server=context.get("server"),
                    shipment_id=input.shipment_id,
                    rates=rates,
                    confirm_default=input.confirm is True,
                )
            if elicited and elicited.get("selected"):
                rate_option = elicited["rate_option"]
                input = BuyShippingLabelInput(
                    **{**input.model_dump(), "rate_option": rate_option, "confirm": elicited.get("confirm", input.confirm)}
                )
                audit = context.get("audit")
                if audit:
                    audit.record("rate_selection_elicited", {
                        "correlation_id": context.get("correlation_id"),
                        "shipment_id": input.shipment_id,
                        "rate_option": rate_option,
                        "confirmed": input.confirm,
                    })
            else:
                if audit := context.get("audit"):
                    audit.record("rate_selection_fallback", {
                        "correlation_id": context.get("correlation_id"),
                        "shipment_id": input.shipment_id,
                        "reason": (elicited or {}).get("reason"),
                    })
                full_rates = _map_selectable_rates(rates)
                return create_fallback_response(
                    error_code="RATE_SELECTION_REQUIRED",
                    message="No rate was selected. Show the list below to the user and wait for them to choose.",
                    missing_fields=["rate_id"],
                    available_options=full_rates,
                    examples={},
                    next_action=(
                        "Display available_options as a plain list showing carrier, service, price, and delivery days. "
                        "Ask the user: 'Which carrier and service would you like?' "
                        "Do NOT suggest or pre-select any option. "
                        "After the user names their choice, match it to the rate_id in available_options "
                        "and retry buy_shipping_label with that rate_id."
                    ),
                    metadata={
                        "elicitation_supported": self._elicitation.supports_form(context.get("server")) if self._elicitation else False,
                        "fallback_reason": (elicited or {}).get("reason"),
                        "elicitation_error": (elicited or {}).get("error"),
                    },
                )

        rate = None
        if rate_id:
            rate = next((r for r in rates if getattr(r, "id", None) == rate_id), None)
        elif rate_option is not None:
            idx = rate_option - 1
            rate = rates[idx] if 0 <= idx < len(rates) else None

        if not rate:
            if audit := context.get("audit"):
                audit.record("rate_selection_failed", {
                    "correlation_id": context.get("correlation_id"),
                    "shipment_id": input.shipment_id,
                    "requested_rate_id": input.rate_id,
                    "requested_rate_option": input.rate_option,
                    "available_rate_ids": [getattr(r, "id", None) for r in rates],
                })
            first_rate = rates[0] if rates else None
            return create_fallback_response(
                error_code="RATE_ID_NOT_AVAILABLE",
                message="The requested rate selection is not available on this shipment. Select one option number or exact id from available_rates.",
                missing_fields=["rate_option"],
                available_options=_map_selectable_rates(rates),
                examples={
                    "rate_option": [1],
                    "rate_id": [getattr(first_rate, "id", None)] if first_rate else [],
                },
                next_action="Retry with a valid rate_option or exact rate_id from available_options.",
                metadata={"requested_rate_id": input.rate_id, "requested_rate_option": input.rate_option},
            )

        mapped_rate = map_rate(rate)
        await self._confirmations.require_confirmed(
            input,
            action="buy_shipping_label",
            message=f"You are about to buy a {mapped_rate['carrier']} {mapped_rate['service']} label for {mapped_rate['rate']} {mapped_rate.get('currency') or 'USD'}. Proceed?",
            details={"shipment_id": input.shipment_id, "rate": mapped_rate},
            context=context,
        )

        async def operation() -> dict:
            if audit := context.get("audit"):
                audit.record("label_purchase_confirmed", {
                    "correlation_id": context.get("correlation_id"),
                    "shipment_id": input.shipment_id,
                    "rate_id": getattr(rate, "id", None),
                    "rate_option": input.rate_option,
                })
            rate_id = getattr(rate, "id", None)
            buy_params: dict = {"rate": {"id": rate_id}}
            if input.insurance is not None:
                buy_params["insurance"] = input.insurance
            bought = await self._easypost.execute(
                "shipment.buy",
                lambda client: client.shipment.buy(input.shipment_id, **buy_params),
                context,
            )
            return {"ok": True, "shipment": map_shipment(bought), "purchased_rate": mapped_rate}

        if not self._idempotency or not input.idempotency_key:
            return await operation()
        outcome = await self._idempotency.run(f"buy_shipping_label:{input.idempotency_key}", operation)
        return {**outcome["result"], "idempotent_replay": True} if outcome["reused"] else outcome["result"]

    async def get_shipment(self, input: GetShipmentInput, context: dict) -> dict[str, Any]:
        shipment = await self._easypost.execute(
            "shipment.retrieve",
            lambda client: client.shipment.retrieve(input.shipment_id),
            context,
        )
        return {"ok": True, "shipment": map_shipment(shipment)}

    async def list_shipments(self, input: ListShipmentsInput, context: dict) -> dict[str, Any]:
        params = input.model_dump(exclude_none=True)
        collection = await self._easypost.execute(
            "shipment.list",
            lambda client: client.shipment.all(**params),
            context,
        )
        return {"ok": True, **map_collection(collection, map_shipment)}

    async def estimate_rates(self, input: CreateShipmentInput, context: dict) -> dict[str, Any]:
        result = await self.create_shipment(input, context)
        return {"ok": True, "shipment_id": result["shipment"]["id"], "rates": result["rates"]}

    async def refund_shipment(self, input: RefundShipmentInput, context: dict) -> dict[str, Any]:
        await self._confirmations.require_confirmed(
            input,
            action="refund_shipment",
            message=f"You are about to void/refund shipment {input.shipment_id}. Proceed?",
            details={"shipment_id": input.shipment_id},
            typed_confirmation="REFUND",
            context=context,
        )
        shipment = await self._easypost.execute(
            "shipment.refund",
            lambda client: client.shipment.refund(input.shipment_id),
            context,
        )
        return {"ok": True, "shipment": map_shipment(shipment), "refund_status": getattr(shipment, "refund_status", None)}

    async def cancel_shipment(self, input: RefundShipmentInput, context: dict) -> dict[str, Any]:
        return await self.refund_shipment(input, context)

    async def insure_shipment(self, input: InsureShipmentInput, context: dict) -> dict[str, Any]:
        amount_val = float(input.amount) if isinstance(input.amount, str) else input.amount
        typed_conf = "INSURE" if amount_val >= 500 else None
        await self._confirmations.require_confirmed(
            input,
            action="insure_shipment",
            message=f"You are about to add insurance for {input.amount} to shipment {input.shipment_id}. Proceed?",
            details={"shipment_id": input.shipment_id, "amount": input.amount},
            typed_confirmation=typed_conf,
            context=context,
        )
        shipment = await self._easypost.execute(
            "shipment.insure",
            lambda client: client.shipment.insure(input.shipment_id, input.amount),
            context,
        )
        return {"ok": True, "shipment": map_shipment(shipment), "insured_amount": input.amount}
