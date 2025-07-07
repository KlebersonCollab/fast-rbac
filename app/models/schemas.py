from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime


# Base schemas
class UserBase(BaseModel):
    username: str
    email: EmailStr
    full_name: Optional[str] = None
    is_active: bool = True


class UserCreate(UserBase):
    password: Optional[str] = None  # Optional for OAuth users
    provider: Optional[str] = None
    provider_id: Optional[str] = None


class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None


class User(UserBase):
    id: int
    is_superuser: bool
    provider: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    roles: List["Role"] = []

    class Config:
        from_attributes = True


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

    class Config:
        from_attributes = True


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

    class Config:
        from_attributes = True


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


# Update forward references
User.model_rebuild()
Role.model_rebuild() 