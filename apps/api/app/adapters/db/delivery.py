"""PostgreSQL persistence for one-time pairing and watch credentials."""

from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.adapters.db.models import PairingCodeRecord, UserRecord, WatchDeviceRecord
from app.application.ports import DeliveryRepository
from app.domain.delivery.models import WATCH_READ_SCOPE, WatchDevice, WatchDeviceSummary


class SqlAlchemyDeliveryRepository(DeliveryRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def user_exists(self, user_id: UUID) -> bool:
        return self._session.get(UserRecord, user_id) is not None

    def add_pairing_code(
        self,
        user_id: UUID,
        code_hash: str,
        created_at: datetime,
        expires_at: datetime,
    ) -> None:
        self._session.add(
            PairingCodeRecord(
                user_id=user_id,
                code_hash=code_hash,
                created_at=created_at,
                expires_at=expires_at,
            )
        )
        self._session.commit()

    def redeem_pairing_code(
        self,
        code_hash: str,
        device_id: UUID,
        device_name: str,
        token_hash: str,
        created_at: datetime,
        expires_at: datetime,
    ) -> UUID | None:
        statement = (
            update(PairingCodeRecord)
            .where(
                PairingCodeRecord.code_hash == code_hash,
                PairingCodeRecord.consumed_at.is_(None),
                PairingCodeRecord.expires_at > created_at,
            )
            .values(consumed_at=created_at)
            .returning(PairingCodeRecord.user_id)
        )
        user_id = self._session.execute(statement).scalar_one_or_none()
        if user_id is None:
            return None
        self._session.add(
            WatchDeviceRecord(
                id=device_id,
                user_id=user_id,
                device_name=device_name,
                token_hash=token_hash,
                scope=WATCH_READ_SCOPE,
                created_at=created_at,
                expires_at=expires_at,
            )
        )
        self._session.commit()
        return user_id

    def find_active_device(self, token_hash: str, now: datetime) -> WatchDevice | None:
        device = self._session.scalar(
            select(WatchDeviceRecord).where(
                WatchDeviceRecord.token_hash == token_hash,
                WatchDeviceRecord.scope == WATCH_READ_SCOPE,
                WatchDeviceRecord.revoked_at.is_(None),
                WatchDeviceRecord.expires_at > now,
            )
        )
        if device is None:
            return None
        return WatchDevice(
            device_id=device.id,
            user_id=device.user_id,
            scope=device.scope,
        )

    def list_devices(self, user_id: UUID) -> Sequence[WatchDeviceSummary]:
        records = self._session.scalars(
            select(WatchDeviceRecord)
            .where(WatchDeviceRecord.user_id == user_id)
            .order_by(WatchDeviceRecord.created_at.desc(), WatchDeviceRecord.id.desc())
        ).all()
        return tuple(
            WatchDeviceSummary(
                device_id=record.id,
                user_id=record.user_id,
                device_name=record.device_name,
                scope=record.scope,
                created_at=_aware_utc(record.created_at),
                expires_at=_aware_utc(record.expires_at),
                revoked_at=(
                    _aware_utc(record.revoked_at) if record.revoked_at is not None else None
                ),
            )
            for record in records
        )

    def revoke_device(self, device_id: UUID, user_id: UUID, now: datetime) -> bool:
        revoked_id = self._session.execute(
            update(WatchDeviceRecord)
            .where(
                WatchDeviceRecord.id == device_id,
                WatchDeviceRecord.user_id == user_id,
                WatchDeviceRecord.revoked_at.is_(None),
            )
            .values(revoked_at=now)
            .returning(WatchDeviceRecord.id)
        ).scalar_one_or_none()
        if revoked_id is not None:
            self._session.commit()
            return True
        return False


def _aware_utc(value: datetime) -> datetime:
    if value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
