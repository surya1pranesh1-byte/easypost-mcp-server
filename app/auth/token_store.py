from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass
class _TokenEntry:
    api_key: str
    expires_at: float


class TokenStore:
    def __init__(self) -> None:
        self._auth_codes: dict[str, _TokenEntry] = {}
        self._access_tokens: dict[str, _TokenEntry] = {}

    def store_auth_code(self, code: str, api_key: str, expiry_seconds: int) -> str:
        self._auth_codes[code] = _TokenEntry(
            api_key=api_key,
            expires_at=time.monotonic() + expiry_seconds,
        )
        return code

    def store_access_token(self, token: str, api_key: str, expiry_seconds: int) -> str:
        self._access_tokens[token] = _TokenEntry(
            api_key=api_key,
            expires_at=time.monotonic() + expiry_seconds,
        )
        return token

    def get_auth_code_api_key(self, code: str) -> str | None:
        entry = self._auth_codes.get(code)
        if entry is None:
            return None
        if time.monotonic() > entry.expires_at:
            del self._auth_codes[code]
            return None
        return entry.api_key

    def get_access_token_api_key(self, token: str) -> str | None:
        entry = self._access_tokens.get(token)
        if entry is None:
            return None
        if time.monotonic() > entry.expires_at:
            del self._access_tokens[token]
            return None
        return entry.api_key

    def consume_auth_code(self, code: str) -> str | None:
        api_key = self.get_auth_code_api_key(code)
        if api_key:
            self._auth_codes.pop(code, None)
        return api_key

    def cleanup(self) -> None:
        now = time.monotonic()
        self._auth_codes = {k: v for k, v in self._auth_codes.items() if v.expires_at > now}
        self._access_tokens = {k: v for k, v in self._access_tokens.items() if v.expires_at > now}
