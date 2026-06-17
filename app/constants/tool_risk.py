from enum import StrEnum


class ToolRisk(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


_RISK_BY_NAME: dict[str, ToolRisk] = {
    "verify_address": ToolRisk.LOW,
    "create_address": ToolRisk.LOW,
    "estimate_rates": ToolRisk.LOW,
    "get_shipment": ToolRisk.LOW,
    "list_shipments": ToolRisk.LOW,
    "track_package": ToolRisk.LOW,
    "get_tracking_history": ToolRisk.LOW,
    "get_order": ToolRisk.LOW,
    "batch_status": ToolRisk.LOW,
    "get_carriers": ToolRisk.LOW,
    "validate_carrier": ToolRisk.LOW,
    "validate_service": ToolRisk.LOW,
    "create_shipment": ToolRisk.MEDIUM,
    "create_return_label": ToolRisk.MEDIUM,
    "insure_shipment": ToolRisk.MEDIUM,
    "create_batch": ToolRisk.MEDIUM,
    "create_order": ToolRisk.MEDIUM,
    "buy_shipping_label": ToolRisk.HIGH,
    "schedule_pickup": ToolRisk.HIGH,
    "cancel_pickup": ToolRisk.HIGH,
    "cancel_shipment": ToolRisk.HIGH,
    "refund_shipment": ToolRisk.HIGH,
    "buy_batch": ToolRisk.HIGH,
}


def risk_for_tool(name: str) -> ToolRisk:
    return _RISK_BY_NAME.get(name, ToolRisk.MEDIUM)
