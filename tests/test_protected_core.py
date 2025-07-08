"""
Testes para funcionalidades CORE protegidas
Testa endpoints protected realmente utilizados pelo frontend
"""

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


class TestProtectedCore:
    """Testes para endpoints protegidos CORE"""

    def test_get_profile_authenticated(self, client: TestClient, admin_auth_headers):
        """Teste de acesso ao perfil com autenticação"""
        response = client.get("/protected/profile", headers=admin_auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "message" in data
        assert "user" in data
        assert data["user"]["username"] == "admin"

    def test_get_profile_unauthenticated(self, client: TestClient):
        """Teste de acesso ao perfil sem autenticação"""
        response = client.get("/protected/profile")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_read_posts_authenticated(self, client: TestClient, admin_auth_headers):
        """Teste de leitura de posts com autenticação"""
        response = client.get("/protected/posts", headers=admin_auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "message" in data
        assert "user" in data
        assert "posts" in data

    def test_read_posts_unauthenticated(self, client: TestClient):
        """Teste de leitura de posts sem autenticação"""
        response = client.get("/protected/posts")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_post_authenticated(self, client: TestClient, admin_auth_headers):
        """Teste de criação de post com autenticação"""
        response = client.post("/protected/posts/create", headers=admin_auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "message" in data
        assert "created_by" in data
        assert "post created successfully" in data["message"].lower()

    def test_create_post_unauthenticated(self, client: TestClient):
        """Teste de criação de post sem autenticação"""
        response = client.post("/protected/posts/create")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_access_settings_authenticated(
        self, client: TestClient, admin_auth_headers
    ):
        """Teste de acesso a configurações com autenticação"""
        response = client.get("/protected/settings", headers=admin_auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "message" in data
        assert "accessed_by" in data
        assert "settings" in data["message"].lower()

    def test_access_settings_unauthenticated(self, client: TestClient):
        """Teste de acesso a configurações sem autenticação"""
        response = client.get("/protected/settings")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestProtectedPermissions:
    """Testes para verificação de permissões em endpoints protegidos"""

    def test_protected_endpoints_require_authentication(self, client: TestClient):
        """Teste que todos os endpoints protegidos exigem autenticação"""
        protected_endpoints_get = [
            "/protected/profile",
            "/protected/posts",
            "/protected/settings",
        ]

        # Teste endpoints GET
        for endpoint in protected_endpoints_get:
            response = client.get(endpoint)
            assert (
                response.status_code == status.HTTP_401_UNAUTHORIZED
            ), f"Endpoint {endpoint} should require authentication"

        # Teste endpoint POST separadamente
        response = client.post("/protected/posts/create")
        assert (
            response.status_code == status.HTTP_401_UNAUTHORIZED
        ), "POST endpoint should require authentication"

    def test_protected_endpoints_work_with_valid_token(
        self, client: TestClient, admin_auth_headers
    ):
        """Teste que todos os endpoints protegidos funcionam com token válido"""
        protected_endpoints_get = [
            "/protected/profile",
            "/protected/posts",
            "/protected/settings",
        ]

        for endpoint in protected_endpoints_get:
            response = client.get(endpoint, headers=admin_auth_headers)
            assert (
                response.status_code == status.HTTP_200_OK
            ), f"Endpoint {endpoint} should work with valid token"

        # Teste para endpoint POST
        response = client.post("/protected/posts/create", headers=admin_auth_headers)
        assert (
            response.status_code == status.HTTP_200_OK
        ), "POST endpoint should work with valid token"
