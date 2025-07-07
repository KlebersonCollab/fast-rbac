from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional
from app.database.base import get_db
from app.auth.utils import verify_token
from app.auth.service import AuthService
from app.models.user import User

security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    token = credentials.credentials
    username = verify_token(token)
    if username is None:
        raise credentials_exception
    
    auth_service = AuthService(db)
    user = auth_service.get_user_by_username(username)
    if user is None:
        raise credentials_exception
    
    return user


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Get current active user"""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


def get_current_superuser(current_user: User = Depends(get_current_user)) -> User:
    """Get current superuser"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges"
        )
    return current_user


def require_permission(permission_name: str):
    """Decorator to require specific permission"""
    def permission_checker(current_user: User = Depends(get_current_active_user)) -> User:
        if not current_user.has_permission(permission_name):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{permission_name}' required"
            )
        return current_user
    return permission_checker


def require_role(role_name: str):
    """Decorator to require specific role"""
    def role_checker(current_user: User = Depends(get_current_active_user)) -> User:
        if not current_user.has_role(role_name):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{role_name}' required"
            )
        return current_user
    return role_checker


def require_superadmin():
    """Decorator to require superadmin role"""
    def superadmin_checker(current_user: User = Depends(get_current_active_user)) -> User:
        # Verificar se é superuser OU tem role superadmin
        if not (current_user.is_superuser or current_user.has_role("superadmin")):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Superadmin privileges required"
            )
        return current_user
    return superadmin_checker


def require_superadmin_or_admin():
    """Decorator to require superadmin or admin role"""
    def admin_checker(current_user: User = Depends(get_current_active_user)) -> User:
        if not (current_user.is_superuser or 
                current_user.has_role("superadmin") or 
                current_user.has_role("admin")):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin or superadmin privileges required"
            )
        return current_user
    return admin_checker 