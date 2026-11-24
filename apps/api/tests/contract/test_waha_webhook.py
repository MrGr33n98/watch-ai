import hashlib
import hmac
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.adapters.storage.jpeg import PillowJpegAdmission
from app.adapters.waha.webhook import WahaWebhookSettings
from app.application.ingestion import IngestionOutcome, IngestionResult
from app.domain.ingestion.models import InboundMessage
from app.domain.sessions.batches import BatchResult, BatchResultStatus
from app.domain.sessions.models import SessionStatus
from app.main import create_app

WEBHOOK_KEY = "waha-webhook-secret-for-tests-32-bytes-minimum"
SENDER_KEY = "sender-hash-key-for-tests-32-bytes-minimum"
OWNER_ID = uuid4()
SESSION_ID = uuid4()


@dataclass
class RecordingIngestor:
    outcomes: list[IngestionOutcome] | None = None

    def __post_init__(self) -> None:
        self.messages: list[InboundMessage] = []

    def execute(self, message: InboundMessage) -> IngestionResult:
        self.messages.append(message)
        outcome = self.outcomes.pop(0) if self.outcomes else IngestionOutcome.ACCEPTED
        return IngestionResult(outcome=outcome, message_id=str(message.id))


class FixtureMediaDownloader:
    async def download(self, media_url: str, *, declared_mime: str):
        del media_url
        return PillowJpegAdmission().admit(JPEG_FIXTURE, declared_mime)


class NoopMediaStore:
    def store(self, image) -> None:
        del image


@dataclass
class RecordingBatchCoordinator:
    expected_count: int = 4
    received_count: int = 0

    def is_duplicate_message(self, provider_message_id: str) -> bool:
        del provider_message_id
        return False

    def start(
        self,
        sender_hmac: str,
        owner_id: UUID,
        *,
        expected_count: int = 4,
        now: datetime | None = None,
    ) -> BatchResult:
        del sender_hmac, owner_id, now
        self.expected_count = expected_count
        self.received_count = 0
        return self._result(BatchResultStatus.STARTED)

    def require_active(
        self,
        sender_hmac: str,
        owner_id: UUID,
        *,
        now: datetime | None = None,
    ) -> BatchResult:
        del sender_hmac, owner_id, now
        return self._result(BatchResultStatus.ALREADY_ACTIVE)

    def add_image(
        self,
        sender_hmac: str,
        media_sha: str,
        *,
        now: datetime | None = None,
        provider_message_id: str | None = None,
        provider_timestamp: datetime | None = None,
    ) -> BatchResult:
        del sender_hmac, media_sha, now, provider_message_id, provider_timestamp
        self.received_count += 1
        status = (
            BatchResultStatus.FINALIZED
            if self.received_count >= self.expected_count
            else BatchResultStatus.IMAGE_ACCEPTED
        )
        return self._result(status, ordinal=self.received_count)

    def finish(self, sender_hmac: str, *, now: datetime | None = None) -> BatchResult:
        del sender_hmac, now
        return self._result(BatchResultStatus.FINALIZED)

    def _result(self, status: BatchResultStatus, *, ordinal: int | None = None) -> BatchResult:
        return BatchResult(
            status=status,
            session_id=SESSION_ID,
            expected_count=self.expected_count,
            received_count=self.received_count,
            session_status=(
                SessionStatus.QUEUED
                if status in {BatchResultStatus.FINALIZED, BatchResultStatus.EXPIRED}
                else SessionStatus.COLLECTING
            ),
            ordinal=ordinal,
        )


API_ROOT = Path(__file__).resolve().parents[2]
JPEG_FIXTURE = (
    API_ROOT.parent.parent / "examples" / "synthetic_jpg" / "Q1_synthetic.jpg"
).read_bytes()


def payload(**payload_overrides: object) -> bytes:
    message = {
        "id": "false_5511999999999@c.us_message-001",
        "timestamp": 1795450000,
        "from": "5511999999999@c.us",
        "fromMe": False,
        "hasMedia": True,
        "body": "",
        "media": {
            "url": "https://waha.example.test/api/files/message-001.jpg",
            "mimetype": "image/jpeg",
            "filename": "Q1.jpg",
            "error": None,
        },
    }
    message.update(payload_overrides)
    return json.dumps({"event": "message", "session": "watch-ai-dev", "payload": message}).encode()


def client(
    ingestor: RecordingIngestor | None = None,
    *,
    enabled: bool = True,
) -> tuple[TestClient, RecordingIngestor]:
    selected_ingestor = ingestor or RecordingIngestor()
    batch_coordinator = RecordingBatchCoordinator()
    application = create_app(
        app_env="test",
        waha_settings=WahaWebhookSettings(
            enabled=enabled,
            webhook_hmac_secret=WEBHOOK_KEY,
            sender_hash_secret=SENDER_KEY,
            allowed_sessions=frozenset({"watch-ai-dev"}),
            allowed_senders=frozenset({"5511999999999@c.us"}),
            sender_owner_ids={"5511999999999@c.us": OWNER_ID},
            media_base_url="https://waha.example.test",
            media_api_key="test-waha-api-key",
        ),
        waha_ingestion=selected_ingestor,
        waha_batch_service=batch_coordinator,
        waha_media_downloader=FixtureMediaDownloader(),
        waha_media_store=NoopMediaStore(),
    )
    return TestClient(application), selected_ingestor


