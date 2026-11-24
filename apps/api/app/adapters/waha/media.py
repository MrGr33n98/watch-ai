"""Bounded, same-origin media download from a configured WAHA instance."""

from __future__ import annotations

from urllib.parse import unquote

import httpx

from app.adapters.storage.jpeg import (
    DEFAULT_MAX_JPEG_BYTES,
    DEFAULT_MAX_JPEG_PIXELS,
    JpegAdmissionError,
    PillowJpegAdmission,
)
from app.domain.ingestion.images import AdmittedJpeg

MAX_WAHA_MEDIA_URL_LENGTH = 4096


class WahaMediaError(Exception):
    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code


class WahaMediaDownloader:
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        max_bytes: int = DEFAULT_MAX_JPEG_BYTES,
        max_pixels: int = DEFAULT_MAX_JPEG_PIXELS,
        timeout: httpx.Timeout | None = None,
    ) -> None:
        self._base_url = _configured_base_url(base_url)
        if not api_key.strip():
            raise ValueError("WAHA API key must not be empty")
        if isinstance(max_bytes, bool) or not 1 <= max_bytes <= DEFAULT_MAX_JPEG_BYTES:
            raise ValueError("WAHA media max_bytes must be between 1 byte and 8 MiB")
        if isinstance(max_pixels, bool) or not 1 <= max_pixels <= DEFAULT_MAX_JPEG_PIXELS:
            raise ValueError("WAHA media max_pixels exceeds the safe pixel limit")
        self._api_key = api_key
        self._max_bytes = max_bytes
        self._admission = PillowJpegAdmission(max_bytes=max_bytes, max_pixels=max_pixels)
        self._timeout = timeout or httpx.Timeout(15.0, connect=3.0)

    async def download(self, media_url: str, *, declared_mime: str) -> AdmittedJpeg:
        if declared_mime.split(";", maxsplit=1)[0].strip().lower() != "image/jpeg":
            raise WahaMediaError(415, "Only JPEG images are accepted")
        url = _validated_media_url(media_url, self._base_url)
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout,
                follow_redirects=False,
                trust_env=False,
            ) as client:
                async with client.stream(
                    "GET",
                    url,
                    headers={"X-Api-Key": self._api_key, "Accept": "image/jpeg"},
                ) as response:
                    content = await self._read_response(response)
        except WahaMediaError:
            raise
        except httpx.TimeoutException as error:
            raise WahaMediaError(504, "WAHA media download timed out") from error
        except httpx.HTTPError as error:
            raise WahaMediaError(502, "WAHA media download failed") from error

        try:
            return self._admission.admit(content, "image/jpeg")
        except JpegAdmissionError as error:
            raise WahaMediaError(error.status_code, str(error)) from error

    async def _read_response(self, response: httpx.Response) -> bytes:
        if 300 <= response.status_code < 400:
            raise WahaMediaError(502, "WAHA media redirects are not accepted")
        if response.status_code != 200:
            raise WahaMediaError(502, "WAHA media service returned an unexpected response")

        response_mime = response.headers.get("content-type", "")
        if response_mime.split(";", maxsplit=1)[0].strip().lower() != "image/jpeg":
            raise WahaMediaError(415, "WAHA media response is not a JPEG image")
        content_length = response.headers.get("content-length")
        if content_length is not None:
            try:
                declared_size = int(content_length)
            except ValueError as error:
                raise WahaMediaError(502, "WAHA media response has an invalid size") from error
            if declared_size < 0:
                raise WahaMediaError(502, "WAHA media response has an invalid size")
            if declared_size > self._max_bytes:
                raise WahaMediaError(413, "WAHA media exceeds the configured size limit")

        content = bytearray()
        async for chunk in response.aiter_bytes():
            if len(content) + len(chunk) > self._max_bytes:
                raise WahaMediaError(413, "WAHA media exceeds the configured size limit")
            content.extend(chunk)
        return bytes(content)


def _configured_base_url(value: str) -> httpx.URL:
    try:
        base_url = httpx.URL(value)
    except (TypeError, ValueError) as error:
        raise ValueError("WAHA base URL is invalid") from error
    if (
        not base_url.is_absolute_url
        or base_url.scheme not in {"http", "https"}
        or not base_url.host
        or base_url.username
        or base_url.password
        or base_url.query
        or base_url.fragment
        or base_url.path not in {"", "/"}
    ):
        raise ValueError("WAHA base URL must be an HTTP(S) origin without credentials or path")
    return base_url


def _validated_media_url(value: str, base_url: httpx.URL) -> httpx.URL:
    if not isinstance(value, str) or not value or len(value) > MAX_WAHA_MEDIA_URL_LENGTH:
        raise WahaMediaError(403, "WAHA media URL is not allowed")
    if any(ord(character) < 32 for character in value):
        raise WahaMediaError(403, "WAHA media URL is not allowed")
    try:
        media_url = httpx.URL(value)
    except (TypeError, ValueError) as error:
        raise WahaMediaError(403, "WAHA media URL is not allowed") from error

    if (
        not media_url.is_absolute_url
        or media_url.scheme != base_url.scheme
        or media_url.host.lower() != base_url.host.lower()
        or _effective_port(media_url) != _effective_port(base_url)
        or media_url.username
        or media_url.password
        or media_url.query
        or media_url.fragment
    ):
        raise WahaMediaError(403, "WAHA media URL is not allowed")

    decoded_path = unquote(media_url.path)
    if (
        not decoded_path.startswith("/api/files/")
        or "\\" in decoded_path
        or any(segment in {".", ".."} for segment in decoded_path.split("/"))
    ):
        raise WahaMediaError(403, "WAHA media URL is not allowed")
    return media_url


def _effective_port(url: httpx.URL) -> int:
    if url.port is not None:
        return url.port
    return 443 if url.scheme == "https" else 80
