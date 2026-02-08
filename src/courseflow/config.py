from pydantic import BaseSettings

class Settings(BaseSettings):
    GEMINI_API_KEY: str | None = None
    RATE_LIMIT_RPM: int = 15
    RATE_LIMIT_DAILY: int = 1500
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    RAG_TOP_K: int = 5

    class Config:
        env_file = ".env"

settings = Settings()
