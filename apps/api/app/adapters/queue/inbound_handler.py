"""Load an admitted WAHA image and pass its outbox event to the solution pipeline."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from app.application.ports import PrivateMediaReader
from app.domain.ingestion.models import InboundMessage, OutboxEvent


class InboundMessageReader(Protocol):
    def get_by_id(self, message_id: UUID) -> InboundMessage | None: ...


class InboundExerciseProcessor(Protocol):
    def process(self, message: InboundMessage, *, image_bytes: bytes) -> object: ...


class InboundMessageOutboxHandler:
    def __init__(
        self,
        message_reader: InboundMessageReader,
        media_reader: PrivateMediaReader,
        processor: InboundExerciseProcessor,
    ) -> None:
        self._message_reader = message_reader
        self._media_reader = media_reader
        self._processor = processor

    def handle(self, event: OutboxEvent) -> None:
        if event.event_type != "inbound_message.accepted":
            raise ValueError("Unsupported outbox event type")
        raw_message_id = event.payload.get("message_id")
        if raw_message_id is None:
            raise ValueError("Outbox event is missing its message ID")
        try:
            message_id = UUID(raw_message_id)
        except ValueError as error:
            raise ValueError("Outbox event has an invalid message ID") from error
        message = self._message_reader.get_by_id(message_id)
        if message is None or message.media_sha is None:
            raise LookupError("Outbox inbound image is unavailable")
        image_bytes = self._media_reader.read(message.media_sha)
        self._processor.process(message, image_bytes=image_bytes)
