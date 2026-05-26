import uuid
from datetime import datetime, timedelta, timezone

import jwt

from core.configs.settings import settings
from core.security.jwks import get_public_key_by_kid, get_signing_key


def create_access_token(redis_client, user_id, session_id):

    kid, private_key = get_signing_key(redis_client)
    token_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    expires = now + timedelta(minutes=settings.jwt_access_ttl_minutes)
    payload = {
        "sub": str(user_id),
        "sid": str(session_id),
        "jti": str(token_id),
        "type": "access",
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "iat": int(now.timestamp()),
        "exp": int(expires.timestamp()),
    }
    token = jwt.encode(
        payload,
        private_key,
        algorithm="RS256",
        headers={"kid": kid},
    )
    return token, token_id, expires


def create_refresh_token(redis_client, user_id, session_id, parent_id=None):

    kid, private_key = get_signing_key(redis_client)
    token_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    expires = now + timedelta(days=settings.jwt_refresh_ttl_days)
    payload = {
        "sub": str(user_id),
        "sid": str(session_id),
        "jti": str(token_id),
        "type": "refresh",
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "iat": int(now.timestamp()),
        "exp": int(expires.timestamp()),
    }
    if parent_id:
        payload["parent"] = str(parent_id)
    token = jwt.encode(
        payload,
        private_key,
        algorithm="RS256",
        headers={"kid": kid},
    )
    return token, token_id, expires


def decode_token(token: str, redis_client) -> dict:

    header = jwt.get_unverified_header(token)
    kid = header.get("kid")
    if not kid:
        raise jwt.InvalidTokenError("missing_kid")

    public_key = get_public_key_by_kid(redis_client, kid)
    return jwt.decode(
        token,
        public_key,
        algorithms=["RS256"],
        audience=settings.jwt_audience,
        issuer=settings.jwt_issuer,
    )
