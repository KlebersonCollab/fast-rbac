"""
Testes para funcionalidades CORE de autenticação
Testa endpoints realmente utilizados pelo frontend
"""

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.database.base import get_db
from app.main import app


class TestAuthCore:
    """Testes para endpoints de autenticação CORE"""

    def test_login_success(self, client: TestClient, admin_user):
        """Teste de login bem-sucedido"""
        response = client.post(
            "/auth/login", json={"username": "admin", "password": "secret"}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_invalid_credentials(self, client: TestClient):
        """Teste de login com credenciais inválidas"""
        response = client.post(
            "/auth/login", json={"username": "admin", "password": "wrong_password"}
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_register_success(self, client: TestClient):
        """Teste de registro bem-sucedido"""
        response = client.post(
            "/auth/register",
            json={
                "username": "newuser",
                "email": "newuser@example.com",
                "password": "newpass123",
                "full_name": "New User",
                "tenant_name": "New Tenant",
            },
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["username"] == "newuser"
        assert data["email"] == "newuser@example.com"

    def test_register_duplicate_username(self, client: TestClient, admin_user):
        """Teste de registro com username duplicado"""
        response = client.post(
            "/auth/register",
            json={
                "username": "admin",
                "email": "another@example.com",
                "password": "newpass123",
                "tenant_name": "Another Tenant",
            },
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Username already registered" in response.json()["detail"]

    def test_get_current_user(self, client: TestClient, admin_auth_headers):
        """Teste de obtenção do usuário atual"""
        response = client.get("/auth/me", headers=admin_auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["username"] == "admin"

    def test_get_current_user_unauthorized(self, client: TestClient):
        """Teste de obtenção do usuário atual sem autenticação"""
        response = client.get("/auth/me")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_test_token_valid(self, client: TestClient, admin_auth_headers):
        """Teste de validação de token válido"""
        response = client.get("/auth/test-token", headers=admin_auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "user_id" in data
        assert "message" in data

    def test_test_token_invalid(self, client: TestClient):
        """Teste de validação de token inválido"""
        headers = {"Authorization": "Bearer invalid_token"}
        response = client.get("/auth/test-token", headers=headers)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestOAuthCore:
    """Testes para endpoints OAuth CORE"""

    def test_get_oauth_providers(self, client: TestClient):
        """Teste de obtenção de provedores OAuth"""
        response = client.get("/oauth/providers")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "providers" in data
        assert isinstance(data["providers"], list)


class TestHealthCore:
    """Testes para endpoints de sistema CORE"""

    def test_health_check(self, client: TestClient):
        """Teste de health check"""
        response = client.get("/health")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"
        assert data["database"] == "connected"
        assert "version" in data

    def test_root_endpoint(self, client: TestClient):
        """Teste do endpoint raiz"""
        response = client.get("/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "message" in data
        assert "version" in data
        assert "status" in data
