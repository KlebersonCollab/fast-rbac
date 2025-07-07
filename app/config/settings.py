from pydantic_settings import BaseSettings
from pydantic import Field, validator
from typing import Optional, List
import os


class Settings(BaseSettings):
    # Application
    app_name: str = "FastAPI RBAC System"
    app_version: str = "1.0.0"
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=False, env="DEBUG")
    
    # Database Configuration
    database_url: str = Field(
        default="sqlite:///./app.db",
        env="DATABASE_URL",
        description="Database URL. Use postgresql://user:pass@host:port/dbname for PostgreSQL"
    )
    
    # Redis Configuration (for caching and sessions)
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        env="REDIS_URL"
    )
    redis_enabled: bool = Field(default=False, env="REDIS_ENABLED")
    
    # Security
    secret_key: str = Field(env="SECRET_KEY")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(default=7, env="REFRESH_TOKEN_EXPIRE_DAYS")
    
    # CORS
    allowed_origins: str = Field(
        default="*", 
        env="ALLOWED_ORIGINS"
    )
    
    # Rate Limiting
    rate_limit_enabled: bool = Field(default=True, env="RATE_LIMIT_ENABLED")
    rate_limit_requests: int = Field(default=100, env="RATE_LIMIT_REQUESTS")
    rate_limit_window: int = Field(default=60, env="RATE_LIMIT_WINDOW")  # seconds
    
    # OAuth Configuration
    google_client_id: Optional[str] = Field(default=None, env="GOOGLE_CLIENT_ID")
    google_client_secret: Optional[str] = Field(default=None, env="GOOGLE_CLIENT_SECRET")
    microsoft_client_id: Optional[str] = Field(default=None, env="MICROSOFT_CLIENT_ID")
    microsoft_client_secret: Optional[str] = Field(default=None, env="MICROSOFT_CLIENT_SECRET")
    github_client_id: Optional[str] = Field(default=None, env="GITHUB_CLIENT_ID")
    github_client_secret: Optional[str] = Field(default=None, env="GITHUB_CLIENT_SECRET")
    
    # Email Configuration (for notifications)
    smtp_host: Optional[str] = Field(default=None, env="SMTP_HOST")
    smtp_port: int = Field(default=587, env="SMTP_PORT")
    smtp_username: Optional[str] = Field(default=None, env="SMTP_USERNAME")
    smtp_password: Optional[str] = Field(default=None, env="SMTP_PASSWORD")
    smtp_use_tls: bool = Field(default=True, env="SMTP_USE_TLS")
    
    # Monitoring
    enable_prometheus: bool = Field(default=False, env="ENABLE_PROMETHEUS")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # File Storage
    upload_max_size: int = Field(default=10*1024*1024, env="UPLOAD_MAX_SIZE")  # 10MB
    upload_allowed_types: str = Field(
        default="image/jpeg,image/png,image/gif,application/pdf",
        env="UPLOAD_ALLOWED_TYPES"
    )
    
    @validator("allowed_origins", pre=True)
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return v  # Return as string, will be converted by property
        return v
    
    @validator("upload_allowed_types", pre=True)
    def parse_upload_types(cls, v):
        if isinstance(v, str):
            return v  # Return as string, will be converted by property
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
            return [mime_type.strip() for mime_type in self.upload_allowed_types.split(",")]
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

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings() 