import json

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class APISettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    DATABASE_URL: str
    API_SECRET_KEY: str = "change-me"
    JWT_EXPIRE_MINUTES: int = 1440
    BOT_TOKEN: str
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, list):
            return value
        if not isinstance(value, str):
            return ["http://localhost:5173", "http://localhost:3000"]

        raw = value.strip()
        if not raw:
            return []

        if raw.startswith("["):
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                parsed = None
            if isinstance(parsed, list):
                return [str(item).strip() for item in parsed if str(item).strip()]

            trimmed = raw.strip("[]")
            return [item.strip().strip("\"'") for item in trimmed.split(",") if item.strip()]

        return [item.strip() for item in raw.split(",") if item.strip()]


api_settings = APISettings()
