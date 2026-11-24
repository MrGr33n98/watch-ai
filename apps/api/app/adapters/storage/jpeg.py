"""Pillow-based admission, safe decoding, EXIF rotation, and metadata stripping."""

import warnings
from hashlib import sha256
from io import BytesIO

from PIL import Image, ImageOps, UnidentifiedImageError

from app.domain.ingestion.images import AdmittedJpeg

DEFAULT_MAX_JPEG_BYTES = 8 * 1024 * 1024
DEFAULT_MAX_JPEG_PIXELS = 40_000_000


class JpegAdmissionError(ValueError):
    def __init__(self, message: str, status_code: int = 415) -> None:
        super().__init__(message)
        self.status_code = status_code


class PillowJpegAdmission:
    def __init__(
        self,
        max_bytes: int = DEFAULT_MAX_JPEG_BYTES,
        max_pixels: int = DEFAULT_MAX_JPEG_PIXELS,
    ) -> None:
        if isinstance(max_bytes, bool) or max_bytes < 1:
            raise ValueError("JPEG max_bytes must be positive")
        if isinstance(max_pixels, bool) or max_pixels < 1:
            raise ValueError("JPEG max_pixels must be positive")
        self._max_bytes = max_bytes
        self._max_pixels = max_pixels

    def admit(self, content: bytes, declared_mime: str) -> AdmittedJpeg:
        mime_type = declared_mime.split(";", maxsplit=1)[0].strip().lower()
        if mime_type != "image/jpeg":
            raise JpegAdmissionError("Only image/jpeg media is accepted")
        if not content:
            raise JpegAdmissionError("JPEG media must not be empty")
        if len(content) > self._max_bytes:
            raise JpegAdmissionError("JPEG exceeds the configured byte limit", 413)

        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(BytesIO(content)) as probe:
                    if probe.format != "JPEG":
                        raise JpegAdmissionError("Media bytes are not a JPEG image")
                    width, height = probe.size
                    if width < 1 or height < 1 or width * height > self._max_pixels:
                        raise JpegAdmissionError("JPEG decoded pixel count exceeds the limit", 413)
                    orientation = probe.getexif().get(274, 1)
                    if isinstance(orientation, bool) or orientation not in range(1, 9):
                        raise JpegAdmissionError("JPEG EXIF orientation is invalid")
                    probe.verify()

                with Image.open(BytesIO(content)) as image:
                    image.load()
                    oriented = ImageOps.exif_transpose(image)
                    normalized = BytesIO()
                    oriented.convert("RGB").save(
                        normalized,
                        format="JPEG",
                        quality=95,
                        optimize=True,
                        exif=b"",
                    )
        except JpegAdmissionError:
            raise
        except (Image.DecompressionBombError, Image.DecompressionBombWarning) as error:
            raise JpegAdmissionError("JPEG exceeds the safe decoded pixel limit", 413) from error
        except (OSError, SyntaxError, UnidentifiedImageError, ValueError) as error:
            raise JpegAdmissionError("JPEG is corrupt or cannot be decoded") from error

        normalized_content = normalized.getvalue()
        if len(normalized_content) > self._max_bytes:
            raise JpegAdmissionError("Normalized JPEG exceeds the configured byte limit", 413)
        return AdmittedJpeg(
            content=normalized_content,
            width=oriented.width,
            height=oriented.height,
            orientation_applied=orientation,
            sha256=sha256(normalized_content).hexdigest(),
        )
