from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session


def get_database_session(request: Request) -> Iterator[Session]:
    session_factory = request.app.state.session_factory
    if session_factory is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is not configured",
        )
    with session_factory() as database_session:
        yield database_session


DatabaseSession = Annotated[Session, Depends(get_database_session)]
