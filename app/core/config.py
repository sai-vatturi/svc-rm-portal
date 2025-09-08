from functools import lru_cache
from typing import List

from pydantic import AnyHttpUrl, BaseModel, Field
from pydantic.functional_validators import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "RM Release Portal API"
    APP_ENV: str = "dev"
    APP_PORT: int = 8000

    MONGO_URI: str = "mongodb://localhost:27017"
    MONGO_DB_NAME: str = "rm_release_portal"

    CORS_ORIGINS: List[AnyHttpUrl] | List[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ]
    )

    JWT_SECRET: str = "change-me-in-prod"
    JWT_ALG: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7

    ADMIN_REGISTRATION_ENABLED: bool = True

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, env_file_encoding="utf-8")

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def split_cors_origins(cls, v):  # type: ignore[no-untyped-def]
        if isinstance(v, str):
            return [s.strip() for s in v.split(",") if s.strip()]
        return v


@lru_cache
def get_settings() -> "Settings":
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
