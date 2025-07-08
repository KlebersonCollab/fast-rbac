from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr


# Base schemas
class UserBase(BaseModel):
    username: str
    email: EmailStr
    full_name: Optional[str] = None
    is_active: bool = True
    phone_number: Optional[str] = None
    timezone: str = "UTC"


class UserCreate(UserBase):
    password: str
    provider: Optional[str] = None
    provider_id: Optional[str] = None


class UserRegister(UserCreate):
    tenant_name: str


class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None
    phone_number: Optional[str] = None
    timezone: Optional[str] = None
    password: Optional[str] = None


class User(UserBase):
    id: int
    is_superuser: bool
    provider: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    provider_id: Optional[str] = None
    avatar_url: Optional[str] = None
    is_2fa_enabled: bool = False
    roles: List["Role"] = []

    model_config = ConfigDict(from_attributes=True)


# Role schemas
class RoleBase(BaseModel):
    name: str
    description: Optional[str] = None
    is_active: bool = True


class RoleCreate(RoleBase):
    pass


class RoleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class Role(RoleBase):
    id: int
    created_at: datetime
    updated_at: datetime
    permissions: List["Permission"] = []

    model_config = ConfigDict(from_attributes=True)


# Permission schemas
class PermissionBase(BaseModel):
    name: str
    description: Optional[str] = None
    resource: str
    action: str


class PermissionCreate(PermissionBase):
    pass


class PermissionUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    resource: Optional[str] = None
    action: Optional[str] = None


class Permission(PermissionBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Auth schemas
class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


class LoginRequest(BaseModel):
    username: str
    password: str


class OAuthCallbackRequest(BaseModel):
    code: str
    state: Optional[str] = None


# 2FA Schemas
class TotpSetupRequest(BaseModel):
    """Schema for TOTP setup request"""

    pass


class TotpSetupResponse(BaseModel):
    """Schema for TOTP setup response"""

    secret: str
    qr_code_url: str
    manual_entry_key: str
    backup_codes: List[str]


class TotpVerifyRequest(BaseModel):
    """Schema for TOTP verification"""

    totp_code: str


class TotpVerifyResponse(BaseModel):
    """Schema for TOTP verification response"""

    success: bool
    message: str
    backup_codes: Optional[List[str]] = None


class TotpEnableRequest(BaseModel):
    """Schema for enabling TOTP"""

    totp_code: str


class TotpDisableRequest(BaseModel):
    """Schema for disabling TOTP"""

    totp_code: Optional[str] = None
    backup_code: Optional[str] = None
    password: str


class LoginWith2FARequest(BaseModel):
    """Schema for login with 2FA"""

    username: str
    password: str
    totp_code: Optional[str] = None
    backup_code: Optional[str] = None


class TotpStatusResponse(BaseModel):
    """Schema for TOTP status"""

    is_2fa_enabled: bool
    has_backup_codes: bool
    setup_date: Optional[datetime] = None


# Update forward references
User.model_rebuild()
Role.model_rebuild()
