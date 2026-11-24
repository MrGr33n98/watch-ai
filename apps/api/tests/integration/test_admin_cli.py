from __future__ import annotations

from pathlib import Path
from uuid import UUID

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.adapters.db.base import Base
from app.adapters.db.delivery import SqlAlchemyDeliveryRepository
from app.adapters.db.models import PairingCodeRecord, UserRecord, WatchDeviceRecord
from app.application.pairing import PairingService
from app.maintenance import admin as admin_cli


def test_admin_cli_bootstraps_user_issues_code_lists_and_revokes_device(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    db_path = tmp_path / "cli.sqlite3"
    db_url = f"sqlite+pysqlite:///{db_path}"
    engine = create_engine(db_url)
    Base.metadata.create_all(
        engine,
        tables=[UserRecord.__table__, PairingCodeRecord.__table__, WatchDeviceRecord.__table__],
    )
    sessions = sessionmaker(bind=engine, expire_on_commit=False)

    monkeypatch.setenv("DATABASE_URL", db_url)

    assert admin_cli.main(["bootstrap-user"]) == 0
    out_user = capsys.readouterr().out.strip()
    user_id = out_user.split("user_id=")[1]

    assert admin_cli.main(["create-pairing-code", "--user-id", user_id]) == 0
    out_code = capsys.readouterr().out.strip()
    code = out_code.split("pairing_code=")[1].split()[0]

    with sessions() as db:
        cred = PairingService(SqlAlchemyDeliveryRepository(db)).pair(code, "Watch4 CLI")

    assert admin_cli.main(["list-devices", "--user-id", user_id]) == 0
    listed = capsys.readouterr().out
    assert str(cred.device_id) in listed
    assert "status=active" in listed

    assert (
        admin_cli.main(
            [
                "revoke-device",
                "--user-id",
                user_id,
                "--device-id",
                str(cred.device_id),
            ]
        )
        == 0
    )
    assert "revoked" in capsys.readouterr().out

    assert admin_cli.main(["list-devices", "--user-id", user_id]) == 0
    listed_after = capsys.readouterr().out
    assert "status=revoked" in listed_after
    assert UUID(user_id)
    engine.dispose()
