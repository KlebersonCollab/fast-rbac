import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database.base import Base


class APIKey(Base):
    """API Key model for enterprise integrations"""

    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    description = Column(Text, nullable=True)

    # Key data
    key_hash = Column(String(128), nullable=False, unique=True, index=True)
    key_prefix = Column(
        String(10), nullable=False, index=True
    )  # First 8 chars for identification

    # Ownership
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    tenant_id = Column(
        Integer, ForeignKey("tenants.id"), nullable=True
    )  # Multi-tenancy

    # Permissions and scopes
    scopes = Column(Text, nullable=False, default="read")  # JSON array of scopes
    permissions = Column(Text, nullable=True)  # JSON array of specific permissions

    # Status and lifecycle
    is_active = Column(Boolean, default=True, nullable=False)
    last_used_at = Column(DateTime, nullable=True)

    # Rate limiting
    rate_limit_per_minute = Column(Integer, default=100)
    usage_count = Column(Integer, default=0)

    # Expiration
    expires_at = Column(DateTime, nullable=True)

    # Audit
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="api_keys")
    tenant = relationship("Tenant", back_populates="api_keys", foreign_keys=[tenant_id])

    @classmethod
    def generate_key(cls) -> tuple[str, str]:
        """Generate a new API key and return (key, hash)"""
        # Generate random key
        key = secrets.token_urlsafe(32)

        # Create prefixed key
        prefix = "rbac_"
        full_key = f"{prefix}{key}"

        # Hash for storage
        key_hash = hashlib.sha256(full_key.encode()).hexdigest()

        return full_key, key_hash

    @classmethod
    def hash_key(cls, key: str) -> str:
        """Hash an API key for storage"""
        return hashlib.sha256(key.encode()).hexdigest()

    @property
    def is_expired(self) -> bool:
        """Check if the API key is expired"""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at

    @property
    def days_until_expiration(self) -> Optional[int]:
        """Get days until expiration"""
        if not self.expires_at:
            return None
        delta = self.expires_at - datetime.utcnow()
        return max(0, delta.days)

    def update_usage(self):
        """Update usage statistics"""
        self.usage_count += 1
        self.last_used_at = datetime.utcnow()

    def is_scope_allowed(self, scope: str) -> bool:
        """Check if a scope is allowed for this API key"""
        if not self.scopes:
            return False

        import json

        try:
            scopes_list = json.loads(self.scopes)
            return scope in scopes_list or "admin" in scopes_list or "*" in scopes_list
        except (json.JSONDecodeError, TypeError):
            return False

    def get_permissions_list(self) -> list[str]:
        """Get list of permissions for this API key"""
        if not self.permissions:
            return []

        import json

        try:
            return json.loads(self.permissions)
        except (json.JSONDecodeError, TypeError):
            return []

    def __repr__(self):
        return f"<APIKey(name='{self.name}', prefix='{self.key_prefix}', active={self.is_active})>"


class APIKeyUsage(Base):
    """API Key usage tracking for analytics"""

    __tablename__ = "api_key_usage"

    id = Column(Integer, primary_key=True, index=True)
    api_key_id = Column(Integer, ForeignKey("api_keys.id"), nullable=False)

    # Request details
    endpoint = Column(String(200), nullable=False)
    method = Column(String(10), nullable=False)
    status_code = Column(Integer, nullable=False)

    # Timing
    response_time_ms = Column(Integer, nullable=True)
    timestamp = Column(DateTime, server_default=func.now())

    # Client info
    ip_address = Column(String(45), nullable=True)  # IPv6 support
    user_agent = Column(String(500), nullable=True)

    # Error info (if applicable)
    error_message = Column(Text, nullable=True)

    # Relationships
    api_key = relationship("APIKey")

    def __repr__(self):
        return f"<APIKeyUsage(key_id={self.api_key_id}, endpoint='{self.endpoint}', status={self.status_code})>"
