from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app

FIXTURE = (
    Path(__file__).resolve().parents[4]
    / "examples"
    / "synthetic_jpg"
    / "Q1_synthetic.jpg"
)


def test_dev_ingest_accepts_a_jpeg_in_development() -> None:
    image = FIXTURE.read_bytes()
    response = TestClient(create_app(app_env="development")).post(
        "/dev/ingest",
        files={"file": ("Q1_synthetic.jpg", image, "image/jpeg")},
    )

    assert response.status_code == 202
    assert response.json() == {"status": "accepted"}


def test_dev_ingest_is_disabled_outside_development_and_test() -> None:
    image = FIXTURE.read_bytes()
    response = TestClient(create_app(app_env="production")).post(
        "/dev/ingest",
        files={"file": ("Q1_synthetic.jpg", image, "image/jpeg")},
    )

    assert response.status_code == 404


def test_dev_ingest_rejects_non_jpeg_mime() -> None:
    response = TestClient(create_app(app_env="development")).post(
        "/dev/ingest",
        files={"file": ("bad.zip", b"not a jpeg", "application/zip")},
    )

    assert response.status_code == 415
