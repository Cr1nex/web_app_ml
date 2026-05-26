from uuid import UUID

import jwt
from fastapi import HTTPException, status

from core.security.jwt import create_access_token, create_refresh_token, decode_token
from core.utils.hashing import hash_token
from core.utils.time import utc_now
from models.token import TokenPair
from repos.token_repo import TokenRepo


class TokenService:
    def __init__(self, db, redis_client):
        self.db = db
        self.redis = redis_client
        self.repo = TokenRepo(db)

    def issue_token_pair(self, user_id: UUID, session_id: UUID | None = None, parent_id: UUID | None = None):
        now = utc_now()
        if session_id is None:
            session = self.repo.create_session(user_id)
            session_id = session.session_id

        access_token, access_id, access_expires = create_access_token(self.redis, user_id, session_id)
        refresh_token, refresh_id, refresh_expires = create_refresh_token(
            self.redis,
            user_id,
            session_id,
            parent_id=parent_id,
        )

        self.repo.create_access_token(
            token_id=access_id,
            user_id=user_id,
            session_id=session_id,
            token_hash=hash_token(access_token),
            issued_at=now,
            expires_at=access_expires,
        )
        self.repo.create_refresh_token(
            token_id=refresh_id,
            user_id=user_id,
            session_id=session_id,
            token_hash=hash_token(refresh_token),
            issued_at=now,
            expires_at=refresh_expires,
            parent_id=parent_id,
        )

        access_ttl = int((access_expires - now).total_seconds())

        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=access_ttl,
        )

    def rotate_refresh_token(self, refresh_token: str) -> TokenPair:
        try:
            payload = decode_token(refresh_token, self.redis)
        except jwt.PyJWTError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_token")

        if payload.get("type") != "refresh":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_token")

        try:
            token_id = UUID(payload["jti"])
            session_id = UUID(payload["sid"])
            user_id = UUID(payload["sub"])
        except (KeyError, ValueError):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_token")

        stored = self.repo.get_refresh_token(token_id)
        if not stored or stored.revoked_at:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="token_revoked")

        if hash_token(refresh_token) != stored.token_hash:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_token")

        now = utc_now()
        self.repo.rotate_refresh_token(token_id, rotated_at=now)

        return self.issue_token_pair(user_id, session_id=session_id, parent_id=token_id)
