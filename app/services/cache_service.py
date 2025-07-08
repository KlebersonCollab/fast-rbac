import asyncio
import hashlib
import json
import logging
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Dict, List, Optional

from app.config.settings import settings
from app.models.user import User
from app.services.redis_service import redis_service

logger = logging.getLogger(__name__)


class CacheService:
    """Service for caching user permissions, sessions, and other RBAC data"""

    def __init__(self):
        self.default_ttl = 3600  # 1 hour
        self.session_ttl = 86400  # 24 hours
        self.permission_ttl = 1800  # 30 minutes
        self.user_ttl = 900  # 15 minutes

    def _get_cache_key(self, prefix: str, identifier: str) -> str:
        """Generate cache key with prefix"""
        return f"{settings.app_name}:{prefix}:{identifier}"

    def _hash_key(self, key: str) -> str:
        """Create hash for long keys"""
        return hashlib.md5(key.encode()).hexdigest()

    # User caching
    async def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get cached user data"""
        cache_key = self._get_cache_key("user", str(user_id))
        return await redis_service.get(cache_key)

    async def set_user(self, user_id: int, user_data: Dict[str, Any]) -> bool:
        """Cache user data"""
        cache_key = self._get_cache_key("user", str(user_id))
        return await redis_service.set(cache_key, user_data, self.user_ttl)

    async def delete_user(self, user_id: int) -> bool:
        """Remove user from cache"""
        cache_key = self._get_cache_key("user", str(user_id))
        return await redis_service.delete(cache_key)

    # Permission caching
    async def get_user_permissions(self, user_id: int) -> Optional[List[str]]:
        """Get cached user permissions"""
        cache_key = self._get_cache_key("permissions", str(user_id))
        return await redis_service.get(cache_key)

    async def set_user_permissions(self, user_id: int, permissions: List[str]) -> bool:
        """Cache user permissions"""
        cache_key = self._get_cache_key("permissions", str(user_id))
        return await redis_service.set(cache_key, permissions, self.permission_ttl)

    async def delete_user_permissions(self, user_id: int) -> bool:
        """Remove user permissions from cache"""
        cache_key = self._get_cache_key("permissions", str(user_id))
        return await redis_service.delete(cache_key)

    # Role caching
    async def get_user_roles(self, user_id: int) -> Optional[List[str]]:
        """Get cached user roles"""
        cache_key = self._get_cache_key("roles", str(user_id))
        return await redis_service.get(cache_key)

    async def set_user_roles(self, user_id: int, roles: List[str]) -> bool:
        """Cache user roles"""
        cache_key = self._get_cache_key("roles", str(user_id))
        return await redis_service.set(cache_key, roles, self.permission_ttl)

    async def delete_user_roles(self, user_id: int) -> bool:
        """Remove user roles from cache"""
        cache_key = self._get_cache_key("roles", str(user_id))
        return await redis_service.delete(cache_key)

    # Session caching
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get cached session data"""
        cache_key = self._get_cache_key("session", session_id)
        return await redis_service.get(cache_key)

    async def set_session(self, session_id: str, session_data: Dict[str, Any]) -> bool:
        """Cache session data"""
        cache_key = self._get_cache_key("session", session_id)
        return await redis_service.set(cache_key, session_data, self.session_ttl)

    async def delete_session(self, session_id: str) -> bool:
        """Remove session from cache"""
        cache_key = self._get_cache_key("session", session_id)
        return await redis_service.delete(cache_key)

    async def extend_session(self, session_id: str) -> bool:
        """Extend session TTL"""
        cache_key = self._get_cache_key("session", session_id)
        return await redis_service.expire(cache_key, self.session_ttl)

    # OAuth state caching
    async def get_oauth_state(self, state: str) -> Optional[Dict[str, Any]]:
        """Get cached OAuth state"""
        cache_key = self._get_cache_key("oauth_state", state)
        return await redis_service.get(cache_key)

    async def set_oauth_state(self, state: str, state_data: Dict[str, Any]) -> bool:
        """Cache OAuth state (short TTL)"""
        cache_key = self._get_cache_key("oauth_state", state)
        return await redis_service.set(cache_key, state_data, 600)  # 10 minutes

    async def delete_oauth_state(self, state: str) -> bool:
        """Remove OAuth state from cache"""
        cache_key = self._get_cache_key("oauth_state", state)
        return await redis_service.delete(cache_key)

    # Rate limiting
    async def get_rate_limit(self, key: str) -> Optional[int]:
        """Get current rate limit count"""
        cache_key = self._get_cache_key("rate_limit", key)
        value = await redis_service.get(cache_key)
        return int(value) if value else None

    async def increment_rate_limit(self, key: str, window: int = 60) -> int:
        """Increment rate limit counter"""
        cache_key = self._get_cache_key("rate_limit", key)

        if not redis_service.is_connected():
            return 0

        try:
            # Use Redis INCR for atomic increment
            count = await asyncio.to_thread(redis_service.redis_client.incr, cache_key)
            if count == 1:
                # Set expiry only on first increment
                await asyncio.to_thread(
                    redis_service.redis_client.expire, cache_key, window
                )
            return count
        except Exception as e:
            logger.error(f"Rate limit increment error: {e}")
            return 0

    async def reset_rate_limit(self, key: str) -> bool:
        """Reset rate limit counter"""
        cache_key = self._get_cache_key("rate_limit", key)
        return await redis_service.delete(cache_key)

    # Query result caching
    async def get_query_result(self, query_hash: str) -> Optional[Any]:
        """Get cached query result"""
        cache_key = self._get_cache_key("query", query_hash)
        return await redis_service.get(cache_key)

    async def set_query_result(
        self, query_hash: str, result: Any, ttl: Optional[int] = None
    ) -> bool:
        """Cache query result"""
        cache_key = self._get_cache_key("query", query_hash)
        return await redis_service.set(cache_key, result, ttl or self.default_ttl)

    # Bulk operations
    async def invalidate_user_cache(self, user_id: int) -> bool:
        """Invalidate all cache entries for a user"""
        tasks = [
            self.delete_user(user_id),
            self.delete_user_permissions(user_id),
            self.delete_user_roles(user_id),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)
        return all(isinstance(r, bool) and r for r in results)

    async def invalidate_role_cache(self, role_name: str) -> bool:
        """Invalidate cache for all users with a specific role"""
        # This would require tracking users by role, which is complex
        # For now, we'll implement a simpler approach
        pattern = self._get_cache_key("permissions", "*")
        keys = await redis_service.keys(pattern)

        if not keys:
            return True

        # Delete all permission caches (they'll be rebuilt on next access)
        delete_tasks = [redis_service.delete(key) for key in keys]
        results = await asyncio.gather(*delete_tasks, return_exceptions=True)
        return all(isinstance(r, bool) and r for r in results)

    async def clear_all_cache(self) -> bool:
        """Clear all application cache"""
        pattern = self._get_cache_key("*", "*")
        keys = await redis_service.keys(pattern)

        if not keys:
            return True

        delete_tasks = [redis_service.delete(key) for key in keys]
        results = await asyncio.gather(*delete_tasks, return_exceptions=True)
        return all(isinstance(r, bool) and r for r in results)

    # Statistics
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        try:
            info = await redis_service.info()

            # Count our application keys
            pattern = self._get_cache_key("*", "*")
            our_keys = await redis_service.keys(pattern)

            return {
                "redis_info": {
                    "connected_clients": info.get("connected_clients", 0),
                    "used_memory": info.get("used_memory_human", "0B"),
                    "keyspace_hits": info.get("keyspace_hits", 0),
                    "keyspace_misses": info.get("keyspace_misses", 0),
                    "total_commands_processed": info.get("total_commands_processed", 0),
                },
                "application_cache": {
                    "total_keys": len(our_keys),
                    "key_patterns": {
                        "users": len([k for k in our_keys if ":user:" in k]),
                        "permissions": len(
                            [k for k in our_keys if ":permissions:" in k]
                        ),
                        "roles": len([k for k in our_keys if ":roles:" in k]),
                        "sessions": len([k for k in our_keys if ":session:" in k]),
                        "rate_limits": len(
                            [k for k in our_keys if ":rate_limit:" in k]
                        ),
                        "queries": len([k for k in our_keys if ":query:" in k]),
                    },
                },
            }
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {"error": str(e)}


# Global cache instance
cache_service = CacheService()


def cache_result(ttl: int = 3600, key_prefix: str = ""):
    """Decorator for caching function results"""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Create cache key from function name and arguments
            cache_key = f"{key_prefix}:{func.__name__}:{hash(str(args) + str(kwargs))}"
            cache_key = cache_service._hash_key(cache_key)

            # Try to get from cache
            cached_result = await cache_service.get_query_result(cache_key)
            if cached_result is not None:
                return cached_result

            # Execute function and cache result
            result = await func(*args, **kwargs)
            await cache_service.set_query_result(cache_key, result, ttl)
            return result

        return wrapper

    return decorator
