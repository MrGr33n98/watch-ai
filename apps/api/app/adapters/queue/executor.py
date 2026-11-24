"""Bounded, in-process executor used to wake interpretation after durable ingest."""

from concurrent.futures import Future, ThreadPoolExecutor
from threading import RLock
from types import TracebackType
from typing import Self
from uuid import UUID

from app.application.interpretation import InterpretationProcessor
from app.domain.ingestion.models import InboundMessage
from app.domain.interpretation.models import InterpretedExercise


class AsyncInterpretationQueue:
    def __init__(self, processor: InterpretationProcessor, max_workers: int = 2) -> None:
        if isinstance(max_workers, bool) or max_workers < 1:
            raise ValueError("max_workers must be a positive integer")
        self._processor = processor
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="watch-ai")
        self._futures: dict[UUID, Future[InterpretedExercise]] = {}
        self._lock = RLock()

    def enqueue(self, message: InboundMessage) -> None:
        with self._lock:
            if message.id in self._futures:
                return
            self._futures[message.id] = self._executor.submit(self._processor.process, message)

    def result(self, message_id: UUID, timeout: float | None = None) -> InterpretedExercise:
        with self._lock:
            future = self._futures.get(message_id)
        if future is None:
            raise KeyError(f"No interpretation job for message {message_id}")
        return future.result(timeout=timeout)

    def shutdown(self) -> None:
        self._executor.shutdown(wait=True, cancel_futures=False)

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.shutdown()
