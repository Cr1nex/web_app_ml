"""
FastAPI dependencies for the ML prediction API.

Auth: validates a Bearer JWT against the public keys cached in Redis by the
backend service. The backend's proxy router translates HttpOnly cookies into
Authorization headers before forwarding requests here, so the ML service only
needs to read from the header.
"""

from typing import Optional
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.configs.security import security_config
from src.core.security.jwt_verify import decode_token


_bearer = HTTPBearer(auto_error=False)


def get_redis(request: Request):
    return request.app.state.redis


def get_current_user_id(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> UUID:
    if not security_config.enable_auth:
        # Escape hatch for local dev / smoke tests; controlled by ML_AUTH_ENABLE_AUTH.
        return UUID("00000000-0000-0000-0000-000000000000")

    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="not_authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    redis_client = request.app.state.redis

    try:
        payload = decode_token(credentials.credentials, redis_client)
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid_token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        return UUID(payload["sub"])
    except (KeyError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid_token",
        )
