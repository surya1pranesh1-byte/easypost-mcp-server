from __future__ import annotations

from typing import TYPE_CHECKING

from app.constants.tool_categories import ToolCategory
from app.schemas.address_schemas import CreateAddressInput, VerifyAddressInput
from app.tools.definition import ToolDefinition

if TYPE_CHECKING:
    from app.services.factory import Services


def address_tools(services: "Services") -> list[ToolDefinition]:
    return [
        ToolDefinition(
            name="verify_address",
            title="Verify Address",
            category=ToolCategory.ADDRESS,
            description="Verify a real shipping address and return normalized verification status and messages.",
            schema_cls=VerifyAddressInput,
            handler=services.addresses.verify_address,
        ),
        ToolDefinition(
            name="create_address",
            title="Create Address",
            category=ToolCategory.ADDRESS,
            description="Create an EasyPost address object, optionally requesting provider verification.",
            schema_cls=CreateAddressInput,
            handler=services.addresses.create_address,
        ),
    ]
