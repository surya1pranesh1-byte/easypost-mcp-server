from __future__ import annotations

import json
import time
from importlib.metadata import version, PackageNotFoundError
from typing import Any, Callable

import mcp.types as types
from mcp.server import Server

from app.audit.audit_logger import AuditLogger
from app.config.settings import AppConfig
from app.exceptions.app_errors import AppError
from app.logging.logger import get_logger
from app.middleware.rate_limiter import InMemoryRateLimiter
from app.pipeline.execution_pipeline import ExecutionPipeline
from app.services.factory import Services
from app.tools import create_tool_registry
from app.utils.correlation import create_correlation_id
from app.utils.sanitize import redact_for_logs


def _get_package_version() -> str:
    try:
        return version("easypost-mcp")
    except PackageNotFoundError:
        return "0.0.0"


def _as_mcp_text(payload: dict[str, Any]) -> list[types.TextContent]:
    return [types.TextContent(type="text", text=json.dumps(payload, indent=2, default=str))]


def _to_safe_error(error: Exception, correlation_id: str) -> dict[str, Any]:
    if isinstance(error, AppError):
        return {
            "ok": False,
            "error": {
                "code": error.code,
                "message": error.safe_message,
                "details": error.details,
                "retryable": error.retryable,
                "correlation_id": correlation_id,
            },
        }
    logger = get_logger()
    logger.error(
        "Unhandled tool error",
        error_message=str(error),
        error_type=type(error).__name__,
        correlation_id=correlation_id,
    )
    return {
        "ok": False,
        "error": {
            "code": "INTERNAL_ERROR",
            "message": "An unexpected server error occurred",
            "retryable": False,
            "correlation_id": correlation_id,
        },
    }


def create_mcp_server(
    config: AppConfig,
    services: Services,
    *,
    get_auth_context: Callable[[], dict | None] | None = None,
) -> Server:
    logger = get_logger()
    audit_logger = AuditLogger(logger)
    pipeline = ExecutionPipeline(
        resource_manager=services.resources,
        elicitation_service=services.elicitation,
        workflow_state=services.workflow_state,
        audit_logger=audit_logger,
    )
    registry = create_tool_registry(services)
    limiter = InMemoryRateLimiter(
        limit=config.rate_limit.per_minute,
        window_ms=60 * 1000,
    )

    server = Server(name="easypost-mcp", version=_get_package_version())

    @server.list_tools()
    async def list_tools() -> list[types.Tool]:
        tools = registry.list()
        logger.debug("Listing MCP tools", tool_count=len(tools))
        return tools

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any] | None) -> list[types.Content]:
        correlation_id = create_correlation_id()
        child_logger = logger.bind(correlation_id=correlation_id, tool_name=name)

        start_ms = time.monotonic() * 1000
        try:
            limiter.consume(name)
            child_logger.info(
                "MCP tool called",
                arguments=redact_for_logs(arguments or {}),
            )

            tool = registry.get(name)
            auth_context = get_auth_context() if get_auth_context else None

            result = await tool.execute(
                arguments,
                {
                    "correlation_id": correlation_id,
                    "logger": child_logger,
                    "pipeline": pipeline,
                    "resources": services.resources,
                    "server": server,
                    "auth": auth_context,
                },
            )

            latency_ms = round(time.monotonic() * 1000 - start_ms)
            child_logger.info(
                "MCP tool completed",
                latency_ms=latency_ms,
                result=redact_for_logs(result),
            )
            return _as_mcp_text({**result, "correlation_id": correlation_id})

        except Exception as exc:
            latency_ms = round(time.monotonic() * 1000 - start_ms)
            child_logger.error(
                "Tool execution failed",
                latency_ms=latency_ms,
                error_name=type(exc).__name__,
                error_message=str(exc),
                error_code=getattr(exc, "code", None),
            )
            return _as_mcp_text(_to_safe_error(exc, correlation_id))

    return server
