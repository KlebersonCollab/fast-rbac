from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database.base import get_db
from app.models.user import User
from app.schemas.webhook import (
    WebhookCreate,
    WebhookDeliveryResponse,
    WebhookLogResponse,
    WebhookResponse,
    WebhookStats,
    WebhookTestRequest,
    WebhookUpdate,
)
from app.services.webhook_service import WebhookService

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.get("/delivery-logs", response_model=List[WebhookDeliveryResponse])
async def get_all_delivery_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all webhook delivery logs for the current user"""
    service = WebhookService(db)
    # Get all webhooks for the user first
    webhooks = service.get_webhooks(
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
        skip=0,
        limit=1000,
    )

    # Collect all deliveries from all webhooks
    all_deliveries = []
    for webhook in webhooks:
        deliveries = service.get_webhook_deliveries(
            webhook_id=webhook.id,
            user_id=current_user.id,
            tenant_id=current_user.tenant_id,
            skip=0,
            limit=50,  # Limit per webhook to avoid too much data
        )
        all_deliveries.extend(deliveries)

    # Sort by creation date (newest first) and apply pagination
    all_deliveries.sort(key=lambda x: x.created_at, reverse=True)
    return all_deliveries[skip : skip + limit]


@router.get("/analytics", response_model=dict)
async def get_webhooks_analytics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get webhook analytics for the current user"""
    service = WebhookService(db)
    webhooks = service.get_webhooks(
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
        skip=0,
        limit=1000,
    )

    # Calculate analytics
    total_webhooks = len(webhooks)
    active_webhooks = len([w for w in webhooks if w.is_active])
    inactive_webhooks = total_webhooks - active_webhooks

    # Calculate delivery stats
    total_deliveries = 0
    successful_deliveries = 0

    for webhook in webhooks:
        try:
            stats = service.get_webhook_stats(
                webhook_id=webhook.id,
                user_id=current_user.id,
                tenant_id=current_user.tenant_id,
                days=30,
            )
            total_deliveries += stats.total_deliveries
            successful_deliveries += stats.successful_deliveries
        except:
            pass

    return {
        "total_webhooks": total_webhooks,
        "active_webhooks": active_webhooks,
        "inactive_webhooks": inactive_webhooks,
        "new_webhooks_this_month": 0,  # Simplified
        "total_deliveries_30d": total_deliveries,
        "successful_deliveries_30d": successful_deliveries,
        "success_rate": (successful_deliveries / max(total_deliveries, 1)) * 100,
        "top_webhooks": [{"name": w.name, "url": w.url} for w in webhooks[:5]],
    }


@router.post("/", response_model=WebhookResponse)
async def create_webhook(
    webhook_data: WebhookCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new webhook for the current user's tenant."""
    service = WebhookService(db)
    webhook = service.create_webhook(
        webhook_data=webhook_data, current_user=current_user
    )
    return webhook


@router.get("/", response_model=List[WebhookResponse])
async def get_webhooks(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all webhooks for the current user's tenant."""
    service = WebhookService(db)
    webhooks = service.get_webhooks(current_user=current_user, skip=skip, limit=limit)
    return webhooks


@router.get("/{webhook_id}", response_model=WebhookResponse)
async def get_webhook(
    webhook_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a specific webhook within the user's tenant."""
    service = WebhookService(db)
    webhook = service.get_webhook(webhook_id=webhook_id, current_user=current_user)

    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found"
        )

    return webhook


@router.put("/{webhook_id}", response_model=WebhookResponse)
async def update_webhook(
    webhook_id: int,
    webhook_data: WebhookUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a webhook within the user's tenant."""
    service = WebhookService(db)
    webhook = service.update_webhook(
        webhook_id=webhook_id, webhook_data=webhook_data, current_user=current_user
    )

    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found"
        )

    return webhook


@router.delete("/{webhook_id}")
async def delete_webhook(
    webhook_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a webhook within the user's tenant."""
    service = WebhookService(db)
    success = service.delete_webhook(webhook_id=webhook_id, current_user=current_user)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found"
        )

    return {"message": "Webhook deleted successfully"}


@router.post("/{webhook_id}/test", response_model=WebhookDeliveryResponse)
async def test_webhook(
    webhook_id: int,
    test_request: WebhookTestRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Test a webhook with a test event."""
    service = WebhookService(db)
    # First, verify the user can access this webhook
    webhook = service.get_webhook(webhook_id, current_user)
    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found"
        )

    delivery = await service.test_webhook(
        webhook=webhook,
        event_type=test_request.event_type.value,
        test_data=test_request.test_data,
    )

    return delivery


@router.get("/{webhook_id}/deliveries", response_model=List[WebhookDeliveryResponse])
async def get_webhook_deliveries(
    webhook_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get webhook delivery history."""
    service = WebhookService(db)
    # First, verify the user can access this webhook
    webhook = service.get_webhook(webhook_id, current_user)
    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found"
        )

    deliveries = service.get_webhook_deliveries(
        webhook_id=webhook_id, skip=skip, limit=limit
    )
    return deliveries


@router.get("/{webhook_id}/logs", response_model=List[WebhookLogResponse])
async def get_webhook_logs(
    webhook_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get webhook logs."""
    service = WebhookService(db)
    # First, verify the user can access this webhook
    webhook = service.get_webhook(webhook_id, current_user)
    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found"
        )

    logs = service.get_webhook_logs(webhook_id=webhook_id, skip=skip, limit=limit)
    return logs


@router.get("/{webhook_id}/stats", response_model=WebhookStats)
async def get_webhook_stats(
    webhook_id: int,
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get webhook usage statistics."""
    service = WebhookService(db)
    # First, verify the user can access this webhook
    webhook = service.get_webhook(webhook_id, current_user)
    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found"
        )

    stats = service.get_webhook_stats(webhook_id=webhook_id, days=days)
    return stats


@router.post("/broadcast")
async def broadcast_webhook_event(
    event_type: str,
    data: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Broadcast an event to all subscribed webhooks (admin only)"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superusers can broadcast events",
        )

    service = WebhookService(db)
    await service.broadcast_event(
        event_type=event_type,
        data=data,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
    )

    return {"message": f"Event '{event_type}' broadcasted successfully"}


@router.get("/events/types")
async def get_webhook_event_types(current_user: User = Depends(get_current_user)):
    """Get available webhook event types"""
    from app.schemas.webhook import WebhookEvent

    return {
        "events": [
            {"type": event.value, "description": event.name.replace("_", " ").title()}
            for event in WebhookEvent
        ]
    }
