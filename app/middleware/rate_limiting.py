from typing import Dict, Optional, Tuple, Callable
from datetime import datetime, timedelta
from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import asyncio
import logging
import time

from app.services.cache_service import cache_service
from app.config.settings import settings

logger = logging.getLogger(__name__)

class RateLimitingMiddleware(BaseHTTPMiddleware):
    """Advanced rate limiting middleware with Redis backend"""
    
    def __init__(self, app, enabled: bool = True):
        super().__init__(app)
        self.enabled = enabled and settings.redis_enabled
        
        # Rate limiting configurations
        self.rate_limits = {
            # Default limits
            "default": {"requests": 100, "window": 60},  # 100 requests per minute
            
            # Authentication endpoints (more restrictive)
            "auth": {"requests": 10, "window": 60},  # 10 requests per minute
            "login": {"requests": 5, "window": 300},  # 5 attempts per 5 minutes
            "register": {"requests": 3, "window": 300},  # 3 attempts per 5 minutes
            
            # API endpoints
            "api": {"requests": 1000, "window": 60},  # 1000 requests per minute
            "api_write": {"requests": 100, "window": 60},  # 100 write operations per minute
            
            # Admin endpoints
            "admin": {"requests": 50, "window": 60},  # 50 requests per minute
            
            # OAuth endpoints
            "oauth": {"requests": 20, "window": 60},  # 20 requests per minute
        }
        
        # Path patterns for different rate limits
        self.path_patterns = {
            r"/auth/login": "login",
            r"/auth/register": "register",
            r"/auth/.*": "auth",
            r"/oauth/.*": "oauth",
            r"/admin/.*": "admin",
            r"/api/.*/create": "api_write",
            r"/api/.*/update": "api_write",
            r"/api/.*/delete": "api_write",
            r"/api/.*": "api",
        }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with rate limiting"""
        if not self.enabled:
            return await call_next(request)
        
        # Get client identifier
        client_id = self._get_client_id(request)
        
        # Determine rate limit type
        rate_limit_type = self._get_rate_limit_type(request.url.path)
        
        # Check rate limit
        allowed, remaining, reset_time = await self._check_rate_limit(
            client_id, rate_limit_type, request.url.path
        )
        
        if not allowed:
            # Rate limit exceeded
            return await self._rate_limit_exceeded_response(remaining, reset_time)
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(self.rate_limits[rate_limit_type]["requests"])
        response.headers["X-RateLimit-Remaining"] = str(max(0, remaining - 1))
        response.headers["X-RateLimit-Reset"] = str(int(reset_time))
        
        return response
    
    def _get_client_id(self, request: Request) -> str:
        """Get client identifier for rate limiting"""
        # Try to get user ID from JWT token
        authorization = request.headers.get("Authorization")
        if authorization:
            try:
                # This would extract user_id from JWT token
                # For now, we'll use a simple approach
                user_id = getattr(request.state, 'user_id', None)
                if user_id:
                    return f"user:{user_id}"
            except:
                pass
        
        # Use IP address as fallback
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return f"ip:{forwarded_for.split(',')[0].strip()}"
        
        return f"ip:{request.client.host}"
    
    def _get_rate_limit_type(self, path: str) -> str:
        """Determine rate limit type based on request path"""
        import re
        
        for pattern, limit_type in self.path_patterns.items():
            if re.match(pattern, path):
                return limit_type
        
        return "default"
    
    async def _check_rate_limit(self, client_id: str, rate_limit_type: str, path: str) -> Tuple[bool, int, float]:
        """Check if request is within rate limit"""
        config = self.rate_limits[rate_limit_type]
        window = config["window"]
        limit = config["requests"]
        
        # Create unique key for this client and rate limit type
        key = f"rate_limit:{rate_limit_type}:{client_id}"
        
        try:
            # Get current count
            current_count = await cache_service.increment_rate_limit(key, window)
            
            # Calculate reset time
            reset_time = time.time() + window
            
            # Check if limit exceeded
            if current_count > limit:
                remaining = 0
                allowed = False
            else:
                remaining = limit - current_count
                allowed = True
            
            return allowed, remaining, reset_time
            
        except Exception as e:
            logger.error(f"Rate limit check error: {e}")
            # If Redis is down, allow the request
            return True, limit, time.time() + window
    
    async def _rate_limit_exceeded_response(self, remaining: int, reset_time: float) -> JSONResponse:
        """Create rate limit exceeded response"""
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "error": "Rate limit exceeded",
                "message": "Too many requests. Please try again later.",
                "remaining": remaining,
                "reset_time": int(reset_time),
                "retry_after": int(reset_time - time.time())
            },
            headers={
                "Retry-After": str(int(reset_time - time.time())),
                "X-RateLimit-Remaining": str(remaining),
                "X-RateLimit-Reset": str(int(reset_time))
            }
        )

class AdaptiveRateLimiter:
    """Adaptive rate limiter that adjusts based on system load"""
    
    def __init__(self):
        self.base_limits = {
            "default": 100,
            "auth": 10,
            "api": 1000,
        }
        self.load_factor = 1.0  # Will be adjusted based on system load
    
    async def get_current_limit(self, rate_limit_type: str) -> int:
        """Get current limit adjusted for system load"""
        base_limit = self.base_limits.get(rate_limit_type, 100)
        return int(base_limit * self.load_factor)
    
    async def update_load_factor(self):
        """Update load factor based on system metrics"""
        try:
            # Get Redis info for system load indicators
            redis_info = await cache_service.redis_service.info()
            
            # Simple load calculation based on Redis metrics
            if redis_info:
                used_memory = redis_info.get('used_memory', 0)
                max_memory = redis_info.get('maxmemory', 0)
                
                if max_memory > 0:
                    memory_usage = used_memory / max_memory
                    
                    # Adjust load factor based on memory usage
                    if memory_usage > 0.8:
                        self.load_factor = 0.5  # Reduce limits by 50%
                    elif memory_usage > 0.6:
                        self.load_factor = 0.7  # Reduce limits by 30%
                    else:
                        self.load_factor = 1.0  # Normal limits
                        
        except Exception as e:
            logger.error(f"Error updating load factor: {e}")
            self.load_factor = 1.0

class CircuitBreaker:
    """Circuit breaker pattern for rate limiting"""
    
    def __init__(self, failure_threshold: int = 5, reset_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.state = "closed"  # closed, open, half-open
        self.failure_count = 0
        self.last_failure_time = 0
    
    async def should_allow_request(self, client_id: str) -> bool:
        """Check if request should be allowed based on circuit breaker state"""
        current_time = time.time()
        
        if self.state == "open":
            # Check if reset timeout has passed
            if current_time - self.last_failure_time > self.reset_timeout:
                self.state = "half-open"
                self.failure_count = 0
                return True
            return False
        
        return True
    
    async def record_success(self, client_id: str):
        """Record successful request"""
        if self.state == "half-open":
            self.state = "closed"
            self.failure_count = 0
    
    async def record_failure(self, client_id: str):
        """Record failed request"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "open"

