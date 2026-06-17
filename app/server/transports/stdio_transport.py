from __future__ import annotations

from typing import TYPE_CHECKING

from mcp.server.stdio import stdio_server

from app.server.mcp_server import create_mcp_server

if TYPE_CHECKING:
    from app.config.settings import AppConfig
    from app.services.factory import Services


async def start_stdio_transport(config: "AppConfig", services: "Services") -> None:
    from app.logging.logger import get_logger

    logger = get_logger()
    server = create_mcp_server(config, services)

    async with stdio_server() as (read_stream, write_stream):
        logger.info("EasyPost MCP server running on stdio")
        await server.run(read_stream, write_stream, server.create_initialization_options())
