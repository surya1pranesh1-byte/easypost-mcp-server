from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.schemas.batch_schemas import BatchStatusInput, BuyBatchInput, CreateBatchInput

if TYPE_CHECKING:
    from app.clients.easypost_client import EasyPostClient
    from app.services.confirmation_service import ConfirmationService


class BatchService:
    def __init__(
        self,
        easypost_client: "EasyPostClient",
        *,
        confirmations: "ConfirmationService | None" = None,
    ) -> None:
        self._easypost = easypost_client
        self._confirmations = confirmations

    async def create_batch(self, input: CreateBatchInput, context: dict) -> dict[str, Any]:
        shipments = []
        for s in input.shipments:
            if hasattr(s, "shipment_id") and s.shipment_id:
                shipments.append({"id": s.shipment_id})
            else:
                shipments.append(s.model_dump(exclude_none=True))

        batch = await self._easypost.execute(
            "batch.create",
            lambda client: client.batch.create(shipments=shipments),
            context,
        )
        return {"ok": True, "batch": batch}

    async def buy_batch(self, input: BuyBatchInput, context: dict) -> dict[str, Any]:
        await self._confirmations.require_confirmed(
            input,
            action="buy_batch",
            message=f"You are about to buy labels for batch {input.batch_id}. Proceed?",
            details={"batch_id": input.batch_id},
            context=context,
        )
        batch = await self._easypost.execute(
            "batch.buy",
            lambda client: client.batch.buy(input.batch_id),
            context,
        )
        return {"ok": True, "batch": batch}

    async def batch_status(self, input: BatchStatusInput, context: dict) -> dict[str, Any]:
        batch = await self._easypost.execute(
            "batch.retrieve",
            lambda client: client.batch.retrieve(input.batch_id),
            context,
        )
        return {"ok": True, "batch": batch}
