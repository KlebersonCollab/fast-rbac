from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database.base import get_db
from app.models.user import User
from app.schemas.api_key import (
    APIKeyCreate,
    APIKeyCreateResponse,
    APIKeyResponse,
    APIKeyUpdate,
    APIKeyUsageResponse,
    APIKeyUsageStats,
)
from app.services.api_key_service import APIKeyService

router = APIRouter(prefix="/api-keys", tags=["api-keys"])


@router.get("/stats", response_model=dict)
async def get_api_keys_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get global API keys statistics for the current user's tenant."""
    service = APIKeyService(db)
    api_keys = service.get_api_keys(current_user=current_user, limit=1000)

    # Calculate aggregated stats
    total_keys = len(api_keys)
    active_keys = len([key for key in api_keys if key.is_active])
    inactive_keys = total_keys - active_keys

    # Calculate usage stats (simplified version)
    total_requests = 0
    for api_key in api_keys:
        # Get usage for each key (last 30 days)
        try:
            stats = service.get_api_key_stats(
                api_key_id=api_key.id,
                current_user=current_user,
                days=30,
            )
            total_requests += stats.get("total_requests", 0)
        except Exception:
            pass

    return {
        "total_keys": total_keys,
        "active_keys": active_keys,
        "inactive_keys": inactive_keys,
        "total_requests_30d": total_requests,
        "average_requests_per_key": total_requests / max(total_keys, 1),
    }


@router.post("/", response_model=APIKeyCreateResponse)
async def create_api_key(
    api_key_data: APIKeyCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new API key for the current user's tenant."""
    service = APIKeyService(db)
    api_key, key = service.create_api_key(
        api_key_data=api_key_data, current_user=current_user
    )
    return APIKeyCreateResponse(api_key=api_key, key=key)


@router.get("/", response_model=List[APIKeyResponse])
async def get_api_keys(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all API keys for the current user's tenant."""
    service = APIKeyService(db)
    api_keys = service.get_api_keys(current_user=current_user, skip=skip, limit=limit)
    return api_keys


@router.get("/{api_key_id}", response_model=APIKeyResponse)
async def get_api_key(
    api_key_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a specific API key within the user's tenant."""
    service = APIKeyService(db)
    api_key = service.get_api_key(api_key_id=api_key_id, current_user=current_user)

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="API key not found"
        )

    return api_key


@router.put("/{api_key_id}", response_model=APIKeyResponse)
async def update_api_key(
    api_key_id: int,
    api_key_data: APIKeyUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update an API key within the user's tenant."""
    service = APIKeyService(db)
    api_key = service.update_api_key(
        api_key_id=api_key_id, api_key_data=api_key_data, current_user=current_user
    )

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="API key not found"
        )

    return api_key


@router.delete("/{api_key_id}")
async def delete_api_key(
    api_key_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete an API key within the user's tenant."""
    service = APIKeyService(db)
    success = service.delete_api_key(api_key_id=api_key_id, current_user=current_user)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="API key not found"
        )

    return {"message": "API key deleted successfully"}


@router.post("/{api_key_id}/rotate", response_model=APIKeyCreateResponse)
async def rotate_api_key(
    api_key_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Rotate (regenerate) an API key within the user's tenant."""
    service = APIKeyService(db)
    api_key, new_key = service.rotate_api_key(
        api_key_id=api_key_id, current_user=current_user
    )
    return APIKeyCreateResponse(api_key=api_key, key=new_key)


@router.get("/{api_key_id}/usage", response_model=List[APIKeyUsageResponse])
async def get_api_key_usage(
    api_key_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get API key usage history within the user's tenant."""
    service = APIKeyService(db)
    # First, verify the user can access this key
    key = service.get_api_key(api_key_id, current_user)
    if not key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="API key not found"
        )
    
    usage = service.get_api_key_usage(
        api_key_id=api_key_id, current_user=current_user, skip=skip, limit=limit
    )
    return usage


@router.get("/{api_key_id}/stats", response_model=APIKeyUsageStats)
async def get_api_key_stats_endpoint(
    api_key_id: int,
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get API key usage statistics within the user's tenant."""
    service = APIKeyService(db)
    # First, verify the user can access this key
    key = service.get_api_key(api_key_id, current_user)
    if not key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="API key not found"
        )

    stats = service.get_api_key_stats(
        api_key_id=api_key_id, current_user=current_user, days=days
    )
    return stats
