import logging

from app.adapters.queue.audit import StructuredOutboxAudit


def test_outbox_audit_logs_only_allowlisted_delivery_fields(caplog) -> None:
    audit = StructuredOutboxAudit(logging.getLogger("watch_ai.outbox.test"))

    with caplog.at_level(logging.INFO, logger="watch_ai.outbox.test"):
        audit.record(
            event_type="inbound_message.accepted",
            outcome="retry_scheduled",
            attempt_count=2,
            error_code="timeout",
        )

    record = caplog.records[0]
    assert record.event_type == "inbound_message.accepted"
    assert record.outcome == "retry_scheduled"
    assert record.error_code == "timeout"
    assert record.attempt_count == 2
    assert "provider_message_id" not in record.__dict__
    assert "sender_hmac" not in record.__dict__
    assert "media_sha" not in record.__dict__
