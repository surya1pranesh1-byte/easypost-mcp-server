from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

if TYPE_CHECKING:
    from app.auth.token_store import TokenStore


_SKIP_PREFIXES = ("/.well-known", "/oauth", "/health")


class AuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, token_store: "TokenStore") -> None:
        super().__init__(app)
        self._token_store = token_store

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path

        if any(path.startswith(prefix) for prefix in _SKIP_PREFIXES):
            return await call_next(request)

        if path == "/mcp":
            from app.logging.logger import get_logger
            logger = get_logger()

            auth_header = request.headers.get("authorization", "")
            if not auth_header.startswith("Bearer "):
                logger.warning("MCP request without Bearer token", path=path)
                return JSONResponse(
                    {
                        "jsonrpc": "2.0",
                        "error": {"code": -32001, "message": "Unauthorized: Bearer token required"},
                        "id": None,
                    },
                    status_code=401,
                )
            token = auth_header[7:]
            api_key = self._token_store.get_access_token_api_key(token)
            if not api_key:
                logger.warning("Invalid or expired access token", path=path)
                return JSONResponse(
                    {
                        "jsonrpc": "2.0",
                        "error": {"code": -32001, "message": "Unauthorized: Invalid token"},
                        "id": None,
                    },
                    status_code=401,
                )
            request.state.auth = {"api_key": api_key, "token": token}

        return await call_next(request)
