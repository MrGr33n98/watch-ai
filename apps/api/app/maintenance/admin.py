"""Operator CLI for user provisioning, watch pairing codes, and remote revocation."""

from __future__ import annotations

import argparse
import os
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.adapters.db.delivery import SqlAlchemyDeliveryRepository
from app.adapters.db.models import UserRecord
from app.application.pairing import PairingService


def _engine_and_sessions() -> tuple[object, sessionmaker[Session]]:
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        raise RuntimeError("DATABASE_URL is required")
    engine = create_engine(database_url, pool_pre_ping=True)
    return engine, sessionmaker(bind=engine, expire_on_commit=False)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Watch AI operator administration CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("bootstrap-user", help="Create a new study user UUID")

    pair_cmd = subparsers.add_parser("create-pairing-code", help="Generate a watch pairing code")
    pair_cmd.add_argument("--user-id", type=UUID, required=True)
    pair_cmd.add_argument("--ttl-minutes", type=int, default=10)

    list_cmd = subparsers.add_parser("list-devices", help="List paired watch devices for a user")
    list_cmd.add_argument("--user-id", type=UUID, required=True)

    revoke_cmd = subparsers.add_parser("revoke-device", help="Revoke a paired or lost watch")
    revoke_cmd.add_argument("--user-id", type=UUID, required=True)
    revoke_cmd.add_argument("--device-id", type=UUID, required=True)

    args = parser.parse_args(argv)
    engine, sessions = _engine_and_sessions()
    try:
        if args.command == "bootstrap-user":
            user_id = uuid4()
            with sessions.begin() as db:
                db.add(UserRecord(id=user_id))
            print(f"user_id={user_id}")
            return 0

        if args.command == "create-pairing-code":
            now = datetime.now(UTC)
            expires = now + timedelta(minutes=max(1, min(args.ttl_minutes, 60)))
            with sessions() as db:
                repo = SqlAlchemyDeliveryRepository(db)
                if not repo.user_exists(args.user_id):
                    raise SystemExit(f"User {args.user_id} was not found")
                code = PairingService(repo).create_pairing_code(
                    args.user_id,
                    expires_at=expires,
                    now=now,
                )
            print(f"pairing_code={code} expires_at={expires.isoformat()}")
            return 0

        if args.command == "list-devices":
            with sessions() as db:
                devices = PairingService(SqlAlchemyDeliveryRepository(db)).list_devices(
                    args.user_id
                )
            for device in devices:
                status = "revoked" if device.revoked_at is not None else "active"
                print(
                    f"{device.device_id} {device.device_name!r} "
                    f"status={status} expires_at={device.expires_at.isoformat()}"
                )
            return 0

        if args.command == "revoke-device":
            with sessions() as db:
                ok = PairingService(SqlAlchemyDeliveryRepository(db)).revoke_device(
                    args.device_id,
                    args.user_id,
                )
            if not ok:
                raise SystemExit("Device not found or already revoked")
            print(f"revoked device_id={args.device_id}")
            return 0

        return 1
    finally:
        engine.dispose()  # type: ignore[attr-defined]


if __name__ == "__main__":
    raise SystemExit(main())
