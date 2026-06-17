from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.schemas.order_schemas import CreateOrderInput, GetOrderInput

if TYPE_CHECKING:
    from app.clients.easypost_client import EasyPostClient


class OrderService:
    def __init__(self, easypost_client: "EasyPostClient") -> None:
        self._easypost = easypost_client

    async def create_order(self, input: CreateOrderInput, context: dict) -> dict[str, Any]:
        api_key = (context.get("auth") or {}).get("api_key")
        order = await self._easypost.execute(
            "order.create",
            lambda client: client.order.create(**input.model_dump(exclude_none=True)),
            context,
            api_key,
        )
        return {"ok": True, "order": order}

    async def get_order(self, input: GetOrderInput, context: dict) -> dict[str, Any]:
        api_key = (context.get("auth") or {}).get("api_key")
        order = await self._easypost.execute(
            "order.retrieve",
            lambda client: client.order.retrieve(input.order_id),
            context,
            api_key,
        )
        return {"ok": True, "order": order}
