"""
FundAI Configuration Module
Centralized settings using Pydantic for type safety and env validation
"""

from typing import Literal
from pydantic import Field, PostgresDsn, RedisDsn, validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings from environment variables"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Application
    app_name: str = "FundAI"
    app_version: str = "0.1.0"
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = False
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_prefix: str = "/api/v1"
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:8000"]

    # Security
    secret_key: str = Field(min_length=32)
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7  # 7 days

    # Database
    postgres_user: str = "fundai"
    postgres_password: str = Field(min_length=8)
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "fundai"
    database_url: PostgresDsn | None = None

    @validator("database_url", pre=True, always=True)
    def assemble_db_url(cls, v, values):
        if v:
            return v
        return PostgresDsn.build(
            scheme="postgresql",
            username=values.get("postgres_user"),
            password=values.get("postgres_password"),
            host=values.get("postgres_host"),
            port=values.get("postgres_port"),
            path=f"/{values.get('postgres_db')}",
        )

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_url: RedisDsn | None = None

    @validator("redis_url", pre=True, always=True)
    def assemble_redis_url(cls, v, values):
        if v:
            return v
        return f"redis://{values.get('redis_host')}:{values.get('redis_port')}/{values.get('redis_db')}"

    # Anthropic Claude
    anthropic_api_key: str = Field(min_length=20)
    claude_model: str = "claude-sonnet-4-20250514"
    claude_max_tokens: int = 8000
    claude_temperature: float = 0.3

    # Data Sources
    einforma_api_key: str | None = None
    racius_api_key: str | None = None
    enable_web_scraping: bool = True
    playwright_headless: bool = True

    # IFIC Specific
    ific_min_eligible: float = 5_000.0
    ific_max_incentive: float = 300_000.0
    ific_cofinancing_rate: float = 0.75
    ific_max_duration_months: int = 24
    ific_max_rh_dedicated: int = 2
    ific_max_roc_cc: float = 2_500.0

    # File Storage
    upload_dir: str = "./data/uploads"
    output_dir: str = "./data/outputs"
    temp_dir: str = "./data/temp"
    max_upload_size_mb: int = 50

    # Celery (async tasks)
    celery_broker_url: str = Field(default="redis://localhost:6379/1")
    celery_result_backend: str = Field(default="redis://localhost:6379/2")

    # Feature Flags
    enable_company_research: bool = True
    enable_stack_intelligence: bool = True
    enable_financial_analysis: bool = True
    enable_merit_scoring: bool = True
    enable_compliance_validation: bool = True

    # Monitoring
    sentry_dsn: str | None = None
    enable_metrics: bool = True

    class Config:
        case_sensitive = False


# Global settings instance
settings = Settings()
