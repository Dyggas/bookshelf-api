from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@db:5432/bookshelf"
    SECRET_KEY: str = "change-me-in-production-use-at-least-32-bytes"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    DEBUG: bool = False

    model_config = {"env_file": ".env"}


settings = Settings()
