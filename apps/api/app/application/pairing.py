"""Use cases for one-time watch pairing and scoped opaque credentials."""

import secrets
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from uuid import UUID, uuid4

from app.application.ports import DeliveryRepository
from app.domain.delivery.models import (
    WATCH_READ_SCOPE,
    PairingCodeRejected,
    WatchCredential,
    WatchDeviceSummary,
)

_PAIRING_ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
_PAIRING_LENGTH = 8


class PairingService:
    def __init__(self, repository: DeliveryRepository) -> None:
        self._repository = repository

    def create_pairing_code(
        self,
        user_id: UUID,
        *,
        expires_at: datetime | None = None,
        now: datetime | None = None,
    ) -> str:
        current_time = now or datetime.now(UTC)
        expiration = expires_at or (current_time + timedelta(minutes=5))
        if current_time.utcoffset() is None or expiration.utcoffset() is None:
            raise ValueError("Pairing timestamps must be timezone-aware")
        if expiration <= current_time:
            raise ValueError("Pairing code expiration must be in the future")

        code = "".join(secrets.choice(_PAIRING_ALPHABET) for _ in range(_PAIRING_LENGTH))
        self._repository.add_pairing_code(
            user_id,
            self._hash(code),
            current_time,
            expiration,
        )
        return code

    def pair(
        self,
        pairing_code: str,
        device_name: str,
        *,
        now: datetime | None = None,
    ) -> WatchCredential:
        current_time = now or datetime.now(UTC)
        if current_time.utcoffset() is None:
            raise ValueError("Pairing timestamp must be timezone-aware")
        normalized_name = device_name.strip()
        if not normalized_name or len(normalized_name) > 120:
            raise ValueError("Device name must contain 1 to 120 characters")
        normalized_code = _normalize_pairing_code(pairing_code)
        if not normalized_code:
            raise PairingCodeRejected("Pairing code is invalid or expired")

        access_token = secrets.token_urlsafe(32)
        device_id = uuid4()
        expires_at = current_time + timedelta(days=30)
        user_id = self._repository.redeem_pairing_code(
            self._hash(normalized_code),
            device_id,
            normalized_name,
            self._hash(access_token),
            current_time,
            expires_at,
        )
        if user_id is None:
            raise PairingCodeRejected("Pairing code is invalid, expired, or already used")
        return WatchCredential(
            device_id=device_id,
            user_id=user_id,
            access_token=access_token,
            scope=WATCH_READ_SCOPE,
            expires_at=expires_at,
        )

    def list_devices(self, user_id: UUID) -> Sequence[WatchDeviceSummary]:
        return self._repository.list_devices(user_id)

    def revoke_device(self, device_id: UUID, user_id: UUID, *, now: datetime | None = None) -> bool:
        return self._repository.revoke_device(device_id, user_id, now or datetime.now(UTC))

    @staticmethod
    def _hash(secret: str) -> str:
        return sha256(secret.encode("utf-8")).hexdigest()


def _normalize_pairing_code(raw: str) -> str:
    return raw.strip().upper().replace("-", "").replace(" ", "")
