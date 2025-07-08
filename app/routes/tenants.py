from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database.base import get_db
from app.models.user import User
from app.schemas.tenant import (
    TenantCreate,
    TenantInvite,
    TenantResponse,
    TenantSettingsCreate,
    TenantSettingsResponse,
    TenantSettingsUpdate,
    TenantUpdate,
    TenantUsageStats,
)
from app.services.tenant_service import TenantService

router = APIRouter(prefix="/tenants", tags=["tenants"])


@router.post("/", response_model=TenantResponse)
async def create_tenant(
    tenant_data: TenantCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new tenant"""
    service = TenantService(db)
    tenant = service.create_tenant(tenant_data=tenant_data, owner_id=current_user.id)

    return tenant


@router.get("/", response_model=List[TenantResponse])
async def get_tenants(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    active_only: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all tenants (admin only)"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superusers can list all tenants",
        )

    service = TenantService(db)
    tenants = service.get_tenants(skip=skip, limit=limit, active_only=active_only)

    return tenants


@router.get("/my", response_model=Optional[TenantResponse])
async def get_my_tenant(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Get the current user's tenant"""
    if not current_user.tenant_id:
        return None

    service = TenantService(db)
    tenant = service.get_tenant(current_user.tenant_id)

    return tenant


@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
    tenant_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a specific tenant"""
    # Check if user can access this tenant
    if not current_user.is_superuser and current_user.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only access your own tenant",
        )

    service = TenantService(db)
    tenant = service.get_tenant(tenant_id)

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found"
        )

    return tenant


@router.put("/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    tenant_id: int,
    tenant_data: TenantUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a tenant"""
    # Check if user can update this tenant
    if not current_user.is_superuser and current_user.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own tenant",
        )

    service = TenantService(db)
    tenant = service.update_tenant(tenant_id=tenant_id, tenant_data=tenant_data)

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found"
        )

    return tenant


@router.delete("/{tenant_id}")
async def delete_tenant(
    tenant_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a tenant"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superusers can delete tenants",
        )

    service = TenantService(db)
    success = service.delete_tenant(tenant_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found"
        )

    return {"message": "Tenant deleted successfully"}


@router.get("/{tenant_id}/users", response_model=List[dict])
async def get_tenant_users(
    tenant_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all users for a tenant"""
    # Check if user can access this tenant
    if not current_user.is_superuser and current_user.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only access your own tenant's users",
        )

    service = TenantService(db)
    users = service.get_tenant_users(tenant_id=tenant_id, skip=skip, limit=limit)

    return [
        {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "is_active": user.is_active,
            "created_at": user.created_at,
        }
        for user in users
    ]


@router.post("/{tenant_id}/users/{user_id}")
async def add_user_to_tenant(
    tenant_id: int,
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Add a user to a tenant"""
    # Check if user can manage this tenant
    if not current_user.is_superuser and current_user.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only manage your own tenant's users",
        )

    service = TenantService(db)
    success = service.add_user_to_tenant(tenant_id=tenant_id, user_id=user_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tenant or user not found"
        )

    return {"message": "User added to tenant successfully"}


@router.delete("/{tenant_id}/users/{user_id}")
async def remove_user_from_tenant(
    tenant_id: int,
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Remove a user from a tenant"""
    # Check if user can manage this tenant
    if not current_user.is_superuser and current_user.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only manage your own tenant's users",
        )

    service = TenantService(db)
    success = service.remove_user_from_tenant(tenant_id=tenant_id, user_id=user_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found in tenant"
        )

    return {"message": "User removed from tenant successfully"}


@router.get("/{tenant_id}/settings", response_model=TenantSettingsResponse)
async def get_tenant_settings(
    tenant_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get tenant settings"""
    # Check if user can access this tenant
    if not current_user.is_superuser and current_user.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only access your own tenant's settings",
        )

    service = TenantService(db)
    settings = service.get_tenant_settings(tenant_id)

    if not settings:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tenant settings not found"
        )

    return settings


@router.put("/{tenant_id}/settings", response_model=TenantSettingsResponse)
async def update_tenant_settings(
    tenant_id: int,
    settings_data: TenantSettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update tenant settings"""
    # Check if user can manage this tenant
    if not current_user.is_superuser and current_user.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only manage your own tenant's settings",
        )

    service = TenantService(db)
    settings = service.update_tenant_settings(
        tenant_id=tenant_id, settings_data=settings_data
    )

    if not settings:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tenant settings not found"
        )

    return settings


@router.get("/{tenant_id}/stats", response_model=TenantUsageStats)
async def get_tenant_stats(
    tenant_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get tenant usage statistics"""
    # Check if user can access this tenant
    if not current_user.is_superuser and current_user.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only access your own tenant's stats",
        )

    service = TenantService(db)
    stats = service.get_tenant_stats(tenant_id)

    if not stats:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found"
        )

    return stats


@router.post("/{tenant_id}/invite")
async def generate_tenant_invite(
    tenant_id: int,
    invite_data: TenantInvite,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate tenant invitation code"""
    # Check if user can manage this tenant
    if not current_user.is_superuser and current_user.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only manage your own tenant's invitations",
        )

    service = TenantService(db)
    invite_code = service.generate_invite_code(
        tenant_id=tenant_id, expires_hours=invite_data.expires_hours
    )

    return {
        "invite_code": invite_code,
        "expires_hours": invite_data.expires_hours,
        "message": "Invitation code generated successfully",
    }


@router.post("/{tenant_id}/features/{feature_name}/enable")
async def enable_tenant_feature(
    tenant_id: int,
    feature_name: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Enable a tenant feature"""
    # Check if user can manage this tenant
    if not current_user.is_superuser and current_user.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only manage your own tenant's features",
        )

    service = TenantService(db)
    success = service.enable_tenant_feature(
        tenant_id=tenant_id, feature_name=feature_name
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found"
        )

    return {"message": f"Feature '{feature_name}' enabled successfully"}


@router.post("/{tenant_id}/features/{feature_name}/disable")
async def disable_tenant_feature(
    tenant_id: int,
    feature_name: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Disable a tenant feature"""
    # Check if user can manage this tenant
    if not current_user.is_superuser and current_user.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only manage your own tenant's features",
        )

    service = TenantService(db)
    success = service.disable_tenant_feature(
        tenant_id=tenant_id, feature_name=feature_name
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found"
        )

    return {"message": f"Feature '{feature_name}' disabled successfully"}
