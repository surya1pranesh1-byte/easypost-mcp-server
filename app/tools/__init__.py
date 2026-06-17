from __future__ import annotations

from typing import TYPE_CHECKING

from app.tools.definitions.address import address_tools
from app.tools.definitions.batches import batch_tools
from app.tools.definitions.orders import order_tools
from app.tools.definitions.pickups import pickup_tools
from app.tools.definitions.resources import resource_tools
from app.tools.definitions.returns import return_tools
from app.tools.definitions.shipments import shipment_tools
from app.tools.definitions.tracking import tracking_tools
from app.tools.registry import ToolRegistry

if TYPE_CHECKING:
    from app.services.factory import Services


def create_tool_registry(services: "Services") -> ToolRegistry:
    registry = ToolRegistry()
    registry.register_many([
        *shipment_tools(services),
        *tracking_tools(services),
        *address_tools(services),
        *return_tools(services),
        *pickup_tools(services),
        *batch_tools(services),
        *order_tools(services),
        *resource_tools(services),
    ])
    return registry


__all__ = ["ToolRegistry", "create_tool_registry"]
