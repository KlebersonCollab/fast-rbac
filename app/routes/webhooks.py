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


@router.post("/", response_model=WebhookResponse)
async def create_webhook(
    webhook_data: WebhookCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new webhook"""
    service = WebhookService(db)
    webhook = service.create_webhook(
        webhook_data=webhook_data,
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
    )

    return webhook


@router.get("/", response_model=List[WebhookResponse])
async def get_webhooks(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all webhooks for the current user"""
    service = WebhookService(db)
    webhooks = service.get_webhooks(
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
        skip=skip,
        limit=limit,
    )

    return webhooks


@router.get("/{webhook_id}", response_model=WebhookResponse)
async def get_webhook(
    webhook_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a specific webhook"""
    service = WebhookService(db)
    webhook = service.get_webhook(
        webhook_id=webhook_id, user_id=current_user.id, tenant_id=current_user.tenant_id
    )

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
    """Update a webhook"""
    service = WebhookService(db)
    webhook = service.update_webhook(
        webhook_id=webhook_id,
        webhook_data=webhook_data,
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
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
    """Delete a webhook"""
    service = WebhookService(db)
    success = service.delete_webhook(
        webhook_id=webhook_id, user_id=current_user.id, tenant_id=current_user.tenant_id
    )

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
    """Test a webhook with a test event"""
    service = WebhookService(db)
    delivery = await service.test_webhook(
        webhook_id=webhook_id,
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
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
    """Get webhook delivery history"""
    service = WebhookService(db)
    deliveries = service.get_webhook_deliveries(
        webhook_id=webhook_id,
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
        skip=skip,
        limit=limit,
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
    """Get webhook logs"""
    service = WebhookService(db)
    logs = service.get_webhook_logs(
        webhook_id=webhook_id,
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
        skip=skip,
        limit=limit,
    )

    return logs


@router.get("/{webhook_id}/stats", response_model=WebhookStats)
async def get_webhook_stats(
    webhook_id: int,
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get webhook statistics"""
    service = WebhookService(db)
    stats = service.get_webhook_stats(
        webhook_id=webhook_id,
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
        days=days,
    )

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
