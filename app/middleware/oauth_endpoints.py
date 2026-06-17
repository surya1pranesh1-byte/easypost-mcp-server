from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Form, Query, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from app.middleware.oauth_form import render_oauth_form
from app.utils.oauth_validation import validate_easypost_api_key
from app.utils.token_generation import generate_authorization_code, generate_secure_token

if TYPE_CHECKING:
    from app.auth.token_store import TokenStore
    from app.config.settings import AppConfig


def create_oauth_router(config: "AppConfig", token_store: "TokenStore") -> APIRouter:
    router = APIRouter()

    @router.get("/.well-known/oauth-authorization-server")
    async def oauth_discovery() -> JSONResponse:
        issuer_url = config.oauth.issuer_url
        if not issuer_url:
            return JSONResponse(
                {"error": "oauth_misconfigured", "error_description": "OAuth discovery endpoint is not configured"},
                status_code=500,
            )
        return JSONResponse({
            "issuer": issuer_url,
            "authorization_endpoint": f"{issuer_url}/oauth/authorize",
            "token_endpoint": f"{issuer_url}/oauth/token",
            "response_types_supported": ["code"],
            "grant_types_supported": ["authorization_code"],
            "token_endpoint_auth_methods_supported": ["client_secret_post"],
            "revocation_endpoint_auth_methods_supported": ["client_secret_post"],
        })

    @router.get("/oauth/authorize")
    async def oauth_authorize_get(
        response_type: str = Query(default=""),
        client_id: str = Query(default=""),
        redirect_uri: str = Query(default=""),
        state: str = Query(default=""),
        scope: str = Query(default=""),
    ) -> HTMLResponse:
        from app.logging.logger import get_logger
        logger = get_logger()

        if response_type != "code":
            logger.warning("Invalid OAuth response_type", response_type=response_type)
            return JSONResponse(
                {"error": "unsupported_response_type", "error_description": "Only response_type=code is supported"},
                status_code=400,
            )
        if not client_id:
            logger.warning("Missing OAuth client_id")
            return JSONResponse(
                {"error": "invalid_client", "error_description": "client_id is required"},
                status_code=400,
            )
        if not redirect_uri:
            logger.warning("Missing OAuth redirect_uri")
            return JSONResponse(
                {"error": "invalid_request", "error_description": "redirect_uri is required"},
                status_code=400,
            )
        html_content = render_oauth_form(client_id=client_id, redirect_uri=redirect_uri, state=state)
        return HTMLResponse(content=html_content)

    @router.post("/oauth/authorize")
    async def oauth_authorize_post(
        api_key: str = Form(default=""),
        client_id: str = Form(default=""),
        redirect_uri: str = Form(default=""),
        state: str = Form(default=""),
    ) -> Any:
        from app.logging.logger import get_logger
        logger = get_logger()

        if not api_key:
            html_content = render_oauth_form(client_id=client_id, redirect_uri=redirect_uri, state=state, error="API key is required")
            return HTMLResponse(content=html_content)

        if not client_id:
            logger.warning("Missing client_id in OAuth authorize")
            html_content = render_oauth_form(client_id=client_id, redirect_uri=redirect_uri, state=state, error="Missing client ID")
            return HTMLResponse(content=html_content)

        validation = await validate_easypost_api_key(api_key, logger)
        if not validation["valid"]:
            logger.warning("OAuth: API key validation failed")
            html_content = render_oauth_form(client_id=client_id, redirect_uri=redirect_uri, state=state, error="Invalid API key. Please check and try again.")
            return HTMLResponse(content=html_content)

        auth_code = generate_authorization_code()
        token_store.store_auth_code(auth_code, api_key, config.oauth.code_expiry_seconds)
        logger.info("OAuth authorization code generated")

        from urllib.parse import urlencode, urlparse, parse_qs, urlunparse
        parts = list(urlparse(redirect_uri))
        params = dict(code=auth_code)
        if state:
            params["state"] = state
        parts[4] = urlencode(params)
        return RedirectResponse(url=urlunparse(parts), status_code=302)

    @router.post("/oauth/token")
    async def oauth_token(
        grant_type: str = Form(default=""),
        code: str = Form(default=""),
        client_id: str = Form(default=""),
        client_secret: str = Form(default=""),
        redirect_uri: str = Form(default=""),
    ) -> JSONResponse:
        from app.logging.logger import get_logger
        logger = get_logger()

        if grant_type != "authorization_code":
            logger.warning("Invalid OAuth grant_type", grant_type=grant_type)
            return JSONResponse(
                {"error": "unsupported_grant_type", "error_description": "Only grant_type=authorization_code is supported"},
                status_code=400,
            )
        if not code:
            logger.warning("Missing authorization code")
            return JSONResponse({"error": "invalid_request", "error_description": "code is required"}, status_code=400)
        if not client_id:
            logger.warning("Missing client_id in token exchange")
            return JSONResponse({"error": "invalid_client", "error_description": "client_id is required"}, status_code=401)
        if not client_secret or client_secret != config.oauth.client_secret:
            logger.warning("Invalid client_secret in token exchange")
            return JSONResponse({"error": "invalid_client", "error_description": "Invalid client_secret"}, status_code=401)

        api_key = token_store.consume_auth_code(code)
        if not api_key:
            logger.warning("Authorization code not found or expired")
            return JSONResponse(
                {"error": "invalid_grant", "error_description": "Authorization code is invalid or expired"},
                status_code=400,
            )

        access_token = generate_secure_token()
        token_store.store_access_token(access_token, api_key, config.oauth.token_expiry_seconds)
        logger.info("OAuth access token issued")

        return JSONResponse({
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": config.oauth.token_expiry_seconds,
        })

    return router
