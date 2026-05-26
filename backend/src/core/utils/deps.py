from uuid import UUID
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from core.security.jwt import decode_token

_bearer = HTTPBearer(auto_error=False)  # auto_error=False so cookie-only requests don't 401 immediately


def get_redis(request: Request):
    return request.app.state.redis


def get_current_user_id(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> UUID:
    """
    Resolve the caller's user_id from either:
      1. HttpOnly cookie  `access_token`  (web browser)
      2. Authorization: Bearer <token>    (mobile / API clients)
    Cookies take precedence when both are present.
    """
    redis_client = request.app.state.redis

    # 1. Cookie (web)
    token = request.cookies.get("access_token")

    # 2. Bearer header (mobile)
    if not token and credentials:
        token = credentials.credentials

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="not_authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_token(token, redis_client)
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid_token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = UUID(payload["sub"])
        request.state.user_id = str(user_id)
        return user_id
    except (KeyError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid_token",
        )