def post_webhook(test_client: TestClient, body: bytes, *, secret: str = WEBHOOK_KEY):
    signature = hmac.new(secret.encode(), body, hashlib.sha512).hexdigest()
    return test_client.post(
        "/waha/webhook",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-Webhook-Hmac-Algorithm": "sha512",
            "X-Webhook-Hmac": signature,
        },
    )


def test_valid_waha_message_is_normalized_without_persisting_sender_identity() -> None:
    test_client, ingestor = client()
    body = payload()

    response = post_webhook(test_client, body)

    assert response.status_code == 202
    assert response.json()["status"] == "accepted"
    assert len(ingestor.messages) == 1
    message = ingestor.messages[0]
    assert message.provider == "waha"
    assert message.provider_message_id == hmac.new(
        SENDER_KEY.encode(),
        b"waha-message-id:false_5511999999999@c.us_message-001",
        hashlib.sha256,
    ).hexdigest()
    assert message.sender_hmac == hmac.new(
        SENDER_KEY.encode(),
        b"5511999999999@c.us",
        hashlib.sha256,
    ).hexdigest()
    assert "5511999999999" not in message.sender_hmac
    assert "5511999999999" not in message.provider_message_id
    assert message.media_sha == PillowJpegAdmission().admit(JPEG_FIXTURE, "image/jpeg").sha256


def test_webhook_hmac_is_required_and_compared_before_json_is_parsed() -> None:
    test_client, ingestor = client()
    response = test_client.post(
        "/waha/webhook",
        content=b"not-json",
        headers={"X-Webhook-Hmac-Algorithm": "sha512", "X-Webhook-Hmac": "wrong"},
    )

    assert response.status_code == 401
    assert ingestor.messages == []


def test_wrong_waha_session_is_rejected() -> None:
    test_client, ingestor = client()
    body = json.dumps({"event": "message", "session": "production", "payload": {}}).encode()

    response = post_webhook(test_client, body)

    assert response.status_code == 403
    assert ingestor.messages == []


def test_unauthorized_sender_is_rejected() -> None:
    test_client, ingestor = client()
    body = payload(**{"from": "5511888888888@c.us"})

    response = post_webhook(test_client, body)

    assert response.status_code == 403
    assert ingestor.messages == []


def test_from_me_and_non_message_events_are_ignored() -> None:
    test_client, ingestor = client()
    own_message = payload(fromMe=True)
    own_response = post_webhook(test_client, own_message)
    event_body = json.dumps(
        {"event": "message.ack", "session": "watch-ai-dev", "payload": {}}
    ).encode()
    event_response = post_webhook(test_client, event_body)

    assert own_response.status_code == 202
    assert own_response.json() == {"status": "ignored", "reason": "from_me"}
    assert event_response.status_code == 202
    assert event_response.json() == {"status": "ignored", "reason": "unsupported_event"}
    assert ingestor.messages == []


def test_disabled_waha_ingest_does_not_accept_events() -> None:
    test_client, ingestor = client(enabled=False)

    response = post_webhook(test_client, payload())

    assert response.status_code == 404
    assert ingestor.messages == []


def test_duplicate_delivery_reports_duplicate_and_does_not_change_identity() -> None:
    duplicate_ingestor = RecordingIngestor(
        outcomes=[IngestionOutcome.ACCEPTED, IngestionOutcome.DUPLICATE]
    )
    test_client, ingestor = client(duplicate_ingestor)
    body = payload()

    first = post_webhook(test_client, body)
    second = post_webhook(test_client, body)

    assert first.status_code == 202
    assert second.status_code == 200
    assert second.json()["status"] == "duplicate"
    assert [message.provider_message_id for message in ingestor.messages] == [
        hmac.new(
            SENDER_KEY.encode(),
            b"waha-message-id:false_5511999999999@c.us_message-001",
            hashlib.sha256,
        ).hexdigest(),
        hmac.new(
            SENDER_KEY.encode(),
            b"waha-message-id:false_5511999999999@c.us_message-001",
            hashlib.sha256,
        ).hexdigest(),
    ]


def test_start_command_uses_configured_question_count_and_sender_owner() -> None:
    test_client, ingestor = client()
    body = payload(hasMedia=False, body="INICIAR 2")

    response = post_webhook(test_client, body)

    assert response.status_code == 202
    assert response.json()["status"] == "started"
    assert response.json()["expected_count"] == 2
    assert ingestor.messages == []


def test_finish_command_is_processed_without_media_download() -> None:
    test_client, ingestor = client()
    body = payload(hasMedia=False, body="FINALIZAR")

    response = post_webhook(test_client, body)

    assert response.status_code == 202
    assert response.json()["status"] == "finalized"
    assert ingestor.messages == []
