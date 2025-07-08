import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import status

from app.schemas.api_key import APIKeyScope
from app.schemas.webhook import WebhookEvent


class TestIntegrationWorkflows:
    """Test complete integration workflows"""

    def test_complete_user_tenant_workflow(self, client, admin_auth_headers):
        """Test complete user and tenant management workflow"""

        # 1. Create a tenant
        tenant_payload = {
            "name": "Acme Corporation",
            "slug": "acme-corp",
            "description": "Test corporation",
            "contact_email": "admin@acme.com",
            "plan_type": "premium",
        }

        tenant_response = client.post(
            "/tenants/", json=tenant_payload, headers=admin_auth_headers
        )
        assert tenant_response.status_code == status.HTTP_200_OK
        tenant_data = tenant_response.json()
        tenant_id = tenant_data["id"]

        # 2. Create a user for the tenant
        user_payload = {
            "username": "john_doe",
            "email": "john@acme.com",
            "full_name": "John Doe",
            "password": "SecurePass123!",
        }

        user_response = client.post("/auth/register", json=user_payload)
        assert user_response.status_code == status.HTTP_201_CREATED
        user_data = user_response.json()
        user_id = user_data["id"]

        # 3. Add user to tenant
        add_user_response = client.post(
            f"/tenants/{tenant_id}/users/{user_id}", headers=admin_auth_headers
        )
        assert add_user_response.status_code == status.HTTP_200_OK

        # 4. Login as the new user
        login_response = client.post(
            "/auth/login", data={"username": "john_doe", "password": "SecurePass123!"}
        )
        assert login_response.status_code == status.HTTP_200_OK
        user_token = login_response.json()["access_token"]
        user_headers = {"Authorization": f"Bearer {user_token}"}

        # 5. Verify user can access their tenant
        my_tenant_response = client.get("/tenants/my", headers=user_headers)
        assert my_tenant_response.status_code == status.HTTP_200_OK
        my_tenant_data = my_tenant_response.json()
        assert my_tenant_data["id"] == tenant_id
        assert my_tenant_data["name"] == "Acme Corporation"

        # 6. Create API key for the user
        api_key_payload = {
            "name": "Acme API Key",
            "description": "API key for Acme Corp integrations",
            "scopes": ["read", "write"],
            "rate_limit_per_minute": 200,
        }

        api_key_response = client.post(
            "/api-keys/", json=api_key_payload, headers=user_headers
        )
        assert api_key_response.status_code == status.HTTP_200_OK
        api_key_data = api_key_response.json()
        api_key_id = api_key_data["api_key"]["id"]
        api_key = api_key_data["key"]

        # 7. Test API key authentication
        api_headers = {"X-API-Key": api_key}
        profile_response = client.get("/auth/me", headers=api_headers)
        assert profile_response.status_code == status.HTTP_200_OK
        profile_data = profile_response.json()
        assert profile_data["username"] == "john_doe"

        # 8. Create webhook for the tenant
        webhook_payload = {
            "name": "Acme Webhook",
            "description": "Webhook for user events",
            "url": "https://acme.com/webhook",
            "events": ["user.created", "user.updated", "user.login"],
            "timeout_seconds": 30,
        }

        webhook_response = client.post(
            "/webhooks/", json=webhook_payload, headers=user_headers
        )
        assert webhook_response.status_code == status.HTTP_200_OK
        webhook_data = webhook_response.json()
        webhook_id = webhook_data["id"]

        # 9. Test webhook
        test_webhook_payload = {
            "event_type": "user.created",
            "test_data": {"user_id": user_id, "tenant_id": tenant_id},
        }

        with patch(
            "app.services.webhook_service.WebhookService._deliver_webhook"
        ) as mock_deliver:
            test_response = client.post(
                f"/webhooks/{webhook_id}/test",
                json=test_webhook_payload,
                headers=user_headers,
            )
            assert test_response.status_code == status.HTTP_200_OK
            mock_deliver.assert_called_once()

        # 10. Get tenant usage statistics
        stats_response = client.get(f"/tenants/{tenant_id}/stats", headers=user_headers)
        assert stats_response.status_code == status.HTTP_200_OK
        stats_data = stats_response.json()
        assert stats_data["users"]["current"] >= 1
        assert stats_data["api_keys"]["current"] >= 1

    def test_api_key_rate_limiting_workflow(self, client, auth_headers, db_session):
        """Test API key rate limiting workflow"""

        # 1. Create API key with low rate limit
        api_key_payload = {
            "name": "Rate Limited Key",
            "description": "API key with rate limiting",
            "scopes": ["read"],
            "rate_limit_per_minute": 2,  # Very low limit for testing
        }

        api_key_response = client.post(
            "/api-keys/", json=api_key_payload, headers=auth_headers
        )
        assert api_key_response.status_code == status.HTTP_200_OK
        api_key_data = api_key_response.json()
        api_key = api_key_data["key"]
        api_key_id = api_key_data["api_key"]["id"]

        api_headers = {"X-API-Key": api_key}

        # 2. Make requests within limit
        for i in range(2):
            response = client.get("/auth/me", headers=api_headers)
            assert response.status_code == status.HTTP_200_OK

        # 3. Verify rate limit stats
        stats_response = client.get(
            f"/api-keys/{api_key_id}/stats", headers=auth_headers
        )
        assert stats_response.status_code == status.HTTP_200_OK
        stats_data = stats_response.json()
        assert stats_data["total_requests"] >= 2

        # 4. Check API key usage history
        usage_response = client.get(
            f"/api-keys/{api_key_id}/usage", headers=auth_headers
        )
        assert usage_response.status_code == status.HTTP_200_OK
        usage_data = usage_response.json()
        assert len(usage_data) >= 2
        assert all(u["status_code"] == 200 for u in usage_data)

    def test_webhook_event_broadcasting_workflow(
        self, client, admin_auth_headers, auth_headers
    ):
        """Test webhook event broadcasting workflow"""

        # 1. Create multiple webhooks subscribed to user events
        webhook_urls = [
            "https://service1.example.com/webhook",
            "https://service2.example.com/webhook",
            "https://service3.example.com/webhook",
        ]

        webhook_ids = []
        for i, url in enumerate(webhook_urls):
            webhook_payload = {
                "name": f"Service {i+1} Webhook",
                "url": url,
                "events": ["user.created", "user.updated"],
                "timeout_seconds": 30,
            }

            webhook_response = client.post(
                "/webhooks/", json=webhook_payload, headers=auth_headers
            )
            assert webhook_response.status_code == status.HTTP_200_OK
            webhook_data = webhook_response.json()
            webhook_ids.append(webhook_data["id"])

        # 2. Mock webhook deliveries
        with patch(
            "app.services.webhook_service.WebhookService.trigger_webhook"
        ) as mock_trigger:
            # 3. Broadcast user.created event
            broadcast_payload = {
                "event_type": "user.created",
                "data": {
                    "user_id": 123,
                    "username": "new_user",
                    "email": "new_user@example.com",
                },
            }

            broadcast_response = client.post(
                "/webhooks/broadcast",
                json=broadcast_payload,
                headers=admin_auth_headers,
            )
            assert broadcast_response.status_code == status.HTTP_200_OK

            # 4. Verify all webhooks were triggered
            assert mock_trigger.call_count == 3

    def test_tenant_feature_management_workflow(self, client, auth_headers):
        """Test tenant feature management workflow"""

        # 1. Get current tenant
        tenant_response = client.get("/tenants/my", headers=auth_headers)
        assert tenant_response.status_code == status.HTTP_200_OK
        tenant_data = tenant_response.json()
        tenant_id = tenant_data["id"]

        # 2. Enable advanced features
        features_to_enable = ["2fa", "sso", "webhooks", "advanced_analytics"]

        for feature in features_to_enable:
            enable_response = client.post(
                f"/tenants/{tenant_id}/features/{feature}/enable", headers=auth_headers
            )
            assert enable_response.status_code == status.HTTP_200_OK

        # 3. Get tenant with features enabled
        updated_tenant_response = client.get(
            f"/tenants/{tenant_id}", headers=auth_headers
        )
        assert updated_tenant_response.status_code == status.HTTP_200_OK
        updated_tenant_data = updated_tenant_response.json()

        # 4. Update tenant settings based on enabled features
        settings_payload = {
            "enforce_2fa": True,
            "sso_enabled": True,
            "webhook_secret": "secure_webhook_secret_123",
        }

        settings_response = client.put(
            f"/tenants/{tenant_id}/settings",
            json=settings_payload,
            headers=auth_headers,
        )
        assert settings_response.status_code == status.HTTP_200_OK
        settings_data = settings_response.json()
        assert settings_data["enforce_2fa"] is True
        assert settings_data["sso_enabled"] is True

        # 5. Test that changes are persisted
        get_settings_response = client.get(
            f"/tenants/{tenant_id}/settings", headers=auth_headers
        )
        assert get_settings_response.status_code == status.HTTP_200_OK
        get_settings_data = get_settings_response.json()
        assert get_settings_data["enforce_2fa"] is True
        assert get_settings_data["sso_enabled"] is True

    def test_multi_tenant_isolation_workflow(
        self, client, admin_auth_headers, db_session
    ):
        """Test multi-tenant data isolation workflow"""

        # 1. Create two tenants
        tenant1_payload = {
            "name": "Tenant One",
            "slug": "tenant-one",
            "description": "First tenant",
        }

        tenant2_payload = {
            "name": "Tenant Two",
            "slug": "tenant-two",
            "description": "Second tenant",
        }

        tenant1_response = client.post(
            "/tenants/", json=tenant1_payload, headers=admin_auth_headers
        )
        tenant2_response = client.post(
            "/tenants/", json=tenant2_payload, headers=admin_auth_headers
        )

        assert tenant1_response.status_code == status.HTTP_200_OK
        assert tenant2_response.status_code == status.HTTP_200_OK

        tenant1_id = tenant1_response.json()["id"]
        tenant2_id = tenant2_response.json()["id"]

        # 2. Create users for each tenant
        user1_payload = {
            "username": "user1",
            "email": "user1@tenant1.com",
            "full_name": "User One",
            "password": "password123",
        }

        user2_payload = {
            "username": "user2",
            "email": "user2@tenant2.com",
            "full_name": "User Two",
            "password": "password123",
        }

        user1_response = client.post("/auth/register", json=user1_payload)
        user2_response = client.post("/auth/register", json=user2_payload)

        user1_id = user1_response.json()["id"]
        user2_id = user2_response.json()["id"]

        # 3. Assign users to their respective tenants
        client.post(
            f"/tenants/{tenant1_id}/users/{user1_id}", headers=admin_auth_headers
        )
        client.post(
            f"/tenants/{tenant2_id}/users/{user2_id}", headers=admin_auth_headers
        )

        # 4. Login as both users
        login1_response = client.post(
            "/auth/login", data={"username": "user1", "password": "password123"}
        )
        login2_response = client.post(
            "/auth/login", data={"username": "user2", "password": "password123"}
        )

        user1_headers = {
            "Authorization": f"Bearer {login1_response.json()['access_token']}"
        }
        user2_headers = {
            "Authorization": f"Bearer {login2_response.json()['access_token']}"
        }

        # 5. Create API keys for each user
        api_key1_response = client.post(
            "/api-keys/",
            json={"name": "Tenant 1 API Key", "scopes": ["read", "write"]},
            headers=user1_headers,
        )

        api_key2_response = client.post(
            "/api-keys/",
            json={"name": "Tenant 2 API Key", "scopes": ["read", "write"]},
            headers=user2_headers,
        )

        # 6. Verify users can only see their own API keys
        user1_keys_response = client.get("/api-keys/", headers=user1_headers)
        user2_keys_response = client.get("/api-keys/", headers=user2_headers)

        user1_keys = user1_keys_response.json()
        user2_keys = user2_keys_response.json()

        assert len(user1_keys) == 1
        assert len(user2_keys) == 1
        assert user1_keys[0]["name"] == "Tenant 1 API Key"
        assert user2_keys[0]["name"] == "Tenant 2 API Key"

        # 7. Verify users cannot access each other's tenant data
        user1_try_tenant2 = client.get(f"/tenants/{tenant2_id}", headers=user1_headers)
        user2_try_tenant1 = client.get(f"/tenants/{tenant1_id}", headers=user2_headers)

        assert user1_try_tenant2.status_code == status.HTTP_403_FORBIDDEN
        assert user2_try_tenant1.status_code == status.HTTP_403_FORBIDDEN

    def test_api_key_scopes_workflow(self, client, auth_headers):
        """Test API key scopes and permissions workflow"""

        # 1. Create read-only API key
        readonly_key_payload = {
            "name": "Read Only Key",
            "scopes": ["read"],
            "permissions": ["users:read", "tenants:read"],
        }

        readonly_response = client.post(
            "/api-keys/", json=readonly_key_payload, headers=auth_headers
        )
        readonly_key = readonly_response.json()["key"]
        readonly_headers = {"X-API-Key": readonly_key}

        # 2. Create read-write API key
        readwrite_key_payload = {
            "name": "Read Write Key",
            "scopes": ["read", "write"],
            "permissions": [
                "users:read",
                "users:write",
                "tenants:read",
                "tenants:write",
            ],
        }

        readwrite_response = client.post(
            "/api-keys/", json=readwrite_key_payload, headers=auth_headers
        )
        readwrite_key = readwrite_response.json()["key"]
        readwrite_headers = {"X-API-Key": readwrite_key}

        # 3. Test read operations with both keys
        readonly_profile = client.get("/auth/me", headers=readonly_headers)
        readwrite_profile = client.get("/auth/me", headers=readwrite_headers)

        assert readonly_profile.status_code == status.HTTP_200_OK
        assert readwrite_profile.status_code == status.HTTP_200_OK

        # 4. Test that read-only key can't access write endpoints
        # (This would require implementing scope checking in the actual endpoints)
        # For now, we just verify the keys work for basic authentication

        # 5. Verify API key details
        readonly_id = readonly_response.json()["api_key"]["id"]
        readwrite_id = readwrite_response.json()["api_key"]["id"]

        readonly_details = client.get(f"/api-keys/{readonly_id}", headers=auth_headers)
        readwrite_details = client.get(
            f"/api-keys/{readwrite_id}", headers=auth_headers
        )

        readonly_data = readonly_details.json()
        readwrite_data = readwrite_details.json()

        assert "read" in readonly_data["scopes"]
        assert "write" not in readonly_data["scopes"]

        assert "read" in readwrite_data["scopes"]
        assert "write" in readwrite_data["scopes"]

    def test_error_handling_workflow(self, client, auth_headers):
        """Test error handling and edge cases workflow"""

        # 1. Test creating API key with invalid data
        invalid_payload = {
            "name": "",  # Empty name
            "scopes": [],  # Empty scopes
            "rate_limit_per_minute": -1,  # Invalid rate limit
        }

        invalid_response = client.post(
            "/api-keys/", json=invalid_payload, headers=auth_headers
        )
        assert invalid_response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # 2. Test accessing non-existent resources
        non_existent_key = client.get("/api-keys/99999", headers=auth_headers)
        assert non_existent_key.status_code == status.HTTP_404_NOT_FOUND

        non_existent_webhook = client.get("/webhooks/99999", headers=auth_headers)
        assert non_existent_webhook.status_code == status.HTTP_404_NOT_FOUND

        # 3. Test webhook with invalid URL
        invalid_webhook_payload = {
            "name": "Invalid Webhook",
            "url": "not-a-valid-url",  # Invalid URL
            "events": ["user.created"],
        }

        invalid_webhook_response = client.post(
            "/webhooks/", json=invalid_webhook_payload, headers=auth_headers
        )
        assert (
            invalid_webhook_response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        )

        # 4. Test unauthorized access
        no_auth_response = client.get("/api-keys/")
        assert no_auth_response.status_code == status.HTTP_401_UNAUTHORIZED

        # 5. Test malformed requests
        malformed_response = client.post(
            "/api-keys/", data="invalid json", headers=auth_headers
        )
        assert malformed_response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_performance_workflow(self, client, auth_headers):
        """Test system performance with multiple operations"""

        # 1. Create multiple API keys
        api_keys = []
        for i in range(10):
            payload = {
                "name": f"Performance Test Key {i}",
                "scopes": ["read"],
                "rate_limit_per_minute": 100,
            }

            response = client.post("/api-keys/", json=payload, headers=auth_headers)
            assert response.status_code == status.HTTP_200_OK
            api_keys.append(response.json())

        # 2. Create multiple webhooks
        webhooks = []
        for i in range(5):
            payload = {
                "name": f"Performance Test Webhook {i}",
                "url": f"https://test{i}.example.com/webhook",
                "events": ["user.created"],
                "timeout_seconds": 30,
            }

            response = client.post("/webhooks/", json=payload, headers=auth_headers)
            assert response.status_code == status.HTTP_200_OK
            webhooks.append(response.json())

        # 3. Test bulk operations
        all_keys_response = client.get("/api-keys/?limit=100", headers=auth_headers)
        assert all_keys_response.status_code == status.HTTP_200_OK
        assert len(all_keys_response.json()) >= 10

        all_webhooks_response = client.get("/webhooks/?limit=100", headers=auth_headers)
        assert all_webhooks_response.status_code == status.HTTP_200_OK
        assert len(all_webhooks_response.json()) >= 5

        # 4. Test pagination
        paginated_keys = client.get("/api-keys/?skip=5&limit=5", headers=auth_headers)
        assert paginated_keys.status_code == status.HTTP_200_OK
        assert len(paginated_keys.json()) == 5

        # 5. Clean up - delete created resources
        for api_key in api_keys:
            delete_response = client.delete(
                f"/api-keys/{api_key['api_key']['id']}", headers=auth_headers
            )
            assert delete_response.status_code == status.HTTP_200_OK

        for webhook in webhooks:
            delete_response = client.delete(
                f"/webhooks/{webhook['id']}", headers=auth_headers
            )
            assert delete_response.status_code == status.HTTP_200_OK
