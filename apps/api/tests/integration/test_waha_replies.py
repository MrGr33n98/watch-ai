from __future__ import annotations

import hashlib
import hmac
import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import httpx
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.adapters.db.base import Base
from app.adapters.db.models import (
    InboundMessageRecord,
    OutboxEventRecord,
    QuestionRecord,
    SenderSessionBindingRecord,
    StudySessionRecord,
    UserRecord,
)
from app.adapters.storage.jpeg import PillowJpegAdmission
from app.adapters.storage.private_media import PrivateMediaStore
from app.adapters.waha.replies import WahaReplyClient
from app.adapters.waha.webhook import WahaWebhookSettings
from app.main import create_app

API_ROOT = Path(__file__).resolve().parents[2]
Q1_BYTES = (
    API_ROOT.parent.parent / "examples" / "synthetic_jpg" / "Q1_synthetic.jpg"
).read_bytes()
WEBHOOK_KEY = "waha-reply-webhook-key-for-tests-32-bytes"
SENDER_KEY = "waha-reply-sender-key-for-tests-32-bytes"
SENDER = "5511999999999@c.us"


class FakeDownloader:
    async def download(self, media_url: str, *, declared_mime: str):
        del media_url
        return PillowJpegAdmission().admit(Q1_BYTES, declared_mime)


def test_waha_reply_client_posts_text_and_webhook_sends_pt_br_confirmations(
    tmp_path: Path,
) -> None:
    sent_messages: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == httpx.URL("https://waha.example.test/api/sendText")
        assert request.headers["X-Api-Key"] == "test-waha-key"
        sent_messages.append(json.loads(request.content))
        return httpx.Response(201, json={"id": "reply-1"})

    reply_client = WahaReplyClient(
        base_url="https://waha.example.test",
        api_key="test-waha-key",
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )

    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        engine,
        tables=[
            UserRecord.__table__,
            StudySessionRecord.__table__,
            QuestionRecord.__table__,
            SenderSessionBindingRecord.__table__,
            InboundMessageRecord.__table__,
            OutboxEventRecord.__table__,
        ],
    )
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    owner_id = uuid4()
    with sessions.begin() as db:
        db.add(UserRecord(id=owner_id))

    app = create_app(
        app_env="test",
        session_factory=sessions,
        waha_settings=WahaWebhookSettings(
            enabled=True,
            webhook_hmac_secret=WEBHOOK_KEY,
            sender_hash_secret=SENDER_KEY,
            allowed_sessions=frozenset({"watch-ai-dev"}),
            allowed_senders=frozenset({SENDER}),
            sender_owner_ids={SENDER: owner_id},
            media_base_url="https://waha.example.test",
            media_api_key="test-waha-key",
            send_replies=True,
        ),
        waha_media_downloader=FakeDownloader(),
        waha_media_store=PrivateMediaStore(tmp_path / "private-media"),
        waha_reply_client=reply_client,
    )

    def send(payload: dict[str, object]):
        body = json.dumps(
            {"event": "message", "session": "watch-ai-dev", "payload": payload}
        ).encode()
        sig = hmac.new(WEBHOOK_KEY.encode(), body, hashlib.sha512).hexdigest()
        return client.post(
            "/waha/webhook",
            content=body,
            headers={
                "X-Webhook-Hmac-Algorithm": "sha512",
                "X-Webhook-Hmac": sig,
            },
        )

    now = int(datetime.now(UTC).timestamp())
    with TestClient(app) as client:
        assert send(
            {
                "id": "m-start",
                "timestamp": now,
                "from": SENDER,
                "fromMe": False,
                "hasMedia": False,
                "body": "INICIAR 2",
            }
        ).status_code == 202
        assert send(
            {
                "id": "m-img-1",
                "timestamp": now + 1,
                "from": SENDER,
                "fromMe": False,
                "hasMedia": True,
                "body": "",
                "media": {
                    "url": "https://waha.example.test/api/files/q1.jpg",
                    "mimetype": "image/jpeg",
                },
            }
        ).status_code == 202
        assert send(
            {
                "id": "m-img-2",
                "timestamp": now + 2,
                "from": SENDER,
                "fromMe": False,
                "hasMedia": True,
                "body": "",
                "media": {
                    "url": "https://waha.example.test/api/files/q2.jpg",
                    "mimetype": "image/jpeg",
                },
            }
        ).status_code == 202

    assert [item["chatId"] for item in sent_messages] == [SENDER, SENDER, SENDER]
    assert "Sessão iniciada" in str(sent_messages[0]["text"])
    assert "1/2" in str(sent_messages[1]["text"])
    assert "Lote fechado" in str(sent_messages[2]["text"])
    engine.dispose()
