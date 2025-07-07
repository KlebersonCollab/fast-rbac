from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Database
    database_url: str = "sqlite:///./app.db"
    
    # JWT
    secret_key: str = "your-secret-key-here"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # OAuth Providers
    microsoft_client_id: Optional[str] = None
    microsoft_client_secret: Optional[str] = None
    
    google_client_id: Optional[str] = None
    google_client_secret: Optional[str] = None
    
    github_client_id: Optional[str] = None
    github_client_secret: Optional[str] = None
    
    # Application
    app_name: str = "FastAPI RBAC"
    app_version: str = "0.1.0"
    debug: bool = False
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings() 