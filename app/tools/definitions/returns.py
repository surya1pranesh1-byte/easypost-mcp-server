from __future__ import annotations

from typing import TYPE_CHECKING

from app.constants.tool_categories import ToolCategory
from app.schemas.return_schemas import CreateReturnLabelInput
from app.tools.definition import ToolDefinition

if TYPE_CHECKING:
    from app.services.factory import Services


def return_tools(services: "Services") -> list[ToolDefinition]:
    return [
        ToolDefinition(
            name="create_return_label",
            title="Create Return Label",
            category=ToolCategory.RETURNS,
            description="Create and optionally buy a return label using business return fields.",
            schema_cls=CreateReturnLabelInput,
            handler=services.returns.create_return_label,
        ),
    ]
