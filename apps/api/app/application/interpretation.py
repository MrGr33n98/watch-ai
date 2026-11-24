"""Application service that delegates image reading through a provider port."""

from app.application.ports import VisionProvider
from app.domain.ingestion.models import InboundMessage
from app.domain.interpretation.models import InterpretedExercise


class InterpretationProcessor:
    def __init__(self, vision_provider: VisionProvider) -> None:
        self._vision_provider = vision_provider

    def process(
        self,
        message: InboundMessage,
        *,
        image_bytes: bytes | None = None,
    ) -> InterpretedExercise:
        return self._vision_provider.interpret(message, image_bytes=image_bytes)
