import pytest
from app.services.api_key_service import APIKeyService
from app.schemas.api_key import APIKeyCreate, APIKeyScope, APIKeyUpdate
from app.models.api_key import APIKeyUsage
from fastapi import status

def test_create_api_key_new(db_session, sample_user):
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
        current_user=sample_user,
    )

    assert api_key.name == "Test API Key"
    assert api_key.description == "Test description"
    assert api_key.user_id == sample_user.id
    assert api_key.tenant_id == sample_user.tenant_id
    assert api_key.rate_limit_per_minute == 50
    assert api_key.is_active is True
    assert key.startswith("rbac_")
    assert api_key.key_prefix == key[:12]

def test_create_api_key_without_tenant(db_session, admin_user):
    """Test creating an API key without tenant"""
    service = APIKeyService(db_session)

    api_key_data = APIKeyCreate(name="Test API Key", scopes=[APIKeyScope.READ])

    with pytest.raises(Exception) as exc_info:
        service.create_api_key(
            api_key_data=api_key_data, current_user=admin_user
        )

    assert "User is not associated with a tenant" in str(exc_info.value)

def test_create_api_key_tenant_limit_exceeded(
    db_session, sample_user
):
    """Test creating API key when tenant limit is exceeded"""
    # Set tenant limit to 0
    sample_user.tenant.max_api_keys = 0
    db_session.commit()

    service = APIKeyService(db_session)

    api_key_data = APIKeyCreate(name="Test API Key", scopes=[APIKeyScope.READ])

    with pytest.raises(Exception) as exc_info:
        service.create_api_key(
            api_key_data=api_key_data,
            current_user=sample_user,
        )

    assert "API key limit reached" in str(exc_info.value)

def test_get_api_key(db_session, sample_api_key, sample_user):
    """Test getting an API key"""
    service = APIKeyService(db_session)

    api_key = service.get_api_key(
        api_key_id=sample_api_key.id, current_user=sample_user
    )

    assert api_key.id == sample_api_key.id
    assert api_key.name == sample_api_key.name

def test_get_api_key_not_found(db_session, sample_user):
    """Test getting non-existent API key"""
    service = APIKeyService(db_session)

    api_key = service.get_api_key(api_key_id=999, current_user=sample_user)

    assert api_key is None

def test_get_api_keys(db_session, sample_user):
    """Test getting all API keys for a user"""
    service = APIKeyService(db_session)

    # Create multiple API keys
    for i in range(3):
        api_key_data = APIKeyCreate(
            name=f"Test API Key {i}", scopes=[APIKeyScope.READ]
        )
        service.create_api_key(
            api_key_data=api_key_data,
            current_user=sample_user,
        )

    api_keys = service.get_api_keys(current_user=sample_user)

    assert len(api_keys) >= 3
    assert all(ak.user_id == sample_user.id for ak in api_keys)

def test_update_api_key(db_session, sample_api_key, sample_user):
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
        current_user=sample_user,
    )

    assert updated_api_key.name == "Updated API Key"
    assert updated_api_key.description == "Updated description"
    assert updated_api_key.rate_limit_per_minute == 200

def test_delete_api_key(db_session, sample_api_key, sample_user):
    """Test deleting an API key"""
    service = APIKeyService(db_session)

    success = service.delete_api_key(
        api_key_id=sample_api_key.id, current_user=sample_user
    )

    assert success is True

    # Verify it's deleted
    api_key = service.get_api_key(
        api_key_id=sample_api_key.id, current_user=sample_user
    )
    assert api_key is None

def test_authenticate_api_key(db_session, sample_user):
    """Test authenticating an API key"""
    service = APIKeyService(db_session)

    # Create API key
    api_key_data = APIKeyCreate(name="Test API Key", scopes=[APIKeyScope.READ])

    api_key, key = service.create_api_key(
        api_key_data=api_key_data, current_user=sample_user
    )

    # Authenticate with the key
    authenticated_key = service.authenticate_api_key(key)

    assert authenticated_key is not None
    assert authenticated_key.id == api_key.id

def test_authenticate_invalid_api_key(db_session):
    """Test authenticating with invalid API key"""
    service = APIKeyService(db_session)

    authenticated_key = service.authenticate_api_key("invalid_key")

    assert authenticated_key is None

def test_authenticate_inactive_api_key(db_session, sample_user):
    """Test authenticating with inactive API key"""
    service = APIKeyService(db_session)

    # Create API key
    api_key_data = APIKeyCreate(name="Test API Key", scopes=[APIKeyScope.READ])

    api_key, key = service.create_api_key(
        api_key_data=api_key_data, current_user=sample_user
    )

    # Deactivate the key
    api_key.is_active = False
    db_session.commit()

    # Try to authenticate
    authenticated_key = service.authenticate_api_key(key)

    assert authenticated_key is None

def test_log_api_key_usage(db_session, sample_api_key):
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

def test_get_api_key_usage(db_session, sample_api_key, sample_user):
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
        api_key_id=sample_api_key.id, current_user=sample_user
    )

    assert len(usage_history) == 5
    assert all(u.api_key_id == sample_api_key.id for u in usage_history)

def test_get_api_key_stats(db_session, sample_api_key, sample_user):
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
            response_time_ms=10,
        )

    stats = service.get_api_key_stats(
        api_key_id=sample_api_key.id, current_user=sample_user, days=1
    )

    assert stats["total_requests"] == 10
    assert stats["successful_requests"] == 8
    assert stats["failed_requests"] == 2
    assert stats["average_response_time_ms"] == 10

