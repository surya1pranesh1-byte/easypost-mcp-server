from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable, Awaitable


@dataclass
class _Entry:
    result: Any
    expires_at: float


class IdempotencyStore:
    def __init__(self, ttl_ms: int = 10 * 60 * 1000) -> None:
        self._ttl_s = ttl_ms / 1000.0
        self._entries: dict[str, _Entry] = {}

    def _purge_expired(self) -> None:
        now = time.monotonic()
        expired = [k for k, v in self._entries.items() if v.expires_at <= now]
        for k in expired:
            del self._entries[k]

    def get(self, key: str) -> Any | None:
        if not key:
            return None
        self._purge_expired()
        entry = self._entries.get(key)
        return entry.result if entry else None

    def set(self, key: str, result: Any) -> Any:
        if not key:
            return result
        self._purge_expired()
        self._entries[key] = _Entry(result=result, expires_at=time.monotonic() + self._ttl_s)
        return result

    async def run(self, key: str, operation: Callable[[], Awaitable[Any]]) -> dict[str, Any]:
        existing = self.get(key)
        if existing is not None:
            return {"reused": True, "result": existing}
        result = await operation()
        self.set(key, result)
        return {"reused": False, "result": result}
