from __future__ import annotations

from typing import TYPE_CHECKING

from app.constants.tool_categories import ToolCategory
from app.schemas.shipment_schemas import (
    BuyShippingLabelInput,
    CancelShipmentInput,
    CreateShipmentInput,
    EstimateRatesInput,
    GetShipmentInput,
    InsureShipmentInput,
    ListShipmentsInput,
    RefundShipmentInput,
)
from app.tools.definition import ToolDefinition

if TYPE_CHECKING:
    from app.services.factory import Services


def shipment_tools(services: "Services") -> list[ToolDefinition]:
    return [
        ToolDefinition(
            name="create_shipment",
            title="Create Shipment",
            category=ToolCategory.SHIPMENTS,
            description="Create an EasyPost shipment and return normalized shipment details plus available carrier rates. Does not buy a label.",
            schema_cls=CreateShipmentInput,
            handler=services.shipments.create_shipment,
        ),
        ToolDefinition(
            name="buy_shipping_label",
            title="Buy Shipping Label",
            category=ToolCategory.SHIPMENTS,
            description="Buy a shipping label for an existing shipment using client elicitation, exact returned rate_id, or numbered rate_option. Requires confirmation and idempotency_key.",
            schema_cls=BuyShippingLabelInput,
            handler=services.shipments.buy_shipping_label,
        ),
        ToolDefinition(
            name="get_shipment",
            title="Get Shipment",
            category=ToolCategory.SHIPMENTS,
            description="Retrieve a shipment by id with normalized label, rate, parcel, and tracking fields.",
            schema_cls=GetShipmentInput,
            handler=services.shipments.get_shipment,
        ),
        ToolDefinition(
            name="list_shipments",
            title="List Shipments",
            category=ToolCategory.SHIPMENTS,
            description="List shipments with bounded pagination.",
            schema_cls=ListShipmentsInput,
            handler=services.shipments.list_shipments,
        ),
        ToolDefinition(
            name="cancel_shipment",
            title="Cancel Shipment",
            category=ToolCategory.SHIPMENTS,
            description="Cancel or void a shipment when supported by the carrier. Requires confirm=true and uses EasyPost refund semantics for purchased labels.",
            schema_cls=CancelShipmentInput,
            handler=services.shipments.cancel_shipment,
        ),
        ToolDefinition(
            name="refund_shipment",
            title="Refund Shipment",
            category=ToolCategory.SHIPMENTS,
            description="Request a refund for a purchased shipment label. Requires confirm=true.",
            schema_cls=RefundShipmentInput,
            handler=services.shipments.refund_shipment,
        ),
        ToolDefinition(
            name="estimate_rates",
            title="Estimate Rates",
            category=ToolCategory.SHIPMENTS,
            description="Create an unrated purchase-free shipment quote and return available carrier rates.",
            schema_cls=EstimateRatesInput,
            handler=services.shipments.estimate_rates,
        ),
        ToolDefinition(
            name="insure_shipment",
            title="Insure Shipment",
            category=ToolCategory.INSURANCE,
            description="Add insurance to an existing shipment.",
            schema_cls=InsureShipmentInput,
            handler=services.shipments.insure_shipment,
        ),
    ]
