"""Application configuration using Pydantic settings.

Configuration is loaded from environment variables (via .env file or system env).
All settings are validated at startup with clear error messages for missing required values.
"""

from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_BASE_DIR = Path(__file__).resolve().parents[2]  # project root


class Settings(BaseSettings):
    """Application settings with validation.

    Settings are loaded from environment variables (case-sensitive).
    A .env file can be used for local development.

    Required variables:
        - GEMINI_API_KEY: Google Gemini API key

    All other variables have sensible defaults.
    """

    # Gemini API
    GEMINI_API_KEY: str  # Required - no default
    GEMINI_MODEL: str = "gemini-2.5-flash-lite"
    GEMINI_EMBEDDING_MODEL: str = "models/gemini-embedding-001"

    # ChromaDB
    CHROMA_PERSIST_DIR: str = "./data/chroma"
    CHROMA_COLLECTION_NAME: str = "courseflow_docs"

    # SQLite
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/courseflow.db"

    # Rate Limiting
    RATE_LIMIT_RPM: int = 15
    RATE_LIMIT_DAILY: int = 1500

    # Vector Search
    SIMILARITY_THRESHOLD: float = Field(default=0.5, ge=0.0, le=1.0)
    TOP_K_RESULTS: int = Field(default=3, ge=1, le=10)

    # API
    API_V1_PREFIX: str = "/api/v1"
    CORS_ORIGINS: str = "*"  # Comma-separated list or "*" for all

    # Timeouts (seconds)
    LLM_TIMEOUT_SECONDS: int = Field(default=30, ge=5, le=120)
    EMBEDDING_TIMEOUT_SECONDS: int = Field(default=10, ge=2, le=60)

    # Logging
    LOG_LEVEL: str = "INFO"

    # Evaluation System
    EVAL_DATABASE_PATH: str = "./data/evaluations.db"
    EVAL_GOLDEN_DATASET_PATH: str = "./tests/fixtures/golden_dataset.json"
    EVAL_SCHEDULE_ENABLED: bool = True
    EVAL_SCHEDULE_HOUR: int = Field(default=2, ge=0, le=23)  # 2 AM UTC
    EVAL_SCHEDULE_MINUTE: int = Field(default=0, ge=0, le=59)
    EVAL_PRECISION_THRESHOLD: float = Field(default=0.70, ge=0.0, le=1.0)
    EVAL_KEYWORD_MATCH_THRESHOLD: float = Field(default=0.80, ge=0.0, le=1.0)
    EVAL_LATENCY_P95_THRESHOLD_MS: int = Field(default=10000, ge=0)

    # Quota Protection (006-demo-protection)
    QUOTA_HOURLY_LIMIT: int = Field(default=100, ge=1)  # Per-IP requests per hour
    QUOTA_DAILY_BUDGET: int = Field(default=300, ge=1)  # Global daily budget
    QUOTA_CACHE_ENABLED: bool = True  # Enable demo cache bypass
    QUOTA_STREAM_DELAY_MS: int = Field(default=30, ge=0)  # Word delay for cached responses

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",  # Ignore unknown environment variables
    )

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS_ORIGINS into a list.

        Returns:
            List of allowed origins, or ["*"] for all origins
        """
        if self.CORS_ORIGINS == "*":
            return ["*"]
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    # Snake case aliases for backward compatibility
    @property
    def gemini_api_key(self) -> str:
        return self.GEMINI_API_KEY

    @property
    def chroma_persist_dir(self) -> str:
        return self.CHROMA_PERSIST_DIR

    @property
    def chroma_collection_name(self) -> str:
        return self.CHROMA_COLLECTION_NAME

    @field_validator("CHROMA_PERSIST_DIR")
    @classmethod
    def _resolve_chroma_dir(cls, v: str) -> str:
        p = Path(v)
        if not p.is_absolute():
            p = (_BASE_DIR / p).resolve()
        return str(p)

    @property
    def database_path(self) -> str:
        raw = self.DATABASE_URL.replace("sqlite+aiosqlite:///", "")
        p = Path(raw)
        if not p.is_absolute():
            p = (_BASE_DIR / p).resolve()
        return str(p)

    @property
    def rate_limit_rpm(self) -> int:
        return self.RATE_LIMIT_RPM

    @property
    def similarity_threshold(self) -> float:
        return self.SIMILARITY_THRESHOLD

    @property
    def top_k_results(self) -> int:
        return self.TOP_K_RESULTS

    @property
    def api_v1_prefix(self) -> str:
        return self.API_V1_PREFIX

    @property
    def eval_database_path(self) -> str:
        """Resolve evaluation database path (absolute)."""
        p = Path(self.EVAL_DATABASE_PATH)
        if not p.is_absolute():
            p = (_BASE_DIR / p).resolve()
        return str(p)

    @property
    def eval_golden_dataset_path(self) -> str:
        """Resolve golden dataset path (absolute)."""
        p = Path(self.EVAL_GOLDEN_DATASET_PATH)
        if not p.is_absolute():
            p = (_BASE_DIR / p).resolve()
        return str(p)

    @property
    def eval_auto_schedule_enabled(self) -> bool:
        """Backward-compatible alias for evaluation auto scheduler toggle."""
        return self.EVAL_SCHEDULE_ENABLED

    @property
    def eval_schedule_hour(self) -> int:
        return self.EVAL_SCHEDULE_HOUR

    @property
    def eval_schedule_minute(self) -> int:
        return self.EVAL_SCHEDULE_MINUTE

    @property
    def quota_hourly_limit(self) -> int:
        return self.QUOTA_HOURLY_LIMIT

    @property
    def quota_daily_budget(self) -> int:
        return self.QUOTA_DAILY_BUDGET

    @property
    def quota_cache_enabled(self) -> bool:
        return self.QUOTA_CACHE_ENABLED

    @property
    def quota_stream_delay_ms(self) -> int:
        return self.QUOTA_STREAM_DELAY_MS


# Global settings instance (initialized once at import)
# Will raise ValidationError if GEMINI_API_KEY is missing (unless tests override via env)
settings = Settings()  # type: ignore[call-arg]
