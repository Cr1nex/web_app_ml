from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.db.models import AccessToken, RefreshToken, SessionToken


class TokenRepo:
    def __init__(self, db: Session):
        self.db = db

    def create_session(self, user_id: UUID) -> SessionToken:
        session = SessionToken(user_id=user_id)
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def create_access_token(
        self,
        token_id: UUID,
        user_id: UUID,
        session_id: UUID,
        token_hash: str,
        issued_at: datetime,
        expires_at: datetime,
    ) -> AccessToken:
        access = AccessToken(
            token_id=token_id,
            user_id=user_id,
            session_id=session_id,
            token_hash=token_hash,
            issued_at=issued_at,
            expires_at=expires_at,
        )
        self.db.add(access)
        self.db.commit()
        self.db.refresh(access)
        return access

    def create_refresh_token(
        self,
        token_id: UUID,
        user_id: UUID,
        session_id: UUID,
        token_hash: str,
        issued_at: datetime,
        expires_at: datetime,
        parent_id: UUID | None = None,
    ) -> RefreshToken:
        refresh = RefreshToken(
            token_id=token_id,
            user_id=user_id,
            session_id=session_id,
            token_hash=token_hash,
            issued_at=issued_at,
            expires_at=expires_at,
            parent_id=parent_id,
        )
        self.db.add(refresh)
        self.db.commit()
        self.db.refresh(refresh)
        return refresh

    def get_refresh_token(self, token_id: UUID) -> RefreshToken | None:
        stmt = select(RefreshToken).where(RefreshToken.token_id == token_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def rotate_refresh_token(self, token_id: UUID, rotated_at: datetime) -> RefreshToken | None:
        refresh = self.get_refresh_token(token_id)
        if not refresh:
            return None

        refresh.revoked_at = rotated_at
        refresh.rotated_at = rotated_at
        self.db.commit()
        self.db.refresh(refresh)
        return refresh

