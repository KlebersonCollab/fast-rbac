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


@router.get("/analytics", response_model=dict)
async def get_tenants_analytics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get tenant analytics (admin only)"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superusers can view tenant analytics",
        )

    service = TenantService(db)
    # Get tenants respecting user's scope (all for superuser, own for others)
    tenants = service.get_tenants(current_user=current_user, limit=1000)

    # Calculate analytics
    total_tenants = len(tenants)
    active_tenants = len([t for t in tenants if t.is_active])
    inactive_tenants = total_tenants - active_tenants

    # Calculate by subscription plan
    plan_distribution = {}
    for tenant in tenants:
        plan = getattr(tenant, "plan_type", "free")
        plan_distribution[plan] = plan_distribution.get(plan, 0) + 1

    # Convert to list of dicts for DataFrame
    plan_distribution_list = [
        {"plan": plan, "count": count} for plan, count in plan_distribution.items()
    ]

    # Generate sample growth data
    from datetime import datetime, timedelta
    base_date = datetime.now() - timedelta(days=30)
    tenant_growth_data = []
    for i in range(30):
        date = base_date + timedelta(days=i)
        tenant_growth_data.append({
            "date": date.strftime("%Y-%m-%d"),
            "tenants": max(1, total_tenants - (30 - i) // 5)
        })

    # Calculate simulated revenue based on plan types
    revenue_per_plan = {"free": 0, "basic": 29, "premium": 99, "enterprise": 299}
    monthly_revenue = sum(revenue_per_plan.get(plan, 0) * count for plan, count in plan_distribution.items())

    return {
        "total_tenants": total_tenants,
        "active_tenants": active_tenants,
        "inactive_tenants": inactive_tenants,
        "new_tenants_this_month": 0,  # Simplified - would need date filtering
        "active_percentage": (active_tenants / total_tenants * 100) if total_tenants > 0 else 0,
        "monthly_revenue": monthly_revenue,
        "revenue_growth": monthly_revenue * 0.1,  # Simulated 10% growth
        "total_users": sum(1 for t in tenants),  # Simplified
        "new_users_this_month": 0,  # Simplified
        "plan_distribution": plan_distribution_list,
        "tenant_growth_data": tenant_growth_data,
        "top_tenants": [
            {"name": t.name, "users": 1} for t in tenants[:5]
        ],  # Simplified
    }


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
    """Get all tenants (superusers) or the user's own tenant."""
    service = TenantService(db)
    tenants = service.get_tenants(
        current_user=current_user, skip=skip, limit=limit, active_only=active_only
    )
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


@router.post("/{tenant_id}/verify")
async def verify_tenant(
    tenant_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Verify a tenant (admin only)"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superusers can verify tenants",
        )

    service = TenantService(db)
    tenant_data = TenantUpdate(is_verified=True)
    tenant = service.update_tenant(tenant_id=tenant_id, tenant_data=tenant_data)

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found"
        )

    return {"message": "Tenant verified successfully", "tenant_id": tenant_id}


@router.post("/{tenant_id}/suspend")
async def suspend_tenant(
    tenant_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Suspend a tenant (admin only)"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superusers can suspend tenants",
        )

    service = TenantService(db)
    tenant_data = TenantUpdate(is_active=False)
    tenant = service.update_tenant(tenant_id=tenant_id, tenant_data=tenant_data)

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found"
        )

    return {"message": "Tenant suspended successfully", "tenant_id": tenant_id}


@router.post("/{tenant_id}/activate")
async def activate_tenant(
    tenant_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Activate/reactivate a tenant (admin only)"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superusers can activate tenants",
        )

    service = TenantService(db)
    tenant_data = TenantUpdate(is_active=True)
    tenant = service.update_tenant(tenant_id=tenant_id, tenant_data=tenant_data)

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found"
        )

    return {"message": "Tenant activated successfully", "tenant_id": tenant_id}


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
