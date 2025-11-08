"""
Configuration settings for EVF Portugal 2030 platform.
Handles database, cache, security, and AI service credentials.
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings with multi-tenant and security configuration."""

    # Application
    app_name: str = "EVF Portugal 2030"
    app_version: str = "1.0.0"
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=True, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")

    # API Configuration
    api_title: str = "EVF Portugal 2030 API"
    api_description: str = "B2B SaaS platform for automating Portuguese funding application processing"
    api_version: str = "1.0.0"
    api_host: str = Field(default="0.0.0.0", env="API_HOST")
    api_port: int = Field(default=8000, env="API_PORT")
    api_prefix: str = "/api/v1"
    api_cors_origins: list = Field(
        default=["http://localhost:3000", "http://localhost:3001"],
        env="CORS_ORIGINS"
    )

    # Database Configuration
    database_url: str = Field(
        default="postgresql+asyncpg://evf_user:evf_password@localhost:5432/evf_portugal_2030",
        env="DATABASE_URL"
    )
    database_min_pool_size: int = Field(default=5, env="DATABASE_MIN_POOL_SIZE")
    database_max_pool_size: int = Field(default=20, env="DATABASE_MAX_POOL_SIZE")
    database_pool_timeout: int = Field(default=30, env="DATABASE_POOL_TIMEOUT")
    database_pool_recycle: int = Field(default=3600, env="DATABASE_POOL_RECYCLE")
    database_echo: bool = Field(default=False, env="DATABASE_ECHO")
    database_ssl_mode: str = Field(default="require", env="DATABASE_SSL_MODE")

    # Alembic Migrations
    alembic_dir: str = "alembic"
    alembic_sqlalchemy_url: Optional[str] = None  # Set to database_url at runtime

    # Redis Cache Configuration
    redis_url: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    redis_pool_size: int = Field(default=10, env="REDIS_POOL_SIZE")
    redis_timeout: int = Field(default=30, env="REDIS_TIMEOUT")
    cache_ttl_seconds: int = Field(default=3600, env="CACHE_TTL_SECONDS")
    session_ttl_hours: int = Field(default=24, env="SESSION_TTL_HOURS")

    # Encryption Configuration
    encryption_key: str = Field(default="", env="ENCRYPTION_KEY")
    encryption_algorithm: str = "AES-256-GCM"
    encryption_key_rotation_days: int = 90

    # Security Configuration
    secret_key: str = Field(default="your-secret-key-change-in-production", env="SECRET_KEY")
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = Field(default=30, env="JWT_EXPIRATION_MINUTES")
    jwt_refresh_expiration_days: int = Field(default=7, env="JWT_REFRESH_EXPIRATION_DAYS")
    rate_limit_requests_per_minute: int = Field(default=100, env="RATE_LIMIT_RPM")

    # Multi-tenant Configuration
    tenant_context_header: str = "X-Tenant-ID"
    tenant_context_subdomain: bool = True
    tenant_isolation_strict: bool = True

    # Claude AI Configuration
    claude_api_key: str = Field(default="", env="CLAUDE_API_KEY")
    claude_model: str = "claude-3-5-sonnet-20241022"
    claude_max_tokens: int = 4096
    claude_temperature: float = 0.7
    claude_api_timeout: int = 60
    claude_rate_limit_tokens_per_minute: int = 90000

    # Cost Control
    claude_daily_limit_euros: float = Field(default=50.0, env="CLAUDE_DAILY_LIMIT")
    claude_monthly_limit_euros: float = Field(default=1000.0, env="CLAUDE_MONTHLY_LIMIT")
    storage_daily_limit_gb: float = Field(default=10.0, env="STORAGE_DAILY_LIMIT")

    # Qdrant Vector Store Configuration
    qdrant_url: str = Field(default="http://localhost:6333", env="QDRANT_URL")
    qdrant_api_key: Optional[str] = Field(default=None, env="QDRANT_API_KEY")
    qdrant_timeout: int = 30
    qdrant_collection_name: str = "evf_documents"
    qdrant_vector_size: int = 1024  # BGE-M3 embedding size
    qdrant_similarity_threshold: float = 0.7
    embeddings_model: str = "BAAI/bge-m3"
    embeddings_batch_size: int = 32

    # File Storage Configuration
    storage_backend: str = Field(default="s3", env="STORAGE_BACKEND")  # s3 or local
    s3_bucket_name: str = Field(default="evf-portugal-2030", env="S3_BUCKET_NAME")
    s3_region: str = Field(default="eu-west-1", env="S3_REGION")
    s3_access_key: str = Field(default="", env="S3_ACCESS_KEY")
    s3_secret_key: str = Field(default="", env="S3_SECRET_KEY")
    s3_endpoint_url: Optional[str] = Field(default=None, env="S3_ENDPOINT_URL")
    local_storage_path: str = "storage/uploads"
    max_file_size_mb: int = 500
    file_retention_days: int = 30

    # Audit Configuration
    audit_retention_years: int = 10
    audit_immutable_log: bool = True
    audit_hash_algorithm: str = "sha256"

    # Monitoring & Logging
    sentry_dsn: Optional[str] = Field(default=None, env="SENTRY_DSN")
    datadog_api_key: Optional[str] = Field(default=None, env="DATADOG_API_KEY")
    metrics_export_interval_seconds: int = 60

    # Email Configuration
    smtp_host: str = Field(default="smtp.sendgrid.net", env="SMTP_HOST")
    smtp_port: int = Field(default=587, env="SMTP_PORT")
    smtp_user: str = Field(default="apikey", env="SMTP_USER")
    smtp_password: str = Field(default="", env="SMTP_PASSWORD")
    from_email: str = Field(default="noreply@evfportugal2030.pt", env="FROM_EMAIL")

    # Feature Flags
    enable_saft_parser: bool = True
    enable_excel_generation: bool = True
    enable_pdf_reports: bool = True
    enable_compliance_checking: bool = True
    enable_ai_narrative: bool = True
    enable_audit_logging: bool = True

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "allow"

    def __init__(self, **data):
        super().__init__(**data)
        # Set Alembic SQLAlchemy URL
        if not self.alembic_sqlalchemy_url:
            self.alembic_sqlalchemy_url = self.database_url

        # Set environment-specific CORS origins if not explicitly configured
        if self.api_cors_origins == ["http://localhost:3000", "http://localhost:3001"]:
            if self.environment == "production":
                # Production: strict allowlist (should be set via env var)
                self.api_cors_origins = [
                    "https://evfportugal2030.pt",
                    "https://www.evfportugal2030.pt",
                    "https://app.evfportugal2030.pt"
                ]
            elif self.environment == "staging":
                self.api_cors_origins = [
                    "https://staging.evfportugal2030.pt",
                    "http://localhost:3000"
                ]
            # Development keeps default localhost origins


# Global settings instance
settings = Settings()
