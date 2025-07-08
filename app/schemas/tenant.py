from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class TenantPlan(str, Enum):
    """Available tenant plans"""

    FREE = "free"
    BASIC = "basic"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"


class TenantCreate(BaseModel):
    """Schema for creating tenants"""

    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    slug: str = Field(..., min_length=1, max_length=50, pattern=r"^[a-z0-9-]+$")
    contact_email: Optional[str] = Field(None, max_length=100)
    contact_phone: Optional[str] = Field(None, max_length=20)
    plan_type: TenantPlan = Field(default=TenantPlan.FREE)
    custom_domain: Optional[str] = Field(None, max_length=255)

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v):
        return v.lower()


class TenantUpdate(BaseModel):
    """Schema for updating tenants"""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    contact_email: Optional[str] = Field(None, max_length=255)
    contact_phone: Optional[str] = Field(None, max_length=20)
    plan_type: Optional[TenantPlan] = None
    max_users: Optional[int] = Field(None, ge=1)
    max_api_keys: Optional[int] = Field(None, ge=1)
    max_storage_mb: Optional[int] = Field(None, ge=1)
    features: Optional[Dict[str, Any]] = None
    custom_domain: Optional[str] = Field(None, max_length=255)
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None


class TenantResponse(BaseModel):
    """Schema for tenant response"""

    id: int
    name: str
    slug: str
    description: Optional[str]
    contact_email: Optional[str]
    contact_phone: Optional[str]
    plan_type: str
    max_users: int
    max_api_keys: int
    max_storage_mb: int
    features: Optional[Dict[str, Any]]
    custom_domain: Optional[str]
    is_active: bool
    is_verified: bool
    subscription_expires_at: Optional[datetime]
    current_user_count: int
    current_api_key_count: int
    is_subscription_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TenantUsageStats(BaseModel):
    """Schema for tenant usage statistics"""

    users: Dict[str, Any]
    api_keys: Dict[str, Any]
    subscription: Dict[str, Any]

    class Config:
        from_attributes = True


class TenantSettingsCreate(BaseModel):
    """Schema for creating tenant settings"""

    logo_url: Optional[str] = Field(None, max_length=500)
    primary_color: Optional[str] = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")
    secondary_color: Optional[str] = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")
    allow_registration: bool = Field(default=True)
    require_email_verification: bool = Field(default=True)
    enforce_2fa: bool = Field(default=False)
    password_policy: Optional[Dict[str, Any]] = None
    sso_enabled: bool = Field(default=False)
    sso_provider: Optional[str] = Field(None, max_length=50)
    sso_config: Optional[Dict[str, Any]] = None
    webhook_secret: Optional[str] = Field(None, max_length=128)


class TenantSettingsUpdate(BaseModel):
    """Schema for updating tenant settings"""

    logo_url: Optional[str] = Field(None, max_length=500)
    primary_color: Optional[str] = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")
    secondary_color: Optional[str] = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")
    allow_registration: Optional[bool] = None
    require_email_verification: Optional[bool] = None
    enforce_2fa: Optional[bool] = None
    password_policy: Optional[Dict[str, Any]] = None
    sso_enabled: Optional[bool] = None
    sso_provider: Optional[str] = Field(None, max_length=50)
    sso_config: Optional[Dict[str, Any]] = None
    webhook_secret: Optional[str] = Field(None, max_length=128)


class TenantSettingsResponse(BaseModel):
    """Schema for tenant settings response"""

    id: int
    tenant_id: int
    logo_url: Optional[str]
    primary_color: Optional[str]
    secondary_color: Optional[str]
    allow_registration: bool
    require_email_verification: bool
    enforce_2fa: bool
    password_policy: Optional[Dict[str, Any]]
    sso_enabled: bool
    sso_provider: Optional[str]
    sso_config: Optional[Dict[str, Any]]
    webhook_secret: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TenantInvite(BaseModel):
    """Schema for tenant user invitations"""

    email: str = Field(..., max_length=255)
    role_names: List[str] = Field(default=["user"])
    message: Optional[str] = Field(None, max_length=500)
    expires_hours: int = Field(default=48, ge=1, le=168)  # 1 hour to 1 week
