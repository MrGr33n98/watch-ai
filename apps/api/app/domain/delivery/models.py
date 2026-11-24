"""Opaque watch credentials and identity values."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

WATCH_READ_SCOPE = "sessions:read"


class PairingCodeRejected(ValueError):
    """Raised for an unknown, expired, or already redeemed pairing code."""


@dataclass(frozen=True, slots=True)
class WatchCredential:
    device_id: UUID
    user_id: UUID
    access_token: str
    scope: str
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class WatchDevice:
    device_id: UUID
    user_id: UUID
    scope: str
