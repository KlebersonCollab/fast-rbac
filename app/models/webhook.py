import hashlib
import hmac
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

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


class WebhookEvent(str, Enum):
    """Webhook event types"""

    USER_CREATED = "user.created"
    USER_UPDATED = "user.updated"
    USER_DELETED = "user.deleted"
    USER_LOGIN = "user.login"
    USER_LOGOUT = "user.logout"

    ROLE_ASSIGNED = "role.assigned"
    ROLE_REMOVED = "role.removed"

    API_KEY_CREATED = "api_key.created"
    API_KEY_DELETED = "api_key.deleted"

    TENANT_CREATED = "tenant.created"
    TENANT_UPDATED = "tenant.updated"

    SECURITY_ALERT = "security.alert"
    RATE_LIMIT_EXCEEDED = "rate_limit.exceeded"


class Webhook(Base):
    """Webhook configuration for external integrations"""

    __tablename__ = "webhooks"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)

    # Target
    url = Column(String(500), nullable=False)
    secret = Column(String(128), nullable=True)  # For signature verification

    # Configuration
    events = Column(JSON, nullable=False)  # List of subscribed events
    headers = Column(JSON, nullable=True)  # Custom headers
    timeout_seconds = Column(Integer, default=30)

    # Retry policy
    retry_enabled = Column(Boolean, default=True)
    max_retries = Column(Integer, default=3)
    retry_delay_seconds = Column(Integer, default=60)

    # Status
    is_active = Column(Boolean, default=True)
    last_triggered_at = Column(DateTime, nullable=True)
    last_success_at = Column(DateTime, nullable=True)
    last_failure_at = Column(DateTime, nullable=True)
    failure_count = Column(Integer, default=0)

    # Ownership
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True)

    # Audit
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User")
    tenant = relationship("Tenant", back_populates="webhooks")
    deliveries = relationship(
        "WebhookDelivery", back_populates="webhook", cascade="all, delete-orphan"
    )

    @property
    def delivery_count(self) -> int:
        """Get total delivery count"""
        from sqlalchemy.orm import object_session

        session = object_session(self)
        if session:
            return (
                session.query(WebhookDelivery)
                .filter(WebhookDelivery.webhook_id == self.id)
                .count()
            )
        return 0

    @property
    def success_count(self) -> int:
        """Get successful delivery count"""
        from sqlalchemy.orm import object_session

        session = object_session(self)
        if session:
            return (
                session.query(WebhookDelivery)
                .filter(
                    WebhookDelivery.webhook_id == self.id,
                    WebhookDelivery.success == True,
                )
                .count()
            )
        return 0

    def is_subscribed_to(self, event: str) -> bool:
        """Check if webhook is subscribed to an event"""
        if not self.events:
            return False
        return event in self.events

    def get_custom_headers(self) -> Dict[str, str]:
        """Get custom headers as dict"""
        if not self.headers:
            return {}
        return self.headers

    def generate_signature(self, payload: str) -> Optional[str]:
        """Generate HMAC signature for payload"""
        if not self.secret:
            return None

        signature = hmac.new(
            self.secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256
        ).hexdigest()

        return f"sha256={signature}"

    def should_retry(self) -> bool:
        """Check if webhook should retry on failure"""
        return (
            self.retry_enabled
            and self.failure_count < self.max_retries
            and self.is_active
        )

    def mark_success(self):
        """Mark webhook as successfully triggered"""
        self.last_success_at = datetime.utcnow()
        self.last_triggered_at = datetime.utcnow()
        self.failure_count = 0

    def mark_failure(self):
        """Mark webhook as failed"""
        self.last_failure_at = datetime.utcnow()
        self.last_triggered_at = datetime.utcnow()
        self.failure_count += 1

        # Auto-disable after too many failures
        if self.failure_count >= self.max_retries * 2:
            self.is_active = False

    def __repr__(self):
        return (
            f"<Webhook(name='{self.name}', url='{self.url}', active={self.is_active})>"
        )


class WebhookDelivery(Base):
    """Individual webhook delivery attempts"""

    __tablename__ = "webhook_deliveries"

    id = Column(Integer, primary_key=True, index=True)
    webhook_id = Column(Integer, ForeignKey("webhooks.id"), nullable=False)

    # Event data
    event_type = Column(String(50), nullable=False)
    event_id = Column(String(36), nullable=False)  # UUID
    payload = Column(JSON, nullable=False)

    # Delivery attempt
    attempt_number = Column(Integer, default=1)

    # Response
    status_code = Column(Integer, nullable=True)
    response_body = Column(Text, nullable=True)
    response_headers = Column(JSON, nullable=True)

    # Timing
    duration_ms = Column(Integer, nullable=True)

    # Status
    success = Column(Boolean, default=False)
    error_message = Column(Text, nullable=True)

    # Audit
    created_at = Column(DateTime, server_default=func.now())
    delivered_at = Column(DateTime, nullable=True)

    # Relationships
    webhook = relationship("Webhook", back_populates="deliveries")

    @property
    def is_successful(self) -> bool:
        """Check if delivery was successful"""
        return self.success and self.status_code and 200 <= self.status_code < 300

    def mark_delivered(
        self,
        status_code: int,
        response_body: str = None,
        response_headers: Dict[str, str] = None,
        duration_ms: int = None,
    ):
        """Mark delivery as completed"""
        self.status_code = status_code
        self.response_body = response_body
        self.response_headers = response_headers
        self.duration_ms = duration_ms
        self.delivered_at = datetime.utcnow()
        self.success = 200 <= status_code < 300

    def mark_failed(self, error_message: str):
        """Mark delivery as failed"""
        self.error_message = error_message
        self.success = False
        self.delivered_at = datetime.utcnow()

    def __repr__(self):
        return f"<WebhookDelivery(webhook_id={self.webhook_id}, event='{self.event_type}', success={self.success})>"


class WebhookLog(Base):
    """Webhook system logs for debugging"""

    __tablename__ = "webhook_logs"

    id = Column(Integer, primary_key=True, index=True)
    webhook_id = Column(Integer, ForeignKey("webhooks.id"), nullable=True)

    # Log data
    level = Column(String(10), nullable=False)  # INFO, WARN, ERROR
    message = Column(Text, nullable=False)
    details = Column(JSON, nullable=True)

    # Context
    event_type = Column(String(50), nullable=True)
    delivery_id = Column(Integer, ForeignKey("webhook_deliveries.id"), nullable=True)

    # Audit
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    webhook = relationship("Webhook")
    delivery = relationship("WebhookDelivery")

    def __repr__(self):
        return f"<WebhookLog(level='{self.level}', message='{self.message[:50]}...')>"
