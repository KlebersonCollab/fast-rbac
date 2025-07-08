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
        self, api_key_data: APIKeyCreate, current_user: User
    ) -> tuple[APIKey, str]:
        """Create a new API key for the current user's tenant."""
        if not current_user.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User is not associated with a tenant.",
            )

        # Check tenant limits
        tenant = self.db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
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
            user_id=current_user.id,
            tenant_id=current_user.tenant_id,
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

    def get_api_key(self, api_key_id: int, current_user: User) -> Optional[APIKey]:
        """Get API key by ID, scoped to the user's tenant."""
        query = self.db.query(APIKey).filter(APIKey.id == api_key_id)

        if not current_user.is_superuser:
            query = query.filter(APIKey.tenant_id == current_user.tenant_id)

        return query.first()

    def get_api_keys(
        self, current_user: User, skip: int = 0, limit: int = 100
    ) -> List[APIKey]:
        """Get all API keys for the user's tenant."""
        query = self.db.query(APIKey)
        
        if not current_user.is_superuser:
            if not current_user.tenant_id:
                return []
            query = query.filter(APIKey.tenant_id == current_user.tenant_id)

        return query.order_by(APIKey.created_at.desc()).offset(skip).limit(limit).all()

    def update_api_key(
        self, api_key_id: int, api_key_data: APIKeyUpdate, current_user: User
    ) -> Optional[APIKey]:
        """Update an API key."""
        api_key = self.get_api_key(api_key_id, current_user)
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

    def delete_api_key(self, api_key_id: int, current_user: User) -> bool:
        """Delete an API key."""
        api_key = self.get_api_key(api_key_id, current_user)
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
        current_user: User,
        skip: int = 0,
        limit: int = 100,
    ) -> List[APIKeyUsage]:
        """Get API key usage history"""
        # Verify ownership
        api_key = self.get_api_key(api_key_id, current_user)
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
        current_user: User,
        days: int = 30,
    ) -> Dict[str, Any]:
        """Get API key usage statistics"""
        # Verify ownership
        api_key = self.get_api_key(api_key_id, current_user)
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

        failed_requests = total_requests - successful_requests

        # Average response time
        avg_response_time = (
            self.db.query(func.avg(APIKeyUsage.response_time_ms))
            .filter(
                APIKeyUsage.api_key_id == api_key_id,
                APIKeyUsage.timestamp >= start_date,
            )
            .scalar()
        )

        # Requests per day
        requests_by_day = (
            self.db.query(
                func.date(APIKeyUsage.timestamp), func.count(APIKeyUsage.id)
            )
            .filter(
                APIKeyUsage.api_key_id == api_key_id,
                APIKeyUsage.timestamp >= start_date,
            )
            .group_by(func.date(APIKeyUsage.timestamp))
            .all()
        )

        # Most used endpoints
        most_used_endpoints = (
            self.db.query(
                APIKeyUsage.endpoint,
                func.count(APIKeyUsage.id).label("count"),
            )
            .filter(
                APIKeyUsage.api_key_id == api_key_id,
                APIKeyUsage.timestamp >= start_date,
            )
            .group_by(APIKeyUsage.endpoint)
            .order_by(func.count(APIKeyUsage.id).desc())
            .limit(10)
            .all()
        )

        # Status code distribution
        status_code_distribution = (
            self.db.query(
                APIKeyUsage.status_code,
                func.count(APIKeyUsage.id).label("count"),
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
            "failed_requests": failed_requests,
            "average_response_time_ms": avg_response_time,
            "requests_per_hour": total_requests / (days * 24) if days > 0 else 0,
            "most_used_endpoints": [
                {"endpoint": endpoint, "count": count}
                for endpoint, count in most_used_endpoints
            ],
            "status_code_distribution": {
                str(status_code): count
                for status_code, count in status_code_distribution
            },
            "usage_over_time": [
                {"date": str(day), "count": count} for day, count in requests_by_day
            ],
        }

    def check_rate_limit(self, api_key: APIKey, window_minutes: int = 1) -> bool:
        """Check if an API key has exceeded its rate limit."""
        if not api_key.rate_limit_per_minute:
            return True  # No rate limit

        # Get usage count in the time window
        time_window = datetime.utcnow() - timedelta(minutes=window_minutes)
        usage_count = (
            self.db.query(func.count(APIKeyUsage.id))
            .filter(
                APIKeyUsage.api_key_id == api_key.id,
                APIKeyUsage.timestamp >= time_window,
            )
            .scalar()
            or 0
        )

        return usage_count < api_key.rate_limit_per_minute

    def rotate_api_key(
        self, api_key_id: int, current_user: User
    ) -> Optional[tuple[APIKey, str]]:
        """Rotate an API key"""
        # Verify ownership
        api_key = self.get_api_key(api_key_id, current_user)
        if not api_key:
            return None

        # Generate a new key and hash
        full_key, key_hash = APIKey.generate_key()
        key_prefix = full_key[:12]

        # Deactivate old key by setting an expiration date
        api_key.expires_at = datetime.utcnow() + timedelta(days=1)
        api_key.is_active = False

        # Create a new API key with the same attributes but new credentials
        new_api_key = APIKey(
            name=api_key.name,
            description=f"{api_key.description} (rotated)",
            key_hash=key_hash,
            key_prefix=key_prefix,
            user_id=api_key.user_id,
            tenant_id=api_key.tenant_id,
            scopes=api_key.scopes,
            permissions=api_key.permissions,
            rate_limit_per_minute=api_key.rate_limit_per_minute,
            is_active=True,
        )

        self.db.add(new_api_key)
        self.db.commit()
        self.db.refresh(new_api_key)

        return new_api_key, full_key
