from pathlib import Path

import pytest

from app.adapters.storage.jpeg import PillowJpegAdmission
from app.adapters.storage.private_media import PrivateMediaStore

FIXTURE = Path(__file__).resolve().parents[4] / "examples" / "synthetic_jpg" / "Q1_synthetic.jpg"


def test_store_is_content_addressed_private_and_readable_by_digest(tmp_path: Path) -> None:
    admitted = PillowJpegAdmission().admit(FIXTURE.read_bytes(), "image/jpeg")
    store = PrivateMediaStore(tmp_path / "private-media")

    store.store(admitted)

    assert store.read(admitted.sha256) == admitted.content
    assert len(list((tmp_path / "private-media").rglob("*.jpg"))) == 1
    assert (tmp_path / "private-media").stat().st_mode & 0o777 == 0o700
    media_file = next((tmp_path / "private-media").rglob("*.jpg"))
    assert media_file.stat().st_mode & 0o777 == 0o600


def test_store_rejects_content_that_does_not_match_its_digest(tmp_path: Path) -> None:
    admitted = PillowJpegAdmission().admit(FIXTURE.read_bytes(), "image/jpeg")
    corrupted = admitted.__class__(
        content=admitted.content + b"corrupt",
        width=admitted.width,
        height=admitted.height,
        orientation_applied=admitted.orientation_applied,
        sha256=admitted.sha256,
    )

    with pytest.raises(ValueError, match="SHA-256"):
        PrivateMediaStore(tmp_path / "private-media").store(corrupted)


def test_store_rejects_invalid_digest_on_read(tmp_path: Path) -> None:
    store = PrivateMediaStore(tmp_path / "private-media")

    with pytest.raises(ValueError, match="SHA-256"):
        store.read("../private-key")
