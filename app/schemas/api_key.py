import json
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class APIKeyScope(str, Enum):
    """Available API key scopes"""

    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"
    ALL = "*"


class APIKeyCreate(BaseModel):
    """Schema for creating API keys"""

    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    scopes: List[str] = Field(default_factory=list, min_length=1)
    permissions: Optional[List[str]] = Field(default=None)
    rate_limit_per_minute: int = Field(default=100, ge=1, le=10000)
    expires_at: Optional[datetime] = None

    @field_validator("scopes")
    @classmethod
    def validate_scopes(cls, v):
        if isinstance(v, str):
            try:
                v = json.loads(v)
            except json.JSONDecodeError:
                raise ValueError("Invalid scopes format")

        if not isinstance(v, list):
            raise ValueError("Scopes must be a list")

        allowed_scopes = ["read", "write", "delete", "admin"]
        invalid_scopes = [scope for scope in v if scope not in allowed_scopes]
        if invalid_scopes:
            raise ValueError(f"Invalid scopes: {invalid_scopes}")

        return v


class APIKeyUpdate(BaseModel):
    """Schema for updating API keys"""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    scopes: Optional[List[APIKeyScope]] = None
    permissions: Optional[List[str]] = None
    rate_limit_per_minute: Optional[int] = Field(None, ge=1, le=10000)
    expires_at: Optional[datetime] = None
    is_active: Optional[bool] = None


class APIKeyResponse(BaseModel):
    """Schema for API key response"""

    id: int
    name: str
    description: Optional[str]
    key_prefix: str
    scopes: List[str]
    permissions: Optional[List[str]]
    rate_limit_per_minute: int
    usage_count: int
    is_active: bool
    last_used_at: Optional[datetime]
    expires_at: Optional[datetime]
    days_until_expiration: Optional[int]
    user_id: int
    tenant_id: Optional[int]
    created_at: datetime
    updated_at: datetime

    @field_validator("scopes", mode="before")
    @classmethod
    def validate_scopes(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return []
        return v if isinstance(v, list) else []

    @field_validator("permissions", mode="before")
    @classmethod
    def validate_permissions(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return None
        return v

    model_config = {"from_attributes": True}


class APIKeyCreateResponse(BaseModel):
    """Schema for API key creation response with the actual key"""

    api_key: APIKeyResponse
    key: str = Field(..., description="The actual API key - save this securely!")

    class Config:
        from_attributes = True


class APIKeyUsageResponse(BaseModel):
    """Schema for API key usage statistics"""

    id: int
    endpoint: str
    method: str
    status_code: int
    response_time_ms: Optional[int]
    timestamp: datetime
    ip_address: Optional[str]
    user_agent: Optional[str]
    error_message: Optional[str]

    class Config:
        from_attributes = True


class APIKeyUsageStats(BaseModel):
    """Schema for API key usage statistics"""

    total_requests: int
    successful_requests: int
    failed_requests: int
    average_response_time_ms: Optional[float]
    requests_per_hour: float
    most_used_endpoints: List[dict]
    status_code_distribution: dict
    usage_over_time: List[dict]

    class Config:
        from_attributes = True
