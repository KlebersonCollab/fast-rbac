import streamlit as st
import time
from typing import Dict, Any, Optional
from front.services.api_client import api_client, APIException
from front.utils.helpers import clear_session
from front.config.logging import (
    log_user_action, 
    log_permission_check, 
    log_frontend_error,
    get_frontend_logger
)

class AuthService:
    # Cache TTL para permissões (em segundos)
    PERMISSIONS_CACHE_TTL = 300  # 5 minutos
    
    @staticmethod
    def login(username: str, password: str) -> bool:
        """Login user and store session data"""
        try:
            # Log login attempt
            log_user_action("login_attempt", page="login", success=False, 
                          resource="authentication", details={"username": username})
            
            # Call API login
            response = api_client.login(username, password)
            
            if response and "access_token" in response:
                # Store token in session
                st.session_state.token = response["access_token"]
                
                # Get user profile
                user_data = api_client.get_current_user()
                st.session_state.user = user_data
                st.session_state.authenticated = True
                # Mark permissions cache timestamp
                st.session_state.permissions_cached_at = time.time()
                
                # Log successful login
                log_user_action("login", page="login", success=True, 
                              resource="authentication", 
                              details={
                                  "username": username,
                                  "roles_count": len(user_data.get("roles", [])),
                                  "user_id": user_data.get("id")
                              })
                
                return True
            else:
                # Log failed login
                log_user_action("login_failed", page="login", success=False, 
                              resource="authentication", 
                              details={"username": username, "reason": "invalid_credentials"})
                return False
                
        except APIException as e:
            st.error(f"Erro no login: {e.message}")
            log_user_action("login_error", page="login", success=False, 
                          resource="authentication", 
                          details={"username": username, "error": e.message})
            return False
        except Exception as e:
            st.error(f"Erro inesperado: {str(e)}")
            log_frontend_error(e, "login_process", page="login")
            return False
    
    @staticmethod
    def logout():
        """Logout user and clear session"""
        # Log logout action before clearing session
        user = AuthService.get_current_user()
        username = user.get("username") if user else "unknown"
        user_id = user.get("id") if user else None
        
        log_user_action("logout", page="auth", success=True, 
                      resource="authentication", 
                      details={"username": username, "user_id": user_id})
        
        clear_session()
        st.session_state.authenticated = False
        st.session_state.user = None
        st.session_state.token = None
        st.success("Logout realizado com sucesso!")
        st.rerun()
    
    @staticmethod
    def register(username: str, email: str, password: str, full_name: str = None) -> bool:
        """Register new user"""
        try:
            response = api_client.register(username, email, password, full_name)
            
            if response:
                st.success("Usuário registrado com sucesso! Faça login para continuar.")
                return True
            else:
                return False
                
        except APIException as e:
            st.error(f"Erro no registro: {e.message}")
            return False
        except Exception as e:
            st.error(f"Erro inesperado: {str(e)}")
            return False
    
    @staticmethod
    def is_authenticated() -> bool:
        """Check if user is authenticated"""
        if not hasattr(st.session_state, 'authenticated'):
            return False
        
        if not st.session_state.authenticated:
            return False
        
        if not st.session_state.token:
            return False
        
        # Test token validity
        try:
            api_client.test_token()
            return True
        except APIException:
            # Token is invalid, clear session
            AuthService.logout()
            return False
        except Exception:
            return False
    
    @staticmethod
    def get_current_user() -> Optional[Dict[str, Any]]:
        """Get current user data"""
        if AuthService.is_authenticated():
            return st.session_state.user
        return None
    
    @staticmethod
    def _is_permissions_cache_expired() -> bool:
        """Check if permissions cache is expired"""
        if not hasattr(st.session_state, 'permissions_cached_at'):
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
        user = AuthService.get_current_user()
        if not user:
            log_permission_check(permission, granted=False, page="unknown", 
                               reason="no_user")
            return False
        
        # Check if user is superuser
        if user.get("is_superuser", False):
            log_permission_check(permission, granted=True, page="unknown", 
                               reason="superuser")
            return True
        
        # Try to refresh permissions if cache is expired
        AuthService.refresh_user_permissions()
        
        # Get updated user data
        user = AuthService.get_current_user()
        if not user:
            log_permission_check(permission, granted=False, page="unknown", 
                               reason="user_lost_after_refresh")
            return False
        
        # Check roles and permissions
        roles = user.get("roles", [])
        for role in roles:
            permissions = role.get("permissions", [])
            for perm in permissions:
                if perm.get("name") == permission:
                    log_permission_check(permission, granted=True, page="unknown", 
                                       role=role.get("name"))
                    return True
        
        log_permission_check(permission, granted=False, page="unknown", 
                           reason="permission_not_found")
        return False
    
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
        if not hasattr(st.session_state, 'permissions_cached_at'):
            return {
                "cached": False,
                "cache_age": 0,
                "expires_in": 0,
                "is_expired": True
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
            "is_expired": is_expired
        }
    
    @staticmethod
    def invalidate_permissions_cache():
        """Force invalidate permissions cache"""
        if hasattr(st.session_state, 'permissions_cached_at'):
            st.session_state.permissions_cached_at = 0

# Global auth service instance
auth_service = AuthService() 