from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.schemas.pickup_schemas import CancelPickupInput, SchedulePickupInput

if TYPE_CHECKING:
    from app.clients.easypost_client import EasyPostClient
    from app.services.confirmation_service import ConfirmationService
    from app.services.idempotency_store import IdempotencyStore


class PickupService:
    def __init__(
        self,
        easypost_client: "EasyPostClient",
        *,
        confirmations: "ConfirmationService | None" = None,
        idempotency: "IdempotencyStore | None" = None,
    ) -> None:
        self._easypost = easypost_client
        self._confirmations = confirmations
        self._idempotency = idempotency

    async def schedule_pickup(self, input: SchedulePickupInput, context: dict) -> dict[str, Any]:
        await self._confirmations.require_confirmed(
            input,
            action="schedule_pickup",
            message=f"You are about to create a pickup window from {input.min_datetime} to {input.max_datetime} for {len(input.shipment_ids)} shipment(s). Proceed?",
            details={
                "shipment_ids": input.shipment_ids,
                "min_datetime": input.min_datetime,
                "max_datetime": input.max_datetime,
            },
            context=context,
        )

        async def operation() -> dict:
            pickup = await self._easypost.execute(
                "pickup.create",
                lambda client: client.pickup.create(
                    shipment={"id": input.shipment_ids[0]},
                    address=input.address.model_dump(exclude_none=True),
                    min_datetime=input.min_datetime,
                    max_datetime=input.max_datetime,
                    instructions=input.instructions,
                    carrier_accounts=input.carrier_accounts,
                ),
                context,
            )
            if audit := context.get("audit"):
                pickup_rates = getattr(pickup, "pickup_rates", []) or []
                audit.record("pickup_created", {
                    "correlation_id": context.get("correlation_id"),
                    "pickup_id": getattr(pickup, "id", None),
                    "pickup_rate_count": len(pickup_rates),
                })
            return {
                "ok": True,
                "pickup": pickup,
                "pickup_rates": getattr(pickup, "pickup_rates", []) or [],
                "next_step": "Review returned pickup_rates. This tool does not auto-buy a pickup rate.",
            }

        if not self._idempotency or not input.idempotency_key:
            return await operation()
        outcome = await self._idempotency.run(f"schedule_pickup:{input.idempotency_key}", operation)
        return {**outcome["result"], "idempotent_replay": True} if outcome["reused"] else outcome["result"]

    async def cancel_pickup(self, input: CancelPickupInput, context: dict) -> dict[str, Any]:
        await self._confirmations.require_confirmed(
            input,
            action="cancel_pickup",
            message=f"You are about to cancel pickup {input.pickup_id}. Proceed?",
            details={"pickup_id": input.pickup_id},
            typed_confirmation="CANCEL",
            context=context,
        )
        pickup = await self._easypost.execute(
            "pickup.cancel",
            lambda client: client.pickup.cancel(input.pickup_id),
            context,
        )
        return {"ok": True, "pickup": pickup}
