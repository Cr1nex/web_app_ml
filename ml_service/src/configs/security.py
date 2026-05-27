"""
Auth / JWT verification configuration for the ML service.

Environment variables (env_prefix = ML_AUTH_):
    ML_AUTH_REDIS_URL          — Redis URL where the backend stores RSA public keys
    ML_AUTH_JWT_ISSUER         — expected `iss` claim
    ML_AUTH_JWT_AUDIENCE       — expected `aud` claim
    ML_AUTH_JWT_REDIS_PREFIX   — Redis key prefix for the JWKS store
    ML_AUTH_ENABLE_AUTH        — toggle auth on prediction endpoints

The defaults match the backend's defaults so the two services share a trust root
out-of-the-box when wired into the same docker network.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class SecurityConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="ML_AUTH_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    redis_url: str = "redis://redis:6379/0"
    jwt_issuer: str = "backend"
    jwt_audience: str = "backend-users"
    jwt_redis_prefix: str = "jwt:keys"
    enable_auth: bool = True


security_config = SecurityConfig()
