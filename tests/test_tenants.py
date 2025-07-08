from unittest.mock import MagicMock, patch

import pytest
from fastapi import status

from app.models.tenant import Tenant, TenantSettings
from app.models.user import User
from app.schemas.tenant import (
    TenantCreate,
    TenantSettingsCreate,
    TenantSettingsUpdate,
    TenantUpdate,
)
from app.services.tenant_service import TenantService


class TestTenantService:
    """Test Tenant service functionality"""

    def test_create_tenant(self, db_session, sample_user):
        """Test creating a tenant"""
        service = TenantService(db_session)

        tenant_data = TenantCreate(
            name="Test Tenant Unique",
            slug="test-tenant-unique",
            description="Test description",
            contact_email="test@tenant.com",
            plan_type="free",
        )

        tenant = service.create_tenant(tenant_data=tenant_data, owner_id=sample_user.id)

        assert tenant.name == "Test Tenant Unique"
        assert tenant.slug == "test-tenant-unique"
        assert tenant.description == "Test description"
        assert tenant.contact_email == "test@tenant.com"
        assert tenant.plan_type == "free"
        assert tenant.is_active is True
        assert tenant.is_verified is False

        # Check if owner was assigned to tenant
        db_session.refresh(sample_user)
        assert sample_user.tenant_id == tenant.id

    def test_create_tenant_duplicate_slug(self, db_session, sample_user, sample_tenant):
        """Test creating tenant with duplicate slug"""
        service = TenantService(db_session)

        tenant_data = TenantCreate(
            name="Another Tenant",
            slug=sample_tenant.slug,  # Same slug as existing tenant
            description="Test description",
        )

        with pytest.raises(Exception) as exc_info:
            service.create_tenant(tenant_data=tenant_data, owner_id=sample_user.id)

        assert "Tenant slug already exists" in str(exc_info.value)

    def test_get_tenant(self, db_session, sample_tenant):
        """Test getting a tenant"""
        service = TenantService(db_session)

        tenant = service.get_tenant(sample_tenant.id)

        assert tenant.id == sample_tenant.id
        assert tenant.name == sample_tenant.name

    def test_get_tenant_by_slug(self, db_session, sample_tenant):
        """Test getting tenant by slug"""
        service = TenantService(db_session)

        tenant = service.get_tenant_by_slug(sample_tenant.slug)

        assert tenant.id == sample_tenant.id
        assert tenant.slug == sample_tenant.slug

    def test_get_tenants(self, db_session, admin_user):
        """Test getting all tenants"""
        service = TenantService(db_session)

        # Create multiple tenants
        for i in range(3):
            tenant_data = TenantCreate(
                name=f"Test Tenant {i}",
                slug=f"test-tenant-{i}",
                description=f"Test description {i}",
            )
            service.create_tenant(tenant_data=tenant_data, owner_id=admin_user.id)

        tenants = service.get_tenants(current_user=admin_user)

        assert len(tenants) >= 3
        assert all(t.is_active for t in tenants)

    def test_get_tenants_active_only(self, db_session, admin_user):
        """Test getting only active tenants"""
        service = TenantService(db_session)

        # Create tenants
        for i in range(3):
            tenant_data = TenantCreate(
                name=f"Test Tenant Active {i}",
                slug=f"test-tenant-active-{i}",
                description=f"Test description {i}",
            )
            tenant = service.create_tenant(
                tenant_data=tenant_data, owner_id=admin_user.id
            )

            # Deactivate one tenant
            if i == 1:
                tenant.is_active = False
                db_session.commit()

        active_tenants = service.get_tenants(current_user=admin_user, active_only=True)

        assert len(active_tenants) >= 2
        assert all(t.is_active for t in active_tenants)

    def test_update_tenant(self, db_session, sample_tenant):
        """Test updating a tenant"""
        service = TenantService(db_session)

        update_data = TenantUpdate(
            name="Updated Tenant",
            description="Updated description",
            plan_type="premium",
            max_users=20,
        )

        updated_tenant = service.update_tenant(
            tenant_id=sample_tenant.id, tenant_data=update_data
        )

        assert updated_tenant.name == "Updated Tenant"
        assert updated_tenant.description == "Updated description"
        assert updated_tenant.plan_type == "premium"
        assert updated_tenant.max_users == 20

    def test_delete_tenant(self, db_session, sample_tenant):
        """Test deleting a tenant (soft delete)"""
        service = TenantService(db_session)
        tenant_id = sample_tenant.id
        success = service.delete_tenant(tenant_id)

        assert success is True

        # Verify it's deleted
        deleted_tenant = service.get_tenant(tenant_id)
        assert deleted_tenant is None

    def test_get_tenant_users(self, db_session, sample_tenant):
        """Test getting tenant users"""
        service = TenantService(db_session)

        # Create users for the tenant
        for i in range(3):
            user = User(
                username=f"user{i}",
                email=f"user{i}@example.com",
                hashed_password="hashed",
                tenant_id=sample_tenant.id,
            )
            db_session.add(user)

        db_session.commit()

        users = service.get_tenant_users(sample_tenant.id)

        assert len(users) == 3  # 3 new users created in this test
        assert all(u.tenant_id == sample_tenant.id for u in users)

    def test_add_user_to_tenant(self, db_session, sample_tenant):
        """Test adding user to tenant"""
        service = TenantService(db_session)

        # Create a user without tenant
        user = User(
            username="newuser", email="newuser@example.com", hashed_password="hashed"
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        success = service.add_user_to_tenant(
            tenant_id=sample_tenant.id, user_id=user.id
        )

        assert success is True
        db_session.refresh(user)
        assert user.tenant_id == sample_tenant.id

    def test_add_user_to_tenant_limit_exceeded(self, db_session, sample_tenant):
        """Test adding user when tenant limit is exceeded"""
        service = TenantService(db_session)

        # Set tenant limit to current user count
        current_users = service.get_tenant_users(sample_tenant.id)
        sample_tenant.max_users = len(current_users)
        db_session.commit()

        # Try to add another user
        user = User(
            username="newuser", email="newuser@example.com", hashed_password="hashed"
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        with pytest.raises(Exception) as exc_info:
            service.add_user_to_tenant(tenant_id=sample_tenant.id, user_id=user.id)

        assert "User limit reached" in str(exc_info.value)

    def test_remove_user_from_tenant(self, db_session, sample_tenant, sample_user):
        """Test removing user from tenant"""
        service = TenantService(db_session)

        success = service.remove_user_from_tenant(
            tenant_id=sample_tenant.id, user_id=sample_user.id
        )

        assert success is True
        db_session.refresh(sample_user)
        assert sample_user.tenant_id is None

    def test_create_tenant_settings(self, db_session, sample_tenant):
        """Test creating tenant settings"""
        service = TenantService(db_session)

        # Delete existing settings created by fixture
        db_session.query(TenantSettings).filter(
            TenantSettings.tenant_id == sample_tenant.id
        ).delete()
        db_session.commit()

        settings_data = TenantSettingsCreate(
            logo_url="https://example.com/logo.png",
            primary_color="#FF0000",
            allow_registration=False,
            enforce_2fa=True,
        )

        settings = service.create_tenant_settings(
            tenant_id=sample_tenant.id, settings_data=settings_data
        )

        assert settings.tenant_id == sample_tenant.id
        assert settings.logo_url == "https://example.com/logo.png"
        assert settings.primary_color == "#FF0000"
        assert settings.allow_registration is False
        assert settings.enforce_2fa is True

    def test_update_tenant_settings(self, db_session, sample_tenant):
        """Test updating tenant settings"""
        service = TenantService(db_session)

        update_data = TenantSettingsUpdate(
            logo_url="https://example.com/new-logo.png",
            primary_color="#00FF00",
            sso_enabled=True,
        )

        settings = service.update_tenant_settings(
            tenant_id=sample_tenant.id, settings_data=update_data
        )

        assert settings.logo_url == "https://example.com/new-logo.png"
        assert settings.primary_color == "#00FF00"
        assert settings.sso_enabled is True

    def test_generate_invite_code(self, db_session, sample_tenant):
        """Test generating tenant invite code"""
        service = TenantService(db_session)

        invite_code = service.generate_invite_code(
            tenant_id=sample_tenant.id, expires_hours=24
        )

        assert invite_code.startswith(f"TENANT_{sample_tenant.id}_")
        assert len(invite_code) > 20  # Should include random part

    def test_validate_invite_code(self, db_session, sample_tenant):
        """Test validating tenant invite code"""
        service = TenantService(db_session)

        # Generate invite code
        invite_code = service.generate_invite_code(
            tenant_id=sample_tenant.id, expires_hours=24
        )

        # Validate the code
        tenant_id = service.validate_invite_code(invite_code)

        assert tenant_id == sample_tenant.id

    def test_validate_invalid_invite_code(self, db_session):
        """Test validating invalid invite code"""
        service = TenantService(db_session)

        tenant_id = service.validate_invite_code("invalid_code")

        assert tenant_id is None

    def test_get_tenant_stats(self, db_session, sample_tenant):
        """Test getting tenant statistics"""
        service = TenantService(db_session)

        stats = service.get_tenant_stats(sample_tenant.id)

        assert "users" in stats
        assert "api_keys" in stats
        assert "subscription" in stats
        assert stats["users"]["current"] >= 0
        assert stats["users"]["limit"] == sample_tenant.max_users

    def test_check_tenant_feature(self, db_session, sample_tenant):
        """Test checking tenant feature"""
        service = TenantService(db_session)

        # Set a feature
        sample_tenant.features = {"test_feature": True, "another_feature": False}
        db_session.commit()

        # Check features
        assert service.check_tenant_feature(sample_tenant.id, "test_feature") is True
        assert (
            service.check_tenant_feature(sample_tenant.id, "another_feature") is False
        )
        assert (
            service.check_tenant_feature(sample_tenant.id, "nonexistent_feature")
            is False
        )

    def test_enable_tenant_feature(self, db_session, sample_tenant):
        """Test enabling tenant feature"""
        service = TenantService(db_session)

        success = service.enable_tenant_feature(
            tenant_id=sample_tenant.id, feature_name="new_feature"
        )

        assert success is True
        db_session.refresh(sample_tenant)
        assert sample_tenant.features["new_feature"] is True

    def test_disable_tenant_feature(self, db_session, sample_tenant):
        """Test disabling tenant feature"""
        service = TenantService(db_session)

        # Enable feature first
        service.enable_tenant_feature(sample_tenant.id, "test_feature")

        # Disable it
        success = service.disable_tenant_feature(
            tenant_id=sample_tenant.id, feature_name="test_feature"
        )

        assert success is True
        db_session.refresh(sample_tenant)
        assert sample_tenant.features["test_feature"] is False


class TestTenantEndpoints:
    """Test Tenant REST endpoints"""

    def test_create_tenant_endpoint(self, client, admin_auth_headers):
        """Test creating tenant via endpoint"""
        payload = {
            "name": "Test Tenant Endpoint",
            "slug": "test-tenant-endpoint",
            "description": "Test description",
            "contact_email": "test@tenant.com",
            "plan_type": "free",
        }

        response = client.post("/tenants/", json=payload, headers=admin_auth_headers)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == "Test Tenant Endpoint"
        assert data["slug"] == "test-tenant-endpoint"

    def test_get_my_tenant_endpoint(self, client, auth_headers):
        """Test getting current user's tenant"""
        response = client.get("/tenants/my", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data is not None
        assert "id" in data
        assert "name" in data

    def test_get_tenant_endpoint(self, client, auth_headers, sample_tenant):
        """Test getting specific tenant"""
        response = client.get(f"/tenants/{sample_tenant.id}", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == sample_tenant.id
        assert data["name"] == sample_tenant.name

    def test_update_tenant_endpoint(self, client, auth_headers, sample_tenant):
        """Test updating tenant via endpoint"""
        payload = {"name": "Updated Tenant", "description": "Updated description"}

        response = client.put(
            f"/tenants/{sample_tenant.id}", json=payload, headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "Updated Tenant"
        assert data["description"] == "Updated description"

    def test_get_tenant_users_endpoint(self, client, auth_headers, sample_tenant):
        """Test getting tenant users via endpoint"""
        response = client.get(
            f"/tenants/{sample_tenant.id}/users", headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1  # At least the sample user

    def test_get_tenant_settings_endpoint(self, client, auth_headers, sample_tenant):
        """Test getting tenant settings via endpoint"""
        response = client.get(
            f"/tenants/{sample_tenant.id}/settings", headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["tenant_id"] == sample_tenant.id
        assert "allow_registration" in data
        assert "enforce_2fa" in data

    def test_update_tenant_settings_endpoint(self, client, auth_headers, sample_tenant):
        """Test updating tenant settings via endpoint"""
        payload = {
            "logo_url": "https://example.com/logo.png",
            "primary_color": "#FF0000",
            "enforce_2fa": True,
        }

        response = client.put(
            f"/tenants/{sample_tenant.id}/settings", json=payload, headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["logo_url"] == "https://example.com/logo.png"
        assert data["primary_color"] == "#FF0000"
        assert data["enforce_2fa"] is True

    def test_get_tenant_stats_endpoint(self, client, auth_headers, sample_tenant):
        """Test getting tenant stats via endpoint"""
        response = client.get(
            f"/tenants/{sample_tenant.id}/stats", headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "users" in data
        assert "api_keys" in data
        assert "subscription" in data

    def test_generate_tenant_invite_endpoint(self, client, auth_headers, sample_tenant):
        """Test generating tenant invite via endpoint"""
        payload = {
            "email": "invite@example.com",
            "role_names": ["user"],
            "expires_hours": 24,
        }

        response = client.post(
            f"/tenants/{sample_tenant.id}/invite", json=payload, headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "invite_code" in data
        assert data["invite_code"].startswith(f"TENANT_{sample_tenant.id}_")

    def test_enable_tenant_feature_endpoint(self, client, auth_headers, sample_tenant):
        """Test enabling tenant feature via endpoint"""
        response = client.post(
            f"/tenants/{sample_tenant.id}/features/test_feature/enable",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "enabled successfully" in data["message"]

    def test_disable_tenant_feature_endpoint(self, client, auth_headers, sample_tenant):
        """Test disabling tenant feature via endpoint"""
        # First, enable the feature
        client.post(
            f"/tenants/{sample_tenant.id}/features/test_feature/enable",
            headers=auth_headers,
        )

        # Then, disable it
        response = client.post(
            f"/tenants/{sample_tenant.id}/features/test_feature/disable",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "disabled successfully" in data["message"]

    def test_get_all_tenants_admin_only(self, client, admin_auth_headers):
        """Test that only admins can list all tenants"""
        response = client.get("/tenants/", headers=admin_auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)

    def test_get_all_tenants_forbidden_for_regular_user(self, client, auth_headers):
        """Test that regular users can't list all tenants"""
        response = client.get("/tenants/", headers=auth_headers)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_delete_tenant_admin_only(self, client, admin_auth_headers):
        """Test that only admins can delete tenants"""
        # Create tenant first
        payload = {
            "name": "Test Tenant",
            "slug": "test-tenant-delete",
            "description": "Test description",
        }
        create_response = client.post(
            "/tenants/", json=payload, headers=admin_auth_headers
        )
        tenant_id = create_response.json()["id"]

        # Delete tenant
        response = client.delete(f"/tenants/{tenant_id}", headers=admin_auth_headers)

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["message"] == "Tenant deleted successfully"

    def test_delete_tenant_forbidden_for_regular_user(
        self, client, auth_headers, sample_tenant
    ):
        """Test that regular users can't delete tenants"""
        response = client.delete(f"/tenants/{sample_tenant.id}", headers=auth_headers)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_access_other_tenant_forbidden(self, client, auth_headers, db_session):
        """Test that users can't access other tenants"""
        # Create another tenant
        other_tenant = Tenant(
            name="Other Tenant", slug="other-tenant", plan_type="free", is_active=True
        )
        db_session.add(other_tenant)
        db_session.commit()
        db_session.refresh(other_tenant)

        # Try to access other tenant
        response = client.get(f"/tenants/{other_tenant.id}", headers=auth_headers)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_unauthorized_access(self, client):
        """Test that endpoints require authentication"""
        response = client.get("/tenants/my")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        payload = {
            "name": "Unauthorized Tenant",
            "slug": "unauthorized-tenant",
            "description": "Test description",
        }
        response = client.post("/tenants/", json=payload)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
