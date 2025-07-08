import json
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator


class WebhookEvent(str, Enum):
    """Available webhook events"""

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


class WebhookCreate(BaseModel):
    """Schema for creating webhooks"""

    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    url: str = Field(..., min_length=1, max_length=2000)
    secret: Optional[str] = Field(None, max_length=255)
    events: List[str] = Field(..., min_length=1)
    headers: Optional[Dict[str, str]] = Field(default=None)
    timeout_seconds: int = Field(default=30, ge=1, le=300)
    retry_enabled: bool = Field(default=True)
    max_retries: int = Field(default=3, ge=0, le=10)
    retry_delay_seconds: int = Field(default=60, ge=1, le=3600)

    @field_validator("url")
    @classmethod
    def validate_url(cls, v):
        parsed = urlparse(v)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError("Invalid URL format")
        if parsed.scheme not in ["http", "https"]:
            raise ValueError("URL must use HTTP or HTTPS")
        return v


class WebhookUpdate(BaseModel):
    """Schema for updating webhooks"""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    url: Optional[str] = Field(None, min_length=1, max_length=2000)
    secret: Optional[str] = Field(None, max_length=255)
    events: Optional[List[str]] = Field(None, min_length=1)
    headers: Optional[Dict[str, str]] = None
    timeout_seconds: Optional[int] = Field(None, ge=1, le=300)
    retry_enabled: Optional[bool] = None
    max_retries: Optional[int] = Field(None, ge=0, le=10)
    retry_delay_seconds: Optional[int] = Field(None, ge=1, le=3600)
    is_active: Optional[bool] = None

    @field_validator("url")
    @classmethod
    def validate_url(cls, v):
        if v is None:
            return v
        parsed = urlparse(v)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError("Invalid URL format")
        if parsed.scheme not in ["http", "https"]:
            raise ValueError("URL must use HTTP or HTTPS")
        return v


class WebhookResponse(BaseModel):
    """Schema for webhook response"""

    id: int
    name: str
    description: Optional[str]
    url: str
    events: List[str]
    headers: Optional[Dict[str, str]]
    timeout_seconds: int
    retry_enabled: bool
    max_retries: int
    retry_delay_seconds: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    last_triggered_at: Optional[datetime]
    delivery_count: int
    success_count: int
    failure_count: int
    user_id: int
    tenant_id: Optional[int]

    @field_validator("events", mode="before")
    @classmethod
    def validate_events(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return []
        return v if isinstance(v, list) else []

    @field_validator("headers", mode="before")
    @classmethod
    def validate_headers(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return None
        return v

    model_config = {"from_attributes": True}


class WebhookTestRequest(BaseModel):
    """Schema for testing webhooks"""

    event_type: WebhookEvent
    test_data: Optional[Dict[str, Any]] = None


class WebhookDeliveryResponse(BaseModel):
    """Schema for webhook delivery response"""

    id: int
    webhook_id: int
    event_type: str
    event_id: str
    payload: Dict[str, Any]
    attempt_number: int
    status_code: Optional[int]
    response_body: Optional[str]
    response_headers: Optional[Dict[str, str]]
    duration_ms: Optional[int]
    success: bool
    error_message: Optional[str]
    created_at: datetime
    delivered_at: Optional[datetime]

    class Config:
        from_attributes = True


class WebhookStats(BaseModel):
    """Schema for webhook statistics"""

    total_deliveries: int
    successful_deliveries: int
    failed_deliveries: int
    success_rate: float
    average_response_time_ms: Optional[float]
    deliveries_per_hour: float
    most_common_events: List[dict]
    status_code_distribution: Dict[str, int]
    deliveries_over_time: List[dict]

    class Config:
        from_attributes = True


class WebhookLogResponse(BaseModel):
    """Schema for webhook log response"""

    id: int
    webhook_id: Optional[int]
    level: str
    message: str
    details: Optional[Dict[str, Any]]
    event_type: Optional[str]
    delivery_id: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True


class WebhookEventData(BaseModel):
    """Base schema for webhook event data"""

    event_type: str
    event_id: str
    timestamp: datetime
    tenant_id: Optional[int]
    user_id: Optional[int]
    data: Dict[str, Any]

    class Config:
        from_attributes = True
