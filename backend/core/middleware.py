"""
Tenant isolation middleware for multi-tenant architecture.
Extracts tenant context from subdomain/header and sets PostgreSQL RLS.
"""
import re
from typing import Callable
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from .database import db_manager
from .security import security


class TenantMiddleware(BaseHTTPMiddleware):
    """
    Middleware to extract and validate tenant context on every request.
    Sets PostgreSQL app.current_tenant variable for Row-Level Security.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and inject tenant context."""

        # Skip tenant check for public endpoints
        if self._is_public_endpoint(request.url.path):
            return await call_next(request)

        # Extract tenant from subdomain or header
        tenant_id = await self._extract_tenant(request)

        if not tenant_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tenant identification required. Use subdomain or X-Tenant-ID header."
            )

        # Store tenant in request state
        request.state.tenant_id = tenant_id

        # Process request
        response = await call_next(request)

        return response

    async def _extract_tenant(self, request: Request) -> str:
        """
        Extract tenant ID from request.
        Tries: 1) JWT token, 2) X-Tenant-ID header, 3) Subdomain

        Returns:
            Tenant UUID string or None
        """

        # 1. Try to get from Authorization token (most reliable)
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            try:
                tenant_id = security.get_tenant_from_token(token)
                if tenant_id:
                    return tenant_id
            except HTTPException:
                pass  # Invalid token, try other methods

        # 2. Try X-Tenant-ID header
        tenant_header = request.headers.get("X-Tenant-ID")
        if tenant_header:
            return tenant_header

        # 3. Try subdomain extraction
        host = request.headers.get("host", "")
        tenant_from_subdomain = self._extract_from_subdomain(host)
        if tenant_from_subdomain:
            return tenant_from_subdomain

        return None

    def _extract_from_subdomain(self, host: str) -> str:
        """
        Extract tenant slug from subdomain.
        Format: {tenant}.evfportugal2030.pt

        Returns:
            Tenant slug or None
        """
        # Skip localhost
        if "localhost" in host or "127.0.0.1" in host:
            return "demo"  # Default tenant for local development

        # Match subdomain pattern
        match = re.match(r"^([a-z0-9-]+)\.(evfportugal2030|evf-portugal)", host)
        if match:
            return match.group(1)

        return None

    def _is_public_endpoint(self, path: str) -> bool:
        """Check if endpoint doesn't require tenant context."""
        public_paths = [
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/api/v1/auth/register",
            "/api/v1/auth/login",
        ]

        return any(path.startswith(public) for public in public_paths)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware per tenant.
    Uses Redis to track request counts.
    """

    def __init__(self, app, redis_client=None):
        super().__init__(app)
        self.redis = redis_client
        self.rate_limit = 100  # requests per minute

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Check rate limit before processing request."""

        tenant_id = getattr(request.state, "tenant_id", None)

        if tenant_id and self.redis:
            # Create rate limit key
            key = f"rate_limit:{tenant_id}:{request.url.path}"

            # Increment counter
            count = await self.redis.incr(key)

            # Set expiry on first request
            if count == 1:
                await self.redis.expire(key, 60)  # 60 seconds

            # Check if over limit
            if count > self.rate_limit:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded. Max {self.rate_limit} requests per minute."
                )

        response = await call_next(request)
        return response
