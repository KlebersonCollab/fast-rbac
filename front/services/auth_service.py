import streamlit as st
from typing import Dict, Any, Optional
from front.services.api_client import api_client, APIException
from front.utils.helpers import clear_session

class AuthService:
    @staticmethod
    def login(username: str, password: str) -> bool:
        """Login user and store session data"""
        try:
            # Call API login
            response = api_client.login(username, password)
            
            if response and "access_token" in response:
                # Store token in session
                st.session_state.token = response["access_token"]
                
                # Get user profile
                user_data = api_client.get_current_user()
                st.session_state.user = user_data
                st.session_state.authenticated = True
                
                return True
            else:
                return False
                
        except APIException as e:
            st.error(f"Erro no login: {e.message}")
            return False
        except Exception as e:
            st.error(f"Erro inesperado: {str(e)}")
            return False
    
    @staticmethod
    def logout():
        """Logout user and clear session"""
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
    def has_permission(permission: str) -> bool:
        """Check if current user has specific permission"""
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
    def get_user_permissions() -> list:
        """Get current user permissions"""
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

# Global auth service instance
auth_service = AuthService() 