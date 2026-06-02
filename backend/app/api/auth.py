from __future__ import annotations

import hashlib
import secrets
from typing import Annotated

from fastapi import HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.app.config import MissingConfigurationError, load_dev_token

bearer_scheme = HTTPBearer(auto_error=False)


def dev_token_subject(token: str) -> str:
    """A stable, non-secret subject identifier for an authenticated dev token.

    The dev token is a single shared bearer secret, so there is no per-user identity;
    this derives a deterministic principal id from the token — rotating when the token
    rotates — for use as the audit ``actor`` (API-07). It hashes the token so the raw
    secret is never written to the audit log.
    """
    fingerprint = hashlib.sha256(token.encode("utf-8")).hexdigest()[:12]
    return f"dev:{fingerprint}"


def require_dev_token(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Security(bearer_scheme)],
) -> str:
    """Validate the bearer dev token and return its audit subject (API-07).

    Returns the token subject so handlers can attribute audit events to the
    authenticated caller (``actor = Depends(require_dev_token)``) instead of a
    hardcoded placeholder. Still raises 401/500 on a missing/invalid token or
    misconfiguration, so it doubles as the router-level auth gate.

    Handlers wire this as BOTH the router-level gate and an injected ``subject``
    param; FastAPI's default ``use_cache=True`` keys both to one entry so it runs
    exactly once per request. Don't wrap it in a lambda or pass ``use_cache=False``
    (that would create a distinct cache key and validate the token twice).
    """
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        expected_token = load_dev_token()
    except MissingConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    if not secrets.compare_digest(credentials.credentials, expected_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return dev_token_subject(credentials.credentials)
