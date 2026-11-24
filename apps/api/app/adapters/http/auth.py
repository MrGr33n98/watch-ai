from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.adapters.db.delivery import SqlAlchemyDeliveryRepository
from app.adapters.http.database import DatabaseSession


@dataclass(frozen=True, slots=True)
class WatchPrincipal:
    user_id: UUID
    device_id: UUID
    scopes: frozenset[str] = frozenset()


_bearer_auth = HTTPBearer(auto_error=False, scheme_name="bearerAuth")


def require_watch_principal(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_auth)],
    database: DatabaseSession,
) -> WatchPrincipal:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Watch authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token_hash = sha256(credentials.credentials.encode("utf-8")).hexdigest()
    device = SqlAlchemyDeliveryRepository(database).find_active_device(
        token_hash,
        datetime.now(UTC),
    )
    if device is None or device.scope != "sessions:read":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Watch credentials are invalid or expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return WatchPrincipal(
        user_id=device.user_id,
        device_id=device.device_id,
        scopes=frozenset({device.scope}),
    )
