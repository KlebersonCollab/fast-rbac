from unittest.mock import MagicMock, patch

import pytest
from fastapi import status

from app.models.api_key import APIKey, APIKeyUsage
from app.schemas.api_key import APIKeyCreate, APIKeyScope, APIKeyUpdate
from app.services.api_key_service import APIKeyService


class TestAPIKeyService:
    """Test API Key service functionality"""

    def test_create_api_key(self, db_session, sample_user, sample_tenant):
        """Test creating an API key"""
        service = APIKeyService(db_session)

        api_key_data = APIKeyCreate(
            name="Test API Key",
            description="Test description",
            scopes=[APIKeyScope.READ, APIKeyScope.WRITE],
            rate_limit_per_minute=50,
        )

        api_key, key = service.create_api_key(
            api_key_data=api_key_data,
            user_id=sample_user.id,
            tenant_id=sample_tenant.id,
        )

        assert api_key.name == "Test API Key"
        assert api_key.description == "Test description"
        assert api_key.user_id == sample_user.id
        assert api_key.tenant_id == sample_tenant.id
        assert api_key.rate_limit_per_minute == 50
        assert api_key.is_active is True
        assert key.startswith("rbac_")
        assert api_key.key_prefix == key[:12]

    def test_create_api_key_without_tenant(self, db_session, sample_user):
        """Test creating an API key without tenant"""
        service = APIKeyService(db_session)

        api_key_data = APIKeyCreate(name="Test API Key", scopes=[APIKeyScope.READ])

        api_key, key = service.create_api_key(
            api_key_data=api_key_data, user_id=sample_user.id
        )

        assert api_key.tenant_id is None
        assert key.startswith("rbac_")

    def test_create_api_key_tenant_limit_exceeded(
        self, db_session, sample_user, sample_tenant
    ):
        """Test creating API key when tenant limit is exceeded"""
        # Set tenant limit to 0
        sample_tenant.max_api_keys = 0
        db_session.commit()

        service = APIKeyService(db_session)

        api_key_data = APIKeyCreate(name="Test API Key", scopes=[APIKeyScope.READ])

        with pytest.raises(Exception) as exc_info:
            service.create_api_key(
                api_key_data=api_key_data,
                user_id=sample_user.id,
                tenant_id=sample_tenant.id,
            )

        assert "API key limit reached" in str(exc_info.value)

    def test_get_api_key(self, db_session, sample_api_key, sample_user):
        """Test getting an API key"""
        service = APIKeyService(db_session)

        api_key = service.get_api_key(
            api_key_id=sample_api_key.id, user_id=sample_user.id
        )

        assert api_key.id == sample_api_key.id
        assert api_key.name == sample_api_key.name

    def test_get_api_key_not_found(self, db_session, sample_user):
        """Test getting non-existent API key"""
        service = APIKeyService(db_session)

        api_key = service.get_api_key(api_key_id=999, user_id=sample_user.id)

        assert api_key is None

    def test_get_api_keys(self, db_session, sample_user, sample_tenant):
        """Test getting all API keys for a user"""
        service = APIKeyService(db_session)

        # Create multiple API keys
        for i in range(3):
            api_key_data = APIKeyCreate(
                name=f"Test API Key {i}", scopes=[APIKeyScope.READ]
            )
            service.create_api_key(
                api_key_data=api_key_data,
                user_id=sample_user.id,
                tenant_id=sample_tenant.id,
            )

        api_keys = service.get_api_keys(
            user_id=sample_user.id, tenant_id=sample_tenant.id
        )

        assert len(api_keys) == 3
        assert all(ak.user_id == sample_user.id for ak in api_keys)

    def test_update_api_key(self, db_session, sample_api_key, sample_user):
        """Test updating an API key"""
        service = APIKeyService(db_session)

        update_data = APIKeyUpdate(
            name="Updated API Key",
            description="Updated description",
            rate_limit_per_minute=200,
        )

        updated_api_key = service.update_api_key(
            api_key_id=sample_api_key.id,
            api_key_data=update_data,
            user_id=sample_user.id,
        )

        assert updated_api_key.name == "Updated API Key"
        assert updated_api_key.description == "Updated description"
        assert updated_api_key.rate_limit_per_minute == 200

    def test_delete_api_key(self, db_session, sample_api_key, sample_user):
        """Test deleting an API key"""
        service = APIKeyService(db_session)

        success = service.delete_api_key(
            api_key_id=sample_api_key.id, user_id=sample_user.id
        )

        assert success is True

        # Verify it's deleted
        api_key = service.get_api_key(
            api_key_id=sample_api_key.id, user_id=sample_user.id
        )
        assert api_key is None

    def test_authenticate_api_key(self, db_session, sample_user):
        """Test authenticating an API key"""
        service = APIKeyService(db_session)

        # Create API key
        api_key_data = APIKeyCreate(name="Test API Key", scopes=[APIKeyScope.READ])

        api_key, key = service.create_api_key(
            api_key_data=api_key_data, user_id=sample_user.id
        )

        # Authenticate with the key
        authenticated_key = service.authenticate_api_key(key)

        assert authenticated_key is not None
        assert authenticated_key.id == api_key.id

    def test_authenticate_invalid_api_key(self, db_session):
        """Test authenticating with invalid API key"""
        service = APIKeyService(db_session)

        authenticated_key = service.authenticate_api_key("invalid_key")

        assert authenticated_key is None

    def test_authenticate_inactive_api_key(self, db_session, sample_user):
        """Test authenticating with inactive API key"""
        service = APIKeyService(db_session)

        # Create API key
        api_key_data = APIKeyCreate(name="Test API Key", scopes=[APIKeyScope.READ])

        api_key, key = service.create_api_key(
            api_key_data=api_key_data, user_id=sample_user.id
        )

        # Deactivate the key
        api_key.is_active = False
        db_session.commit()

        # Try to authenticate
        authenticated_key = service.authenticate_api_key(key)

        assert authenticated_key is None

    def test_log_api_key_usage(self, db_session, sample_api_key):
        """Test logging API key usage"""
        service = APIKeyService(db_session)

        service.log_api_key_usage(
            api_key_id=sample_api_key.id,
            endpoint="/test",
            method="GET",
            status_code=200,
            response_time_ms=150,
            ip_address="127.0.0.1",
            user_agent="TestClient",
        )

        # Verify usage was logged
        usage = (
            db_session.query(APIKeyUsage)
            .filter(APIKeyUsage.api_key_id == sample_api_key.id)
            .first()
        )

        assert usage is not None
        assert usage.endpoint == "/test"
        assert usage.method == "GET"
        assert usage.status_code == 200
        assert usage.response_time_ms == 150

    def test_get_api_key_usage(self, db_session, sample_api_key, sample_user):
        """Test getting API key usage history"""
        service = APIKeyService(db_session)

        # Log some usage
        for i in range(5):
            service.log_api_key_usage(
                api_key_id=sample_api_key.id,
                endpoint=f"/test{i}",
                method="GET",
                status_code=200,
            )

        usage_history = service.get_api_key_usage(
            api_key_id=sample_api_key.id, user_id=sample_user.id
        )

        assert len(usage_history) == 5
        assert all(u.api_key_id == sample_api_key.id for u in usage_history)

    def test_get_api_key_stats(self, db_session, sample_api_key, sample_user):
        """Test getting API key statistics"""
        service = APIKeyService(db_session)

        # Log some usage
        for i in range(10):
            status_code = 200 if i < 8 else 500
            service.log_api_key_usage(
                api_key_id=sample_api_key.id,
                endpoint="/test",
                method="GET",
                status_code=status_code,
                response_time_ms=100 + i * 10,
            )

        stats = service.get_api_key_stats(
            api_key_id=sample_api_key.id, user_id=sample_user.id, days=30
        )

        assert stats["total_requests"] == 10
        assert stats["successful_requests"] == 8
        assert stats["failed_requests"] == 2
        assert stats["average_response_time_ms"] is not None

    def test_check_rate_limit(self, db_session, sample_user):
        """Test rate limiting functionality"""
        service = APIKeyService(db_session)

        # Create API key with low rate limit
        api_key_data = APIKeyCreate(
            name="Test API Key", scopes=[APIKeyScope.READ], rate_limit_per_minute=2
        )

        api_key, key = service.create_api_key(
            api_key_data=api_key_data, user_id=sample_user.id
        )

        # Should pass initially
        assert service.check_rate_limit(api_key) is True

        # Log some usage
        for i in range(3):
            service.log_api_key_usage(
                api_key_id=api_key.id, endpoint="/test", method="GET", status_code=200
            )

        # Should fail now
        assert service.check_rate_limit(api_key) is False

    def test_rotate_api_key(self, db_session, sample_api_key, sample_user):
        """Test rotating an API key"""
        service = APIKeyService(db_session)

        original_hash = sample_api_key.key_hash
        original_prefix = sample_api_key.key_prefix

        rotated_key, new_key = service.rotate_api_key(
            api_key_id=sample_api_key.id, user_id=sample_user.id
        )

        assert rotated_key.key_hash != original_hash
        assert rotated_key.key_prefix != original_prefix
        assert new_key.startswith("rbac_")
        assert rotated_key.usage_count == 0
        assert rotated_key.last_used_at is None


