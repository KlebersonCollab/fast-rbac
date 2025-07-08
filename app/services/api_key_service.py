import hashlib
import json
import secrets
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

import bcrypt
from fastapi import HTTPException, status
from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from app.auth.utils import verify_password
from app.models.api_key import APIKey, APIKeyUsage
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.api_key import APIKeyCreate, APIKeyScope, APIKeyUpdate


class APIKeyService:
    """Service for managing API Keys"""

    def __init__(self, db: Session):
        self.db = db

    def create_api_key(
        self, api_key_data: APIKeyCreate, user_id: int, tenant_id: Optional[int] = None
    ) -> tuple[APIKey, str]:
        """Create a new API key"""
        # Check if user exists
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        # Check tenant limits if applicable
        if tenant_id:
            tenant = self.db.query(Tenant).filter(Tenant.id == tenant_id).first()
            if not tenant:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found"
                )

            if not tenant.can_add_api_key():
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="API key limit reached for this tenant",
                )

        # Generate API key
        full_key, key_hash = APIKey.generate_key()
        key_prefix = full_key[:12]  # rbac_XXXXXX

        # Create API key record
        api_key = APIKey(
            name=api_key_data.name,
            description=api_key_data.description,
            key_hash=key_hash,
            key_prefix=key_prefix,
            user_id=user_id,
            tenant_id=tenant_id,
            scopes=json.dumps(api_key_data.scopes),
            permissions=(
                json.dumps(api_key_data.permissions)
                if api_key_data.permissions
                else None
            ),
            rate_limit_per_minute=api_key_data.rate_limit_per_minute,
            expires_at=api_key_data.expires_at,
        )

        self.db.add(api_key)
        self.db.commit()
        self.db.refresh(api_key)

        return api_key, full_key

    def get_api_key(
        self, api_key_id: int, user_id: int, tenant_id: Optional[int] = None
    ) -> Optional[APIKey]:
        """Get API key by ID"""
        query = self.db.query(APIKey).filter(
            APIKey.id == api_key_id, APIKey.user_id == user_id
        )

        if tenant_id:
            query = query.filter(APIKey.tenant_id == tenant_id)

        return query.first()

    def get_api_keys(
        self,
        user_id: int,
        tenant_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[APIKey]:
        """Get all API keys for a user"""
        query = self.db.query(APIKey).filter(APIKey.user_id == user_id)

        if tenant_id:
            query = query.filter(APIKey.tenant_id == tenant_id)

        return query.offset(skip).limit(limit).all()

    def update_api_key(
        self,
        api_key_id: int,
        api_key_data: APIKeyUpdate,
        user_id: int,
        tenant_id: Optional[int] = None,
    ) -> Optional[APIKey]:
        """Update an API key"""
        api_key = self.get_api_key(api_key_id, user_id, tenant_id)
        if not api_key:
            return None

        # Update fields
        if api_key_data.name is not None:
            api_key.name = api_key_data.name
        if api_key_data.description is not None:
            api_key.description = api_key_data.description
        if api_key_data.scopes is not None:
            api_key.scopes = json.dumps(api_key_data.scopes)
        if api_key_data.permissions is not None:
            api_key.permissions = json.dumps(api_key_data.permissions)
        if api_key_data.rate_limit_per_minute is not None:
            api_key.rate_limit_per_minute = api_key_data.rate_limit_per_minute
        if api_key_data.expires_at is not None:
            api_key.expires_at = api_key_data.expires_at
        if api_key_data.is_active is not None:
            api_key.is_active = api_key_data.is_active

        self.db.commit()
        self.db.refresh(api_key)

        return api_key

    def delete_api_key(
        self, api_key_id: int, user_id: int, tenant_id: Optional[int] = None
    ) -> bool:
        """Delete an API key"""
        api_key = self.get_api_key(api_key_id, user_id, tenant_id)
        if not api_key:
            return False

        self.db.delete(api_key)
        self.db.commit()

        return True

    def authenticate_api_key(self, key: str) -> Optional[APIKey]:
        """Authenticate an API key"""
        if not key or not key.startswith("rbac_"):
            return None

        key_hash = APIKey.hash_key(key)

        api_key = (
            self.db.query(APIKey)
            .filter(APIKey.key_hash == key_hash, APIKey.is_active == True)
            .first()
        )

        if not api_key:
            return None

        # Check if expired
        if api_key.is_expired:
            return None

        # Update usage statistics
        api_key.update_usage()
        self.db.commit()

        return api_key

    def log_api_key_usage(
        self,
        api_key_id: int,
        endpoint: str,
        method: str,
        status_code: int,
        response_time_ms: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        error_message: Optional[str] = None,
    ):
        """Log API key usage"""
        usage = APIKeyUsage(
            api_key_id=api_key_id,
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            response_time_ms=response_time_ms,
            ip_address=ip_address,
            user_agent=user_agent,
            error_message=error_message,
        )

        self.db.add(usage)
        self.db.commit()

    def get_api_key_usage(
        self,
        api_key_id: int,
        user_id: int,
        tenant_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[APIKeyUsage]:
        """Get API key usage history"""
        # Verify ownership
        api_key = self.get_api_key(api_key_id, user_id, tenant_id)
        if not api_key:
            return []

        return (
            self.db.query(APIKeyUsage)
            .filter(APIKeyUsage.api_key_id == api_key_id)
            .order_by(APIKeyUsage.timestamp.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_api_key_stats(
        self,
        api_key_id: int,
        user_id: int,
        tenant_id: Optional[int] = None,
        days: int = 30,
    ) -> Dict[str, Any]:
        """Get API key usage statistics"""
        # Verify ownership
        api_key = self.get_api_key(api_key_id, user_id, tenant_id)
        if not api_key:
            return {}

        # Date range
        start_date = datetime.utcnow() - timedelta(days=days)

        # Basic stats
        total_requests = (
            self.db.query(func.count(APIKeyUsage.id))
            .filter(
                APIKeyUsage.api_key_id == api_key_id,
                APIKeyUsage.timestamp >= start_date,
            )
            .scalar()
            or 0
        )

        successful_requests = (
            self.db.query(func.count(APIKeyUsage.id))
            .filter(
                APIKeyUsage.api_key_id == api_key_id,
                APIKeyUsage.timestamp >= start_date,
                APIKeyUsage.status_code >= 200,
                APIKeyUsage.status_code < 300,
            )
            .scalar()
            or 0
        )

        # Average response time
        avg_response_time = (
            self.db.query(func.avg(APIKeyUsage.response_time_ms))
            .filter(
                APIKeyUsage.api_key_id == api_key_id,
                APIKeyUsage.timestamp >= start_date,
                APIKeyUsage.response_time_ms.isnot(None),
            )
            .scalar()
        )

        # Most used endpoints
        most_used_endpoints = (
            self.db.query(
                APIKeyUsage.endpoint,
                APIKeyUsage.method,
                func.count(APIKeyUsage.id).label("count"),
            )
            .filter(
                APIKeyUsage.api_key_id == api_key_id,
                APIKeyUsage.timestamp >= start_date,
            )
            .group_by(APIKeyUsage.endpoint, APIKeyUsage.method)
            .order_by(func.count(APIKeyUsage.id).desc())
            .limit(10)
            .all()
        )

        # Status code distribution
        status_distribution = (
            self.db.query(
                APIKeyUsage.status_code, func.count(APIKeyUsage.id).label("count")
            )
            .filter(
                APIKeyUsage.api_key_id == api_key_id,
                APIKeyUsage.timestamp >= start_date,
            )
            .group_by(APIKeyUsage.status_code)
            .all()
        )

        return {
            "total_requests": total_requests,
            "successful_requests": successful_requests,
            "failed_requests": total_requests - successful_requests,
            "average_response_time_ms": (
                float(avg_response_time) if avg_response_time else None
            ),
            "requests_per_hour": total_requests / (days * 24) if days > 0 else 0,
            "most_used_endpoints": [
                {"endpoint": endpoint, "method": method, "count": count}
                for endpoint, method, count in most_used_endpoints
            ],
            "status_code_distribution": {
                str(status_code): count for status_code, count in status_distribution
            },
            "usage_over_time": [],  # Empty for now, can be expanded later
        }

    def check_rate_limit(self, api_key: APIKey, window_minutes: int = 1) -> bool:
        """Check if API key is within rate limits"""
        if not api_key.rate_limit_per_minute:
            return True

        # Get recent usage
        since = datetime.utcnow() - timedelta(minutes=window_minutes)
        recent_requests = (
            self.db.query(func.count(APIKeyUsage.id))
            .filter(
                APIKeyUsage.api_key_id == api_key.id, APIKeyUsage.timestamp >= since
            )
            .scalar()
            or 0
        )

        return recent_requests < api_key.rate_limit_per_minute

    def rotate_api_key(
        self, api_key_id: int, user_id: int, tenant_id: Optional[int] = None
    ) -> tuple[APIKey, str]:
        """Rotate (regenerate) an API key"""
        api_key = self.get_api_key(api_key_id, user_id, tenant_id)
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="API key not found"
            )

        # Generate new key
        full_key, key_hash = APIKey.generate_key()
        key_prefix = full_key[:12]

        # Update API key
        api_key.key_hash = key_hash
        api_key.key_prefix = key_prefix
        api_key.usage_count = 0
        api_key.last_used_at = None

        self.db.commit()
        self.db.refresh(api_key)

        return api_key, full_key
