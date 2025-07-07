from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from functools import wraps
import asyncio
import logging

from app.models.user import User, Permission
from app.database.base import get_db
from app.services.cache_service import cache_service, cache_result
from app.config.settings import settings

logger = logging.getLogger(__name__)

class PermissionService:
    """Enhanced permission service with Redis caching"""
    
    def __init__(self):
        self.cache_enabled = settings.redis_enabled
    
    async def get_user_permissions(self, user_id: int, db: Session = None) -> List[str]:
        """Get user permissions with caching"""
        if self.cache_enabled:
            # Try to get from cache first
            cached_permissions = await cache_service.get_user_permissions(user_id)
            if cached_permissions is not None:
                return cached_permissions
        
        # Get from database
        permissions = await self._get_user_permissions_from_db(user_id, db)
        
        # Cache the result
        if self.cache_enabled:
            await cache_service.set_user_permissions(user_id, permissions)
        
        return permissions
    
    async def _get_user_permissions_from_db(self, user_id: int, db: Session = None) -> List[str]:
        """Get user permissions from database"""
        if db is None:
            db = next(get_db())
        
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return []
            
            permissions = set()
            
            # Get permissions from user's roles
            for role in user.roles:
                for permission in role.permissions:
                    permissions.add(permission.name)
            
            # Get direct permissions (if implemented)
            for permission in user.permissions:
                permissions.add(permission.name)
            
            return list(permissions)
            
        except Exception as e:
            logger.error(f"Error getting permissions for user {user_id}: {e}")
            return []
    
    async def get_user_roles(self, user_id: int, db: Session = None) -> List[str]:
        """Get user roles with caching"""
        if self.cache_enabled:
            # Try to get from cache first
            cached_roles = await cache_service.get_user_roles(user_id)
            if cached_roles is not None:
                return cached_roles
        
        # Get from database
        roles = await self._get_user_roles_from_db(user_id, db)
        
        # Cache the result
        if self.cache_enabled:
            await cache_service.set_user_roles(user_id, roles)
        
        return roles
    
    async def _get_user_roles_from_db(self, user_id: int, db: Session = None) -> List[str]:
        """Get user roles from database"""
        if db is None:
            db = next(get_db())
        
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return []
            
            return [role.name for role in user.roles]
            
        except Exception as e:
            logger.error(f"Error getting roles for user {user_id}: {e}")
            return []
    
    async def has_permission(self, user_id: int, permission: str, db: Session = None) -> bool:
        """Check if user has specific permission"""
        permissions = await self.get_user_permissions(user_id, db)
        return permission in permissions
    
    async def has_role(self, user_id: int, role: str, db: Session = None) -> bool:
        """Check if user has specific role"""
        roles = await self.get_user_roles(user_id, db)
        return role in roles
    
    async def has_any_permission(self, user_id: int, permissions: List[str], db: Session = None) -> bool:
        """Check if user has any of the specified permissions"""
        user_permissions = await self.get_user_permissions(user_id, db)
        return any(perm in user_permissions for perm in permissions)
    
    async def has_all_permissions(self, user_id: int, permissions: List[str], db: Session = None) -> bool:
        """Check if user has all specified permissions"""
        user_permissions = await self.get_user_permissions(user_id, db)
        return all(perm in user_permissions for perm in permissions)
    
    async def invalidate_user_cache(self, user_id: int) -> bool:
        """Invalidate user cache when permissions change"""
        if not self.cache_enabled:
            return True
        
        return await cache_service.invalidate_user_cache(user_id)
    
    async def invalidate_role_cache(self, role_name: str) -> bool:
        """Invalidate cache for all users with a specific role"""
        if not self.cache_enabled:
            return True
        
        return await cache_service.invalidate_role_cache(role_name)
    
    @cache_result(ttl=1800, key_prefix="permission_check")
    async def check_resource_permission(self, user_id: int, resource: str, action: str) -> bool:
        """Check if user has permission for specific resource and action"""
        permission_name = f"{resource}:{action}"
        return await self.has_permission(user_id, permission_name)

# Global permission service instance
permission_service = PermissionService()

def require_permission(permission: str):
    """Decorator to require specific permission"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # This would be used with FastAPI dependency injection
            # For now, we'll implement a basic version
            # In real implementation, you'd extract user_id from JWT token
            user_id = kwargs.get('current_user_id')
            if not user_id:
                raise Exception("User not authenticated")
            
            has_perm = await permission_service.has_permission(user_id, permission)
            if not has_perm:
                raise Exception(f"Permission denied: {permission}")
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

def require_role(role: str):
    """Decorator to require specific role"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            user_id = kwargs.get('current_user_id')
            if not user_id:
                raise Exception("User not authenticated")
            
            has_role = await permission_service.has_role(user_id, role)
            if not has_role:
                raise Exception(f"Role required: {role}")
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

def require_any_permission(permissions: List[str]):
    """Decorator to require any of the specified permissions"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            user_id = kwargs.get('current_user_id')
            if not user_id:
                raise Exception("User not authenticated")
            
            has_any = await permission_service.has_any_permission(user_id, permissions)
            if not has_any:
                raise Exception(f"One of these permissions required: {permissions}")
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

# Compatibility with existing code
async def get_user_permissions(user_id: int, db: Session = None) -> List[str]:
    """Get user permissions (legacy compatibility)"""
    return await permission_service.get_user_permissions(user_id, db)

async def check_permission(user_id: int, permission: str, db: Session = None) -> bool:
    """Check user permission (legacy compatibility)"""
    return await permission_service.has_permission(user_id, permission, db)

async def check_role(user_id: int, role: str, db: Session = None) -> bool:
    """Check user role (legacy compatibility)"""
    return await permission_service.has_role(user_id, role, db) 