from __future__ import annotations

import copy
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class _WorkflowEntry:
    tool_name: str
    input: dict[str, Any]
    reason: str | None
    correlation_id: str | None
    created_at: str
    expires_at: float


def _deep_merge(base: dict, override: dict) -> dict:
    output = dict(base) if isinstance(base, dict) else {}
    for key, value in override.items():
        if key == "workflow_id":
            continue
        if isinstance(value, dict) and isinstance(output.get(key), dict):
            output[key] = _deep_merge(output[key], value)
        else:
            output[key] = value
    return output


class WorkflowStateStore:
    def __init__(self, ttl_ms: int = 30 * 60 * 1000) -> None:
        self._ttl_s = ttl_ms / 1000.0
        self._entries: dict[str, _WorkflowEntry] = {}

    def _purge_expired(self) -> None:
        now = time.monotonic()
        expired = [k for k, v in self._entries.items() if v.expires_at <= now]
        for k in expired:
            del self._entries[k]

    def create(
        self,
        *,
        tool_name: str,
        input: dict[str, Any] | None = None,
        reason: str | None = None,
        correlation_id: str | None = None,
    ) -> str:
        self._purge_expired()
        workflow_id = f"wf_{uuid.uuid4()}"
        self._entries[workflow_id] = _WorkflowEntry(
            tool_name=tool_name,
            input=input or {},
            reason=reason,
            correlation_id=correlation_id,
            created_at=datetime.now(timezone.utc).isoformat(),
            expires_at=time.monotonic() + self._ttl_s,
        )
        return workflow_id

    def get(self, workflow_id: str | None) -> _WorkflowEntry | None:
        if not workflow_id:
            return None
        self._purge_expired()
        return self._entries.get(workflow_id)

    def merge(self, workflow_id: str | None, input: dict[str, Any]) -> dict[str, Any]:
        state = self.get(workflow_id)
        if not state:
            return input
        return _deep_merge(state.input, input)

    def update(self, workflow_id: str | None, input: dict[str, Any]) -> None:
        if not workflow_id:
            return
        state = self.get(workflow_id)
        if not state:
            return
        self._entries[workflow_id] = _WorkflowEntry(
            tool_name=state.tool_name,
            input=input,
            reason=state.reason,
            correlation_id=state.correlation_id,
            created_at=state.created_at,
            expires_at=time.monotonic() + self._ttl_s,
        )
