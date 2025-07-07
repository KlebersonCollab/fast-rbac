import logging
import logging.config
import logging.handlers
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
import json

# Base logs directory
LOGS_DIR = Path("logs")
BACKEND_LOGS_DIR = LOGS_DIR / "backend"
SYSTEM_LOGS_DIR = LOGS_DIR / "system"

# Create log directories
for log_dir in [BACKEND_LOGS_DIR, SYSTEM_LOGS_DIR, 
                BACKEND_LOGS_DIR / "auth", BACKEND_LOGS_DIR / "rbac", 
                BACKEND_LOGS_DIR / "api", BACKEND_LOGS_DIR / "errors",
                SYSTEM_LOGS_DIR / "startup", SYSTEM_LOGS_DIR / "health"]:
    log_dir.mkdir(parents=True, exist_ok=True)


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging"""
    
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
        
        # Add extra fields if present
        if hasattr(record, 'user_id'):
            log_data['user_id'] = record.user_id
        if hasattr(record, 'username'):
            log_data['username'] = record.username
        if hasattr(record, 'ip_address'):
            log_data['ip_address'] = record.ip_address
        if hasattr(record, 'endpoint'):
            log_data['endpoint'] = record.endpoint
        if hasattr(record, 'method'):
            log_data['method'] = record.method
        if hasattr(record, 'status_code'):
            log_data['status_code'] = record.status_code
        if hasattr(record, 'duration'):
            log_data['duration'] = record.duration
        if hasattr(record, 'permission'):
            log_data['permission'] = record.permission
        if hasattr(record, 'role'):
            log_data['role'] = record.role
        if hasattr(record, 'action'):
            log_data['action'] = record.action
        if hasattr(record, 'resource'):
            log_data['resource'] = record.resource
        if hasattr(record, 'error_type'):
            log_data['error_type'] = record.error_type
        if hasattr(record, 'trace_id'):
            log_data['trace_id'] = record.trace_id
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_data, ensure_ascii=False)


class ColoredFormatter(logging.Formatter):
    """Colored formatter for console output"""
    
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
        'RESET': '\033[0m'       # Reset
    }
    
    def format(self, record):
        color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        reset = self.COLORS['RESET']
        
        # Format timestamp
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Build the formatted message
        formatted = f"{color}[{timestamp}] {record.levelname:8s}{reset} "
        formatted += f"{record.name:20s} | {record.getMessage()}"
        
        # Add extra context if available
        extras = []
        if hasattr(record, 'username'):
            extras.append(f"user={record.username}")
        if hasattr(record, 'endpoint'):
            extras.append(f"endpoint={record.endpoint}")
        if hasattr(record, 'method'):
            extras.append(f"method={record.method}")
        if hasattr(record, 'status_code'):
            extras.append(f"status={record.status_code}")
        
        if extras:
            formatted += f" [{', '.join(extras)}]"
        
        return formatted


def get_logging_config() -> Dict[str, Any]:
    """Get logging configuration dictionary"""
    
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "()": JSONFormatter,
            },
            "colored": {
                "()": ColoredFormatter,
            },
            "detailed": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(funcName)s:%(lineno)d - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S"
            }
        },
        "handlers": {
            # Console handler
            "console": {
                "class": "logging.StreamHandler",
                "level": "INFO",
                "formatter": "colored",
                "stream": sys.stdout
            },
            
            # Main application log
            "app_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "DEBUG",
                "formatter": "json",
                "filename": str(BACKEND_LOGS_DIR / "app.log"),
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5,
                "encoding": "utf8"
            },
            
            # Authentication logs
            "auth_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "INFO",
                "formatter": "json",
                "filename": str(BACKEND_LOGS_DIR / "auth" / "auth.log"),
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5,
                "encoding": "utf8"
            },
            
            # RBAC logs
            "rbac_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "INFO",
                "formatter": "json",
                "filename": str(BACKEND_LOGS_DIR / "rbac" / "rbac.log"),
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5,
                "encoding": "utf8"
            },
            
            # API access logs
            "api_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "INFO",
                "formatter": "json",
                "filename": str(BACKEND_LOGS_DIR / "api" / "access.log"),
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5,
                "encoding": "utf8"
            },
            
            # Error logs
            "error_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "ERROR",
                "formatter": "json",
                "filename": str(BACKEND_LOGS_DIR / "errors" / "errors.log"),
                "maxBytes": 10485760,  # 10MB
                "backupCount": 10,
                "encoding": "utf8"
            },
            
            # System startup logs
            "startup_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "INFO",
                "formatter": "detailed",
                "filename": str(SYSTEM_LOGS_DIR / "startup" / "startup.log"),
                "maxBytes": 5242880,  # 5MB
                "backupCount": 3,
                "encoding": "utf8"
            },
            
            # Health check logs
            "health_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "INFO",
                "formatter": "json",
                "filename": str(SYSTEM_LOGS_DIR / "health" / "health.log"),
                "maxBytes": 5242880,  # 5MB
                "backupCount": 3,
                "encoding": "utf8"
            }
        },
        "loggers": {
            # Main application logger
            "app": {
                "level": "DEBUG",
                "handlers": ["console", "app_file"],
                "propagate": False
            },
            
            # Authentication logger
            "app.auth": {
                "level": "INFO",
                "handlers": ["console", "auth_file", "app_file"],
                "propagate": False
            },
            
            # RBAC logger
            "app.rbac": {
                "level": "INFO",
                "handlers": ["console", "rbac_file", "app_file"],
                "propagate": False
            },
            
            # API logger
            "app.api": {
                "level": "INFO",
                "handlers": ["console", "api_file", "app_file"],
                "propagate": False
            },
            
            # Error logger
            "app.errors": {
                "level": "ERROR",
                "handlers": ["console", "error_file", "app_file"],
                "propagate": False
            },
            
            # System logger
            "app.system": {
                "level": "INFO",
                "handlers": ["console", "startup_file"],
                "propagate": False
            },
            
            # Health logger
            "app.health": {
                "level": "INFO",
                "handlers": ["health_file"],
                "propagate": False
            },
            
            # Third-party loggers
            "uvicorn.access": {
                "level": "INFO",
                "handlers": ["api_file"],
                "propagate": False
            },
            "uvicorn.error": {
                "level": "INFO",
                "handlers": ["error_file"],
                "propagate": False
            },
            "fastapi": {
                "level": "INFO",
                "handlers": ["app_file"],
                "propagate": False
            },
            "sqlalchemy.engine": {
                "level": "WARNING",
                "handlers": ["app_file"],
                "propagate": False
            }
        },
        "root": {
            "level": "INFO",
            "handlers": ["console", "app_file"]
        }
    }


def setup_logging():
    """Setup logging configuration"""
    config = get_logging_config()
    logging.config.dictConfig(config)
    
    # Log startup message
    startup_logger = logging.getLogger("app.system")
    startup_logger.info("Logging system initialized", extra={
        "action": "logging_setup",
        "timestamp": datetime.utcnow().isoformat()
    })


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the specified name"""
    return logging.getLogger(name)


