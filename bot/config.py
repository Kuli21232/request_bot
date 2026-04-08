from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Telegram
    BOT_TOKEN: str
    WEBHOOK_BASE_URL: str = ""
    BOT_PORT: int = 8080
    # Если WEBHOOK_BASE_URL пустой — используем polling

    # PostgreSQL
    DATABASE_URL: str  # postgresql+asyncpg://user:pass@host:5432/db

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT
    API_SECRET_KEY: str = "change-me-in-production"
    JWT_EXPIRE_MINUTES: int = 1440

    # Ollama (бесплатный LLM)
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3"
    OLLAMA_ENABLED: bool = False  # включить AI-классификацию

    # SLA
    DEFAULT_SLA_HOURS: int = 24
    CRITICAL_SLA_HOURS: int = 4
    HIGH_SLA_HOURS: int = 8
    NORMAL_SLA_HOURS: int = 24
    LOW_SLA_HOURS: int = 72

    # Дубликаты
    DUPLICATE_SIMILARITY_THRESHOLD: float = 0.80

    # Уведомления
    WAITING_REMINDER_HOURS: int = 48
    POST_RESOLVE_SURVEY_HOURS: int = 24
    NOTIFICATION_RETRY_LIMIT: int = 3

    # Ограничение запросов (сообщений в минуту от одного пользователя)
    RATE_LIMIT_PER_MINUTE: int = 10


settings = Settings()
