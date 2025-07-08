import time
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from fastapi import HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database.base import get_db
from app.models.api_key import APIKey
from app.models.user import User
from app.services.api_key_service import APIKeyService


class APIKeyAuth:
    """API Key authentication handler"""

    def __init__(self):
        self.security = HTTPBearer(auto_error=False)

    async def __call__(self, request: Request) -> Optional[APIKey]:
        """Authenticate API key from request"""
        # Try to get API key from header
        api_key = self._get_api_key_from_request(request)

        if not api_key:
            return None

        # Get database session
        db = next(get_db())

        try:
            # Authenticate API key
            service = APIKeyService(db)
            api_key_obj = service.authenticate_api_key(api_key)

            if not api_key_obj:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key"
                )

            # Check rate limiting
            if not service.check_rate_limit(api_key_obj):
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="API key rate limit exceeded",
                )

            # Log usage (start timing)
            request.state.api_key_start_time = time.time()
            request.state.api_key_obj = api_key_obj

            return api_key_obj

        finally:
            db.close()

    def _get_api_key_from_request(self, request: Request) -> Optional[str]:
        """Extract API key from request headers"""
        # Check Authorization header (Bearer token)
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1]
            if token.startswith("rbac_"):
                return token

        # Check X-API-Key header
        api_key_header = request.headers.get("X-API-Key")
        if api_key_header and api_key_header.startswith("rbac_"):
            return api_key_header

        return None


class APIKeyMiddleware:
    """Middleware for API key authentication and logging"""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)

        # Skip API key auth for certain paths
        if self._should_skip_api_key_auth(request.url.path):
            await self.app(scope, receive, send)
            return

        # Check for API key authentication
        api_key_auth = APIKeyAuth()
        api_key_obj = await api_key_auth(request)

        if api_key_obj:
            # Add API key info to request state
            request.state.api_key_authenticated = True
            request.state.api_key_obj = api_key_obj

            # Add user info to request state for permission checks
            db = next(get_db())
            try:
                user = db.query(User).filter(User.id == api_key_obj.user_id).first()
                if user:
                    request.state.current_user = user
            finally:
                db.close()

        # Create response handler to log API usage
        async def response_handler(scope, receive, send):
            response_started = False
            status_code = 200

            async def wrapped_send(message):
                nonlocal response_started, status_code

                if message["type"] == "http.response.start":
                    response_started = True
                    status_code = message["status"]

                elif message["type"] == "http.response.body" and not message.get(
                    "more_body", False
                ):
                    # Response is complete, log API usage
                    if (
                        hasattr(request.state, "api_key_obj")
                        and request.state.api_key_obj
                    ):
                        await self._log_api_usage(request, status_code)

                await send(message)

            await self.app(scope, receive, wrapped_send)

        await response_handler(scope, receive, send)

    def _should_skip_api_key_auth(self, path: str) -> bool:
        """Check if API key authentication should be skipped for this path"""
        skip_paths = [
            "/docs",
            "/redoc",
            "/openapi.json",
            "/health",
            "/metrics",
            "/auth/login",
            "/auth/register",
            "/auth/oauth",
            "/static",
            "/favicon.ico",
        ]

        return any(path.startswith(skip_path) for skip_path in skip_paths)

    async def _log_api_usage(self, request: Request, status_code: int):
        """Log API key usage"""
        try:
            api_key_obj = request.state.api_key_obj

            # Calculate response time
            response_time_ms = None
            if hasattr(request.state, "api_key_start_time"):
                response_time_ms = int(
                    (time.time() - request.state.api_key_start_time) * 1000
                )

            # Get client info
            client_ip = request.client.host if request.client else None
            user_agent = request.headers.get("User-Agent")

            # Log to database
            db = next(get_db())
            try:
                service = APIKeyService(db)
                service.log_api_key_usage(
                    api_key_id=api_key_obj.id,
                    endpoint=str(request.url.path),
                    method=request.method,
                    status_code=status_code,
                    response_time_ms=response_time_ms,
                    ip_address=client_ip,
                    user_agent=user_agent,
                )
            finally:
                db.close()

        except Exception as e:
            # Log error but don't fail the request
            print(f"Error logging API usage: {e}")


def get_api_key_user(request: Request) -> Optional[User]:
    """Get the current user from API key authentication"""
    if hasattr(request.state, "current_user"):
        return request.state.current_user
    return None


def require_api_key_scope(scope: str):
    """Decorator to require specific API key scope"""

    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Get request from function arguments
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break

            if not request:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Request object not found",
                )

            # Check if API key authenticated
            if (
                not hasattr(request.state, "api_key_obj")
                or not request.state.api_key_obj
            ):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, detail="API key required"
                )

            # Check scope
            api_key_obj = request.state.api_key_obj
            if not api_key_obj.is_scope_allowed(scope):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"API key does not have required scope: {scope}",
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator
