import json
import logging
import logging.config
import logging.handlers
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import streamlit as st

# Base logs directory
LOGS_DIR = Path("logs")
FRONTEND_LOGS_DIR = LOGS_DIR / "frontend"

# Create log directories
for log_dir in [
    FRONTEND_LOGS_DIR,
    FRONTEND_LOGS_DIR / "user_actions",
    FRONTEND_LOGS_DIR / "permissions",
    FRONTEND_LOGS_DIR / "ui",
]:
    log_dir.mkdir(parents=True, exist_ok=True)


class StreamlitJSONFormatter(logging.Formatter):
    """Custom JSON formatter for Streamlit frontend logging"""

    def format(self, record):
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add Streamlit session info
        if hasattr(st, "session_state"):
            if hasattr(st.session_state, "user") and st.session_state.user:
                log_data["user_id"] = st.session_state.user.get("id")
                log_data["username"] = st.session_state.user.get("username")

            if hasattr(st.session_state, "session_id"):
                log_data["session_id"] = st.session_state.session_id

        # Add extra fields if present
        if hasattr(record, "action"):
            log_data["action"] = record.action
        if hasattr(record, "page"):
            log_data["page"] = record.page
        if hasattr(record, "component"):
            log_data["component"] = record.component
        if hasattr(record, "permission"):
            log_data["permission"] = record.permission
        if hasattr(record, "resource"):
            log_data["resource"] = record.resource
        if hasattr(record, "status"):
            log_data["status"] = record.status
        if hasattr(record, "duration"):
            log_data["duration"] = record.duration
        if hasattr(record, "error_type"):
            log_data["error_type"] = record.error_type
        if hasattr(record, "user_input"):
            log_data["user_input"] = record.user_input
        if hasattr(record, "api_endpoint"):
            log_data["api_endpoint"] = record.api_endpoint
        if hasattr(record, "response_status"):
            log_data["response_status"] = record.response_status

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data, ensure_ascii=False)


def get_frontend_logging_config() -> Dict[str, Any]:
    """Get frontend logging configuration"""

    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "()": StreamlitJSONFormatter,
            },
            "simple": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "datefmt": "%H:%M:%S",
            },
        },
        "handlers": {
            # Console handler (visible in Streamlit)
            "console": {
                "class": "logging.StreamHandler",
                "level": "INFO",
                "formatter": "simple",
                "stream": sys.stdout,
            },
            # Main frontend log
            "frontend_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "DEBUG",
                "formatter": "json",
                "filename": str(FRONTEND_LOGS_DIR / "frontend.log"),
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5,
                "encoding": "utf8",
            },
            # User actions log
            "user_actions_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "INFO",
                "formatter": "json",
                "filename": str(FRONTEND_LOGS_DIR / "user_actions" / "actions.log"),
                "maxBytes": 10485760,  # 10MB
                "backupCount": 10,
                "encoding": "utf8",
            },
            # Permissions log
            "permissions_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "INFO",
                "formatter": "json",
                "filename": str(FRONTEND_LOGS_DIR / "permissions" / "permissions.log"),
                "maxBytes": 5242880,  # 5MB
                "backupCount": 5,
                "encoding": "utf8",
            },
            # UI interactions log
            "ui_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "DEBUG",
                "formatter": "json",
                "filename": str(FRONTEND_LOGS_DIR / "ui" / "interactions.log"),
                "maxBytes": 5242880,  # 5MB
                "backupCount": 3,
                "encoding": "utf8",
            },
        },
        "loggers": {
            # Main frontend logger
            "frontend": {
                "level": "DEBUG",
                "handlers": ["console", "frontend_file"],
                "propagate": False,
            },
            # User actions logger
            "frontend.actions": {
                "level": "INFO",
                "handlers": ["console", "user_actions_file", "frontend_file"],
                "propagate": False,
            },
            # Permissions logger
            "frontend.permissions": {
                "level": "INFO",
                "handlers": ["permissions_file", "frontend_file"],
                "propagate": False,
            },
            # UI logger
            "frontend.ui": {
                "level": "DEBUG",
                "handlers": ["ui_file"],
                "propagate": False,
            },
            # API communication logger
            "frontend.api": {
                "level": "INFO",
                "handlers": ["console", "frontend_file"],
                "propagate": False,
            },
        },
        "root": {"level": "INFO", "handlers": ["console", "frontend_file"]},
    }


def setup_frontend_logging():
    """Setup frontend logging configuration"""
    config = get_frontend_logging_config()
    logging.config.dictConfig(config)

    # Initialize session ID if not exists
    if not hasattr(st.session_state, "session_id"):
        import uuid

        st.session_state.session_id = str(uuid.uuid4())[:8]

    # Log frontend startup
    logger = logging.getLogger("frontend")
    logger.info(
        "Frontend logging system initialized",
        extra={"action": "logging_setup", "session_id": st.session_state.session_id},
    )


def get_frontend_logger(name: str = "frontend") -> logging.Logger:
    """Get frontend logger"""
    return logging.getLogger(name)


def get_actions_logger() -> logging.Logger:
    """Get user actions logger"""
    return logging.getLogger("frontend.actions")


def get_permissions_logger() -> logging.Logger:
    """Get permissions logger"""
    return logging.getLogger("frontend.permissions")


