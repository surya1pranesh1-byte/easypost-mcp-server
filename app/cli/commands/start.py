from __future__ import annotations

import asyncio

import click

from app.config.settings import apply_bootstrap_options, get_config
from app.logging.logger import init_logger
from app.services.factory import create_services


def _normalize_transport_mode(mode: str) -> str:
    value = str(mode or "stdio").lower()
    if value in ("stdio", "http"):
        return value
    raise click.BadParameter(f'Invalid --mode "{mode}". Use "stdio" or "http".')


@click.command("start")
@click.option("--api-key", default=None, help="EasyPost API key (or set EASYPOST_API_KEY)")
@click.option("--mode", default="stdio", help="Transport mode: stdio or http")
@click.option("--easypost-mode", default=None, help="EasyPost environment: sandbox or production")
@click.option("--log-level", default=None, help="Log level (trace, debug, info, warn, error)")
@click.option("--port", default=None, type=int, help="HTTP port when --mode=http")
@click.option("--host", default=None, help="HTTP bind host when --mode=http")
@click.option("--timeout-ms", default=None, type=int, help="EasyPost request timeout in milliseconds")
@click.option("--retry-attempts", default=None, type=int, help="EasyPost retry attempts")
@click.option("--rate-limit", default=None, type=int, help="MCP tool calls per minute")
def start_command(
    api_key: str | None,
    mode: str,
    easypost_mode: str | None,
    log_level: str | None,
    port: int | None,
    host: str | None,
    timeout_ms: int | None,
    retry_attempts: int | None,
    rate_limit: int | None,
) -> None:
    """Start the EasyPost MCP server."""
    apply_bootstrap_options(
        api_key=api_key,
        easypost_mode=easypost_mode,
        log_level=log_level,
        timeout_ms=timeout_ms,
        retry_attempts=retry_attempts,
        rate_limit_per_minute=rate_limit,
        http_port=port,
        http_host=host,
    )

    config = get_config()
    logger = init_logger(config)
    transport_mode = _normalize_transport_mode(mode)
    services = create_services(config)

    logger.info(
        "Starting EasyPost MCP server",
        transport=transport_mode,
        easypost_mode=config.easypost.mode,
        env=config.env,
        **({"http": {"host": config.http.host, "port": config.http.port}} if transport_mode == "http" else {}),
    )

    async def _initialize_resources() -> None:
        try:
            await services.resources.initialize()
            logger.info("Resource grounding initialized", **services.resources.get_operational_context())
        except Exception as exc:
            logger.warning(
                "Resource grounding initialization failed; retrying lazily on first tool call",
                error_name=type(exc).__name__,
                error_code=getattr(exc, "code", None),
                error_message=str(exc),
            )

    if transport_mode == "stdio":
        from app.server.transports.stdio_transport import start_stdio_transport

        async def run() -> None:
            await _initialize_resources()
            await start_stdio_transport(config, services)

        asyncio.run(run())
    else:
        from app.server.transports.http_transport import start_http_transport

        async def run() -> None:
            await _initialize_resources()
            await start_http_transport(config, services)

        asyncio.run(run())
