from __future__ import annotations

from typing import Annotated

from fastapi import HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.app.config import MissingConfigurationError, load_config

bearer_scheme = HTTPBearer(auto_error=False)


def require_dev_token(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Security(bearer_scheme)],
) -> None:
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        expected_token = load_config()["DEV_TOKEN"]
    except MissingConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    if credentials.credentials != expected_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
