"""Best-effort WAHA text reply client for sender batch status feedback."""

from __future__ import annotations

import logging
from urllib.parse import urlsplit

import httpx

_WAHA_REPLY_LOGGER = logging.getLogger("watch_ai.waha.reply")


class WahaReplyClient:
    """Send concise status replies back to an authorized WhatsApp sender via WAHA."""

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        client: httpx.AsyncClient | None = None,
        timeout_seconds: float = 3.0,
    ) -> None:
        parsed = urlsplit(base_url.strip())
        if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
            raise ValueError("WAHA base URL must include an HTTP(S) host")
        if not api_key.strip():
            raise ValueError("WAHA API key must not be empty")
        self._endpoint = f"{parsed.scheme.lower()}://{parsed.netloc}/api/sendText"
        self._api_key = api_key
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(
            timeout=httpx.Timeout(timeout_seconds),
            follow_redirects=False,
            trust_env=False,
        )

    async def send_text(self, *, session: str, chat_id: str, text: str) -> bool:
        try:
            response = await self._client.post(
                self._endpoint,
                headers={"X-Api-Key": self._api_key, "Content-Type": "application/json"},
                json={"session": session, "chatId": chat_id, "text": text},
            )
            return response.is_success
        except httpx.HTTPError:
            _WAHA_REPLY_LOGGER.warning("waha_reply_failed")
            return False

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()
