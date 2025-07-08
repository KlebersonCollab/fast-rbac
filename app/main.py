import logging
import os
import time
from contextlib import asynccontextmanager
from typing import Any, Dict

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import Response

from app.config.logging import (
    get_error_logger,
    get_system_logger,
    log_error,
    setup_logging,
)
from app.config.settings import settings
from app.database.base import check_database_connection, create_tables
from app.middleware.api_key_auth import APIKeyMiddleware
from app.middleware.logging import LoggingMiddleware
from app.middleware.rate_limiting import RateLimitingMiddleware
from app.middleware.rbac import RBACMiddleware
from app.models.api_key import APIKey, APIKeyUsage
from app.models.tenant import Tenant, TenantSettings

# Import all models to ensure they are registered with SQLAlchemy
from app.models.user import Permission, Role, User
from app.models.webhook import Webhook, WebhookDelivery, WebhookLog
from app.routes import admin, auth, cache, oauth, protected

# Import new Level 5 routers
from app.routes.api_keys import router as api_keys_router
from app.routes.auth_2fa import router as auth_2fa_router
from app.routes.tenants import router as tenants_router
from app.routes.webhooks import router as webhooks_router

# Setup logging
setup_logging()
system_logger = get_system_logger()
error_logger = get_error_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    system_logger.info("Starting FastAPI RBAC System...")

    # Test database connection
    if not check_database_connection():
        error_logger.error("Database connection failed!")
        raise Exception("Database connection failed!")

    # Create tables
    create_tables()

    # Initialize database with default data
    try:
        from app.database.init_data import init_database

        init_database()
        system_logger.info("Database initialized successfully")
    except Exception as e:
        error_logger.error(f"Database initialization failed: {e}")
        raise

    system_logger.info("FastAPI RBAC System started successfully")

    yield

    # Shutdown
    system_logger.info("Shutting down FastAPI RBAC System...")
    # Add any cleanup tasks here
    system_logger.info("FastAPI RBAC System shut down")


# Create FastAPI app with lifespan
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=settings.description,
    docs_url=settings.docs_url,
    redoc_url=settings.redoc_url,
    openapi_url=settings.openapi_url,
    lifespan=lifespan,
)

# Add rate limiting if enabled
# if settings.rate_limit_enabled:
#     app.state.limiter = limiter
#     app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add advanced rate limiting middleware with Redis
if settings.redis_enabled:
    app.add_middleware(RateLimitingMiddleware, enabled=True)

# Security middlewares (order matters!)
if settings.is_production:
    # Trusted host middleware for production
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=(
            ["*"]
            if "*" in settings.allowed_origins_list
            else [
                origin.replace("https://", "").replace("http://", "")
                for origin in settings.allowed_origins_list
            ]
        ),
    )

# Gzip compression for better performance
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Add logging middlewares (order matters!)
# app.add_middleware(UserActivityLoggingMiddleware)
# app.add_middleware(PerformanceLoggingMiddleware, threshold_ms=500.0)
# app.add_middleware(HealthCheckLoggingMiddleware)
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

# Include routers ATIVOS (usados pelo frontend)
app.include_router(auth.router, prefix="/auth")
app.include_router(oauth.router, prefix="/oauth")
app.include_router(admin.router, prefix="/admin")
app.include_router(protected.router, prefix="/protected")

# Include NÍVEL 5 - Enterprise routers (AGORA INTEGRADOS AO FRONTEND!)
app.include_router(api_keys_router)
app.include_router(tenants_router)
app.include_router(webhooks_router)

# Include outros routers ATIVOS
app.include_router(auth_2fa_router, prefix="/auth/2fa")

# Include cache router if Redis is enabled (NÃO USADO PELO FRONTEND)
# if settings.redis_enabled:
#     app.include_router(cache.router)


@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint with basic info"""
    return {
        "message": "FastAPI RBAC System",
        "version": settings.app_version,
        "environment": settings.environment,
        "status": "running",
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
            },
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
        },
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