def test_check_rate_limit(db_session, sample_user):
    """Test checking the rate limit for an API key"""
    service = APIKeyService(db_session)
    api_key_data = APIKeyCreate(
        name="Rate Limit Test Key",
        scopes=[APIKeyScope.READ],
        rate_limit_per_minute=5,
    )
    api_key, _ = service.create_api_key(
        api_key_data=api_key_data, current_user=sample_user
    )

    # Log some usage
    for _ in range(4):
        service.log_api_key_usage(
            api_key_id=api_key.id,
            endpoint="/test",
            method="GET",
            status_code=200,
        )

    # Check rate limit (should not be exceeded)
    assert service.check_rate_limit(api_key) is True

    # Log one more usage to meet the limit
    service.log_api_key_usage(
        api_key_id=api_key.id, endpoint="/test", method="GET", status_code=200
    )

    # Check rate limit (should be exceeded now)
    assert service.check_rate_limit(api_key) is False

def test_rotate_api_key(db_session, sample_api_key, sample_user):
    """Test rotating an API key"""
    service = APIKeyService(db_session)

    old_key_hash = sample_api_key.key_hash

    rotated_key, new_key_str = service.rotate_api_key(
        api_key_id=sample_api_key.id, current_user=sample_user
    )

    assert rotated_key is not None
    assert rotated_key.id != sample_api_key.id
    assert rotated_key.key_hash != old_key_hash
    assert new_key_str.startswith("rbac_")

    # Verify old key is inactive
    db_session.refresh(sample_api_key)
    assert sample_api_key.is_active is False

    # Verify new key is active
    assert rotated_key.is_active is True

class TestAPIKeyEndpoints:
    """Test API Key endpoints"""

    def test_create_api_key_endpoint(self, client, auth_headers):
        """Test creating an API key via endpoint"""
        payload = {"name": "Test API Key", "scopes": ["read", "write"]}
        response = client.post("/api-keys/", json=payload, headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["api_key"]["name"] == "Test API Key"
        assert "key" in data

    def test_get_api_keys_endpoint(self, client, auth_headers):
        """Test getting all API keys via endpoint"""
        response = client.get("/api-keys/", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.json(), list)

    def test_get_api_key_endpoint(self, client, auth_headers):
        """Test getting a specific API key via endpoint"""
        # Create a key first
        payload = {"name": "Test Get Key", "scopes": ["read"]}
        create_response = client.post("/api-keys/", json=payload, headers=auth_headers)
        api_key_id = create_response.json()["api_key"]["id"]

        response = client.get(f"/api-keys/{api_key_id}", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["id"] == api_key_id

    def test_update_api_key_endpoint(self, client, auth_headers):
        """Test updating an API key via endpoint"""
        # Create a key first
        payload = {"name": "Test Update Key", "scopes": ["read"]}
        create_response = client.post("/api-keys/", json=payload, headers=auth_headers)
        api_key_id = create_response.json()["api_key"]["id"]

        update_payload = {"name": "Updated Key Name"}
        response = client.put(
            f"/api-keys/{api_key_id}", json=update_payload, headers=auth_headers
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["name"] == "Updated Key Name"

    def test_delete_api_key_endpoint(self, client, auth_headers):
        """Test deleting an API key via endpoint"""
        # Create a key first
        payload = {"name": "Test Delete Key", "scopes": ["read"]}
        create_response = client.post("/api-keys/", json=payload, headers=auth_headers)
        api_key_id = create_response.json()["api_key"]["id"]

        response = client.delete(f"/api-keys/{api_key_id}", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["message"] == "API key deleted successfully"

    def test_rotate_api_key_endpoint(self, client, auth_headers):
        """Test rotating an API key via endpoint"""
        # Create a key first
        payload = {"name": "Test Rotate Key", "scopes": ["read"]}
        create_response = client.post("/api-keys/", json=payload, headers=auth_headers)
        api_key_id = create_response.json()["api_key"]["id"]

        response = client.post(
            f"/api-keys/{api_key_id}/rotate", headers=auth_headers
        )
        assert response.status_code == status.HTTP_200_OK
        assert "key" in response.json()

    def test_get_api_key_usage_endpoint(self, client, auth_headers):
        """Test getting API key usage via endpoint"""
        # Create API key
        payload = {"name": "Test API Key", "scopes": ["read"]}
        create_response = client.post("/api-keys/", json=payload, headers=auth_headers)
        api_key_id = create_response.json()["api_key"]["id"]

        # Get usage (should be empty initially)
        response = client.get(f"/api-keys/{api_key_id}/usage", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []

    def test_get_api_key_stats_endpoint(self, client, auth_headers):
        """Test getting API key stats via endpoint"""
        # Create API key
        payload = {"name": "Test API Key", "scopes": ["read"]}
        create_response = client.post("/api-keys/", json=payload, headers=auth_headers)
        api_key_id = create_response.json()["api_key"]["id"]

        # Get stats
        response = client.get(f"/api-keys/{api_key_id}/stats", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        stats = response.json()
        assert stats["total_requests"] == 0

    def test_unauthorized_access(self, client):
        """Test that endpoints require authentication"""
        response = client.get("/api-keys/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        response = client.post("/api-keys/", json={})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED