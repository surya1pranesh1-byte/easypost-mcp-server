from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine, Type

from pydantic import BaseModel

from app.constants.tool_risk import ToolRisk, risk_for_tool
from app.validators.validate import model_to_json_schema, validate_input


@dataclass
class ToolDefinition:
    name: str
    title: str
    description: str
    category: str
    schema_cls: Type[BaseModel]
    handler: Callable[..., Coroutine[Any, Any, dict]]
    risk: ToolRisk | None = None
    annotations: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.risk is None:
            self.risk = risk_for_tool(self.name)

    def to_mcp_tool(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "title": self.title,
            "description": self.description,
            "inputSchema": model_to_json_schema(self.schema_cls, self.name),
            "annotations": {
                "category": self.category,
                "risk": self.risk,
                **self.annotations,
            },
        }

    async def execute(self, args: dict | None, context: dict) -> dict[str, Any]:
        pipeline = context.get("pipeline")
        if pipeline:
            return await pipeline.run(self, args or {}, context)

        validated = validate_input(
            self.schema_cls,
            args,
            resource_manager=context.get("resources"),
            tool_name=self.name,
            risk=self.risk,
        )
        return await self.handler(validated, context)
