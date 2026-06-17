from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class _EnvVars(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).parent.parent.parent / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    NODE_ENV: Literal["development", "test", "production"] = "development"
    EASYPOST_API_KEY: str | None = None
    EASYPOST_MODE: Literal["sandbox", "production"] = "sandbox"
    LOG_LEVEL: Literal["trace", "debug", "info", "warn", "error", "fatal", "silent"] = "info"
    DEBUG: str | None = None
    EASYPOST_TIMEOUT_MS: int = Field(default=30000, gt=0)
    EASYPOST_RETRY_ATTEMPTS: int = Field(default=2, ge=0, le=5)
    MCP_RATE_LIMIT_PER_MINUTE: int = Field(default=60, gt=0)
    MCP_HTTP_PORT: int = Field(default=8080, gt=0)
    MCP_HTTP_HOST: str = "0.0.0.0"
    # Cloud Run (and other container platforms) inject PORT; takes precedence over MCP_HTTP_PORT
    PORT: int | None = Field(default=None, gt=0)
    OAUTH_ISSUER_URL: str | None = None
    OAUTH_CLIENT_ID: str = "easypost-mcp"
    OAUTH_CLIENT_SECRET: str | None = None
    OAUTH_CODE_EXPIRY_SECONDS: int = Field(default=300, gt=0)
    OAUTH_TOKEN_EXPIRY_SECONDS: int = Field(default=3600, gt=0)


@dataclass(frozen=True)
class EasyPostConfig:
    api_key: str | None
    mode: str
    timeout_ms: int
    retry_attempts: int


@dataclass(frozen=True)
class LoggingConfig:
    level: str


@dataclass(frozen=True)
class RateLimitConfig:
    per_minute: int


@dataclass(frozen=True)
class HttpConfig:
    port: int
    host: str


@dataclass(frozen=True)
class OAuthConfig:
    issuer_url: str | None
    client_id: str
    client_secret: str | None
    code_expiry_seconds: int
    token_expiry_seconds: int


@dataclass(frozen=True)
class AppConfig:
    env: str
    is_production: bool
    debug: bool
    easypost: EasyPostConfig
    logging: LoggingConfig
    rate_limit: RateLimitConfig
    http: HttpConfig
    oauth: OAuthConfig


def _build_config(env: _EnvVars) -> AppConfig:
    return AppConfig(
        env=env.NODE_ENV,
        is_production=env.NODE_ENV == "production",
        debug=env.DEBUG == "true" or env.LOG_LEVEL == "debug",
        easypost=EasyPostConfig(
            api_key=env.EASYPOST_API_KEY,
            mode=env.EASYPOST_MODE,
            timeout_ms=env.EASYPOST_TIMEOUT_MS,
            retry_attempts=env.EASYPOST_RETRY_ATTEMPTS,
        ),
        logging=LoggingConfig(level=env.LOG_LEVEL),
        rate_limit=RateLimitConfig(per_minute=env.MCP_RATE_LIMIT_PER_MINUTE),
        http=HttpConfig(port=env.PORT if env.PORT is not None else env.MCP_HTTP_PORT, host=env.MCP_HTTP_HOST),
        oauth=OAuthConfig(
            issuer_url=env.OAUTH_ISSUER_URL,
            client_id=env.OAUTH_CLIENT_ID,
            client_secret=env.OAUTH_CLIENT_SECRET,
            code_expiry_seconds=env.OAUTH_CODE_EXPIRY_SECONDS,
            token_expiry_seconds=env.OAUTH_TOKEN_EXPIRY_SECONDS,
        ),
    )


_cached_config: AppConfig | None = None


def get_config() -> AppConfig:
    global _cached_config
    if _cached_config is None:
        _cached_config = _build_config(_EnvVars())
    return _cached_config


def reset_config_for_tests() -> None:
    global _cached_config
    _cached_config = None


def apply_bootstrap_options(
    *,
    api_key: str | None = None,
    node_env: str | None = None,
    easypost_mode: str | None = None,
    log_level: str | None = None,
    timeout_ms: int | None = None,
    retry_attempts: int | None = None,
    rate_limit_per_minute: int | None = None,
    http_port: int | None = None,
    http_host: str | None = None,
) -> None:
    """Apply CLI options to environment before config is loaded. Priority: CLI → env → .env file."""
    if api_key:
        os.environ["EASYPOST_API_KEY"] = api_key
    if node_env:
        os.environ["NODE_ENV"] = node_env
    if easypost_mode:
        os.environ["EASYPOST_MODE"] = easypost_mode
    if log_level:
        os.environ["LOG_LEVEL"] = log_level
    if timeout_ms is not None:
        os.environ["EASYPOST_TIMEOUT_MS"] = str(timeout_ms)
    if retry_attempts is not None:
        os.environ["EASYPOST_RETRY_ATTEMPTS"] = str(retry_attempts)
    if rate_limit_per_minute is not None:
        os.environ["MCP_RATE_LIMIT_PER_MINUTE"] = str(rate_limit_per_minute)
    if http_port is not None:
        os.environ["MCP_HTTP_PORT"] = str(http_port)
    if http_host:
        os.environ["MCP_HTTP_HOST"] = http_host
    reset_config_for_tests()
