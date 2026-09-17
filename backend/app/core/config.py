from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_ENV: str = "development"
    APP_NAME: str = "SafeZone API"
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000

    # Database (Defaults to local SQLite for frictionless zero-config review & execution)
    DATABASE_URL: str = "sqlite+aiosqlite:///./safezone.db"

    # Security & JWT
    JWT_SECRET_KEY: str = "change_this_to_a_secure_random_secret_key_in_production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # CORS
    ALLOWED_ORIGINS: str = "*"

    # External Integrations
    FIREBASE_CREDENTIALS_PATH: str | None = None
    OSRM_ROUTING_URL: str = "http://router.project-osrm.org"

    # Operational Parameters
    COVERAGE_RADIUS_KM: float = 3.0
    RISK_RECENCY_LAMBDA: float = 0.05

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origins(self) -> list[str]:
        if not self.ALLOWED_ORIGINS:
            return []
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
