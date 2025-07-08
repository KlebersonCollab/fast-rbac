import time
from typing import Any, Dict, List, Optional

import requests
import streamlit as st

from front.config.logging import log_api_call, log_frontend_error
from front.config.settings import settings


class APIException(Exception):
    """Custom exception for API errors"""

    def __init__(self, message: str, status_code: int = None, details: Dict = None):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class APIClient:
    def __init__(self):
        self.base_url = settings.API_BASE_URL
        self.session = requests.Session()

    def _get_headers(self, token: Optional[str] = None) -> Dict[str, str]:
        """Get headers for API requests"""
        headers = {"Content-Type": "application/json", "Accept": "application/json"}

        if token:
            headers["Authorization"] = f"Bearer {token}"
        elif hasattr(st.session_state, "token") and st.session_state.token:
            headers["Authorization"] = f"Bearer {st.session_state.token}"

        return headers

    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Dict = None,
        token: Optional[str] = None,
        params: Dict = None,
    ) -> Dict[str, Any]:
        """Make HTTP request to API"""
        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers(token)
        start_time = time.time()

        try:
            # Make the request
            if method.upper() == "GET":
                response = self.session.get(url, headers=headers, params=params)
            elif method.upper() == "POST":
                response = self.session.post(url, headers=headers, json=data)
            elif method.upper() == "PUT":
                response = self.session.put(url, headers=headers, json=data)
            elif method.upper() == "DELETE":
                response = self.session.delete(url, headers=headers)
            else:
                raise APIException(f"Método HTTP não suportado: {method}")

            # Calculate duration
            duration = time.time() - start_time

            # Log successful requests
            log_api_call(
                endpoint=endpoint,
                method=method.upper(),
                status_code=response.status_code,
                duration=duration,
                success=response.status_code < 400,
            )

            # Handle response
            if response.status_code == 200:
                return response.json() if response.content else {}
            elif response.status_code == 201:
                return response.json() if response.content else {}
            elif response.status_code == 204:
                return {}
            else:
                # Try to get error details from response
                try:
                    error_data = response.json()
                    detail = error_data.get("detail", "Erro desconhecido")
                except:
                    detail = f"Erro HTTP {response.status_code}"

                # Log error response
                log_api_call(
                    endpoint=endpoint,
                    method=method.upper(),
                    status_code=response.status_code,
                    duration=duration,
                    success=False,
                    error_detail=detail,
                )

                raise APIException(
                    message=detail,
                    status_code=response.status_code,
                    details=error_data if "error_data" in locals() else {},
                )

        except requests.exceptions.ConnectionError as e:
            duration = time.time() - start_time
            log_api_call(
                endpoint=endpoint,
                method=method.upper(),
                duration=duration,
                success=False,
                error_detail="Connection error",
            )
            log_frontend_error(e, f"API connection error: {method} {endpoint}")
            raise APIException(
                "Não foi possível conectar com a API. Verifique se o backend está rodando."
            )

        except requests.exceptions.Timeout as e:
            duration = time.time() - start_time
            log_api_call(
                endpoint=endpoint,
                method=method.upper(),
                duration=duration,
                success=False,
                error_detail="Timeout",
            )
            log_frontend_error(e, f"API timeout: {method} {endpoint}")
            raise APIException("Timeout na requisição para a API.")

        except requests.exceptions.RequestException as e:
            duration = time.time() - start_time
            log_api_call(
                endpoint=endpoint,
                method=method.upper(),
                duration=duration,
                success=False,
                error_detail=str(e),
            )
            log_frontend_error(e, f"API request error: {method} {endpoint}")
            raise APIException(f"Erro na requisição: {str(e)}")

        except Exception as e:
            duration = time.time() - start_time
            log_frontend_error(e, f"Unexpected API error: {method} {endpoint}")
            raise APIException(f"Erro inesperado: {str(e)}")

    # Authentication endpoints
    def login(self, username: str, password: str) -> Dict[str, Any]:
        """Login user"""
        data = {"username": username, "password": password}
        return self._make_request("POST", "/auth/login", data=data)

    def register(
        self, username: str, email: str, password: str, full_name: str = None
    ) -> Dict[str, Any]:
        """Register new user"""
        data = {
            "username": username,
            "email": email,
            "password": password,
            "full_name": full_name,
        }
        return self._make_request("POST", "/auth/register", data=data)

    def get_current_user(self) -> Dict[str, Any]:
        """Get current user profile"""
        return self._make_request("GET", "/auth/me")

    def test_token(self) -> Dict[str, Any]:
        """Test if token is valid"""
        return self._make_request("GET", "/auth/test-token")

    # OAuth endpoints
    def get_oauth_providers(self) -> Dict[str, Any]:
        """Get available OAuth providers"""
        return self._make_request("GET", "/oauth/providers")

    # User management endpoints
    def get_users(self) -> List[Dict[str, Any]]:
        """Get all users"""
        return self._make_request("GET", "/admin/users")

    def get_user(self, user_id: int) -> Dict[str, Any]:
        """Get user by ID"""
        return self._make_request("GET", f"/admin/users/{user_id}")

    def assign_role_to_user(self, user_id: int, role_id: int) -> Dict[str, Any]:
        """Assign role to user"""
        return self._make_request("POST", f"/admin/users/{user_id}/roles/{role_id}")

    def remove_role_from_user(self, user_id: int, role_id: int) -> Dict[str, Any]:
        """Remove role from user"""
        return self._make_request("DELETE", f"/admin/users/{user_id}/roles/{role_id}")

    # Role management endpoints
    def get_roles(self) -> List[Dict[str, Any]]:
        """Get all roles"""
        return self._make_request("GET", "/admin/roles")

    def create_role(
        self, name: str, description: str = None, is_active: bool = True
    ) -> Dict[str, Any]:
        """Create new role"""
        data = {"name": name, "description": description, "is_active": is_active}
        return self._make_request("POST", "/admin/roles", data=data)

    def update_role(
        self,
        role_id: int,
        name: str = None,
        description: str = None,
        is_active: bool = None,
    ) -> Dict[str, Any]:
        """Update role"""
        data = {}
        if name is not None:
            data["name"] = name
        if description is not None:
            data["description"] = description
        if is_active is not None:
            data["is_active"] = is_active

        return self._make_request("PUT", f"/admin/roles/{role_id}", data=data)

    def delete_role(self, role_id: int) -> Dict[str, Any]:
        """Delete role"""
        return self._make_request("DELETE", f"/admin/roles/{role_id}")

    def assign_permission_to_role(
        self, role_id: int, permission_id: int
    ) -> Dict[str, Any]:
        """Assign permission to role"""
        return self._make_request(
            "POST", f"/admin/roles/{role_id}/permissions/{permission_id}"
        )

    def remove_permission_from_role(
        self, role_id: int, permission_id: int
    ) -> Dict[str, Any]:
        """Remove permission from role"""
        return self._make_request(
            "DELETE", f"/admin/roles/{role_id}/permissions/{permission_id}"
        )

    # Permission management endpoints
    def get_permissions(self) -> List[Dict[str, Any]]:
        """Get all permissions"""
        return self._make_request("GET", "/admin/permissions")

    def create_permission(
        self, name: str, resource: str, action: str, description: str = None
    ) -> Dict[str, Any]:
        """Create new permission"""
        data = {
            "name": name,
            "resource": resource,
            "action": action,
            "description": description,
        }
        return self._make_request("POST", "/admin/permissions", data=data)

    # Protected endpoints (examples)
    def get_profile(self) -> Dict[str, Any]:
        """Get user profile"""
        return self._make_request("GET", "/protected/profile")

    def read_posts(self) -> Dict[str, Any]:
        """Read posts"""
        return self._make_request("GET", "/protected/posts")

    def create_post(self) -> Dict[str, Any]:
        """Create post"""
        return self._make_request("POST", "/protected/posts/create")

    def access_settings(self) -> Dict[str, Any]:
        """Access settings"""
        return self._make_request("GET", "/protected/settings")

    # Health check
    def health_check(self) -> Dict[str, Any]:
        """Check API health"""
        return self._make_request("GET", "/health")

    # Generic HTTP methods for Level 5 enterprise features
    def get(self, endpoint: str, params: Dict = None) -> Dict[str, Any]:
        """Generic GET request"""
        try:
            result = self._make_request("GET", endpoint, params=params)
            return {"status_code": 200, "data": result}
        except APIException as e:
            return {"status_code": e.status_code or 500, "error": e.message}
        except Exception as e:
            return {"status_code": 500, "error": str(e)}

    def post(self, endpoint: str, data: Dict = None) -> Dict[str, Any]:
        """Generic POST request"""
        try:
            result = self._make_request("POST", endpoint, data=data)
            return {"status_code": 200, "data": result}
        except APIException as e:
            return {"status_code": e.status_code or 500, "error": e.message}
        except Exception as e:
            return {"status_code": 500, "error": str(e)}

    def put(self, endpoint: str, data: Dict = None) -> Dict[str, Any]:
        """Generic PUT request"""
        try:
            result = self._make_request("PUT", endpoint, data=data)
            return {"status_code": 200, "data": result}
        except APIException as e:
            return {"status_code": e.status_code or 500, "error": e.message}
        except Exception as e:
            return {"status_code": 500, "error": str(e)}

    def delete(self, endpoint: str) -> Dict[str, Any]:
        """Generic DELETE request"""
        try:
            result = self._make_request("DELETE", endpoint)
            return {"status_code": 200, "data": result}
        except APIException as e:
            return {"status_code": e.status_code or 500, "error": e.message}
        except Exception as e:
            return {"status_code": 500, "error": str(e)}


# Global API client instance
api_client = APIClient()