# Convenience functions for different log types
def get_app_logger() -> logging.Logger:
    """Get the main application logger"""
    return logging.getLogger("app")


def get_auth_logger() -> logging.Logger:
    """Get the authentication logger"""
    return logging.getLogger("app.auth")


def get_rbac_logger() -> logging.Logger:
    """Get the RBAC logger"""
    return logging.getLogger("app.rbac")


def get_api_logger() -> logging.Logger:
    """Get the API logger"""
    return logging.getLogger("app.api")


def get_error_logger() -> logging.Logger:
    """Get the error logger"""
    return logging.getLogger("app.errors")


def get_system_logger() -> logging.Logger:
    """Get the system logger"""
    return logging.getLogger("app.system")


def get_health_logger() -> logging.Logger:
    """Get the health logger"""
    return logging.getLogger("app.health")


# Context manager for adding extra context to logs
class LogContext:
    """Context manager for adding extra context to log records"""
    
    def __init__(self, logger: logging.Logger, **kwargs):
        self.logger = logger
        self.extra = kwargs
        self.old_extra = {}
    
    def __enter__(self):
        # Store old values
        for key, value in self.extra.items():
            if hasattr(self.logger, key):
                self.old_extra[key] = getattr(self.logger, key)
            setattr(self.logger, key, value)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Restore old values
        for key in self.extra.keys():
            if key in self.old_extra:
                setattr(self.logger, key, self.old_extra[key])
            else:
                delattr(self.logger, key)


# Helper functions for common logging patterns
def log_auth_event(action: str, username: str = None, user_id: int = None, 
                   success: bool = True, ip_address: str = None, **kwargs):
    """Log authentication events"""
    logger = get_auth_logger()
    level = logging.INFO if success else logging.WARNING
    
    extra = {
        "action": action,
        "success": success,
        "username": username,
        "user_id": user_id,
        "ip_address": ip_address,
        **kwargs
    }
    
    message = f"Auth {action}: {'success' if success else 'failed'}"
    if username:
        message += f" for user {username}"
    
    logger.log(level, message, extra=extra)


def log_rbac_event(action: str, user_id: int = None, username: str = None, 
                   role: str = None, permission: str = None, resource: str = None,
                   success: bool = True, **kwargs):
    """Log RBAC events"""
    logger = get_rbac_logger()
    level = logging.INFO if success else logging.WARNING
    
    extra = {
        "action": action,
        "user_id": user_id,
        "username": username,
        "role": role,
        "permission": permission,
        "resource": resource,
        "success": success,
        **kwargs
    }
    
    message = f"RBAC {action}"
    if username:
        message += f" for user {username}"
    if permission:
        message += f" permission {permission}"
    if role:
        message += f" role {role}"
    
    logger.log(level, message, extra=extra)


def log_api_request(method: str, endpoint: str, status_code: int, 
                    duration: float, user_id: int = None, username: str = None,
                    ip_address: str = None, **kwargs):
    """Log API requests"""
    logger = get_api_logger()
    
    extra = {
        "method": method,
        "endpoint": endpoint,
        "status_code": status_code,
        "duration": duration,
        "user_id": user_id,
        "username": username,
        "ip_address": ip_address,
        **kwargs
    }
    
    message = f"{method} {endpoint} - {status_code} ({duration:.3f}s)"
    
    if status_code >= 400:
        logger.warning(message, extra=extra)
    else:
        logger.info(message, extra=extra)


def log_error(error: Exception, context: str = None, user_id: int = None, 
              username: str = None, **kwargs):
    """Log errors with context"""
    logger = get_error_logger()
    
    extra = {
        "error_type": type(error).__name__,
        "error_message": str(error),
        "context": context,
        "user_id": user_id,
        "username": username,
        **kwargs
    }
    
    message = f"Error in {context}: {error}" if context else f"Error: {error}"
    
    logger.error(message, extra=extra, exc_info=True) 