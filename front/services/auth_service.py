import time
from typing import Any, Dict, Optional

import streamlit as st

from front.config.logging import (
    get_frontend_logger,
    log_frontend_error,
    log_permission_check,
    log_user_action,
)
from front.services.api_client import APIException, api_client
from front.utils.helpers import clear_session


class AuthService:
    # Cache TTL para permissões (em segundos)
    PERMISSIONS_CACHE_TTL = 300  # 5 minutos
    # Cache TTL para validação de token (em segundos)
    TOKEN_VALIDATION_CACHE_TTL = 60  # 1 minuto

    @staticmethod
    def login(username: str, password: str) -> bool:
        """Login user with username and password"""
        try:
            response = api_client.login(username, password)

            # Store authentication state
            st.session_state.authenticated = True
            st.session_state.token = response.get("access_token")
            st.session_state.user = response.get("user")
            st.session_state.token_valid = True

            # Initialize cache timestamps
            st.session_state.permissions_cached_at = time.time()
            st.session_state.token_validated_at = (
                time.time()
            )  # Token just validated during login

            # Log successful login
            log_user_action(
                username, "login", "login", "authentication", {"login_type": "basic"}
            )

            return True

        except APIException as e:
            # Log failed login attempt
            log_user_action(
                username,
                "login_attempt",
                "login",
                "authentication",
                {"error": str(e)},
                level="WARNING",
            )

            st.error(f"Erro no login: {e.message}")
            return False
        except Exception as e:
            # Log failed login attempt
            log_user_action(
                username,
                "login_attempt",
                "login",
                "authentication",
                {"error": str(e)},
                level="WARNING",
            )

            st.error(f"Erro inesperado: {str(e)}")
            return False

    @staticmethod
    def oauth_login(provider: str, token: str) -> bool:
        """Login user with OAuth provider"""
        try:
            response = api_client.oauth_login(provider, token)

            # Store authentication state
            st.session_state.authenticated = True
            st.session_state.token = response.get("access_token")
            st.session_state.user = response.get("user")
            st.session_state.token_valid = True

            # Initialize cache timestamps
            st.session_state.permissions_cached_at = time.time()
            st.session_state.token_validated_at = (
                time.time()
            )  # Token just validated during login

            return True

        except APIException as e:
            st.error(f"Erro no login OAuth: {e.message}")
            return False
        except Exception as e:
            st.error(f"Erro inesperado: {str(e)}")
            return False

    @staticmethod
    def logout():
        """Logout current user"""
        username = st.session_state.get("user", {}).get("username", "unknown")

        # Log logout action
        log_user_action(username, "logout", "auth", "authentication")

        # Clear authentication state
        st.session_state.authenticated = False
        st.session_state.token = None
        st.session_state.user = None
        st.session_state.token_valid = False

        # Clear cache timestamps
        if hasattr(st.session_state, "permissions_cached_at"):
            del st.session_state.permissions_cached_at
        if hasattr(st.session_state, "token_validated_at"):
            del st.session_state.token_validated_at

    @staticmethod
    def register(
        username: str,
        email: str,
        password: str,
        full_name: str,
        tenant_name: str,
    ) -> bool:
        """Register new user and tenant."""
        try:
            response = api_client.register(
                username, email, password, full_name, tenant_name
            )

            # Optionally auto-login after registration
            if response:
                st.success("Cadastro realizado com sucesso! Fazendo login...")
                return AuthService.login(username, password)

            return True

        except APIException as e:
            st.error(f"Erro no registro: {e.message}")
            return False
        except Exception as e:
            st.error(f"Erro inesperado: {str(e)}")
            return False

    @staticmethod
    def _is_token_validation_cached() -> bool:
        """Check if token validation is still cached and valid"""
        if not hasattr(st.session_state, "token_validated_at"):
            return False

        cache_time = st.session_state.token_validated_at
        current_time = time.time()
        return (current_time - cache_time) <= AuthService.TOKEN_VALIDATION_CACHE_TTL

    @staticmethod
    def is_authenticated() -> bool:
        """Check if user is authenticated (with token cache)"""
        if not hasattr(st.session_state, "authenticated"):
            return False

        if not st.session_state.authenticated:
            return False

        if not st.session_state.token:
            return False

        # Check if token was recently validated (cache)
        if AuthService._is_token_validation_cached():
            return True

        # Test token validity only if cache expired
        try:
            api_client.test_token()
            # Update token validation cache
            st.session_state.token_validated_at = time.time()
            return True
        except APIException:
            # Token is invalid, clear session
            AuthService.logout()
            return False
        except Exception:
            return False

    @staticmethod
    def get_current_user() -> Optional[Dict[str, Any]]:
        """Get current user data (with auto-reload if missing)"""
        if not AuthService.is_authenticated():
            return None

        # Se user está em cache, retorna
        user = st.session_state.get("user")
        if user:
            return user

        # Se autenticado mas user é None, tenta recarregar do backend
        try:
            user_data = api_client.get_current_user()
            if user_data:
                st.session_state.user = user_data
                st.session_state.permissions_cached_at = time.time()
                return user_data
        except Exception:
            # Se falhar recarregar, logout para evitar estado inconsistente
            AuthService.logout()

        return None

    @staticmethod
    def _is_permissions_cache_expired() -> bool:
        """Check if permissions cache is expired"""
        if not hasattr(st.session_state, "permissions_cached_at"):
            return True

        cache_time = st.session_state.permissions_cached_at
        current_time = time.time()
        return (current_time - cache_time) > AuthService.PERMISSIONS_CACHE_TTL

    @staticmethod
    def refresh_user_permissions(force: bool = False) -> bool:
        """Refresh user permissions from backend"""
        try:
            # Only refresh if cache is expired or forced
            if not force and not AuthService._is_permissions_cache_expired():
                return True

            # Get fresh user data from backend
            user_data = api_client.get_current_user()
            st.session_state.user = user_data
            st.session_state.permissions_cached_at = time.time()
            return True

        except APIException:
            # If refresh fails, keep using cached data
            return False
        except Exception:
            return False

    @staticmethod
    def has_permission(permission: str) -> bool:
        """Check if current user has specific permission (with auto-refresh)"""
        # Single authentication check instead of multiple calls
        if not AuthService.is_authenticated():
            log_permission_check(
                permission, granted=False, page="unknown", reason="not_authenticated"
            )
            return False

        # Get user once and reuse
        user = st.session_state.user
        if not user:
            log_permission_check(
                permission, granted=False, page="unknown", reason="no_user"
            )
            return False

        # Check if user is superuser (fast path)
        if user.get("is_superuser", False):
            log_permission_check(
                permission, granted=True, page="unknown", reason="superuser"
            )
            return True

        # Try to refresh permissions if cache is expired (but don't call get_current_user again)
        if AuthService._is_permissions_cache_expired():
            try:
                user_data = api_client.get_current_user()
                if user_data:
                    st.session_state.user = user_data
                    st.session_state.permissions_cached_at = time.time()
                    user = user_data  # Use fresh data for this check
            except Exception:
                # If refresh fails, use cached data
                pass

        # Check roles and permissions using the user data we have
        roles = user.get("roles", [])
        for role in roles:
            permissions = role.get("permissions", [])
            for perm in permissions:
                if perm.get("name") == permission:
                    log_permission_check(
                        permission, granted=True, page="unknown", role=role.get("name")
                    )
                    return True

        log_permission_check(
            permission, granted=False, page="unknown", reason="permission_not_found"
        )
        return False

    @staticmethod
    def has_permission_force_refresh(permission: str) -> bool:
        """Check permission with forced refresh from backend (more reliable)"""
        try:
            # Sempre força um refresh do backend
            from front.services.api_client import api_client

            # Busca dados frescos do backend
            user_data = api_client.get_current_user()
            if not user_data:
                log_permission_check(
                    permission,
                    granted=False,
                    page="unknown",
                    reason="no_user_from_backend",
                )
                return False

            # Atualiza session state com dados frescos
            st.session_state["user"] = user_data
            st.session_state.permissions_cached_at = time.time()

            # Check if user is superuser
            if user_data.get("is_superuser", False):
                log_permission_check(
                    permission, granted=True, page="unknown", reason="superuser_fresh"
                )
                return True

            # Check roles and permissions from fresh data
            roles = user_data.get("roles", [])
            for role in roles:
                permissions = role.get("permissions", [])
                for perm in permissions:
                    if perm.get("name") == permission:
                        log_permission_check(
                            permission,
                            granted=True,
                            page="unknown",
                            role=role.get("name"),
                            method="force_refresh",
                        )
                        return True

            log_permission_check(
                permission,
                granted=False,
                page="unknown",
                reason="permission_not_found_fresh",
            )
            return False

        except Exception as e:
            # Se falhar, tentar método normal
            log_permission_check(
                permission,
                granted=False,
                page="unknown",
                reason=f"force_refresh_error_{str(e)}",
            )
            return AuthService.has_permission_cached(permission)

    @staticmethod
    def has_permission_cached(permission: str) -> bool:
        """Check permission using only cached data (faster)"""
        user = AuthService.get_current_user()
        if not user:
            return False

        # Check if user is superuser
        if user.get("is_superuser", False):
            return True

        # Check roles and permissions
        roles = user.get("roles", [])
        for role in roles:
            permissions = role.get("permissions", [])
            for perm in permissions:
                if perm.get("name") == permission:
                    return True

        return False

    @staticmethod
    def has_role(role_name: str) -> bool:
        """Check if current user has specific role"""
        user = AuthService.get_current_user()
        if not user:
            return False

        roles = user.get("roles", [])
        for role in roles:
            if role.get("name") == role_name:
                return True

        return False

    @staticmethod
    def get_user_roles() -> list:
        """Get current user roles"""
        user = AuthService.get_current_user()
        if not user:
            return []

        return [role.get("name") for role in user.get("roles", [])]

    @staticmethod
    def get_user_permissions(refresh: bool = False) -> list:
        """Get current user permissions (with optional refresh)"""
        if refresh:
            AuthService.refresh_user_permissions(force=True)
        else:
            AuthService.refresh_user_permissions()

        user = AuthService.get_current_user()
        if not user:
            return []

        permissions = []
        roles = user.get("roles", [])

        for role in roles:
            role_permissions = role.get("permissions", [])
            for perm in role_permissions:
                perm_name = perm.get("name")
                if perm_name and perm_name not in permissions:
                    permissions.append(perm_name)

        return permissions

    @staticmethod
    def require_permission(permission: str) -> bool:
        """Require specific permission (shows error if not authorized)"""
        if not AuthService.is_authenticated():
            st.error("Você precisa estar logado para acessar esta funcionalidade.")
            return False

        if not AuthService.has_permission(permission):
            st.error(f"Você não tem permissão para: {permission}")
            return False

        return True

    @staticmethod
    def require_role(role_name: str) -> bool:
        """Require specific role (shows error if not authorized)"""
        if not AuthService.is_authenticated():
            st.error("Você precisa estar logado para acessar esta funcionalidade.")
            return False

        if not AuthService.has_role(role_name):
            st.error(f"Você precisa do papel: {role_name}")
            return False

        return True

    @staticmethod
    def get_permissions_cache_info() -> Dict[str, Any]:
        """Get information about permissions cache status"""
        if not hasattr(st.session_state, "permissions_cached_at"):
            return {
                "cached": False,
                "cache_age": 0,
                "expires_in": 0,
                "is_expired": True,
            }

        cache_time = st.session_state.permissions_cached_at
        current_time = time.time()
        cache_age = current_time - cache_time
        expires_in = max(0, AuthService.PERMISSIONS_CACHE_TTL - cache_age)
        is_expired = cache_age > AuthService.PERMISSIONS_CACHE_TTL

        return {
            "cached": True,
            "cache_age": cache_age,
            "expires_in": expires_in,
            "is_expired": is_expired,
        }

    @staticmethod
    def invalidate_permissions_cache():
        """Force invalidate permissions cache"""
        if hasattr(st.session_state, "permissions_cached_at"):
            st.session_state.permissions_cached_at = 0
        if "permissions_cache" in st.session_state:
            del st.session_state["permissions_cache"]
        if "permissions_cache_timestamp" in st.session_state:
            del st.session_state["permissions_cache_timestamp"]

    @staticmethod
    def reload_user_from_backend() -> bool:
        """Recarrega todas as informações do usuário do backend, incluindo permissões"""
        try:
            if not AuthService.is_authenticated():
                return False

            # Força uma nova consulta ao backend
            from front.services.api_client import api_client

            user_data = api_client.get_current_user()

            if user_data:
                # Atualiza os dados do usuário na sessão
                st.session_state["user"] = user_data

                # Limpa o cache de permissões para forçar reload
                AuthService.invalidate_permissions_cache()

                # Recarrega as permissões do backend
                AuthService.refresh_user_permissions(force=True)

                logger.info(
                    f"User data reloaded from backend for user: {user_data.get('username')}"
                )
                return True
            else:
                logger.error("Failed to reload user data from backend")
                return False

        except Exception as e:
            logger.error(f"Error reloading user from backend: {str(e)}")
            return False


# Global auth service instance
auth_service = AuthService()
