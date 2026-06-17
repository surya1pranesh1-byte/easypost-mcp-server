from __future__ import annotations

from typing import TYPE_CHECKING

from app.constants.tool_categories import ToolCategory
from app.schemas.order_schemas import CreateOrderInput, GetOrderInput
from app.tools.definition import ToolDefinition

if TYPE_CHECKING:
    from app.services.factory import Services


def order_tools(services: "Services") -> list[ToolDefinition]:
    return [
        ToolDefinition(
            name="create_order",
            title="Create Order",
            category=ToolCategory.ORDERS,
            description="Create an EasyPost order with multiple shipments using business order fields.",
            schema_cls=CreateOrderInput,
            handler=services.orders.create_order,
        ),
        ToolDefinition(
            name="get_order",
            title="Get Order",
            category=ToolCategory.ORDERS,
            description="Retrieve an order by id.",
            schema_cls=GetOrderInput,
            handler=services.orders.get_order,
        ),
    ]
