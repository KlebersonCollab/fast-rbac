from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
import logging
import asyncio

from app.database.base import get_db
from app.services.cache_service import cache_service
from app.services.redis_service import redis_service
from app.middleware.rate_limiting import get_rate_limit_stats
from app.auth.dependencies import get_current_user, require_superuser
from app.models.user import User
from app.config.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cache", tags=["cache"])

@router.get("/stats", response_model=Dict[str, Any])
async def get_cache_stats(
    current_user: User = Depends(require_superuser),
    db: Session = Depends(get_db)
):
    """Get comprehensive cache statistics (superuser only)"""
    try:
        if not settings.redis_enabled:
            return {"error": "Redis not enabled"}
        
        # Get cache statistics
        cache_stats = await cache_service.get_cache_stats()
        
        # Get rate limit statistics
        rate_limit_stats = await get_rate_limit_stats()
        
        return {
            "cache_stats": cache_stats,
            "rate_limit_stats": rate_limit_stats,
            "redis_enabled": settings.redis_enabled,
            "redis_connected": redis_service.is_connected(),
        }
        
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting cache stats: {str(e)}"
        )

@router.get("/health")
async def cache_health():
    """Check cache health status"""
    try:
        if not settings.redis_enabled:
            return {"status": "disabled", "message": "Redis not enabled"}
        
        if not redis_service.is_connected():
            return {"status": "disconnected", "message": "Redis not connected"}
        
        # Test Redis connection
        await redis_service.set("health_check", "test", 60)
        test_value = await redis_service.get("health_check")
        await redis_service.delete("health_check")
        
        if test_value == "test":
            return {"status": "healthy", "message": "Redis connection working"}
        else:
            return {"status": "unhealthy", "message": "Redis test failed"}
            
    except Exception as e:
        logger.error(f"Cache health check failed: {e}")
        return {"status": "error", "message": str(e)}

@router.post("/clear")
async def clear_cache(
    cache_type: Optional[str] = None,
    current_user: User = Depends(require_superuser),
    db: Session = Depends(get_db)
):
    """Clear cache (superuser only)"""
    try:
        if not settings.redis_enabled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Redis not enabled"
            )
        
        if cache_type == "all":
            success = await cache_service.clear_all_cache()
            message = "All cache cleared" if success else "Failed to clear cache"
        elif cache_type == "permissions":
            # Clear all permission caches
            keys = await redis_service.keys("*permissions*")
            if keys:
                delete_tasks = [redis_service.delete(key) for key in keys]
                results = await asyncio.gather(*delete_tasks)
                success = all(results)
            else:
                success = True
            message = "Permission cache cleared" if success else "Failed to clear permission cache"
        elif cache_type == "users":
            # Clear all user caches
            keys = await redis_service.keys("*user*")
            if keys:
                delete_tasks = [redis_service.delete(key) for key in keys]
                results = await asyncio.gather(*delete_tasks)
                success = all(results)
            else:
                success = True
            message = "User cache cleared" if success else "Failed to clear user cache"
        elif cache_type == "sessions":
            # Clear all session caches
            keys = await redis_service.keys("*session*")
            if keys:
                delete_tasks = [redis_service.delete(key) for key in keys]
                results = await asyncio.gather(*delete_tasks)
                success = all(results)
            else:
                success = True
            message = "Session cache cleared" if success else "Failed to clear session cache"
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid cache type. Use: all, permissions, users, or sessions"
            )
        
        return {"success": success, "message": message}
        
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error clearing cache: {str(e)}"
        )

@router.get("/keys")
async def get_cache_keys(
    pattern: str = "*",
    current_user: User = Depends(require_superuser),
    db: Session = Depends(get_db)
):
    """Get cache keys matching pattern (superuser only)"""
    try:
        if not settings.redis_enabled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Redis not enabled"
            )
        
        keys = await redis_service.keys(pattern)
        return {"keys": keys, "count": len(keys)}
        
    except Exception as e:
        logger.error(f"Error getting cache keys: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting cache keys: {str(e)}"
        )

@router.get("/key/{key}")
async def get_cache_value(
    key: str,
    current_user: User = Depends(require_superuser),
    db: Session = Depends(get_db)
):
    """Get value for specific cache key (superuser only)"""
    try:
        if not settings.redis_enabled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Redis not enabled"
            )
        
        value = await redis_service.get(key)
        exists = await redis_service.exists(key)
        
        return {
            "key": key,
            "value": value,
            "exists": exists,
            "type": type(value).__name__ if value is not None else None
        }
        
    except Exception as e:
        logger.error(f"Error getting cache value: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting cache value: {str(e)}"
        )

@router.delete("/key/{key}")
async def delete_cache_key(
    key: str,
    current_user: User = Depends(require_superuser),
    db: Session = Depends(get_db)
):
    """Delete specific cache key (superuser only)"""
    try:
        if not settings.redis_enabled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Redis not enabled"
            )
        
        existed = await redis_service.exists(key)
        success = await redis_service.delete(key)
        
        return {
            "key": key,
            "existed": existed,
            "deleted": success,
            "message": "Key deleted successfully" if success else "Key not found or deletion failed"
        }
        
    except Exception as e:
        logger.error(f"Error deleting cache key: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting cache key: {str(e)}"
        )

@router.post("/invalidate/user/{user_id}")
async def invalidate_user_cache(
    user_id: int,
    current_user: User = Depends(require_superuser),
    db: Session = Depends(get_db)
):
    """Invalidate cache for specific user (superuser only)"""
    try:
        if not settings.redis_enabled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Redis not enabled"
            )
        
        success = await cache_service.invalidate_user_cache(user_id)
        
        return {
            "user_id": user_id,
            "success": success,
            "message": "User cache invalidated successfully" if success else "Failed to invalidate user cache"
        }
        
    except Exception as e:
        logger.error(f"Error invalidating user cache: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error invalidating user cache: {str(e)}"
        )

@router.post("/test")
async def test_cache_performance(
    iterations: int = 100,
    current_user: User = Depends(require_superuser),
    db: Session = Depends(get_db)
):
    """Test cache performance (superuser only)"""
    try:
        if not settings.redis_enabled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Redis not enabled"
            )
        
        import time
        import asyncio
        
        # Test write performance
        start_time = time.time()
        write_tasks = []
        for i in range(iterations):
            task = redis_service.set(f"test_key_{i}", f"test_value_{i}", 60)
            write_tasks.append(task)
        
        await asyncio.gather(*write_tasks)
        write_time = time.time() - start_time
        
        # Test read performance
        start_time = time.time()
        read_tasks = []
        for i in range(iterations):
            task = redis_service.get(f"test_key_{i}")
            read_tasks.append(task)
        
        await asyncio.gather(*read_tasks)
        read_time = time.time() - start_time
        
        # Clean up test keys
        cleanup_tasks = []
        for i in range(iterations):
            task = redis_service.delete(f"test_key_{i}")
            cleanup_tasks.append(task)
        
        await asyncio.gather(*cleanup_tasks)
        
        return {
            "iterations": iterations,
            "write_time": round(write_time, 4),
            "read_time": round(read_time, 4),
            "write_ops_per_second": round(iterations / write_time, 2),
            "read_ops_per_second": round(iterations / read_time, 2),
            "total_time": round(write_time + read_time, 4)
        }
        
    except Exception as e:
        logger.error(f"Error testing cache performance: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error testing cache performance: {str(e)}"
        ) 