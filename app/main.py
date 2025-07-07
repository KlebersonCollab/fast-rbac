from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware
import secrets

from app.config.settings import settings
from app.config.logging import setup_logging, get_system_logger, get_error_logger, log_error
from app.database.base import create_tables
from app.routes import auth, oauth, admin, protected
from app.database.init_data import initialize_database
from app.middleware.logging import (
    LoggingMiddleware,
    PerformanceLoggingMiddleware,
    HealthCheckLoggingMiddleware,
    UserActivityLoggingMiddleware
)

# Setup logging first
setup_logging()
system_logger = get_system_logger()

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="FastAPI application with RBAC and multiple authentication providers",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add logging middlewares (order matters!)
app.add_middleware(UserActivityLoggingMiddleware)
app.add_middleware(PerformanceLoggingMiddleware, threshold_ms=500.0)
app.add_middleware(HealthCheckLoggingMiddleware)
app.add_middleware(LoggingMiddleware, log_requests=True, log_responses=True)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add session middleware for OAuth
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key or secrets.token_urlsafe(32)
)

# Include routers
app.include_router(auth.router)
app.include_router(oauth.router)
app.include_router(admin.router)
app.include_router(protected.router)


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    system_logger.info("Application startup initiated")
    
    try:
        create_tables()
        system_logger.info("Database tables created successfully")
        
        # Uncomment to initialize default data
        # initialize_database()
        # system_logger.info("Default data initialized")
        
        system_logger.info("Application startup completed successfully")
        
    except Exception as e:
        system_logger.error(f"Error during startup: {e}", exc_info=True)
        raise


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "FastAPI RBAC Application",
        "version": settings.app_version,
        "docs": "/docs",
        "endpoints": {
            "auth": "/auth",
            "oauth": "/oauth",
            "admin": "/admin",
            "protected": "/protected"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": settings.app_name}


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """Custom 404 handler"""
    error_logger = get_error_logger()
    trace_id = getattr(request.state, 'trace_id', 'unknown')
    
    error_logger.warning(
        f"404 Not Found: {request.method} {request.url.path}",
        extra={
            "trace_id": trace_id,
            "method": request.method,
            "endpoint": request.url.path,
            "status_code": 404,
            "ip_address": request.client.host if request.client else "unknown",
            "user_agent": request.headers.get("user-agent", ""),
            "action": "not_found"
        }
    )
    
    return JSONResponse(
        status_code=404,
        content={
            "detail": "Endpoint not found",
            "trace_id": trace_id
        }
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    """Custom 500 handler"""
    trace_id = getattr(request.state, 'trace_id', 'unknown')
    
    log_error(
        error=exc,
        context=f"Internal server error for {request.method} {request.url.path}",
        trace_id=trace_id,
        method=request.method,
        endpoint=request.url.path,
        ip_address=request.client.host if request.client else "unknown"
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "trace_id": trace_id
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    ) 