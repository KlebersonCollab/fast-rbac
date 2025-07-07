import redis
import json
import pickle
from typing import Any, Optional, Dict, List
from datetime import datetime, timedelta
import asyncio
from contextlib import asynccontextmanager
import logging

from app.config.settings import settings

logger = logging.getLogger(__name__)

class RedisService:
    """Service for Redis operations with connection pooling and error handling"""
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.connection_pool: Optional[redis.ConnectionPool] = None
        self._connected = False
        
    async def connect(self) -> bool:
        """Initialize Redis connection with pool"""
        if not settings.redis_enabled:
            logger.info("Redis disabled in settings")
            return False
            
        try:
            # Create connection pool
            self.connection_pool = redis.ConnectionPool(
                host=settings.redis_host,
                port=settings.redis_port,
                db=settings.redis_db,
                password=settings.redis_password if settings.redis_password else None,
                max_connections=settings.redis_max_connections,
                retry_on_timeout=True,
                socket_timeout=5,
                socket_connect_timeout=5,
                health_check_interval=30,
            )
            
            # Create Redis client
            self.redis_client = redis.Redis(
                connection_pool=self.connection_pool,
                decode_responses=True,
                socket_keepalive=True,
                socket_keepalive_options={}
            )
            
            # Test connection
            await asyncio.to_thread(self.redis_client.ping)
            self._connected = True
            
            logger.info(f"Redis connected to {settings.redis_host}:{settings.redis_port}")
            return True
            
        except Exception as e:
            logger.error(f"Redis connection failed: {e}")
            self._connected = False
            return False
    
    async def disconnect(self):
        """Close Redis connection"""
        if self.connection_pool:
            await asyncio.to_thread(self.connection_pool.disconnect)
            self._connected = False
            logger.info("Redis disconnected")
    
    def is_connected(self) -> bool:
        """Check if Redis is connected"""
        return self._connected and self.redis_client is not None
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from Redis with JSON deserialization"""
        if not self.is_connected():
            return None
            
        try:
            value = await asyncio.to_thread(self.redis_client.get, key)
            if value is None:
                return None
            return json.loads(value)
        except json.JSONDecodeError:
            # Try to return as string if not JSON
            return value
        except Exception as e:
            logger.error(f"Redis GET error for key {key}: {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in Redis with JSON serialization"""
        if not self.is_connected():
            return False
            
        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value, default=str)
            
            if ttl:
                result = await asyncio.to_thread(self.redis_client.setex, key, ttl, value)
            else:
                result = await asyncio.to_thread(self.redis_client.set, key, value)
            
            return bool(result)
        except Exception as e:
            logger.error(f"Redis SET error for key {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from Redis"""
        if not self.is_connected():
            return False
            
        try:
            result = await asyncio.to_thread(self.redis_client.delete, key)
            return bool(result)
        except Exception as e:
            logger.error(f"Redis DELETE error for key {key}: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in Redis"""
        if not self.is_connected():
            return False
            
        try:
            result = await asyncio.to_thread(self.redis_client.exists, key)
            return bool(result)
        except Exception as e:
            logger.error(f"Redis EXISTS error for key {key}: {e}")
            return False
    
    async def expire(self, key: str, ttl: int) -> bool:
        """Set TTL for existing key"""
        if not self.is_connected():
            return False
            
        try:
            result = await asyncio.to_thread(self.redis_client.expire, key, ttl)
            return bool(result)
        except Exception as e:
            logger.error(f"Redis EXPIRE error for key {key}: {e}")
            return False
    
    async def keys(self, pattern: str = "*") -> List[str]:
        """Get keys matching pattern"""
        if not self.is_connected():
            return []
            
        try:
            keys = await asyncio.to_thread(self.redis_client.keys, pattern)
            return keys if keys else []
        except Exception as e:
            logger.error(f"Redis KEYS error for pattern {pattern}: {e}")
            return []
    
    async def flushdb(self) -> bool:
        """Clear all keys in current database"""
        if not self.is_connected():
            return False
            
        try:
            result = await asyncio.to_thread(self.redis_client.flushdb)
            return bool(result)
        except Exception as e:
            logger.error(f"Redis FLUSHDB error: {e}")
            return False
    
    async def info(self) -> Dict[str, Any]:
        """Get Redis server info"""
        if not self.is_connected():
            return {}
            
        try:
            info = await asyncio.to_thread(self.redis_client.info)
            return info
        except Exception as e:
            logger.error(f"Redis INFO error: {e}")
            return {}
    
    # Hash operations
    async def hset(self, name: str, key: str, value: Any) -> bool:
        """Set field in hash"""
        if not self.is_connected():
            return False
            
        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value, default=str)
            result = await asyncio.to_thread(self.redis_client.hset, name, key, value)
            return bool(result)
        except Exception as e:
            logger.error(f"Redis HSET error for hash {name}, key {key}: {e}")
            return False
    
    async def hget(self, name: str, key: str) -> Optional[Any]:
        """Get field from hash"""
        if not self.is_connected():
            return None
            
        try:
            value = await asyncio.to_thread(self.redis_client.hget, name, key)
            if value is None:
                return None
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        except Exception as e:
            logger.error(f"Redis HGET error for hash {name}, key {key}: {e}")
            return None
    
    async def hdel(self, name: str, key: str) -> bool:
        """Delete field from hash"""
        if not self.is_connected():
            return False
            
        try:
            result = await asyncio.to_thread(self.redis_client.hdel, name, key)
            return bool(result)
        except Exception as e:
            logger.error(f"Redis HDEL error for hash {name}, key {key}: {e}")
            return False
    
    async def hgetall(self, name: str) -> Dict[str, Any]:
        """Get all fields from hash"""
        if not self.is_connected():
            return {}
            
        try:
            data = await asyncio.to_thread(self.redis_client.hgetall, name)
            result = {}
            for key, value in data.items():
                try:
                    result[key] = json.loads(value)
                except json.JSONDecodeError:
                    result[key] = value
            return result
        except Exception as e:
            logger.error(f"Redis HGETALL error for hash {name}: {e}")
            return {}

# Global Redis instance
redis_service = RedisService()

@asynccontextmanager
async def get_redis():
    """Context manager for Redis operations"""
    if not redis_service.is_connected():
        await redis_service.connect()
    yield redis_service 