# Global instances
adaptive_rate_limiter = AdaptiveRateLimiter()
circuit_breaker = CircuitBreaker()

async def check_rate_limit(client_id: str, rate_limit_type: str = "default") -> Tuple[bool, int, float]:
    """Standalone function to check rate limit"""
    if not settings.redis_enabled:
        return True, 100, time.time() + 60
    
    # Check circuit breaker
    if not await circuit_breaker.should_allow_request(client_id):
        return False, 0, time.time() + circuit_breaker.reset_timeout
    
    # Get current limit (adaptive)
    current_limit = await adaptive_rate_limiter.get_current_limit(rate_limit_type)
    
    # Check rate limit
    key = f"rate_limit:{rate_limit_type}:{client_id}"
    try:
        current_count = await cache_service.increment_rate_limit(key, 60)
        
        if current_count > current_limit:
            await circuit_breaker.record_failure(client_id)
            return False, 0, time.time() + 60
        
        await circuit_breaker.record_success(client_id)
        return True, current_limit - current_count, time.time() + 60
        
    except Exception as e:
        logger.error(f"Rate limit check error: {e}")
        return True, current_limit, time.time() + 60

async def reset_rate_limit(client_id: str, rate_limit_type: str = "default") -> bool:
    """Reset rate limit for a client"""
    if not settings.redis_enabled:
        return True
    
    key = f"rate_limit:{rate_limit_type}:{client_id}"
    return await cache_service.reset_rate_limit(key)

async def get_rate_limit_stats() -> Dict[str, any]:
    """Get rate limiting statistics"""
    if not settings.redis_enabled:
        return {"error": "Redis not enabled"}
    
    try:
        # Get all rate limit keys
        keys = await cache_service.redis_service.keys("*rate_limit*")
        
        stats = {
            "total_clients": len(keys),
            "load_factor": adaptive_rate_limiter.load_factor,
            "circuit_breaker_state": circuit_breaker.state,
            "circuit_breaker_failures": circuit_breaker.failure_count,
        }
        
        return stats
        
    except Exception as e:
        logger.error(f"Error getting rate limit stats: {e}")
        return {"error": str(e)} 