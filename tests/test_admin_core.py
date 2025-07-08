"""
Testes para funcionalidades CORE de administração
Testa endpoints admin realmente utilizados pelo frontend
"""
import pytest
from fastapi.testclient import TestClient
from fastapi import status
from sqlalchemy.orm import Session
import time


class TestAdminUsersCore:
    """Testes para gerenciamento de usuários CORE"""
    
    def test_get_users(self, client: TestClient, admin_auth_headers):
        """Teste de listagem de usuários"""
        response = client.get("/admin/users", headers=admin_auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1  # Pelo menos o admin
    
    def test_get_users_unauthorized(self, client: TestClient):
        """Teste de listagem de usuários sem autorização"""
        response = client.get("/admin/users")
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_get_user_by_id(self, client: TestClient, admin_auth_headers, admin_user):
        """Teste de obtenção de usuário por ID"""
        # Primeiro pega a lista para obter um ID válido
        users_response = client.get("/admin/users", headers=admin_auth_headers)
        users = users_response.json()
        user_id = users[0]["id"]
        
        response = client.get(f"/admin/users/{user_id}", headers=admin_auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == user_id
    
    def test_assign_role_to_user(self, client: TestClient, admin_auth_headers, admin_user):
        """Teste de atribuição de role a usuário"""
        # Primeiro pega usuário e role
        users_response = client.get("/admin/users", headers=admin_auth_headers)
        user_id = users_response.json()[0]["id"]
        
        roles_response = client.get("/admin/roles", headers=admin_auth_headers)
        role_id = roles_response.json()[0]["id"]
        
        response = client.post(f"/admin/users/{user_id}/roles/{role_id}", headers=admin_auth_headers)
        
        # Pode ser 200 (sucesso) ou 400 (já tem o role)
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST]
    
    def test_remove_role_from_user(self, client: TestClient, admin_auth_headers, admin_user):
        """Teste de remoção de role de usuário"""
        # Este teste pode falhar se o usuário não tiver o role, mas é um teste válido
        users_response = client.get("/admin/users", headers=admin_auth_headers)
        user_id = users_response.json()[0]["id"]
        
        roles_response = client.get("/admin/roles", headers=admin_auth_headers)
        role_id = roles_response.json()[0]["id"]
        
        response = client.delete(f"/admin/users/{user_id}/roles/{role_id}", headers=admin_auth_headers)
        
        # Pode ser 200 (sucesso) ou 404 (não tem o role)
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]


class TestAdminRolesCore:
    """Testes para gerenciamento de roles CORE"""
    
    def test_get_roles(self, client: TestClient, admin_auth_headers):
        """Teste de listagem de roles"""
        response = client.get("/admin/roles", headers=admin_auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1  # Pelo menos alguns roles padrão
    
    def test_create_role(self, client: TestClient, admin_auth_headers):
        """Teste de criação de role"""
        unique_name = f"test_role_{int(time.time())}"
        
        response = client.post("/admin/roles", headers=admin_auth_headers, json={
            "name": unique_name,
            "description": "Test role for testing",
            "is_active": True
        })
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == unique_name
        assert data["description"] == "Test role for testing"
        assert data["is_active"] is True
    
    def test_create_role_duplicate(self, client: TestClient, admin_auth_headers):
        """Teste de criação de role duplicado"""
        # Primeiro cria
        client.post("/admin/roles", headers=admin_auth_headers, json={
            "name": "duplicate_role",
            "description": "First role"
        })
        
        # Tenta criar novamente
        response = client.post("/admin/roles", headers=admin_auth_headers, json={
            "name": "duplicate_role",
            "description": "Second role"
        })
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_update_role(self, client: TestClient, admin_auth_headers):
        """Teste de atualização de role"""
        # Primeiro cria um role
        create_response = client.post("/admin/roles", headers=admin_auth_headers, json={
            "name": "update_test_role",
            "description": "Original description"
        })
        role_id = create_response.json()["id"]
        
        # Atualiza o role
        response = client.put(f"/admin/roles/{role_id}", headers=admin_auth_headers, json={
            "name": "updated_role",
            "description": "Updated description"
        })
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "updated_role"
        assert data["description"] == "Updated description"
    
    def test_delete_role(self, client: TestClient, admin_auth_headers):
        """Teste de exclusão de role"""
        # Primeiro cria um role
        create_response = client.post("/admin/roles", headers=admin_auth_headers, json={
            "name": "delete_test_role",
            "description": "Role to be deleted"
        })
        role_id = create_response.json()["id"]
        
        # Deleta o role
        response = client.delete(f"/admin/roles/{role_id}", headers=admin_auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
    
    def test_assign_permission_to_role(self, client: TestClient, admin_auth_headers):
        """Teste de atribuição de permissão a role"""
        # Pega role e permissão existentes
        roles_response = client.get("/admin/roles", headers=admin_auth_headers)
        role_id = roles_response.json()[0]["id"]
        
        permissions_response = client.get("/admin/permissions", headers=admin_auth_headers)
        permission_id = permissions_response.json()[0]["id"]
        
        response = client.post(f"/admin/roles/{role_id}/permissions/{permission_id}", headers=admin_auth_headers)
        
        # Pode ser 200 (sucesso) ou 400 (já tem a permissão)
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST]


class TestAdminPermissionsCore:
    """Testes para gerenciamento de permissões CORE"""
    
    def test_get_permissions(self, client: TestClient, admin_auth_headers):
        """Teste de listagem de permissões"""
        response = client.get("/admin/permissions", headers=admin_auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1  # Pelo menos algumas permissões padrão
    
    def test_create_permission(self, client: TestClient, admin_auth_headers):
        """Teste de criação de permissão"""
        unique_name = f"test_permission_{int(time.time())}"
        
        response = client.post("/admin/permissions", headers=admin_auth_headers, json={
            "name": unique_name,
            "resource": "test_resource",
            "action": "test_action",
            "description": "Test permission for testing"
        })
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == unique_name
        assert data["resource"] == "test_resource"
        assert data["action"] == "test_action"
    
    def test_create_permission_duplicate(self, client: TestClient, admin_auth_headers):
        """Teste de criação de permissão duplicada"""
        # Primeiro cria
        client.post("/admin/permissions", headers=admin_auth_headers, json={
            "name": "duplicate_permission",
            "resource": "resource",
            "action": "action"
        })
        
        # Tenta criar novamente
        response = client.post("/admin/permissions", headers=admin_auth_headers, json={
            "name": "duplicate_permission",
            "resource": "resource",
            "action": "action"
        })
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST 