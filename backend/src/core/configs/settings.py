

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "backend-service"
    env: str = "dev"
    api_v1_prefix: str = "/api/v1"

    db_host: str = "db"
    db_port: int = 5432
    db_name: str = "appdb"
    db_user: str = "appuser"
    db_password: str = "apppassword"
    database_url: str | None = None

    redis_url: str = "redis://redis:6379/0"
    rabbitmq_url: str = "amqp://guest:guest@rabbitmq:5672/"
    ml_service_url: str = "http://ml-service:5002"

    jwt_issuer: str = "backend"
    jwt_audience: str = "backend-users"
    jwt_key_id: str = "backend-1"
    jwt_private_key: str | None = None
    jwt_access_ttl_minutes: int = 15
    jwt_refresh_ttl_days: int = 7
    jwt_key_rotation_days: int = 30
    jwt_retired_public_key_ttl_days: int = 45
    jwt_redis_prefix: str = "jwt:keys"
    jwks_cache_ttl_seconds: int = 3600

    @property
    def db_url(self) -> str:
        if self.database_url:
            return self.database_url
        return (
            f"postgresql+psycopg2://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


settings = Settings()
