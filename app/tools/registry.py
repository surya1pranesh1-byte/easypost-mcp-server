from __future__ import annotations

from mcp.types import Tool

from app.exceptions.app_errors import UnknownToolError
from app.tools.definition import ToolDefinition


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}

    def register(self, tool: ToolDefinition) -> None:
        if tool.name in self._tools:
            raise ValueError(f"Duplicate tool registered: {tool.name}")
        self._tools[tool.name] = tool

    def register_many(self, tools: list[ToolDefinition]) -> None:
        for tool in tools:
            self.register(tool)

    def count(self) -> int:
        return len(self._tools)

    def list(self) -> list[Tool]:
        """Return MCP Tool objects for the server's list_tools handler."""
        result = []
        for t in self._tools.values():
            schema = t.to_mcp_tool()
            result.append(
                Tool(
                    name=schema["name"],
                    title=schema.get("title"),
                    description=schema["description"],
                    inputSchema=schema["inputSchema"],
                )
            )
        return result

    def get(self, name: str) -> ToolDefinition:
        tool = self._tools.get(name)
        if not tool:
            raise UnknownToolError(name)
        return tool
