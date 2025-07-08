from typing import Callable, List, Optional

from fastapi import HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.auth.service import AuthService
from app.auth.utils import verify_token
from app.database.base import get_db
from app.models.user import User

security = HTTPBearer()


class RBACMiddleware(BaseHTTPMiddleware):
    """Middleware for Role-Based Access Control"""

    def __init__(self, app, excluded_paths: Optional[List[str]] = None):
        super().__init__(app)
        self.excluded_paths = excluded_paths or [
            "/docs",
            "/redoc",
            "/openapi.json",
            "/auth/login",
            "/auth/register",
            "/auth/token",
            "/oauth",
            "/health",
        ]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process the request through RBAC checks"""

        # Skip RBAC for excluded paths
        if any(request.url.path.startswith(path) for path in self.excluded_paths):
            return await call_next(request)

        # Skip RBAC for OPTIONS requests (CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)

        # Get authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authorization header required",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Extract and verify token
        token = auth_header.split(" ")[1]
        username = verify_token(token)
        if not username:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Get user from database
        db_generator = get_db()
        db = next(db_generator)
        try:
            auth_service = AuthService(db)
            user = auth_service.get_user_by_username(username)
            if not user or not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found or inactive",
                )

            # Add user to request state
            request.state.current_user = user

        finally:
            db.close()

        # Continue with the request
        response = await call_next(request)
        return response


def check_permission(permission: str):
    """Decorator to check if user has specific permission"""

    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Get request from args/kwargs (FastAPI injects it)
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

            user = getattr(request.state, "current_user", None)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required",
                )

            if not user.has_permission(permission):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission '{permission}' required",
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def check_role(role: str):
    """Decorator to check if user has specific role"""

    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Get request from args/kwargs
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

            user = getattr(request.state, "current_user", None)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required",
                )

            if not user.has_role(role):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Role '{role}' required",
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator
