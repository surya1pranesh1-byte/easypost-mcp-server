from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class _CacheEntry:
    value: Any
    expires_at: float
    loaded_at: str


class ResourceCache:
    def __init__(self, ttl_ms: int = 15 * 60 * 1000) -> None:
        self._ttl_s = ttl_ms / 1000.0
        self._entries: dict[str, _CacheEntry] = {}

    def get(self, key: str) -> Any | None:
        entry = self._entries.get(key)
        if entry is None:
            return None
        if time.monotonic() >= entry.expires_at:
            del self._entries[key]
            return None
        return entry.value

    def set(self, key: str, value: Any, ttl_ms: int | None = None) -> Any:
        from datetime import datetime, timezone

        ttl_s = (ttl_ms / 1000.0) if ttl_ms is not None else self._ttl_s
        self._entries[key] = _CacheEntry(
            value=value,
            expires_at=time.monotonic() + ttl_s,
            loaded_at=datetime.now(timezone.utc).isoformat(),
        )
        return value

    def has_fresh(self, key: str) -> bool:
        return self.get(key) is not None

    def metadata(self, key: str) -> dict | None:
        from datetime import datetime, timezone, timedelta

        entry = self._entries.get(key)
        if entry is None:
            return None
        now = time.monotonic()
        real_now = datetime.now(timezone.utc)
        remaining_s = entry.expires_at - now
        expires_at = (real_now + timedelta(seconds=max(0, remaining_s))).isoformat()
        return {
            "loaded_at": entry.loaded_at,
            "expires_at": expires_at,
            "stale": now >= entry.expires_at,
        }
