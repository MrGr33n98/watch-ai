from __future__ import annotations

from io import BytesIO

import pytest
from PIL import Image

from app.adapters.storage.jpeg import JpegAdmissionError, PillowJpegAdmission


def encode_image(
    image_format: str = "JPEG",
    size: tuple[int, int] = (3, 2),
    exif: Image.Exif | None = None,
) -> bytes:
    output = BytesIO()
    if exif is not None:
        Image.new("RGB", size, color=(240, 240, 240)).save(
            output,
            format=image_format,
            exif=exif,
        )
    else:
        Image.new("RGB", size, color=(240, 240, 240)).save(output, format=image_format)
    return output.getvalue()


def test_valid_jpeg_is_decoded_normalized_and_hashed() -> None:
    original = encode_image()

    admitted = PillowJpegAdmission().admit(original, "image/jpeg")

    assert admitted.width == 3
    assert admitted.height == 2
    assert admitted.sha256
    with Image.open(BytesIO(admitted.content)) as decoded:
        assert decoded.format == "JPEG"
        assert decoded.size == (3, 2)


@pytest.mark.parametrize(
    ("content", "declared_mime"),
    [
        (b"not a jpeg", "image/jpeg"),
        (encode_image("PNG"), "image/jpeg"),
        (encode_image(), "application/octet-stream"),
    ],
)
def test_corrupt_disguised_and_wrong_mime_images_are_rejected(
    content: bytes,
    declared_mime: str,
) -> None:
    with pytest.raises(JpegAdmissionError):
        PillowJpegAdmission().admit(content, declared_mime)


def test_oversized_jpeg_is_rejected_before_decode() -> None:
    content = encode_image()

    with pytest.raises(JpegAdmissionError) as error:
        PillowJpegAdmission(max_bytes=len(content) - 1).admit(content, "image/jpeg")

    assert error.value.status_code == 413


def test_exif_orientation_is_applied_and_metadata_is_removed() -> None:
    exif = Image.Exif()
    exif[274] = 6

    admitted = PillowJpegAdmission().admit(encode_image(size=(2, 3), exif=exif), "image/jpeg")

    assert admitted.width == 3
    assert admitted.height == 2
    assert admitted.orientation_applied == 6
    with Image.open(BytesIO(admitted.content)) as decoded:
        assert decoded.getexif().get(274) is None


def test_decompression_bomb_pixel_budget_is_enforced() -> None:
    with pytest.raises(JpegAdmissionError) as error:
        PillowJpegAdmission(max_pixels=5).admit(encode_image(size=(3, 2)), "image/jpeg")

    assert error.value.status_code == 413