def get_ui_logger() -> logging.Logger:
    """Get UI interactions logger"""
    return logging.getLogger("frontend.ui")


def get_api_logger() -> logging.Logger:
    """Get API communication logger"""
    return logging.getLogger("frontend.api")


# Helper functions for common frontend logging patterns
def log_user_action(
    action: str,
    page: str = None,
    success: bool = True,
    resource: str = None,
    details: Dict = None,
    **kwargs,
):
    """Log user actions"""
    logger = get_actions_logger()
    level = logging.INFO if success else logging.WARNING

    user_id = None
    username = None
    if hasattr(st.session_state, "user") and st.session_state.user:
        user_id = st.session_state.user.get("id")
        username = st.session_state.user.get("username")

    extra = {
        "action": action,
        "page": page,
        "success": success,
        "resource": resource,
        "user_id": user_id,
        "username": username,
        "session_id": getattr(st.session_state, "session_id", "unknown"),
        **kwargs,
    }

    if details:
        extra.update(details)

    message = f"User action: {action}"
    if page:
        message += f" on {page}"
    if resource:
        message += f" for {resource}"

    logger.log(level, message, extra=extra)


def log_permission_check(
    permission: str,
    resource: str = None,
    granted: bool = True,
    page: str = None,
    **kwargs,
):
    """Log permission checks"""
    logger = get_permissions_logger()
    level = logging.INFO if granted else logging.WARNING

    user_id = None
    username = None
    if hasattr(st.session_state, "user") and st.session_state.user:
        user_id = st.session_state.user.get("id")
        username = st.session_state.user.get("username")

    extra = {
        "action": "permission_check",
        "permission": permission,
        "resource": resource,
        "granted": granted,
        "page": page,
        "user_id": user_id,
        "username": username,
        "session_id": getattr(st.session_state, "session_id", "unknown"),
        **kwargs,
    }

    message = f"Permission {permission}: {'granted' if granted else 'denied'}"
    if resource:
        message += f" for {resource}"

    logger.log(level, message, extra=extra)


def log_ui_interaction(
    component: str, action: str, page: str = None, user_input: Any = None, **kwargs
):
    """Log UI interactions"""
    logger = get_ui_logger()

    user_id = None
    username = None
    if hasattr(st.session_state, "user") and st.session_state.user:
        user_id = st.session_state.user.get("id")
        username = st.session_state.user.get("username")

    extra = {
        "action": action,
        "component": component,
        "page": page,
        "user_input": str(user_input) if user_input is not None else None,
        "user_id": user_id,
        "username": username,
        "session_id": getattr(st.session_state, "session_id", "unknown"),
        **kwargs,
    }

    message = f"UI interaction: {action} on {component}"
    if page:
        message += f" ({page})"

    logger.debug(message, extra=extra)


def log_api_call(
    endpoint: str,
    method: str = "GET",
    status_code: int = None,
    duration: float = None,
    success: bool = True,
    **kwargs,
):
    """Log API calls"""
    logger = get_api_logger()
    level = logging.INFO if success else logging.ERROR

    user_id = None
    username = None
    if hasattr(st.session_state, "user") and st.session_state.user:
        user_id = st.session_state.user.get("id")
        username = st.session_state.user.get("username")

    extra = {
        "action": "api_call",
        "api_endpoint": endpoint,
        "method": method,
        "response_status": status_code,
        "duration": duration,
        "success": success,
        "user_id": user_id,
        "username": username,
        "session_id": getattr(st.session_state, "session_id", "unknown"),
        **kwargs,
    }

    message = f"API call: {method} {endpoint}"
    if status_code:
        message += f" - {status_code}"
    if duration:
        message += f" ({duration:.3f}s)"

    logger.log(level, message, extra=extra)


def log_frontend_error(
    error: Exception,
    context: str = None,
    page: str = None,
    component: str = None,
    **kwargs,
):
    """Log frontend errors"""
    logger = get_frontend_logger()

    user_id = None
    username = None
    if hasattr(st.session_state, "user") and st.session_state.user:
        user_id = st.session_state.user.get("id")
        username = st.session_state.user.get("username")

    extra = {
        "error_type": type(error).__name__,
        "error_message": str(error),
        "context": context,
        "page": page,
        "component": component,
        "user_id": user_id,
        "username": username,
        "session_id": getattr(st.session_state, "session_id", "unknown"),
        **kwargs,
    }

    message = (
        f"Frontend error in {context}: {error}"
        if context
        else f"Frontend error: {error}"
    )

    logger.error(message, extra=extra, exc_info=True)


# Decorator for logging function calls
def log_function_call(logger_name: str = "frontend", log_args: bool = False):
    """Decorator to log function calls"""

    def decorator(func):
        def wrapper(*args, **kwargs):
            logger = logging.getLogger(logger_name)
            func_name = func.__name__

            extra = {"action": "function_call", "function": func_name}

            if log_args:
                extra["args"] = str(args)
                extra["kwargs"] = str(kwargs)

            logger.debug(f"Function called: {func_name}", extra=extra)

            try:
                result = func(*args, **kwargs)
                logger.debug(f"Function completed: {func_name}", extra=extra)
                return result
            except Exception as e:
                extra["error"] = str(e)
                logger.error(
                    f"Function failed: {func_name}", extra=extra, exc_info=True
                )
                raise

        return wrapper

    return decorator
