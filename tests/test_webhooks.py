import asyncio
import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest
from fastapi import status

from app.models.webhook import Webhook, WebhookDelivery, WebhookLog
from app.schemas.webhook import (
    WebhookCreate,
    WebhookEvent,
    WebhookEventData,
    WebhookUpdate,
)
from app.services.webhook_service import WebhookService


class TestWebhookService:
    """Test Webhook service functionality"""

    def test_create_webhook(self, db_session, sample_user, sample_tenant):
        """Test creating a webhook"""
        service = WebhookService(db_session)

        webhook_data = WebhookCreate(
            name="Test Webhook",
            description="Test description",
            url="https://example.com/webhook",
            events=[WebhookEvent.USER_CREATED, WebhookEvent.USER_UPDATED],
            timeout_seconds=30,
            retry_enabled=True,
            max_retries=3,
        )

        webhook = service.create_webhook(
            webhook_data=webhook_data,
            user_id=sample_user.id,
            tenant_id=sample_tenant.id,
        )

        assert webhook.name == "Test Webhook"
        assert webhook.description == "Test description"
        assert webhook.url == "https://example.com/webhook"
        assert webhook.user_id == sample_user.id
        assert webhook.tenant_id == sample_tenant.id
        assert webhook.timeout_seconds == 30
        assert webhook.retry_enabled is True
        assert webhook.max_retries == 3
        assert webhook.is_active is True
        assert webhook.secret is not None  # Should be auto-generated

    def test_create_webhook_with_custom_secret(self, db_session, sample_user):
        """Test creating webhook with custom secret"""
        service = WebhookService(db_session)

        webhook_data = WebhookCreate(
            name="Test Webhook",
            url="https://example.com/webhook",
            secret="custom_secret_123",
            events=[WebhookEvent.USER_CREATED],
        )

        webhook = service.create_webhook(
            webhook_data=webhook_data, user_id=sample_user.id
        )

        assert webhook.secret == "custom_secret_123"

    def test_get_webhook(self, db_session, sample_webhook, sample_user):
        """Test getting a webhook"""
        service = WebhookService(db_session)

        webhook = service.get_webhook(
            webhook_id=sample_webhook.id, user_id=sample_user.id
        )

        assert webhook.id == sample_webhook.id
        assert webhook.name == sample_webhook.name

    def test_get_webhook_not_found(self, db_session, sample_user):
        """Test getting non-existent webhook"""
        service = WebhookService(db_session)

        webhook = service.get_webhook(webhook_id=999, user_id=sample_user.id)

        assert webhook is None

    def test_get_webhooks(self, db_session, sample_user, sample_tenant):
        """Test getting all webhooks for a user"""
        service = WebhookService(db_session)

        # Create multiple webhooks
        for i in range(3):
            webhook_data = WebhookCreate(
                name=f"Test Webhook {i}",
                url=f"https://example.com/webhook{i}",
                events=[WebhookEvent.USER_CREATED],
            )
            service.create_webhook(
                webhook_data=webhook_data,
                user_id=sample_user.id,
                tenant_id=sample_tenant.id,
            )

        webhooks = service.get_webhooks(
            user_id=sample_user.id, tenant_id=sample_tenant.id
        )

        assert len(webhooks) == 3
        assert all(w.user_id == sample_user.id for w in webhooks)

    def test_update_webhook(self, db_session, sample_webhook, sample_user):
        """Test updating a webhook"""
        service = WebhookService(db_session)

        update_data = WebhookUpdate(
            name="Updated Webhook",
            description="Updated description",
            url="https://example.com/updated-webhook",
            timeout_seconds=60,
        )

        updated_webhook = service.update_webhook(
            webhook_id=sample_webhook.id,
            webhook_data=update_data,
            user_id=sample_user.id,
        )

        assert updated_webhook.name == "Updated Webhook"
        assert updated_webhook.description == "Updated description"
        assert updated_webhook.url == "https://example.com/updated-webhook"
        assert updated_webhook.timeout_seconds == 60

    def test_delete_webhook(self, db_session, sample_webhook, sample_user):
        """Test deleting a webhook"""
        service = WebhookService(db_session)

        success = service.delete_webhook(
            webhook_id=sample_webhook.id, user_id=sample_user.id
        )

        assert success is True

        # Verify it's deleted
        webhook = service.get_webhook(
            webhook_id=sample_webhook.id, user_id=sample_user.id
        )
        assert webhook is None

    @pytest.mark.asyncio
    async def test_trigger_webhook(self, db_session, sample_webhook, sample_user):
        """Test triggering a webhook"""
        service = WebhookService(db_session)

        event_data = WebhookEventData(
            event_type=WebhookEvent.USER_CREATED.value,
            event_id="test-event-123",
            timestamp=datetime.utcnow(),
            user_id=sample_user.id,
            data={"user_id": sample_user.id, "username": "testuser"},
        )

        delivery = await service.trigger_webhook(sample_webhook, event_data)

        assert delivery.webhook_id == sample_webhook.id
        assert delivery.event_type == WebhookEvent.USER_CREATED.value
        assert delivery.event_id == "test-event-123"
        assert delivery.attempt_number == 1
        assert delivery.payload == event_data.dict()

    @pytest.mark.asyncio
    async def test_trigger_webhook_not_subscribed(
        self, db_session, sample_webhook, sample_user
    ):
        """Test triggering webhook for non-subscribed event"""
        service = WebhookService(db_session)

        # Create event that webhook is not subscribed to
        event_data = WebhookEventData(
            event_type=WebhookEvent.TENANT_CREATED.value,  # Not in sample_webhook.events
            event_id="test-event-123",
            timestamp=datetime.utcnow(),
            user_id=sample_user.id,
            data={"test": "data"},
        )

        with pytest.raises(Exception) as exc_info:
            await service.trigger_webhook(sample_webhook, event_data)

        assert "not subscribed to event" in str(exc_info.value)

    @pytest.mark.asyncio
    @patch("aiohttp.ClientSession.post")
    async def test_deliver_webhook_success(self, mock_post, db_session, sample_webhook):
        """Test successful webhook delivery"""
        service = WebhookService(db_session)

        # Mock successful HTTP response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value='{"success": true}')
        mock_response.headers = {"Content-Type": "application/json"}

        mock_post.return_value.__aenter__.return_value = mock_response

        # Create delivery
        delivery = WebhookDelivery(
            webhook_id=sample_webhook.id,
            event_type="user.created",
            event_id="test-123",
            payload={"test": "data"},
            attempt_number=1,
        )
        db_session.add(delivery)
        db_session.commit()
        db_session.refresh(delivery)

        # Deliver webhook
        await service._deliver_webhook(sample_webhook, delivery)

        # Verify delivery was marked as successful
        db_session.refresh(delivery)
        assert delivery.success is True
        assert delivery.status_code == 200
        assert delivery.response_body == '{"success": true}'

    @pytest.mark.asyncio
    @patch("aiohttp.ClientSession.post")
    async def test_deliver_webhook_failure(self, mock_post, db_session, sample_webhook):
        """Test failed webhook delivery"""
        service = WebhookService(db_session)

        # Mock failed HTTP response
        mock_response = AsyncMock()
        mock_response.status = 500
        mock_response.text = AsyncMock(
            return_value='{"error": "Internal Server Error"}'
        )
        mock_response.headers = {"Content-Type": "application/json"}

        mock_post.return_value.__aenter__.return_value = mock_response

        # Create delivery
        delivery = WebhookDelivery(
            webhook_id=sample_webhook.id,
            event_type="user.created",
            event_id="test-123",
            payload={"test": "data"},
            attempt_number=1,
        )
        db_session.add(delivery)
        db_session.commit()
        db_session.refresh(delivery)

        # Deliver webhook
        await service._deliver_webhook(sample_webhook, delivery)

        # Verify delivery was marked as failed
        db_session.refresh(delivery)
        assert delivery.success is False
        assert delivery.status_code == 500
        assert delivery.response_body == '{"error": "Internal Server Error"}'

    @pytest.mark.asyncio
    @patch("aiohttp.ClientSession.post")
    async def test_deliver_webhook_timeout(self, mock_post, db_session, sample_webhook):
        """Test webhook delivery timeout"""
        service = WebhookService(db_session)

        # Mock timeout
        mock_post.side_effect = asyncio.TimeoutError()

        # Create delivery
        delivery = WebhookDelivery(
            webhook_id=sample_webhook.id,
            event_type="user.created",
            event_id="test-123",
            payload={"test": "data"},
            attempt_number=1,
        )
        db_session.add(delivery)
        db_session.commit()
        db_session.refresh(delivery)

        # Deliver webhook
        await service._deliver_webhook(sample_webhook, delivery)

        # Verify delivery was marked as failed
        db_session.refresh(delivery)
        assert delivery.success is False
        assert delivery.error_message == "Request timeout"

    def test_get_webhook_deliveries(self, db_session, sample_webhook, sample_user):
        """Test getting webhook deliveries"""
        service = WebhookService(db_session)

        # Create deliveries
        for i in range(5):
            delivery = WebhookDelivery(
                webhook_id=sample_webhook.id,
                event_type="user.created",
                event_id=f"test-{i}",
                payload={"test": f"data{i}"},
                attempt_number=1,
            )
            db_session.add(delivery)

        db_session.commit()

        deliveries = service.get_webhook_deliveries(
            webhook_id=sample_webhook.id, user_id=sample_user.id
        )

        assert len(deliveries) == 5
        assert all(d.webhook_id == sample_webhook.id for d in deliveries)

    def test_get_webhook_logs(self, db_session, sample_webhook, sample_user):
        """Test getting webhook logs"""
        service = WebhookService(db_session)

        # Create logs
        for i in range(3):
            log = WebhookLog(
                webhook_id=sample_webhook.id,
                level="INFO",
                message=f"Test log message {i}",
                event_type="user.created",
            )
            db_session.add(log)

        db_session.commit()

        logs = service.get_webhook_logs(
            webhook_id=sample_webhook.id, user_id=sample_user.id
        )

        assert len(logs) == 3
        assert all(l.webhook_id == sample_webhook.id for l in logs)

    def test_get_webhook_stats(self, db_session, sample_webhook, sample_user):
        """Test getting webhook statistics"""
        service = WebhookService(db_session)

        # Create deliveries with different outcomes
        for i in range(10):
            success = i < 7  # 7 successful, 3 failed
            delivery = WebhookDelivery(
                webhook_id=sample_webhook.id,
                event_type="user.created",
                event_id=f"test-{i}",
                payload={"test": f"data{i}"},
                attempt_number=1,
                success=success,
                status_code=200 if success else 500,
                duration_ms=100 + i * 10,
            )
            db_session.add(delivery)

        db_session.commit()

        stats = service.get_webhook_stats(
            webhook_id=sample_webhook.id, user_id=sample_user.id, days=30
        )

        assert stats["total_deliveries"] == 10
        assert stats["successful_deliveries"] == 7
        assert stats["failed_deliveries"] == 3
        assert stats["success_rate"] == 70.0
        assert stats["average_response_time_ms"] is not None

    @pytest.mark.asyncio
    async def test_test_webhook(self, db_session, sample_webhook, sample_user):
        """Test webhook testing functionality"""
        service = WebhookService(db_session)

        with patch.object(service, "_deliver_webhook") as mock_deliver:
            delivery = await service.test_webhook(
                webhook_id=sample_webhook.id,
                user_id=sample_user.id,
                event_type="test.event",
                test_data={"test": "data"},
            )

            assert delivery.webhook_id == sample_webhook.id
            assert delivery.event_type == "test.event"
            assert delivery.payload["data"]["test"] == "data"
            mock_deliver.assert_called_once()

    @pytest.mark.asyncio
    async def test_broadcast_event(self, db_session, sample_user, sample_tenant):
        """Test broadcasting events to all subscribed webhooks"""
        service = WebhookService(db_session)

        # Create multiple webhooks subscribed to the same event
        webhooks = []
        for i in range(3):
            webhook_data = WebhookCreate(
                name=f"Webhook {i}",
                url=f"https://example.com/webhook{i}",
                events=[WebhookEvent.USER_CREATED],
            )
            webhook = service.create_webhook(
                webhook_data=webhook_data,
                user_id=sample_user.id,
                tenant_id=sample_tenant.id,
            )
            webhooks.append(webhook)

        with patch.object(service, "trigger_webhook") as mock_trigger:
            await service.broadcast_event(
                event_type=WebhookEvent.USER_CREATED.value,
                data={"user_id": sample_user.id},
                tenant_id=sample_tenant.id,
                user_id=sample_user.id,
            )

            # Should trigger all 3 webhooks
            assert mock_trigger.call_count == 3


