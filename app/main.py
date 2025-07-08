from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.security.utils import get_authorization_scheme_param
from starlette.middleware.sessions import SessionMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import secrets
import logging

from app.config.settings import settings
from app.config.logging import setup_logging, get_system_logger, get_error_logger, log_error
from app.database.base import create_tables, check_database_connection
from app.routes import auth, oauth, admin, protected, cache
from app.routes.auth_2fa import router as auth_2fa_router
from app.database.init_data import initialize_database
from app.services.redis_service import redis_service
from app.services.cache_service import cache_service
from app.middleware.rate_limiting import RateLimitingMiddleware
from app.middleware.logging import (
    LoggingMiddleware,
    PerformanceLoggingMiddleware,
    HealthCheckLoggingMiddleware,
    UserActivityLoggingMiddleware
)

# Setup logging first
setup_logging()
system_logger = get_system_logger()

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address) if settings.rate_limit_enabled else None

# Create FastAPI app with production-ready settings
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="FastAPI application with RBAC and multiple authentication providers",
    docs_url="/docs" if settings.is_development else None,  # Disable docs in production
    redoc_url="/redoc" if settings.is_development else None,  # Disable redoc in production
    openapi_url="/openapi.json" if settings.is_development else None,  # Disable OpenAPI in production
)

# Add rate limiting if enabled
if settings.rate_limit_enabled:
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add advanced rate limiting middleware with Redis
if settings.redis_enabled:
    app.add_middleware(RateLimitingMiddleware, enabled=True)

# Security middlewares (order matters!)
if settings.is_production:
    # Trusted host middleware for production
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*"] if "*" in settings.allowed_origins_list else [
            origin.replace("https://", "").replace("http://", "") 
            for origin in settings.allowed_origins_list
        ]
    )

# Gzip compression for better performance
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Add logging middlewares (order matters!)
app.add_middleware(UserActivityLoggingMiddleware)
app.add_middleware(PerformanceLoggingMiddleware, threshold_ms=500.0)
app.add_middleware(HealthCheckLoggingMiddleware)
app.add_middleware(LoggingMiddleware, log_requests=True, log_responses=settings.debug)

# CORS middleware with security considerations
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "Accept",
        "Origin",
        "User-Agent",
        "X-Requested-With",
        "X-CSRF-Token",
    ],
    expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"],
)

# Session middleware for OAuth with secure settings
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key,
    max_age=86400,  # 24 hours
    same_site="lax",
    https_only=settings.is_production,
)

# Include routers
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(oauth.router, prefix="/oauth", tags=["OAuth"])
app.include_router(auth_2fa_router, prefix="/auth/2fa", tags=["2FA Authentication"])
app.include_router(admin.router, prefix="/admin", tags=["Admin"])
app.include_router(protected.router, prefix="/protected", tags=["Protected"])

# Include cache router if Redis is enabled
if settings.redis_enabled:
    app.include_router(cache.router)


@app.on_event("startup")
async def startup_event():
    """Application startup event"""
    try:
        system_logger.info("Application startup initiated")
        
        # Check database connection
        if not check_database_connection():
            raise Exception("Database connection failed")
        
        # Initialize Redis if enabled
        if settings.redis_enabled:
            redis_connected = await redis_service.connect()
            if redis_connected:
                system_logger.info("Redis connected successfully")
            else:
                system_logger.warning("Redis connection failed - cache disabled")
        
        # Create tables if needed
        create_tables()
        
        # Initialize database with default data
        initialize_database()
        
        system_logger.info("Application startup completed successfully")
        
    except Exception as e:
        error_msg = f"Application startup failed: {e}"
        log_error("system", error_msg, exc_info=e)
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event"""
    system_logger.info("Application shutdown initiated")
    
    # Disconnect Redis if enabled
    if settings.redis_enabled:
        await redis_service.disconnect()
        system_logger.info("Redis disconnected")
    
    system_logger.info("Application shutdown completed")


@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint with basic info"""
    return {
        "message": "FastAPI RBAC System",
        "version": settings.app_version,
        "environment": settings.environment,
        "status": "running"
    }


@app.get("/health", include_in_schema=False)
async def health_check():
    """Health check endpoint for monitoring"""
    try:
        db_status = check_database_connection()
        
        return {
            "status": "healthy" if db_status else "unhealthy",
            "database": "connected" if db_status else "disconnected",
            "environment": settings.environment,
            "version": settings.app_version,
        }
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e),
                "environment": settings.environment,
                "version": settings.app_version,
            }
        )


@app.get("/info", include_in_schema=False)
async def app_info():
    """Application information endpoint (development only)"""
    if not settings.is_development:
        return JSONResponse(status_code=404, content={"detail": "Not found"})
    
    from app.database.base import get_database_info
    
    return {
        "app": {
            "name": settings.app_name,
            "version": settings.app_version,
            "environment": settings.environment,
            "debug": settings.debug,
        },
        "database": get_database_info(),
        "security": {
            "rate_limiting": settings.rate_limit_enabled,
            "redis_enabled": settings.redis_enabled,
        }
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
        access_log=settings.debug,
    ) 