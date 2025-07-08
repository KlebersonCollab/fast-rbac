import time
import uuid
from typing import Callable, Optional

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.config.logging import (
    get_api_logger,
    get_error_logger,
    log_api_request,
    log_error,
)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all API requests and responses"""

    def __init__(
        self, app: ASGIApp, log_requests: bool = True, log_responses: bool = True
    ):
        super().__init__(app)
        self.log_requests = log_requests
        self.log_responses = log_responses
        self.api_logger = get_api_logger()
        self.error_logger = get_error_logger()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate unique trace ID for this request
        trace_id = str(uuid.uuid4())[:8]
        request.state.trace_id = trace_id

        # Extract request info
        method = request.method
        url = str(request.url)
        path = request.url.path
        query_params = str(request.query_params)
        client_ip = self.get_client_ip(request)
        user_agent = request.headers.get("user-agent", "")

        # Get user info if available
        user_id = None
        username = None
        if hasattr(request.state, "current_user") and request.state.current_user:
            user_id = request.state.current_user.id
            username = request.state.current_user.username

        # Log request start
        start_time = time.time()
        if self.log_requests:
            self.api_logger.info(
                f"Request started: {method} {path}",
                extra={
                    "trace_id": trace_id,
                    "method": method,
                    "endpoint": path,
                    "url": url,
                    "query_params": query_params,
                    "ip_address": client_ip,
                    "user_agent": user_agent,
                    "user_id": user_id,
                    "username": username,
                    "action": "request_start",
                },
            )

        # Process the request
        response = None
        error_occurred = False

        try:
            response = await call_next(request)

        except Exception as e:
            error_occurred = True
            duration = time.time() - start_time

            # Log the error
            log_error(
                error=e,
                context=f"API request {method} {path}",
                user_id=user_id,
                username=username,
                trace_id=trace_id,
                method=method,
                endpoint=path,
                ip_address=client_ip,
                duration=duration,
            )

            # Return error response
            response = JSONResponse(
                status_code=500,
                content={"detail": "Internal server error", "trace_id": trace_id},
            )

        # Calculate response time
        duration = time.time() - start_time
        status_code = response.status_code

        # Log the response
        if self.log_responses or error_occurred:
            log_api_request(
                method=method,
                endpoint=path,
                status_code=status_code,
                duration=duration,
                user_id=user_id,
                username=username,
                ip_address=client_ip,
                trace_id=trace_id,
                url=url,
                query_params=query_params,
                user_agent=user_agent,
                error_occurred=error_occurred,
            )

        # Add trace ID to response headers
        response.headers["X-Trace-ID"] = trace_id

        return response

    def get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request"""
        # Check for forwarded headers first (for proxy/load balancer scenarios)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip

        # Fallback to direct client IP
        return request.client.host if request.client else "unknown"


class PerformanceLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log performance metrics"""

    def __init__(self, app: ASGIApp, threshold_ms: float = 1000.0):
        super().__init__(app)
        self.threshold_ms = threshold_ms
        self.api_logger = get_api_logger()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        response = await call_next(request)
        duration = time.time() - start_time
        duration_ms = duration * 1000

        # Log slow requests
        if duration_ms > self.threshold_ms:
            trace_id = getattr(request.state, "trace_id", "unknown")
            user_id = None
            username = None

            if hasattr(request.state, "current_user") and request.state.current_user:
                user_id = request.state.current_user.id
                username = request.state.current_user.username

            self.api_logger.warning(
                f"Slow request detected: {request.method} {request.url.path} took {duration_ms:.2f}ms",
                extra={
                    "trace_id": trace_id,
                    "method": request.method,
                    "endpoint": request.url.path,
                    "duration": duration,
                    "duration_ms": duration_ms,
                    "threshold_ms": self.threshold_ms,
                    "user_id": user_id,
                    "username": username,
                    "action": "slow_request",
                },
            )

        return response


class HealthCheckLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log health check requests separately"""

    def __init__(self, app: ASGIApp, health_endpoints: list = None):
        super().__init__(app)
        self.health_endpoints = health_endpoints or [
            "/health",
            "/health/",
            "/healthcheck",
        ]
        self.health_logger = get_api_logger()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Check if this is a health check endpoint
        if request.url.path in self.health_endpoints:
            start_time = time.time()
            response = await call_next(request)
            duration = time.time() - start_time

            # Log health check with minimal info
            self.health_logger.debug(
                f"Health check: {request.method} {request.url.path} - {response.status_code}",
                extra={
                    "method": request.method,
                    "endpoint": request.url.path,
                    "status_code": response.status_code,
                    "duration": duration,
                    "action": "health_check",
                },
            )

            return response

        # Not a health check, continue normally
        return await call_next(request)


class UserActivityLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log user activity for audit purposes"""

    def __init__(self, app: ASGIApp, track_endpoints: list = None):
        super().__init__(app)
        # Endpoints to track for user activity
        self.track_endpoints = track_endpoints or [
            "/admin/users",
            "/admin/roles",
            "/admin/permissions",
            "/auth/login",
            "/auth/register",
        ]
        self.api_logger = get_api_logger()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Check if we should track this endpoint
        should_track = any(
            request.url.path.startswith(endpoint) for endpoint in self.track_endpoints
        )

        if should_track:
            response = await call_next(request)

            # Log user activity
            user_id = None
            username = None
            if hasattr(request.state, "current_user") and request.state.current_user:
                user_id = request.state.current_user.id
                username = request.state.current_user.username

            trace_id = getattr(request.state, "trace_id", "unknown")

            self.api_logger.info(
                f"User activity: {request.method} {request.url.path}",
                extra={
                    "trace_id": trace_id,
                    "method": request.method,
                    "endpoint": request.url.path,
                    "status_code": response.status_code,
                    "user_id": user_id,
                    "username": username,
                    "ip_address": self.get_client_ip(request),
                    "action": "user_activity",
                },
            )

            return response

        # Not tracked, continue normally
        return await call_next(request)

    def get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request"""
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip

        return request.client.host if request.client else "unknown"
