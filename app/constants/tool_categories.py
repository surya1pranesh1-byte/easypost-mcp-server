from enum import StrEnum


class ToolCategory(StrEnum):
    SHIPMENTS = "shipments"
    TRACKING = "tracking"
    ADDRESS = "address"
    RETURNS = "returns"
    PICKUPS = "pickups"
    INSURANCE = "insurance"
    BATCHES = "batches"
    ORDERS = "orders"
