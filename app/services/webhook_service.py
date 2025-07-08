import asyncio
import json
import secrets
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import aiohttp
from fastapi import HTTPException, status
from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from app.models.tenant import Tenant
from app.models.user import User
from app.models.webhook import Webhook, WebhookDelivery, WebhookEvent, WebhookLog
from app.schemas.webhook import WebhookCreate, WebhookEventData, WebhookUpdate


class WebhookService:
    """Service for managing webhooks"""

    def __init__(self, db: Session):
        self.db = db

    def create_webhook(
        self, webhook_data: WebhookCreate, user_id: int, tenant_id: Optional[int] = None
    ) -> Webhook:
        """Create a new webhook"""
        # Check if user exists
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        # Check tenant if specified
        if tenant_id:
            tenant = self.db.query(Tenant).filter(Tenant.id == tenant_id).first()
            if not tenant:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found"
                )

        # Generate secret if not provided
        secret = webhook_data.secret
        if not secret:
            secret = secrets.token_urlsafe(32)

        # Create webhook
        webhook = Webhook(
            name=webhook_data.name,
            description=webhook_data.description,
            url=webhook_data.url,
            secret=secret,
            events=webhook_data.events,
            headers=webhook_data.headers,
            timeout_seconds=webhook_data.timeout_seconds,
            retry_enabled=webhook_data.retry_enabled,
            max_retries=webhook_data.max_retries,
            retry_delay_seconds=webhook_data.retry_delay_seconds,
            user_id=user_id,
            tenant_id=tenant_id,
        )

        self.db.add(webhook)
        self.db.commit()
        self.db.refresh(webhook)

        return webhook

    def get_webhook(
        self, webhook_id: int, user_id: int, tenant_id: Optional[int] = None
    ) -> Optional[Webhook]:
        """Get webhook by ID"""
        query = self.db.query(Webhook).filter(
            Webhook.id == webhook_id, Webhook.user_id == user_id
        )

        if tenant_id:
            query = query.filter(Webhook.tenant_id == tenant_id)

        return query.first()

    def get_webhooks(
        self,
        user_id: int,
        tenant_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Webhook]:
        """Get all webhooks for a user"""
        query = self.db.query(Webhook).filter(Webhook.user_id == user_id)

        if tenant_id:
            query = query.filter(Webhook.tenant_id == tenant_id)

        return query.offset(skip).limit(limit).all()

    def update_webhook(
        self,
        webhook_id: int,
        webhook_data: WebhookUpdate,
        user_id: int,
        tenant_id: Optional[int] = None,
    ) -> Optional[Webhook]:
        """Update a webhook"""
        webhook = self.get_webhook(webhook_id, user_id, tenant_id)
        if not webhook:
            return None

        # Update fields
        if webhook_data.name is not None:
            webhook.name = webhook_data.name
        if webhook_data.description is not None:
            webhook.description = webhook_data.description
        if webhook_data.url is not None:
            webhook.url = webhook_data.url
        if webhook_data.secret is not None:
            webhook.secret = webhook_data.secret
        if webhook_data.events is not None:
            webhook.events = webhook_data.events
        if webhook_data.headers is not None:
            webhook.headers = webhook_data.headers
        if webhook_data.timeout_seconds is not None:
            webhook.timeout_seconds = webhook_data.timeout_seconds
        if webhook_data.retry_enabled is not None:
            webhook.retry_enabled = webhook_data.retry_enabled
        if webhook_data.max_retries is not None:
            webhook.max_retries = webhook_data.max_retries
        if webhook_data.retry_delay_seconds is not None:
            webhook.retry_delay_seconds = webhook_data.retry_delay_seconds
        if webhook_data.is_active is not None:
            webhook.is_active = webhook_data.is_active

        self.db.commit()
        self.db.refresh(webhook)

        return webhook

    def delete_webhook(
        self, webhook_id: int, user_id: int, tenant_id: Optional[int] = None
    ) -> bool:
        """Delete a webhook"""
        webhook = self.get_webhook(webhook_id, user_id, tenant_id)
        if not webhook:
            return False

        self.db.delete(webhook)
        self.db.commit()

        return True

    async def trigger_webhook(
        self, webhook: Webhook, event_data: WebhookEventData
    ) -> WebhookDelivery:
        """Trigger a webhook delivery"""
        # Check if webhook is subscribed to this event
        if not webhook.is_subscribed_to(event_data.event_type):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Webhook is not subscribed to event: {event_data.event_type}",
            )

        # Create delivery record
        delivery = WebhookDelivery(
            webhook_id=webhook.id,
            event_type=event_data.event_type,
            event_id=event_data.event_id,
            payload=event_data.dict(),
            attempt_number=1,
        )

        self.db.add(delivery)
        self.db.commit()
        self.db.refresh(delivery)

        # Trigger delivery asynchronously
        asyncio.create_task(self._deliver_webhook(webhook, delivery))

        return delivery

    async def _deliver_webhook(self, webhook: Webhook, delivery: WebhookDelivery):
        """Deliver webhook payload"""
        try:
            # Prepare payload
            payload = json.dumps(delivery.payload)

            # Prepare headers
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "FastAPI-RBAC-Webhook/1.0",
                "X-Webhook-ID": str(webhook.id),
                "X-Event-Type": delivery.event_type,
                "X-Event-ID": delivery.event_id,
                "X-Delivery-ID": str(delivery.id),
                "X-Timestamp": datetime.utcnow().isoformat(),
            }

            # Add signature if secret is provided
            if webhook.secret:
                signature = webhook.generate_signature(payload)
                if signature:
                    headers["X-Webhook-Signature"] = signature

            # Add custom headers
            if webhook.headers:
                headers.update(webhook.get_custom_headers())

            # Record start time
            start_time = datetime.utcnow()

            # Make HTTP request
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    webhook.url,
                    data=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=webhook.timeout_seconds),
                ) as response:
                    # Calculate duration
                    duration_ms = int(
                        (datetime.utcnow() - start_time).total_seconds() * 1000
                    )

                    # Read response
                    response_body = await response.text()
                    response_headers = dict(response.headers)

                    # Update delivery record
                    delivery.mark_delivered(
                        status_code=response.status,
                        response_body=response_body,
                        response_headers=response_headers,
                        duration_ms=duration_ms,
                    )

                    # Update webhook status
                    if delivery.is_successful:
                        webhook.mark_success()
                        self._log_webhook_event(
                            webhook,
                            "INFO",
                            f"Webhook delivered successfully: {response.status}",
                        )
                    else:
                        webhook.mark_failure()
                        self._log_webhook_event(
                            webhook,
                            "WARN",
                            f"Webhook delivery failed: {response.status}",
                        )

                        # Schedule retry if needed
                        if webhook.should_retry():
                            await self._schedule_retry(webhook, delivery)

        except asyncio.TimeoutError:
            delivery.mark_failed("Request timeout")
            webhook.mark_failure()
            self._log_webhook_event(webhook, "ERROR", "Webhook delivery timed out")

            if webhook.should_retry():
                await self._schedule_retry(webhook, delivery)

        except Exception as e:
            delivery.mark_failed(str(e))
            webhook.mark_failure()
            self._log_webhook_event(
                webhook, "ERROR", f"Webhook delivery error: {str(e)}"
            )

            if webhook.should_retry():
                await self._schedule_retry(webhook, delivery)

        finally:
            self.db.commit()

    async def _schedule_retry(
        self, webhook: Webhook, original_delivery: WebhookDelivery
    ):
        """Schedule webhook retry"""
        if original_delivery.attempt_number >= webhook.max_retries:
            return

        # Create retry delivery
        retry_delivery = WebhookDelivery(
            webhook_id=webhook.id,
            event_type=original_delivery.event_type,
            event_id=original_delivery.event_id,
            payload=original_delivery.payload,
            attempt_number=original_delivery.attempt_number + 1,
        )

        self.db.add(retry_delivery)
        self.db.commit()
        self.db.refresh(retry_delivery)

        # Schedule retry after delay
        await asyncio.sleep(webhook.retry_delay_seconds)
        await self._deliver_webhook(webhook, retry_delivery)

    def _log_webhook_event(
        self, webhook: Webhook, level: str, message: str, details: Optional[Dict] = None
    ):
        """Log webhook event"""
        log = WebhookLog(
            webhook_id=webhook.id, level=level, message=message, details=details
        )

        self.db.add(log)
        self.db.commit()

    def get_webhook_deliveries(
        self,
        webhook_id: int,
        user_id: int,
        tenant_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[WebhookDelivery]:
        """Get webhook deliveries"""
        # Verify ownership
        webhook = self.get_webhook(webhook_id, user_id, tenant_id)
        if not webhook:
            return []

        return (
            self.db.query(WebhookDelivery)
            .filter(WebhookDelivery.webhook_id == webhook_id)
            .order_by(WebhookDelivery.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_webhook_logs(
        self,
        webhook_id: int,
        user_id: int,
        tenant_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[WebhookLog]:
        """Get webhook logs"""
        # Verify ownership
        webhook = self.get_webhook(webhook_id, user_id, tenant_id)
        if not webhook:
            return []

        return (
            self.db.query(WebhookLog)
            .filter(WebhookLog.webhook_id == webhook_id)
            .order_by(WebhookLog.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_webhook_stats(
        self,
        webhook_id: int,
        user_id: int,
        tenant_id: Optional[int] = None,
        days: int = 30,
    ) -> Dict[str, Any]:
        """Get webhook statistics"""
        # Verify ownership
        webhook = self.get_webhook(webhook_id, user_id, tenant_id)
        if not webhook:
            return {}

        # Date range
        start_date = datetime.utcnow() - timedelta(days=days)

        # Basic stats
        total_deliveries = (
            self.db.query(func.count(WebhookDelivery.id))
            .filter(
                WebhookDelivery.webhook_id == webhook_id,
                WebhookDelivery.created_at >= start_date,
            )
            .scalar()
            or 0
        )

        successful_deliveries = (
            self.db.query(func.count(WebhookDelivery.id))
            .filter(
                WebhookDelivery.webhook_id == webhook_id,
                WebhookDelivery.created_at >= start_date,
                WebhookDelivery.success == True,
            )
            .scalar()
            or 0
        )

        # Average response time
        avg_response_time = (
            self.db.query(func.avg(WebhookDelivery.duration_ms))
            .filter(
                WebhookDelivery.webhook_id == webhook_id,
                WebhookDelivery.created_at >= start_date,
                WebhookDelivery.duration_ms.isnot(None),
            )
            .scalar()
        )

        # Most common events
        most_common_events = (
            self.db.query(
                WebhookDelivery.event_type,
                func.count(WebhookDelivery.id).label("count"),
            )
            .filter(
                WebhookDelivery.webhook_id == webhook_id,
                WebhookDelivery.created_at >= start_date,
            )
            .group_by(WebhookDelivery.event_type)
            .order_by(func.count(WebhookDelivery.id).desc())
            .limit(10)
            .all()
        )

        # Status code distribution
        status_distribution = (
            self.db.query(
                WebhookDelivery.status_code,
                func.count(WebhookDelivery.id).label("count"),
            )
            .filter(
                WebhookDelivery.webhook_id == webhook_id,
                WebhookDelivery.created_at >= start_date,
                WebhookDelivery.status_code.isnot(None),
            )
            .group_by(WebhookDelivery.status_code)
            .all()
        )

        return {
            "total_deliveries": total_deliveries,
            "successful_deliveries": successful_deliveries,
            "failed_deliveries": total_deliveries - successful_deliveries,
            "success_rate": (
                (successful_deliveries / total_deliveries * 100)
                if total_deliveries > 0
                else 0
            ),
            "average_response_time_ms": (
                float(avg_response_time) if avg_response_time else None
            ),
            "deliveries_per_hour": total_deliveries / (days * 24) if days > 0 else 0,
            "most_common_events": [
                {"event_type": event_type, "count": count}
                for event_type, count in most_common_events
            ],
            "status_code_distribution": {
                str(status_code): count for status_code, count in status_distribution
            },
        }

    async def test_webhook(
        self,
        webhook_id: int,
        user_id: int,
        tenant_id: Optional[int] = None,
        event_type: str = "test.event",
        test_data: Optional[Dict] = None,
    ) -> WebhookDelivery:
        """Test a webhook with a test event"""
        webhook = self.get_webhook(webhook_id, user_id, tenant_id)
        if not webhook:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found"
            )

        # Create test event data
        test_event = WebhookEventData(
            event_type=event_type,
            event_id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            tenant_id=tenant_id,
            user_id=user_id,
            data=test_data or {"message": "This is a test webhook"},
        )

        # Force subscription to test event
        original_events = webhook.events
        webhook.events = [event_type]

        try:
            # Trigger webhook
            delivery = await self.trigger_webhook(webhook, test_event)
            return delivery
        finally:
            # Restore original events
            webhook.events = original_events
            self.db.commit()

    async def broadcast_event(
        self,
        event_type: str,
        data: Dict[str, Any],
        tenant_id: Optional[int] = None,
        user_id: Optional[int] = None,
    ):
        """Broadcast an event to all subscribed webhooks"""
        # Get all active webhooks subscribed to this event
        query = self.db.query(Webhook).filter(
            Webhook.is_active == True, Webhook.events.contains([event_type])
        )

        if tenant_id:
            query = query.filter(Webhook.tenant_id == tenant_id)

        webhooks = query.all()

        # Create event data
        event_data = WebhookEventData(
            event_type=event_type,
            event_id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            tenant_id=tenant_id,
            user_id=user_id,
            data=data,
        )

        # Trigger all webhooks
        for webhook in webhooks:
            try:
                await self.trigger_webhook(webhook, event_data)
            except Exception as e:
                self._log_webhook_event(
                    webhook, "ERROR", f"Failed to trigger webhook: {str(e)}"
                )
