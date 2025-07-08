import pytest
from fastapi.testclient import TestClient


def test_list_api_keys_is_isolated(client: TestClient, multi_tenant_setup):
    """User A should only see their own API keys, not User B's."""
    # User A requests their keys
    response = client.get("/api-keys/", headers=multi_tenant_setup["headers_a"])
    assert response.status_code == 200
    data = response.json()
    
    # Assert only Key A is returned
    assert len(data) == 1
    assert data[0]["name"] == "Key A"
    assert data[0]["id"] == multi_tenant_setup["key_a"].id


def test_get_api_key_is_isolated(client: TestClient, multi_tenant_setup):
    """User A should not be able to fetch User B's key directly."""
    key_b_id = multi_tenant_setup["key_b"].id
    
    # User A attempts to fetch Key B
    response = client.get(f"/api-keys/{key_b_id}", headers=multi_tenant_setup["headers_a"])
    
    # Assert it's not found
    assert response.status_code == 404


def test_list_webhooks_is_isolated(client: TestClient, multi_tenant_setup):
    """User A should only see their own webhooks, not User B's."""
    # User A requests their webhooks
    response = client.get("/webhooks/", headers=multi_tenant_setup["headers_a"])
    assert response.status_code == 200
    data = response.json()

    # Assert only Hook A is returned
    assert len(data) == 1
    assert data[0]["name"] == "Hook A"
    assert data[0]["id"] == multi_tenant_setup["webhook_a"].id


def test_get_webhook_is_isolated(client: TestClient, multi_tenant_setup):
    """User A should not be able to fetch User B's webhook directly."""
    webhook_b_id = multi_tenant_setup["webhook_b"].id

    # User A attempts to fetch Hook B
    response = client.get(f"/webhooks/{webhook_b_id}", headers=multi_tenant_setup["headers_a"])

    # Assert it's not found
    assert response.status_code == 404

def test_list_tenants_is_isolated_for_regular_user(client: TestClient, multi_tenant_setup):
    """A regular user should only see their own tenant."""
    # User A requests tenants
    response = client.get("/tenants/", headers=multi_tenant_setup["headers_a"])
    assert response.status_code == 200
    data = response.json()

    # Assert only Tenant A is returned
    assert len(data) == 1
    assert data[0]["name"] == "Tenant A"
    assert data[0]["id"] == multi_tenant_setup["tenant_a"].id 