class TestWebhookEndpoints:
    """Test Webhook REST endpoints"""

    def test_create_webhook_endpoint(self, client, auth_headers):
        """Test creating webhook via endpoint"""
        payload = {
            "name": "Test Webhook",
            "description": "Test description",
            "url": "https://example.com/webhook",
            "events": ["user.created", "user.updated"],
            "timeout_seconds": 30,
            "retry_enabled": True,
            "max_retries": 3,
        }

        response = client.post("/webhooks/", json=payload, headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "Test Webhook"
        assert data["url"] == "https://example.com/webhook"
        assert "user.created" in data["events"]
        assert "user.updated" in data["events"]

    def test_get_webhooks_endpoint(self, client, auth_headers):
        """Test getting webhooks via endpoint"""
        # Create a few webhooks first
        for i in range(3):
            payload = {
                "name": f"Test Webhook {i}",
                "url": f"https://example.com/webhook{i}",
                "events": ["user.created"],
            }
            client.post("/webhooks/", json=payload, headers=auth_headers)

        response = client.get("/webhooks/", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 3

    def test_get_webhook_endpoint(self, client, auth_headers):
        """Test getting specific webhook via endpoint"""
        # Create webhook
        payload = {
            "name": "Test Webhook",
            "url": "https://example.com/webhook",
            "events": ["user.created"],
        }
        create_response = client.post("/webhooks/", json=payload, headers=auth_headers)
        webhook_id = create_response.json()["id"]

        # Get the webhook
        response = client.get(f"/webhooks/{webhook_id}", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == webhook_id
        assert data["name"] == "Test Webhook"

    def test_update_webhook_endpoint(self, client, auth_headers):
        """Test updating webhook via endpoint"""
        # Create webhook
        payload = {
            "name": "Test Webhook",
            "url": "https://example.com/webhook",
            "events": ["user.created"],
        }
        create_response = client.post("/webhooks/", json=payload, headers=auth_headers)
        webhook_id = create_response.json()["id"]

        # Update the webhook
        update_payload = {
            "name": "Updated Webhook",
            "description": "Updated description",
            "url": "https://example.com/updated-webhook",
        }
        response = client.put(
            f"/webhooks/{webhook_id}", json=update_payload, headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "Updated Webhook"
        assert data["description"] == "Updated description"
        assert data["url"] == "https://example.com/updated-webhook"

    def test_delete_webhook_endpoint(self, client, auth_headers):
        """Test deleting webhook via endpoint"""
        # Create webhook
        payload = {
            "name": "Test Webhook",
            "url": "https://example.com/webhook",
            "events": ["user.created"],
        }
        create_response = client.post("/webhooks/", json=payload, headers=auth_headers)
        webhook_id = create_response.json()["id"]

        # Delete the webhook
        response = client.delete(f"/webhooks/{webhook_id}", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["message"] == "Webhook deleted successfully"

        # Verify it's deleted
        get_response = client.get(f"/webhooks/{webhook_id}", headers=auth_headers)
        assert get_response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_test_webhook_endpoint(self, client, auth_headers):
        """Test webhook testing via endpoint"""
        # Create webhook
        payload = {
            "name": "Test Webhook",
            "url": "https://example.com/webhook",
            "events": ["user.created"],
        }
        create_response = client.post("/webhooks/", json=payload, headers=auth_headers)
        webhook_id = create_response.json()["id"]

        # Test the webhook
        test_payload = {"event_type": "user.created", "test_data": {"test": "data"}}

        with patch("app.services.webhook_service.WebhookService._deliver_webhook"):
            response = client.post(
                f"/webhooks/{webhook_id}/test", json=test_payload, headers=auth_headers
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["webhook_id"] == webhook_id
            assert data["event_type"] == "user.created"

    def test_get_webhook_deliveries_endpoint(self, client, auth_headers):
        """Test getting webhook deliveries via endpoint"""
        # Create webhook
        payload = {
            "name": "Test Webhook",
            "url": "https://example.com/webhook",
            "events": ["user.created"],
        }
        create_response = client.post("/webhooks/", json=payload, headers=auth_headers)
        webhook_id = create_response.json()["id"]

        # Get deliveries (should be empty initially)
        response = client.get(
            f"/webhooks/{webhook_id}/deliveries", headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)

    def test_get_webhook_logs_endpoint(self, client, auth_headers):
        """Test getting webhook logs via endpoint"""
        # Create webhook
        payload = {
            "name": "Test Webhook",
            "url": "https://example.com/webhook",
            "events": ["user.created"],
        }
        create_response = client.post("/webhooks/", json=payload, headers=auth_headers)
        webhook_id = create_response.json()["id"]

        # Get logs (should be empty initially)
        response = client.get(f"/webhooks/{webhook_id}/logs", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)

    def test_get_webhook_stats_endpoint(self, client, auth_headers):
        """Test getting webhook stats via endpoint"""
        # Create webhook
        payload = {
            "name": "Test Webhook",
            "url": "https://example.com/webhook",
            "events": ["user.created"],
        }
        create_response = client.post("/webhooks/", json=payload, headers=auth_headers)
        webhook_id = create_response.json()["id"]

        # Get stats
        response = client.get(f"/webhooks/{webhook_id}/stats", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "total_deliveries" in data
        assert "successful_deliveries" in data
        assert "failed_deliveries" in data
        assert "success_rate" in data

    def test_get_webhook_event_types_endpoint(self, client, auth_headers):
        """Test getting available webhook event types"""
        response = client.get("/webhooks/events/types", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "events" in data
        assert isinstance(data["events"], list)
        assert len(data["events"]) > 0

        # Check that each event has type and description
        for event in data["events"]:
            assert "type" in event
            assert "description" in event

    def test_broadcast_event_admin_only(self, client, admin_auth_headers):
        """Test that only admins can broadcast events"""
        payload = {"event_type": "user.created", "data": {"user_id": 1}}

        response = client.post(
            "/webhooks/broadcast", json=payload, headers=admin_auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "broadcasted successfully" in data["message"]

    def test_broadcast_event_forbidden_for_regular_user(self, client, auth_headers):
        """Test that regular users can't broadcast events"""
        payload = {"event_type": "user.created", "data": {"user_id": 1}}

        response = client.post(
            "/webhooks/broadcast", json=payload, headers=auth_headers
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_unauthorized_access(self, client):
        """Test that endpoints require authentication"""
        response = client.get("/webhooks/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        payload = {
            "name": "Test Webhook",
            "url": "https://example.com/webhook",
            "events": ["user.created"],
        }
        response = client.post("/webhooks/", json=payload)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