class TestAPIKeyEndpoints:
    """Test API Key REST endpoints"""

    def test_create_api_key_endpoint(self, client, auth_headers):
        """Test creating API key via endpoint"""
        payload = {
            "name": "Test API Key",
            "description": "Test description",
            "scopes": ["read", "write"],
            "rate_limit_per_minute": 100,
        }

        response = client.post("/api-keys/", json=payload, headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["api_key"]["name"] == "Test API Key"
        assert data["key"].startswith("rbac_")

    def test_get_api_keys_endpoint(self, client, auth_headers):
        """Test getting API keys via endpoint"""
        # Create a few API keys first
        for i in range(3):
            payload = {"name": f"Test API Key {i}", "scopes": ["read"]}
            client.post("/api-keys/", json=payload, headers=auth_headers)

        response = client.get("/api-keys/", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 3

    def test_get_api_key_endpoint(self, client, auth_headers):
        """Test getting specific API key via endpoint"""
        # Create API key
        payload = {"name": "Test API Key", "scopes": ["read"]}
        create_response = client.post("/api-keys/", json=payload, headers=auth_headers)
        api_key_id = create_response.json()["api_key"]["id"]

        # Get the API key
        response = client.get(f"/api-keys/{api_key_id}", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == api_key_id
        assert data["name"] == "Test API Key"

    def test_update_api_key_endpoint(self, client, auth_headers):
        """Test updating API key via endpoint"""
        # Create API key
        payload = {"name": "Test API Key", "scopes": ["read"]}
        create_response = client.post("/api-keys/", json=payload, headers=auth_headers)
        api_key_id = create_response.json()["api_key"]["id"]

        # Update the API key
        update_payload = {
            "name": "Updated API Key",
            "description": "Updated description",
        }
        response = client.put(
            f"/api-keys/{api_key_id}", json=update_payload, headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "Updated API Key"
        assert data["description"] == "Updated description"

    def test_delete_api_key_endpoint(self, client, auth_headers):
        """Test deleting API key via endpoint"""
        # Create API key
        payload = {"name": "Test API Key", "scopes": ["read"]}
        create_response = client.post("/api-keys/", json=payload, headers=auth_headers)
        api_key_id = create_response.json()["api_key"]["id"]

        # Delete the API key
        response = client.delete(f"/api-keys/{api_key_id}", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["message"] == "API key deleted successfully"

        # Verify it's deleted
        get_response = client.get(f"/api-keys/{api_key_id}", headers=auth_headers)
        assert get_response.status_code == status.HTTP_404_NOT_FOUND

    def test_rotate_api_key_endpoint(self, client, auth_headers):
        """Test rotating API key via endpoint"""
        # Create API key
        payload = {"name": "Test API Key", "scopes": ["read"]}
        create_response = client.post("/api-keys/", json=payload, headers=auth_headers)
        api_key_id = create_response.json()["api_key"]["id"]
        original_key = create_response.json()["key"]

        # Rotate the API key
        response = client.post(f"/api-keys/{api_key_id}/rotate", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["key"] != original_key
        assert data["key"].startswith("rbac_")

    def test_get_api_key_usage_endpoint(self, client, auth_headers):
        """Test getting API key usage via endpoint"""
        # Create API key
        payload = {"name": "Test API Key", "scopes": ["read"]}
        create_response = client.post("/api-keys/", json=payload, headers=auth_headers)
        api_key_id = create_response.json()["api_key"]["id"]

        # Get usage (should be empty initially)
        response = client.get(f"/api-keys/{api_key_id}/usage", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)

    def test_get_api_key_stats_endpoint(self, client, auth_headers):
        """Test getting API key stats via endpoint"""
        # Create API key
        payload = {"name": "Test API Key", "scopes": ["read"]}
        create_response = client.post("/api-keys/", json=payload, headers=auth_headers)
        api_key_id = create_response.json()["api_key"]["id"]

        # Get stats
        response = client.get(f"/api-keys/{api_key_id}/stats", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "total_requests" in data
        assert "successful_requests" in data
        assert "failed_requests" in data

    def test_unauthorized_access(self, client):
        """Test that endpoints require authentication"""
        # Try to access without authentication
        response = client.get("/api-keys/")
        assert response.status_code == status.HTTP_403_FORBIDDEN

        # Try to create without authentication
        payload = {"name": "Test API Key", "scopes": ["read"]}
        response = client.post("/api-keys/", json=payload)
        assert response.status_code == status.HTTP_403_FORBIDDEN
