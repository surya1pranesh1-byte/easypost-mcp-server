from __future__ import annotations

import structlog
from structlog.testing import capture_logs

from app.audit.audit_logger import AuditLogger


def test_record_logs_event_without_duplicate_event_argument() -> None:
    with capture_logs() as captured:
        logger = structlog.get_logger()
        AuditLogger(logger).record(
            "intent_extracted",
            {"status": "ok", "details": "sample"},
        )

    assert len(captured) == 1
    log_entry = captured[0]
    assert log_entry["event"] == "intent_extracted"
    assert log_entry["audit"] is True
    assert log_entry["status"] == "ok"
    assert log_entry["details"] == "sample"
