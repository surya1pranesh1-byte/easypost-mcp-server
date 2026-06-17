from __future__ import annotations

from typing import TYPE_CHECKING

from app.constants.tool_categories import ToolCategory
from app.schemas.batch_schemas import BatchStatusInput, BuyBatchInput, CreateBatchInput
from app.tools.definition import ToolDefinition

if TYPE_CHECKING:
    from app.services.factory import Services


def batch_tools(services: "Services") -> list[ToolDefinition]:
    return [
        ToolDefinition(
            name="create_batch",
            title="Create Batch",
            category=ToolCategory.BATCHES,
            description="Create a batch from multiple shipments.",
            schema_cls=CreateBatchInput,
            handler=services.batches.create_batch,
        ),
        ToolDefinition(
            name="buy_batch",
            title="Buy Batch",
            category=ToolCategory.BATCHES,
            description="Buy labels for all purchasable shipments in a batch.",
            schema_cls=BuyBatchInput,
            handler=services.batches.buy_batch,
        ),
        ToolDefinition(
            name="batch_status",
            title="Batch Status",
            category=ToolCategory.BATCHES,
            description="Get current batch processing and purchase status.",
            schema_cls=BatchStatusInput,
            handler=services.batches.batch_status,
        ),
    ]
