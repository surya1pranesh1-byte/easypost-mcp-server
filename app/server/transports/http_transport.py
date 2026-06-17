from __future__ import annotations

import asyncio
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from mcp.server.streamable_http import StreamableHTTPServerTransport

from app.server.mcp_server import create_mcp_server

if TYPE_CHECKING:
    from app.config.settings import AppConfig
    from app.services.factory import Services


@dataclass
class _Session:
    transport: StreamableHTTPServerTransport
    task: asyncio.Task


async def start_http_transport(config: "AppConfig", services: "Services") -> None:
    from app.logging.logger import get_logger

    logger = get_logger()
    sessions: dict[str, _Session] = {}

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        logger.info(
            "EasyPost MCP HTTP server starting",
            host=config.http.host,
            port=config.http.port,
            easypost_mode=config.easypost.mode,
            env=config.env,
        )
        try:
            yield
        finally:
            logger.info("EasyPost MCP HTTP server shutting down", active_sessions=len(sessions))
            for session in list(sessions.values()):
                session.task.cancel()

    app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None)

    @app.get("/health")
    async def health() -> dict[str, Any]:
        return {"status": "UP"}

    @app.get("/ready")
    async def ready() -> JSONResponse:
        """Readiness probe: confirms the EasyPost API key is configured."""
        if not config.easypost.api_key:
            return JSONResponse(
                {"status": "NOT_READY", "reason": "EASYPOST_API_KEY is not configured"},
                status_code=503,
            )
        return JSONResponse({"status": "READY"})

    @app.post("/mcp")
    async def mcp_post(request: Request) -> None:
        """Handle MCP POST requests.

        Per the Streamable HTTP spec, the absence of Mcp-Session-Id means this is
        an `initialize` message that creates a new session. All subsequent messages
        must include the session ID header.
        """
        session_id = request.headers.get("mcp-session-id")

        if session_id:
            session = sessions.get(session_id)
            if not session:
                await JSONResponse(
                    {
                        "jsonrpc": "2.0",
                        "error": {
                            "code": -32000,
                            "message": "Bad Request: Unknown or expired session ID",
                        },
                        "id": None,
                    },
                    status_code=400,
                )(request.scope, request.receive, request._send)
                return
            await session.transport.handle_request(request.scope, request.receive, request._send)
            return

        # No session ID → new session (must be initialize)
        new_session_id = str(uuid.uuid4())
        transport = StreamableHTTPServerTransport(mcp_session_id=new_session_id)

        mcp_server = create_mcp_server(
            config,
            services,
        )

        async def run_session() -> None:
            try:
                async with transport.connect() as (read_stream, write_stream):
                    logger.debug("MCP HTTP session started", session_id=new_session_id)
                    await mcp_server.run(
                        read_stream,
                        write_stream,
                        mcp_server.create_initialization_options(),
                    )
            except asyncio.CancelledError:
                pass
            except Exception as exc:
                logger.error(
                    "MCP HTTP session error",
                    session_id=new_session_id,
                    error_type=type(exc).__name__,
                    error_message=str(exc),
                )
            finally:
                sessions.pop(new_session_id, None)
                logger.debug("MCP HTTP session closed", session_id=new_session_id)

        task = asyncio.create_task(run_session())
        sessions[new_session_id] = _Session(transport=transport, task=task)

        # Yield control so run_session can start and transport.connect() initializes streams
        await asyncio.sleep(0)

        logger.debug("MCP HTTP session created", session_id=new_session_id, active_sessions=len(sessions))
        await transport.handle_request(request.scope, request.receive, request._send)

    @app.get("/mcp")
    async def mcp_get(request: Request) -> None:
        """Handle MCP GET requests (SSE stream for server-initiated notifications)."""
        session_id = request.headers.get("mcp-session-id")
        session = sessions.get(session_id) if session_id else None
        if not session:
            await PlainTextResponse("Invalid or missing session ID", status_code=400)(
                request.scope, request.receive, request._send
            )
            return
        await session.transport.handle_request(request.scope, request.receive, request._send)

    @app.delete("/mcp")
    async def mcp_delete(request: Request) -> None:
        """Handle MCP DELETE requests (explicit session termination)."""
        session_id = request.headers.get("mcp-session-id")
        session = sessions.get(session_id) if session_id else None
        if not session:
            await PlainTextResponse("Invalid or missing session ID", status_code=400)(
                request.scope, request.receive, request._send
            )
            return
        await session.transport.handle_request(request.scope, request.receive, request._send)

    host = config.http.host
    port = config.http.port
    logger.info("EasyPost MCP server running on HTTP", host=host, port=port, path="/mcp")

    uv_config = uvicorn.Config(
        app=app,
        host=host,
        port=port,
        log_level="warning",
        # Graceful shutdown: wait up to 5 s for in-flight requests
        timeout_graceful_shutdown=5,
    )
    server = uvicorn.Server(uv_config)
    await server.serve()
