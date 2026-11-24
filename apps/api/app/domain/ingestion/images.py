"""Validated, metadata-clean JPEG values passed into interpretation."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AdmittedJpeg:
    content: bytes
    width: int
    height: int
    orientation_applied: int
    sha256: str

    def __post_init__(self) -> None:
        if not self.content:
            raise ValueError("Admitted JPEG content must not be empty")
        if self.width < 1 or self.height < 1:
            raise ValueError("Admitted JPEG dimensions must be positive")
        if self.orientation_applied not in range(1, 9):
            raise ValueError("JPEG EXIF orientation must be between 1 and 8")
        if len(self.sha256) != 64:
            raise ValueError("JPEG SHA-256 must contain 64 hexadecimal characters")
