import os
from functools import lru_cache
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlparse

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Application
    app_name: str = "FastAPI RBAC System"
    version: str = "1.0.0"
    description: str = "FastAPI-based RBAC system with JWT authentication"
    environment: str = "development"
    debug: bool = False

    # Database Configuration
    database_url: str = "sqlite:///./app.db"
    db_echo: bool = False

    # Redis Configuration (for caching and sessions)
    redis_url: str = "redis://localhost:6379"
    redis_enabled: bool = False

    # Security
    secret_key: str = "your-secret-key-here-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # CORS
    allowed_origins: List[str] = ["*"]
    allow_credentials: bool = True
    allow_methods: List[str] = ["*"]
    allow_headers: List[str] = ["*"]

    # Rate Limiting
    rate_limit_enabled: bool = True
    rate_limit_requests: int = 100
    rate_limit_window: int = 60  # seconds

    # OAuth Configuration
    google_client_id: Optional[str] = None
    google_client_secret: Optional[str] = None
    microsoft_client_id: Optional[str] = None
    microsoft_client_secret: Optional[str] = None
    github_client_id: Optional[str] = None
    github_client_secret: Optional[str] = None

    # Email Configuration (for notifications)
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_use_tls: bool = True

    # Monitoring
    enable_prometheus: bool = False
    log_level: str = "INFO"

    # File Storage
    upload_max_size: int = 10 * 1024 * 1024  # 10MB
    upload_allowed_types: List[str] = [
        "jpg",
        "jpeg",
        "png",
        "gif",
        "pdf",
        "doc",
        "docx",
    ]

    # API Documentation
    docs_url: str = "/docs"
    redoc_url: str = "/redoc"
    openapi_url: str = "/openapi.json"

    # Application version
    app_version: str = "5.0.0"

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def validate_allowed_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    @field_validator("upload_allowed_types", mode="before")
    @classmethod
    def validate_upload_allowed_types(cls, v):
        if isinstance(v, str):
            return [ext.strip() for ext in v.split(",")]
        return v

    @property
    def allowed_origins_list(self) -> List[str]:
        """Convert allowed_origins string to list"""
        if isinstance(self.allowed_origins, str):
            if self.allowed_origins == "*":
                return ["*"]
            return [origin.strip() for origin in self.allowed_origins.split(",")]
        return self.allowed_origins

    @property
    def upload_allowed_types_list(self) -> List[str]:
        """Convert upload_allowed_types string to list"""
        if isinstance(self.upload_allowed_types, str):
            return [
                mime_type.strip() for mime_type in self.upload_allowed_types.split(",")
            ]
        return self.upload_allowed_types

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"

    @property
    def is_development(self) -> bool:
        return self.environment.lower() == "development"

    @property
    def database_type(self) -> str:
        if self.database_url.startswith("postgresql"):
            return "postgresql"
        elif self.database_url.startswith("sqlite"):
            return "sqlite"
        elif self.database_url.startswith("mysql"):
            return "mysql"
        return "unknown"

    @property
    def redis_host(self) -> str:
        """Extract Redis host from URL"""
        parsed = urlparse(self.redis_url)
        return parsed.hostname or "localhost"

    @property
    def redis_port(self) -> int:
        """Extract Redis port from URL"""
        parsed = urlparse(self.redis_url)
        return parsed.port or 6379

    @property
    def redis_db(self) -> int:
        """Extract Redis database from URL"""
        parsed = urlparse(self.redis_url)
        if parsed.path and parsed.path.startswith("/"):
            try:
                return int(parsed.path[1:])
            except ValueError:
                return 0
        return 0

    @property
    def redis_password(self) -> Optional[str]:
        """Extract Redis password from URL"""
        parsed = urlparse(self.redis_url)
        return parsed.password

    @property
    def redis_max_connections(self) -> int:
        """Redis max connections for connection pool"""
        return 20

    # Pydantic V2 configuration - sem arquivo .env
    model_config = {
        "case_sensitive": False,
        "extra": "ignore",
    }


@lru_cache()
def get_settings():
    return Settings()


settings = get_settings()
