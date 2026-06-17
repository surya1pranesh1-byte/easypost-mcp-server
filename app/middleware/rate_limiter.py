from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from app.exceptions.app_errors import RateLimitError


@dataclass
class _Bucket:
    count: int
    reset_at: float  # monotonic timestamp when window resets


class InMemoryRateLimiter:
    def __init__(self, *, limit: int, window_ms: int) -> None:
        self._limit = limit
        self._window_s = window_ms / 1000.0
        self._buckets: dict[str, _Bucket] = {}

    def consume(self, key: str) -> None:
        now = time.monotonic()
        bucket = self._buckets.get(key)

        if bucket is None or bucket.reset_at <= now:
            self._buckets[key] = _Bucket(count=1, reset_at=now + self._window_s)
            return

        bucket.count += 1
        if bucket.count > self._limit:
            # Compute actual wall-clock window reset time from monotonic offset
            reset_wall = datetime.now(timezone.utc) + timedelta(seconds=bucket.reset_at - now)
            raise RateLimitError(reset_at=reset_wall.isoformat())
