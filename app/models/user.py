from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Table
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database.base import Base

# Association tables for many-to-many relationships
user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("role_id", Integer, ForeignKey("roles.id"), primary_key=True),
)

role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", Integer, ForeignKey("roles.id"), primary_key=True),
    Column("permission_id", Integer, ForeignKey("permissions.id"), primary_key=True),
)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=True)
    hashed_password = Column(String, nullable=True)  # Nullable for OAuth users
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)

    # OAuth provider information
    provider = Column(String, nullable=True)  # 'basic', 'google', 'microsoft', 'github'
    provider_id = Column(String, nullable=True)  # External ID from OAuth provider

    # OAuth fields
    oauth_access_token = Column(String, nullable=True)
    oauth_refresh_token = Column(String, nullable=True)

    # 2FA fields
    totp_secret = Column(String, nullable=True)
    is_2fa_enabled = Column(Boolean, default=False)
    backup_codes = Column(String, nullable=True)  # JSON string of backup codes
    last_totp_used = Column(String, nullable=True)  # To prevent replay attacks

    # Profile fields
    avatar_url = Column(String, nullable=True)
    phone_number = Column(String, nullable=True)
    timezone = Column(String, default="UTC")

    # Multi-tenancy
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    roles = relationship("Role", secondary=user_roles, back_populates="users")
    tenant = relationship("Tenant", back_populates="users")
    api_keys = relationship(
        "APIKey", back_populates="user", cascade="all, delete-orphan"
    )

    def has_permission(self, permission_name: str) -> bool:
        """Check if user has a specific permission"""
        # Superusers have all permissions
        if self.is_superuser:
            return True

        for role in self.roles:
            for permission in role.permissions:
                if permission.name == permission_name:
                    return True
        return False

    def has_role(self, role_name: str) -> bool:
        """Check if user has a specific role"""
        for role in self.roles:
            if role.name == role_name:
                return True
        return False


class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    description = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    users = relationship("User", secondary=user_roles, back_populates="roles")
    permissions = relationship(
        "Permission", secondary=role_permissions, back_populates="roles"
    )


class Permission(Base):
    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    description = Column(String, nullable=True)
    resource = Column(String, nullable=False)  # e.g., 'users', 'posts', 'settings'
    action = Column(
        String, nullable=False
    )  # e.g., 'create', 'read', 'update', 'delete'

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    roles = relationship(
        "Role", secondary=role_permissions, back_populates="permissions"
    )
