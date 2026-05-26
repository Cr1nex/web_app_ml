import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID

from core.db.base import Base


class User(Base):
    __tablename__ = "users"

    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(50), nullable=False, unique=True, index=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class SessionToken(Base):
    __tablename__ = "session_tokens"

    session_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)


class AccessToken(Base):
    __tablename__ = "access_tokens"

    token_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False, index=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey("session_tokens.session_id"), nullable=False, index=True)
    token_hash = Column(String(64), nullable=False, index=True)
    issued_at = Column(DateTime(timezone=True), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    token_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False, index=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey("session_tokens.session_id"), nullable=False, index=True)
    token_hash = Column(String(64), nullable=False, index=True)
    issued_at = Column(DateTime(timezone=True), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    rotated_at = Column(DateTime(timezone=True), nullable=True)
    parent_id = Column(UUID(as_uuid=True), nullable=True)


class GameScore(Base):
    __tablename__ = "game_scores"

    score_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False, index=True)
    score = Column(Integer, nullable=False)
    game_name = Column(String(50), nullable=False, default="snake")
    played_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class RequestLog(Base):
    __tablename__ = "request_logs"

    request_id = Column(String(50), primary_key=True)
    user_id = Column(String(36), nullable=True)
    method = Column(String(10), nullable=False)
    path = Column(String(255), nullable=False)
    status_code = Column(Integer, nullable=False)
    duration_ms = Column(Integer, nullable=False)
    client_host = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
