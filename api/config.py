from pydantic_settings import BaseSettings, SettingsConfigDict


class APISettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    DATABASE_URL: str
    API_SECRET_KEY: str = "change-me"
    JWT_EXPIRE_MINUTES: int = 1440
    BOT_TOKEN: str
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    @property
    def cors_origins(self) -> list[str]:
        raw = self.CORS_ORIGINS.strip()
        if not raw:
            return []

        if raw.startswith("[") and raw.endswith("]"):
            raw = raw[1:-1]

        return [
            item.strip().strip("\"'")
            for item in raw.split(",")
            if item.strip().strip("\"'")
        ]


api_settings = APISettings()
