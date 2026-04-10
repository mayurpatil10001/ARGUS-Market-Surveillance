"""
api/auth.py — Shared JWT authentication dependency.
Extracted to avoid circular imports with api.main.
"""
from __future__ import annotations

import os
from typing import Optional
from fastapi import Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

JWT_SECRET = os.getenv("JWT_SECRET", "argus-dev-secret-change-in-prod")
JWT_ALGORITHM = "HS256"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


def _decode_token(token: str) -> dict:
    """Shared JWT decode logic — raises HTTP 401 on failure."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        username: str = payload.get("sub", "")
        if not username:
            raise credentials_exception
        return {"username": username}
    except JWTError:
        raise credentials_exception


def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """FastAPI dependency: validates JWT from Authorization header."""
    return _decode_token(token)


def get_current_user_sse(
    token: Optional[str] = Query(None, description="Bearer token for SSE (EventSource cannot set headers)"),
) -> dict:
    """FastAPI dependency for SSE endpoints: reads JWT from ?token= query param.

    Browsers cannot set custom headers on EventSource connections, so the
    frontend passes the JWT as a query parameter instead.
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing token query parameter",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return _decode_token(token)
