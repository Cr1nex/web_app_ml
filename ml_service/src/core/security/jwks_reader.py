"""
Read-only JWKS lookup against the backend's Redis-cached public keys.

Mirrors `backend/src/core/security/jwks.py:get_public_key_by_kid` — same Redis
key layout (`{prefix}:kid:{kid}:public` storing a JSON-serialised JWK).
"""

import jwt
from jwt.algorithms import RSAAlgorithm

from src.configs.security import security_config


def _public_key_redis_key(kid: str) -> str:
    return f"{security_config.jwt_redis_prefix}:kid:{kid}:public"


def _to_str(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return str(value)


def get_public_key_by_kid(redis_client, kid: str):
    public_jwk_raw = _to_str(redis_client.get(_public_key_redis_key(kid)))
    if not public_jwk_raw:
        raise jwt.InvalidTokenError(f"unknown_kid:{kid}")
    return RSAAlgorithm.from_jwk(public_jwk_raw)
