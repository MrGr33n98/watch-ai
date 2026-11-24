from dataclasses import dataclass
from enum import StrEnum

from app.application.ports import MessageJobScheduler, UnitOfWorkFactory
from app.domain.ingestion.models import InboundMessage, OutboxEvent


class IngestionOutcome(StrEnum):
    ACCEPTED = "accepted"
    DUPLICATE = "duplicate"


@dataclass(frozen=True, slots=True)
class IngestionResult:
    outcome: IngestionOutcome
    message_id: str


class IngestInboundMessage:
    """Persist an inbound event and wake an async worker after committing it."""

    def __init__(
        self,
        unit_of_work_factory: UnitOfWorkFactory,
        job_scheduler: MessageJobScheduler | None = None,
    ) -> None:
        self._unit_of_work_factory = unit_of_work_factory
        self._job_scheduler = job_scheduler

    def execute(self, message: InboundMessage) -> IngestionResult:
        with self._unit_of_work_factory() as unit_of_work:
            stored_message, created = unit_of_work.inbound_messages.add_if_absent(message)
            if not created:
                return IngestionResult(
                    outcome=IngestionOutcome.DUPLICATE,
                    message_id=str(stored_message.id),
                )

            unit_of_work.outbox.add(OutboxEvent.for_inbound_message(stored_message))
            unit_of_work.commit()

        if self._job_scheduler is not None:
            self._job_scheduler.enqueue(stored_message)
        return IngestionResult(
            outcome=IngestionOutcome.ACCEPTED,
            message_id=str(stored_message.id),
        )
