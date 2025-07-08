from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database.base import Base


class Tenant(Base):
    """Tenant model for multi-tenancy support"""

    __tablename__ = "tenants"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    slug = Column(String(50), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)

    # Contact info
    contact_email = Column(String(255), nullable=True)
    contact_phone = Column(String(20), nullable=True)

    # Billing and limits
    plan_type = Column(String(50), default="free")  # free, basic, premium, enterprise
    max_users = Column(Integer, default=10)
    max_api_keys = Column(Integer, default=5)
    max_storage_mb = Column(Integer, default=100)

    # Features
    features = Column(
        JSON, nullable=True
    )  # {"2fa": true, "sso": false, "webhooks": true}
    custom_domain = Column(String(255), nullable=True)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)

    # Billing
    subscription_expires_at = Column(DateTime, nullable=True)

    # Audit
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    users = relationship("User", back_populates="tenant")
    api_keys = relationship("APIKey", back_populates="tenant")
    webhooks = relationship("Webhook", back_populates="tenant")

    def get_feature(self, feature_name: str) -> bool:
        """Check if a feature is enabled for this tenant"""
        if not self.features:
            return False
        return self.features.get(feature_name, False)

    def set_feature(self, feature_name: str, enabled: bool):
        """Enable or disable a feature for this tenant"""
        if not self.features:
            self.features = {}
        self.features[feature_name] = enabled

    @property
    def is_subscription_active(self) -> bool:
        """Check if subscription is active"""
        if not self.subscription_expires_at:
            return self.plan_type == "free"
        return datetime.utcnow() < self.subscription_expires_at

    @property
    def current_user_count(self) -> int:
        """Get current number of users"""
        return len(self.users) if self.users else 0

    @property
    def current_api_key_count(self) -> int:
        """Get current number of API keys"""
        return (
            len([key for key in self.api_keys if key.is_active]) if self.api_keys else 0
        )

    def can_add_user(self) -> bool:
        """Check if tenant can add more users"""
        return self.current_user_count < self.max_users

    def can_add_api_key(self) -> bool:
        """Check if tenant can add more API keys"""
        return self.current_api_key_count < self.max_api_keys

    def get_usage_stats(self) -> Dict[str, Any]:
        """Get usage statistics for this tenant"""
        return {
            "users": {
                "current": self.current_user_count,
                "limit": self.max_users,
                "percentage": (
                    (self.current_user_count / self.max_users) * 100
                    if self.max_users > 0
                    else 0
                ),
            },
            "api_keys": {
                "current": self.current_api_key_count,
                "limit": self.max_api_keys,
                "percentage": (
                    (self.current_api_key_count / self.max_api_keys) * 100
                    if self.max_api_keys > 0
                    else 0
                ),
            },
            "subscription": {
                "plan": self.plan_type,
                "active": self.is_subscription_active,
                "expires_at": self.subscription_expires_at,
            },
        }

    def __repr__(self):
        return (
            f"<Tenant(name='{self.name}', slug='{self.slug}', plan='{self.plan_type}')>"
        )


class TenantSettings(Base):
    """Tenant-specific settings"""

    __tablename__ = "tenant_settings"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, nullable=False, unique=True, index=True)

    # Branding
    logo_url = Column(String(500), nullable=True)
    primary_color = Column(String(7), nullable=True)  # Hex color
    secondary_color = Column(String(7), nullable=True)

    # Authentication settings
    allow_registration = Column(Boolean, default=True)
    require_email_verification = Column(Boolean, default=True)
    enforce_2fa = Column(Boolean, default=False)
    password_policy = Column(
        JSON, nullable=True
    )  # {"min_length": 8, "require_symbols": true}

    # SSO settings
    sso_enabled = Column(Boolean, default=False)
    sso_provider = Column(String(50), nullable=True)  # saml, oidc
    sso_config = Column(JSON, nullable=True)

    # Webhooks
    webhook_secret = Column(String(128), nullable=True)

    # Audit
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def get_password_policy(self) -> Dict[str, Any]:
        """Get password policy settings"""
        default_policy = {
            "min_length": 8,
            "require_uppercase": True,
            "require_lowercase": True,
            "require_numbers": True,
            "require_symbols": False,
            "max_length": 128,
        }

        if not self.password_policy:
            return default_policy

        # Merge with defaults
        policy = default_policy.copy()
        policy.update(self.password_policy)
        return policy

    def __repr__(self):
        return f"<TenantSettings(tenant_id={self.tenant_id}, sso_enabled={self.sso_enabled})>"
