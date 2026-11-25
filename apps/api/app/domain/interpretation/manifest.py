"""Structured inventory of questions, subitems, figures, and tables in an exercise sheet."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class ManifestQuestion:
    source_number: str
    ordinal: int
    statement: str
    subitems: tuple[str, ...] = ()
    figure_references: tuple[str, ...] = ()
    table_references: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.source_number.strip():
            raise ValueError("Manifest question source number must not be empty")
        if self.ordinal < 1:
            raise ValueError("Manifest question ordinal must be at least 1")
        if not self.statement.strip():
            raise ValueError("Manifest question statement must not be empty")
        object.__setattr__(self, "subitems", tuple(self.subitems))
        object.__setattr__(self, "figure_references", tuple(self.figure_references))
        object.__setattr__(self, "table_references", tuple(self.table_references))


@dataclass(frozen=True, slots=True)
class DocumentManifest:
    document_id: str
    detected_questions: int
    questions: tuple[ManifestQuestion, ...] = field(default_factory=tuple)
    has_shared_figures: bool = False
    has_shared_tables: bool = False

    def __post_init__(self) -> None:
        if not self.document_id.strip():
            raise ValueError("Document ID must not be empty")
        if self.detected_questions < 0:
            raise ValueError("Detected questions count must be non-negative")
        object.__setattr__(self, "questions", tuple(self.questions))

