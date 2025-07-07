from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware
import secrets

from app.config.settings import settings
from app.database.base import create_tables
from app.routes import auth, oauth, admin, protected
from app.database.init_data import initialize_database

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="FastAPI application with RBAC and multiple authentication providers",
    docs_url="/docs",
    redoc_url="/redoc"
)

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
    create_tables()
    # Uncomment to initialize default data
    # initialize_database()


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
    return JSONResponse(
        status_code=404,
        content={"detail": "Endpoint not found"}
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    """Custom 500 handler"""
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    ) 