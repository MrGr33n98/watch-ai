import asyncio
import hashlib
from pathlib import Path

import httpx
import pytest
import respx

from app.adapters.waha.media import WahaMediaDownloader, WahaMediaError

API_ROOT = Path(__file__).resolve().parents[2]
JPEG_FIXTURE = (
    API_ROOT.parent.parent / "examples" / "synthetic_jpg" / "Q1_synthetic.jpg"
).read_bytes()
WAHA_BASE_URL = "https://waha.example.test"
MEDIA_URL = f"{WAHA_BASE_URL}/api/files/Q1_synthetic.jpg"
API_KEY = "test-waha-api-key"


def download(media_url: str = MEDIA_URL, *, max_bytes: int = 8 * 1024 * 1024):
    downloader = WahaMediaDownloader(
        base_url=WAHA_BASE_URL,
        api_key=API_KEY,
        max_bytes=max_bytes,
    )
    return asyncio.run(downloader.download(media_url, declared_mime="image/jpeg"))


def test_download_uses_api_key_header_and_returns_normalized_jpeg() -> None:
    with respx.mock(assert_all_called=True) as routes:
        route = routes.get(MEDIA_URL).mock(
            return_value=httpx.Response(
                200,
                headers={"Content-Type": "image/jpeg"},
                content=JPEG_FIXTURE,
            )
        )

        admitted = download()

    assert route.calls[0].request.headers["X-Api-Key"] == API_KEY
    assert admitted.sha256 == hashlib.sha256(admitted.content).hexdigest()
    assert admitted.content.startswith(b"\xff\xd8")
    assert admitted.width > 0 and admitted.height > 0


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/latest/meta-data",
        "https://waha.example.test.evil.invalid/api/files/Q1.jpg",
        "https://user:password@waha.example.test/api/files/Q1.jpg",
        "https://waha.example.test/api/sessions",
        "https://waha.example.test/api/files/%2e%2e/sessions",
    ],
)
def test_media_url_cannot_escape_the_configured_waha_file_endpoint(url: str) -> None:
    with pytest.raises(WahaMediaError) as raised:
        download(url)

    assert raised.value.status_code == 403


def test_redirect_is_not_followed() -> None:
    with respx.mock(assert_all_called=True) as routes:
        route = routes.get(MEDIA_URL).mock(
            return_value=httpx.Response(302, headers={"Location": "http://127.0.0.1/admin"})
        )

        with pytest.raises(WahaMediaError) as raised:
            download()

    assert raised.value.status_code == 502
    assert route.call_count == 1


def test_response_mime_must_be_jpeg() -> None:
    with respx.mock(assert_all_called=True) as routes:
        routes.get(MEDIA_URL).mock(
            return_value=httpx.Response(
                200,
                headers={"Content-Type": "text/html"},
                content=JPEG_FIXTURE,
            )
        )

        with pytest.raises(WahaMediaError) as raised:
            download()

    assert raised.value.status_code == 415


def test_download_rejects_content_larger_than_the_configured_limit() -> None:
    with respx.mock(assert_all_called=True) as routes:
        routes.get(MEDIA_URL).mock(
            return_value=httpx.Response(
                200,
                headers={"Content-Type": "image/jpeg"},
                content=b"x" * 33,
            )
        )

        with pytest.raises(WahaMediaError) as raised:
            download(max_bytes=32)

    assert raised.value.status_code == 413


def test_upstream_timeout_is_mapped_to_a_safe_gateway_error() -> None:
    with respx.mock(assert_all_called=True) as routes:
        routes.get(MEDIA_URL).mock(side_effect=httpx.ReadTimeout("sensitive upstream detail"))

        with pytest.raises(WahaMediaError) as raised:
            download()

    assert raised.value.status_code == 504
    assert "sensitive" not in str(raised.value).lower()


def test_non_jpeg_bytes_are_rejected_even_when_the_upstream_claims_jpeg() -> None:
    with respx.mock(assert_all_called=True) as routes:
        routes.get(MEDIA_URL).mock(
            return_value=httpx.Response(
                200,
                headers={"Content-Type": "image/jpeg"},
                content=b"not a jpeg",
            )
        )

        with pytest.raises(WahaMediaError) as raised:
            download()

    assert raised.value.status_code == 415
