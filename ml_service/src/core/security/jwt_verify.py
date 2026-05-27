"""
JWT decode helper — mirrors `backend/src/core/security/jwt.py:decode_token`
but uses the read-only JWKS reader, since the ML service never signs tokens.
"""

import jwt

from src.configs.security import security_config
from src.core.security.jwks_reader import get_public_key_by_kid


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
        audience=security_config.jwt_audience,
        issuer=security_config.jwt_issuer,
    )
