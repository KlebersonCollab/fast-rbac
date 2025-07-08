import secrets
import string
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status
from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from app.models.tenant import Tenant, TenantSettings
from app.models.user import User
from app.schemas.tenant import (
    TenantCreate,
    TenantSettingsCreate,
    TenantSettingsUpdate,
    TenantUpdate,
)


class TenantService:
    """Service for managing tenants"""

    def __init__(self, db: Session):
        self.db = db

    def create_tenant(self, tenant_data: TenantCreate, owner_id: int) -> Tenant:
        """Create a new tenant"""
        # Check if slug is unique
        existing_tenant = (
            self.db.query(Tenant).filter(Tenant.slug == tenant_data.slug).first()
        )
        if existing_tenant:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Tenant slug already exists",
            )

        # Check if owner exists
        owner = self.db.query(User).filter(User.id == owner_id).first()
        if not owner:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Owner user not found"
            )

        # Create tenant
        tenant = Tenant(
            name=tenant_data.name,
            slug=tenant_data.slug,
            description=tenant_data.description,
            contact_email=tenant_data.contact_email,
            contact_phone=tenant_data.contact_phone,
            plan_type=tenant_data.plan_type.value,
            custom_domain=tenant_data.custom_domain,
            is_active=True,
            is_verified=False,
        )

        self.db.add(tenant)
        self.db.commit()
        self.db.refresh(tenant)

        # Assign owner to tenant
        owner.tenant_id = tenant.id
        self.db.commit()

        # Create default tenant settings
        self.create_tenant_settings(tenant.id, TenantSettingsCreate())

        return tenant

    def get_tenant(self, tenant_id: int) -> Optional[Tenant]:
        """Get tenant by ID"""
        return self.db.query(Tenant).filter(Tenant.id == tenant_id).first()

    def get_tenant_by_slug(self, slug: str) -> Optional[Tenant]:
        """Get tenant by slug"""
        return self.db.query(Tenant).filter(Tenant.slug == slug).first()

    def get_tenants(
        self,
        current_user: User,
        skip: int = 0,
        limit: int = 100,
        active_only: bool = False,
    ) -> List[Tenant]:
        """
        Get tenants.
        - Superusers can see all tenants.
        - Regular users can only see their own tenant.
        """
        query = self.db.query(Tenant)

        if not current_user.is_superuser:
            if not current_user.tenant_id:
                return []  # No tenant assigned, can't see any
            query = query.filter(Tenant.id == current_user.tenant_id)

        if active_only:
            query = query.filter(Tenant.is_active == True)

        return query.offset(skip).limit(limit).all()

    def update_tenant(
        self, tenant_id: int, tenant_data: TenantUpdate
    ) -> Optional[Tenant]:
        """Update a tenant"""
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            return None

        # Update fields
        if tenant_data.name is not None:
            tenant.name = tenant_data.name
        if tenant_data.description is not None:
            tenant.description = tenant_data.description
        if tenant_data.contact_email is not None:
            tenant.contact_email = tenant_data.contact_email
        if tenant_data.contact_phone is not None:
            tenant.contact_phone = tenant_data.contact_phone
        if tenant_data.plan_type is not None:
            tenant.plan_type = tenant_data.plan_type.value
        if tenant_data.max_users is not None:
            tenant.max_users = tenant_data.max_users
        if tenant_data.max_api_keys is not None:
            tenant.max_api_keys = tenant_data.max_api_keys
        if tenant_data.max_storage_mb is not None:
            tenant.max_storage_mb = tenant_data.max_storage_mb
        if tenant_data.features is not None:
            tenant.features = tenant_data.features
        if tenant_data.custom_domain is not None:
            tenant.custom_domain = tenant_data.custom_domain
        if tenant_data.is_active is not None:
            tenant.is_active = tenant_data.is_active
        if tenant_data.is_verified is not None:
            tenant.is_verified = tenant_data.is_verified

        self.db.commit()
        self.db.refresh(tenant)

        return tenant

    def delete_tenant(self, tenant_id: int) -> bool:
        """Delete a tenant (hard delete - removes from database)"""
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            return False

        # Remove all users from this tenant first
        users = self.db.query(User).filter(User.tenant_id == tenant_id).all()
        for user in users:
            user.tenant_id = None

        # Delete tenant settings
        self.db.query(TenantSettings).filter(TenantSettings.tenant_id == tenant_id).delete()

        # Delete the tenant
        self.db.delete(tenant)
        self.db.commit()

        return True

    def get_tenant_users(
        self, tenant_id: int, skip: int = 0, limit: int = 100
    ) -> List[User]:
        """Get all users for a tenant"""
        return (
            self.db.query(User)
            .filter(User.tenant_id == tenant_id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def add_user_to_tenant(self, tenant_id: int, user_id: int) -> bool:
        """Add user to tenant"""
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            return False

        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return False

        # Check tenant limits
        if not tenant.can_add_user():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User limit reached for this tenant",
            )

        user.tenant_id = tenant_id
        self.db.commit()

        return True

    def remove_user_from_tenant(self, tenant_id: int, user_id: int) -> bool:
        """Remove user from tenant"""
        user = (
            self.db.query(User)
            .filter(User.id == user_id, User.tenant_id == tenant_id)
            .first()
        )

        if not user:
            return False

        user.tenant_id = None
        self.db.commit()

        return True

    def get_tenant_settings(self, tenant_id: int) -> Optional[TenantSettings]:
        """Get tenant settings"""
        return (
            self.db.query(TenantSettings)
            .filter(TenantSettings.tenant_id == tenant_id)
            .first()
        )

    def create_tenant_settings(
        self, tenant_id: int, settings_data: TenantSettingsCreate
    ) -> TenantSettings:
        """Create tenant settings"""
        # Check if settings already exist
        existing_settings = self.get_tenant_settings(tenant_id)
        if existing_settings:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Tenant settings already exist",
            )

        settings = TenantSettings(
            tenant_id=tenant_id,
            logo_url=settings_data.logo_url,
            primary_color=settings_data.primary_color,
            secondary_color=settings_data.secondary_color,
            allow_registration=settings_data.allow_registration,
            require_email_verification=settings_data.require_email_verification,
            enforce_2fa=settings_data.enforce_2fa,
            password_policy=settings_data.password_policy,
            sso_enabled=settings_data.sso_enabled,
            sso_provider=settings_data.sso_provider,
            sso_config=settings_data.sso_config,
            webhook_secret=settings_data.webhook_secret,
        )

        self.db.add(settings)
        self.db.commit()
        self.db.refresh(settings)

        return settings

    def update_tenant_settings(
        self, tenant_id: int, settings_data: TenantSettingsUpdate
    ) -> Optional[TenantSettings]:
        """Update tenant settings"""
        settings = self.get_tenant_settings(tenant_id)
        if not settings:
            return None

        # Update fields
        if settings_data.logo_url is not None:
            settings.logo_url = settings_data.logo_url
        if settings_data.primary_color is not None:
            settings.primary_color = settings_data.primary_color
        if settings_data.secondary_color is not None:
            settings.secondary_color = settings_data.secondary_color
        if settings_data.allow_registration is not None:
            settings.allow_registration = settings_data.allow_registration
        if settings_data.require_email_verification is not None:
            settings.require_email_verification = (
                settings_data.require_email_verification
            )
        if settings_data.enforce_2fa is not None:
            settings.enforce_2fa = settings_data.enforce_2fa
        if settings_data.password_policy is not None:
            settings.password_policy = settings_data.password_policy
        if settings_data.sso_enabled is not None:
            settings.sso_enabled = settings_data.sso_enabled
        if settings_data.sso_provider is not None:
            settings.sso_provider = settings_data.sso_provider
        if settings_data.sso_config is not None:
            settings.sso_config = settings_data.sso_config
        if settings_data.webhook_secret is not None:
            settings.webhook_secret = settings_data.webhook_secret

        self.db.commit()
        self.db.refresh(settings)

        return settings

    def generate_invite_code(self, tenant_id: int, expires_hours: int = 48) -> str:
        """Generate invitation code for tenant"""
        # Simple invite code generation (in production, use signed tokens)
        code = "".join(
            secrets.choice(string.ascii_letters + string.digits) for _ in range(12)
        )

        # Store in cache or database (simplified for demo)
        # In production, use Redis or database table for invite codes

        return f"TENANT_{tenant_id}_{code}"

    def validate_invite_code(self, invite_code: str) -> Optional[int]:
        """Validate invitation code and return tenant ID"""
        # Simple validation (in production, use proper token verification)
        if not invite_code.startswith("TENANT_"):
            return None

        try:
            parts = invite_code.split("_")
            if len(parts) >= 3:
                tenant_id = int(parts[1])

                # Check if tenant exists and is active
                tenant = self.get_tenant(tenant_id)
                if tenant and tenant.is_active:
                    return tenant_id
        except ValueError:
            pass

        return None

    def get_tenant_stats(self, tenant_id: int) -> Dict[str, Any]:
        """Get tenant statistics"""
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            return {}

        # Get basic stats
        stats = tenant.get_usage_stats()

        # Add more detailed stats
        total_api_requests = 0  # Would query from api_key_usage table
        active_users_last_30_days = 0  # Would query from user activity

        stats.update(
            {
                "total_api_requests": total_api_requests,
                "active_users_last_30_days": active_users_last_30_days,
                "features": tenant.features or {},
                "created_at": tenant.created_at,
                "last_activity": None,  # Would track last user activity
            }
        )

        return stats

    def check_tenant_feature(self, tenant_id: int, feature_name: str) -> bool:
        """Check if tenant has a specific feature enabled"""
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            return False

        return tenant.get_feature(feature_name)

    def enable_tenant_feature(self, tenant_id: int, feature_name: str) -> bool:
        """Enable a feature for tenant"""
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            return False

        tenant.set_feature(feature_name, True)
        self.db.commit()

        return True

    def disable_tenant_feature(self, tenant_id: int, feature_name: str) -> bool:
        """Disable a feature for tenant"""
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            return False

        tenant.set_feature(feature_name, False)
        self.db.commit()

        return True
