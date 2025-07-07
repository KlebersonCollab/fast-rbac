import os
from typing import Optional

class FrontendSettings:
    # API Backend Configuration
    API_BASE_URL: str = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
    
    # Frontend Configuration
    APP_TITLE: str = "FastAPI RBAC - Admin Panel"
    APP_ICON: str = "🔐"
    
    # Page Configuration
    PAGE_TITLE: str = "RBAC Admin"
    PAGE_ICON: str = "🛡️"
    LAYOUT: str = "wide"
    INITIAL_SIDEBAR_STATE: str = "expanded"
    
    # Theme
    PRIMARY_COLOR: str = "#1f77b4"
    
    # Session Configuration
    SESSION_TIMEOUT: int = 30  # minutes
    
    # Debug
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

# Global settings instance
settings = FrontendSettings() 