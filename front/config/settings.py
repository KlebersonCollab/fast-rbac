import os
from typing import Optional

import pytz


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

    # Timezone Configuration
    DEFAULT_TIMEZONE: str = os.getenv("TIMEZONE", "America/Sao_Paulo")

    @property
    def timezone(self):
        """Get timezone object"""
        try:
            return pytz.timezone(self.DEFAULT_TIMEZONE)
        except:
            return pytz.timezone("UTC")

    @property
    def available_timezones(self):
        """Get list of available timezones"""
        return [
            "UTC",
            "America/Sao_Paulo",
            "America/New_York",
            "Europe/London",
            "Europe/Paris",
            "Asia/Tokyo",
            "Australia/Sydney",
        ]

    # Debug
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"


# Global settings instance
settings = FrontendSettings()
