import asyncio
import hashlib
import os
import secrets
import tempfile
from datetime import datetime, timedelta
from typing import Any, Dict
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.base import Base, get_db

# Import da aplicação
from app.main import app
from app.models.api_key import APIKey
from app.models.tenant import Tenant, TenantSettings
from app.models.user import Permission, Role, User
from app.models.webhook import Webhook

# Configuração do banco de dados de teste
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def db_session():
    """Create a fresh database session for each test."""
    # Create all tables
    Base.metadata.create_all(bind=engine)

    # Create session
    session = TestingSessionLocal()

    try:
        yield session
    finally:
        session.close()
        # Drop all tables
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(db_session):
    """Create a test client with database dependency override."""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    # Clean up
    app.dependency_overrides.clear()


@pytest.fixture
def sample_permission(db_session):
    """Create a sample permission for testing."""
    permission = Permission(
        name="test_permission",
        description="Test permission",
        resource="test",
        action="read",
    )
    db_session.add(permission)
    db_session.commit()
    db_session.refresh(permission)
    return permission


@pytest.fixture
def sample_role(db_session, sample_permission):
    """Create a sample role for testing."""
    role = Role(name="test_role", description="Test role", is_active=True)
    db_session.add(role)
    db_session.commit()
    db_session.refresh(role)

    # Add permission to role
    role.permissions.append(sample_permission)
    db_session.commit()

    return role


@pytest.fixture
def sample_tenant(db_session):
    """Create a sample tenant for testing."""
    tenant = Tenant(
        name="Test Tenant",
        slug="test-tenant",
        description="Test tenant description",
        contact_email="test@tenant.com",
        plan_type="free",
        max_users=10,
        max_api_keys=5,
        max_storage_mb=100,
        is_active=True,
        is_verified=True,
    )
    db_session.add(tenant)
    db_session.commit()
    db_session.refresh(tenant)

    # Create tenant settings
    settings = TenantSettings(
        tenant_id=tenant.id,
        allow_registration=True,
        require_email_verification=False,
        enforce_2fa=False,
    )
    db_session.add(settings)
    db_session.commit()

    return tenant


@pytest.fixture
def sample_user(db_session, sample_role, sample_tenant):
    """Create a sample user for testing."""
    user = User(
        username="testuser",
        email="test@example.com",
        full_name="Test User",
        hashed_password="$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",  # "secret"
        is_active=True,
        is_superuser=False,
        provider="basic",
        tenant_id=sample_tenant.id,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    # Add role to user
    user.roles.append(sample_role)
    db_session.commit()

    return user


@pytest.fixture
def admin_user(db_session, sample_role):
    """Create an admin user for testing."""
    user = User(
        username="admin",
        email="admin@example.com",
        full_name="Admin User",
        hashed_password="$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",  # "secret"
        is_active=True,
        is_superuser=True,
        provider="basic",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    # Add role to user
    user.roles.append(sample_role)
    db_session.commit()

    return user


@pytest.fixture
def sample_api_key(db_session, sample_user):
    """Create a sample API key for testing."""
    api_key = APIKey(
        name="Test API Key",
        description="Test API key description",
        key_hash="test_hash_123",
        key_prefix="rbac_test",
        user_id=sample_user.id,
        tenant_id=sample_user.tenant_id,
        scopes='["read", "write"]',
        rate_limit_per_minute=100,
        is_active=True,
    )
    db_session.add(api_key)
    db_session.commit()
    db_session.refresh(api_key)
    return api_key


@pytest.fixture
def sample_webhook(db_session, sample_user):
    """Create a sample webhook for testing."""
    webhook = Webhook(
        name="Test Webhook",
        description="Test webhook description",
        url="https://example.com/webhook",
        secret="test_secret",
        events=["user.created", "user.updated"],
        timeout_seconds=30,
        retry_enabled=True,
        max_retries=3,
        retry_delay_seconds=60,
        is_active=True,
        user_id=sample_user.id,
        tenant_id=sample_user.tenant_id,
    )
    db_session.add(webhook)
    db_session.commit()
    db_session.refresh(webhook)
    return webhook


@pytest.fixture
def auth_headers(client, sample_user):
    """Get authentication headers for the sample user."""
    # Login and get token
    response = client.post(
        "/auth/login", json={"username": sample_user.username, "password": "secret"}
    )

    assert response.status_code == 200
    token = response.json()["access_token"]

    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_auth_headers(client, admin_user):
    """Get authentication headers for the admin user."""
    # Login and get token
    response = client.post(
        "/auth/login", json={"username": admin_user.username, "password": "secret"}
    )

    assert response.status_code == 200
    token = response.json()["access_token"]

    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def temp_file():
    """Create a temporary file for testing."""
    with tempfile.NamedTemporaryFile(delete=False) as f:
        yield f.name

    # Clean up
    if os.path.exists(f.name):
        os.unlink(f.name)


@pytest.fixture
def mock_redis():
    """Mock Redis for testing."""

    class MockRedis:
        def __init__(self):
            self._data = {}

        def get(self, key):
            return self._data.get(key)

        def set(self, key, value, ex=None):
            self._data[key] = value
            return True

        def delete(self, key):
            if key in self._data:
                del self._data[key]
                return 1
            return 0

        def exists(self, key):
            return key in self._data

        def incr(self, key):
            if key not in self._data:
                self._data[key] = 0
            self._data[key] += 1
            return self._data[key]

        def expire(self, key, seconds):
            # Simplified - just keep the key
            return True

    return MockRedis()


# Funções auxiliares para testes
def create_test_user(
    db_session,
    username="testuser",
    email="test@example.com",
    is_superuser=False,
    tenant_id=None,
):
    """Create a test user."""
    user = User(
        username=username,
        email=email,
        full_name=f"Test User {username}",
        hashed_password="$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",
        is_active=True,
        is_superuser=is_superuser,
        provider="basic",
        tenant_id=tenant_id,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def create_test_tenant(db_session, name="Test Tenant", slug="test-tenant"):
    """Create a test tenant."""
    tenant = Tenant(
        name=name,
        slug=slug,
        description="Test tenant",
        plan_type="free",
        max_users=10,
        max_api_keys=5,
        is_active=True,
        is_verified=True,
    )
    db_session.add(tenant)
    db_session.commit()
    db_session.refresh(tenant)
    return tenant


def login_user(client, username="testuser", password="secret"):
    """Login a user and return the token."""
    response = client.post(
        "/auth/login", data={"username": username, "password": password}
    )

    if response.status_code != 200:
        return None

    return response.json()["access_token"]
