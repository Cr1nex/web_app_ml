import json
import time
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt.algorithms import RSAAlgorithm

from core.configs.settings import settings


def _to_str(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return str(value)


def _prefix() -> str:
    return settings.jwt_redis_prefix


def _active_kid_key() -> str:
    return f"{_prefix()}:active_kid"


def _public_kids_key() -> str:
    return f"{_prefix()}:public_kids"


def _rotate_lock_key() -> str:
    return f"{_prefix()}:rotate_lock"


def _private_key_key(kid: str) -> str:
    return f"{_prefix()}:kid:{kid}:private"


def _public_key_key(kid: str) -> str:
    return f"{_prefix()}:kid:{kid}:public"


def _created_at_key(kid: str) -> str:
    return f"{_prefix()}:kid:{kid}:created_at"


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _build_rotated_kid() -> str:

    stamp = _now_utc().strftime("%Y%m%d")
    rand = uuid.uuid4().hex[:8]
    return f"{settings.jwt_key_id}-{stamp}-{rand}"


def _load_private_key(pem_data: str):
    return serialization.load_pem_private_key(pem_data.encode("utf-8"), password=None)


def _serialize_private_key(private_key) -> str:
    pem_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return pem_bytes.decode("utf-8")


def _build_public_jwk(private_key, kid: str) -> dict:
    jwk = json.loads(RSAAlgorithm.to_jwk(private_key.public_key()))
    jwk.update({"kid": kid, "use": "sig", "alg": "RS256"})
    return jwk


def _read_created_at(redis_client, kid: str) -> datetime | None:
    raw = _to_str(redis_client.get(_created_at_key(kid)))
    if not raw:
        return None
    try:
        return datetime.fromtimestamp(int(raw), tz=timezone.utc)
    except (TypeError, ValueError, OSError):
        return None


def _is_rotation_due(redis_client, kid: str) -> bool:

    created_at = _read_created_at(redis_client, kid)
    if created_at is None:
        return True
    return _now_utc() >= created_at + timedelta(days=settings.jwt_key_rotation_days)


def _store_key_material(redis_client, kid: str, private_pem: str, public_jwk: dict, created_at_ts: int) -> None:
    pipe = redis_client.pipeline()
    pipe.set(_private_key_key(kid), private_pem)
    pipe.set(_public_key_key(kid), json.dumps(public_jwk))
    pipe.set(_created_at_key(kid), str(created_at_ts))
    pipe.sadd(_public_kids_key(), kid)
    pipe.set(_active_kid_key(), kid)
    pipe.execute()


def _retire_key_material(redis_client, kid: str) -> None:

    ttl_seconds = settings.jwt_retired_public_key_ttl_days * 24 * 60 * 60

    pipe = redis_client.pipeline()
    pipe.delete(_private_key_key(kid))
    pipe.expire(_public_key_key(kid), ttl_seconds)
    pipe.expire(_created_at_key(kid), ttl_seconds)
    pipe.execute()


def _prune_missing_public_kids(redis_client) -> list[str]:
    kids = sorted(_to_str(k) for k in redis_client.smembers(_public_kids_key()) if k is not None)
    valid_kids: list[str] = []

    for kid in kids:
        if redis_client.get(_public_key_key(kid)):
            valid_kids.append(kid)
        else:
            redis_client.srem(_public_kids_key(), kid)

    return valid_kids


def _rotate_signing_key(redis_client, previous_kid: str | None) -> tuple[str, object]:

    now_ts = int(_now_utc().timestamp())

    if previous_kid is None and settings.jwt_private_key:
        kid = settings.jwt_key_id
        private_pem = settings.jwt_private_key.replace("\\n", "\n")
        private_key = _load_private_key(private_pem)
    else:
        kid = _build_rotated_kid() if previous_kid else settings.jwt_key_id
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        private_pem = _serialize_private_key(private_key)

    public_jwk = _build_public_jwk(private_key, kid)
    _store_key_material(redis_client, kid, private_pem, public_jwk, now_ts)

    if previous_kid and previous_kid != kid:
        _retire_key_material(redis_client, previous_kid)

    return kid, private_key


def get_signing_key(redis_client) -> tuple[str, object]:
    active_kid = _to_str(redis_client.get(_active_kid_key()))

    if active_kid:
        private_pem = _to_str(redis_client.get(_private_key_key(active_kid)))
        if private_pem and not _is_rotation_due(redis_client, active_kid):
            return active_kid, _load_private_key(private_pem)

    lock_acquired = bool(redis_client.set(_rotate_lock_key(), "1", nx=True, ex=15))
    if not lock_acquired:
        for _ in range(5):
            active_kid = _to_str(redis_client.get(_active_kid_key()))
            private_pem = _to_str(redis_client.get(_private_key_key(active_kid))) if active_kid else None
            if active_kid and private_pem:
                return active_kid, _load_private_key(private_pem)
            time.sleep(0.1)

        raise RuntimeError("jwt_signing_key_unavailable")

    try:
        current_kid = _to_str(redis_client.get(_active_kid_key()))
        if current_kid:
            private_pem = _to_str(redis_client.get(_private_key_key(current_kid)))
            if private_pem and not _is_rotation_due(redis_client, current_kid):
                return current_kid, _load_private_key(private_pem)

        return _rotate_signing_key(redis_client, current_kid)
    finally:
        redis_client.delete(_rotate_lock_key())


def get_public_key_by_kid(redis_client, kid: str):
    public_jwk_raw = _to_str(redis_client.get(_public_key_key(kid)))
    if not public_jwk_raw:
        raise jwt.InvalidTokenError(f"unknown_kid:{kid}")

    return RSAAlgorithm.from_jwk(public_jwk_raw)


def get_cached_jwks(redis_client) -> dict:
    # Ensure at least one active key exists so JWKS is always usable.
    get_signing_key(redis_client)

    keys = []
    for kid in _prune_missing_public_kids(redis_client):
        public_jwk_raw = _to_str(redis_client.get(_public_key_key(kid)))
        if not public_jwk_raw:
            continue
        keys.append(json.loads(public_jwk_raw))

    return {"keys": keys}
