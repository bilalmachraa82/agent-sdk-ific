"""
Redis caching service with multi-tenant support.
Manages session caching, calculation caching, and rate limiting.
"""

import json
import logging
from typing import Optional, Any
from datetime import datetime, timedelta
import hashlib
import redis.asyncio as redis
from functools import wraps
from uuid import UUID

from backend.core.config import settings

logger = logging.getLogger(__name__)


class CacheService:
    """Redis cache service with tenant isolation."""

    def __init__(self):
        self.redis_url = settings.redis_url
        self.ttl_seconds = settings.cache_ttl_seconds
        self.session_ttl_hours = settings.session_ttl_hours
        self.client: Optional[redis.Redis] = None

    async def connect(self):
        """Connect to Redis."""
        try:
            self.client = await redis.from_url(
                self.redis_url,
                encoding="utf8",
                decode_responses=True,
                socket_pool_kwargs={"max_connections": settings.redis_pool_size},
                socket_connect_timeout=settings.redis_timeout,
            )
            # Test connection
            await self.client.ping()
            logger.info("Connected to Redis successfully")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    async def disconnect(self):
        """Disconnect from Redis."""
        if self.client:
            await self.client.close()
            logger.info("Disconnected from Redis")

    def _make_key(self, namespace: str, key: str, tenant_id: str = None) -> str:
        """
        Create a Redis key with tenant isolation.

        Args:
            namespace: Cache namespace (e.g., 'calculations', 'sessions')
            key: The actual cache key
            tenant_id: Tenant ID for multi-tenant isolation

        Returns:
            Formatted Redis key
        """
        if tenant_id:
            return f"tenant:{tenant_id}:{namespace}:{key}"
        return f"{namespace}:{key}"

    async def get(self, key: str, tenant_id: str = None, namespace: str = "default") -> Optional[Any]:
        """
        Get value from cache.

        Args:
            key: Cache key
            tenant_id: Tenant ID for isolation
            namespace: Cache namespace

        Returns:
            Cached value or None if not found
        """
        if not self.client:
            return None

        try:
            full_key = self._make_key(namespace, key, tenant_id)
            value = await self.client.get(full_key)

            if value:
                # Try to parse as JSON
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return value

            return None
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None

    async def set(
        self,
        key: str,
        value: Any,
        tenant_id: str = None,
        namespace: str = "default",
        ttl_seconds: Optional[int] = None
    ) -> bool:
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            tenant_id: Tenant ID for isolation
            namespace: Cache namespace
            ttl_seconds: Time to live (uses default if None)

        Returns:
            True if successful
        """
        if not self.client:
            return False

        try:
            full_key = self._make_key(namespace, key, tenant_id)
            ttl = ttl_seconds or self.ttl_seconds

            # Convert value to JSON if it's not a string
            if not isinstance(value, str):
                value = json.dumps(value, default=str)

            await self.client.setex(full_key, ttl, value)
            logger.debug(f"Cached {full_key} with TTL {ttl}s")
            return True

        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False

    async def delete(self, key: str, tenant_id: str = None, namespace: str = "default") -> bool:
        """
        Delete value from cache.

        Args:
            key: Cache key
            tenant_id: Tenant ID for isolation
            namespace: Cache namespace

        Returns:
            True if successful
        """
        if not self.client:
            return False

        try:
            full_key = self._make_key(namespace, key, tenant_id)
            await self.client.delete(full_key)
            logger.debug(f"Deleted cache key: {full_key}")
            return True
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False

    async def clear_tenant(self, tenant_id: str) -> bool:
        """
        Clear all cache entries for a tenant.
        WARNING: This is slow on large cache, use sparingly.

        Args:
            tenant_id: Tenant ID to clear

        Returns:
            True if successful
        """
        if not self.client:
            return False

        try:
            pattern = f"tenant:{tenant_id}:*"
            cursor = 0
            deleted = 0

            while True:
                cursor, keys = await self.client.scan(cursor, match=pattern, count=100)
                if keys:
                    await self.client.delete(*keys)
                    deleted += len(keys)
                if cursor == 0:
                    break

            logger.info(f"Cleared {deleted} cache entries for tenant {tenant_id}")
            return True
        except Exception as e:
            logger.error(f"Cache clear tenant error: {e}")
            return False

    # Session management
    async def set_session(
        self,
        session_id: str,
        user_id: str,
        tenant_id: str,
        data: dict,
        ttl_hours: Optional[int] = None
    ) -> bool:
        """
        Store session data.

        Args:
            session_id: Session ID
            user_id: User ID
            tenant_id: Tenant ID
            data: Session data
            ttl_hours: Time to live in hours

        Returns:
            True if successful
        """
        ttl = (ttl_hours or self.session_ttl_hours) * 3600
        session_data = {
            "user_id": str(user_id),
            "tenant_id": str(tenant_id),
            "created_at": datetime.utcnow().isoformat(),
            **data
        }
        return await self.set(
            session_id,
            session_data,
            namespace="sessions",
            ttl_seconds=ttl
        )

    async def get_session(self, session_id: str) -> Optional[dict]:
        """Get session data."""
        return await self.get(session_id, namespace="sessions")

    async def delete_session(self, session_id: str) -> bool:
        """Delete session."""
        return await self.delete(session_id, namespace="sessions")

    # Rate limiting
    async def check_rate_limit(
        self,
        user_id: str,
        tenant_id: str,
        limit_requests: int = None,
        window_seconds: int = 60
    ) -> tuple[bool, int, int]:
        """
        Check if user has exceeded rate limit.

        Args:
            user_id: User ID
            tenant_id: Tenant ID
            limit_requests: Max requests per window (uses settings if None)
            window_seconds: Time window in seconds

        Returns:
            (allowed: bool, current_count: int, reset_seconds: int)
        """
        if not self.client:
            return True, 0, 0

        limit = limit_requests or settings.rate_limit_requests_per_minute
        key = f"{user_id}:requests"

        try:
            current = await self.client.incr(key)

            if current == 1:
                # First request, set expiry
                await self.client.expire(key, window_seconds)

            ttl = await self.client.ttl(key)
            allowed = current <= limit

            return allowed, current, ttl if ttl > 0 else 0

        except Exception as e:
            logger.error(f"Rate limit check error: {e}")
            return True, 0, 0

    # Financial calculation caching
    async def cache_calculation(
        self,
        project_id: str,
        tenant_id: str,
        calculation_type: str,
        input_data: dict,
        result: dict
    ) -> bool:
        """
        Cache financial calculation result.

        Args:
            project_id: Project ID
            tenant_id: Tenant ID
            calculation_type: Type of calculation (valf, trf, etc.)
            input_data: Input data used
            result: Calculation result

        Returns:
            True if successful
        """
        # Create deterministic hash of inputs
        input_str = json.dumps(input_data, sort_keys=True, default=str)
        input_hash = hashlib.sha256(input_str.encode()).hexdigest()[:16]

        key = f"{project_id}:{calculation_type}:{input_hash}"
        cache_data = {
            "result": result,
            "input_hash": input_hash,
            "calculation_type": calculation_type,
            "cached_at": datetime.utcnow().isoformat()
        }

        return await self.set(
            key,
            cache_data,
            tenant_id=tenant_id,
            namespace="calculations",
            ttl_seconds=86400  # 24 hours for calculations
        )

    async def get_calculation(
        self,
        project_id: str,
        tenant_id: str,
        calculation_type: str,
        input_data: dict
    ) -> Optional[dict]:
        """
        Retrieve cached calculation result if inputs match.

        Args:
            project_id: Project ID
            tenant_id: Tenant ID
            calculation_type: Type of calculation
            input_data: Input data to verify

        Returns:
            Cached result or None if not found/invalid
        """
        input_str = json.dumps(input_data, sort_keys=True, default=str)
        input_hash = hashlib.sha256(input_str.encode()).hexdigest()[:16]

        key = f"{project_id}:{calculation_type}:{input_hash}"
        cached = await self.get(key, tenant_id=tenant_id, namespace="calculations")

        if cached and cached.get("input_hash") == input_hash:
            return cached.get("result")

        return None


# Global cache service instance
cache_service = CacheService()


async def init_cache():
    """Initialize cache service."""
    await cache_service.connect()


async def close_cache():
    """Close cache service."""
    await cache_service.disconnect()
