"""
Tenant isolation middleware for multi-tenant architecture.
Extracts tenant context from subdomain/header and sets PostgreSQL RLS.
"""
import re
import logging
from typing import Callable
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from .database import db_manager
from .security import security

logger = logging.getLogger(__name__)


class TenantMiddleware(BaseHTTPMiddleware):
    """
    Middleware to extract and validate tenant context on every request.
    Sets PostgreSQL app.current_tenant variable for Row-Level Security.

    CRITICAL: This middleware must run FIRST (added last to stack) to ensure
    tenant_id is available for audit logging and other downstream middleware.
    """

    def __init__(self, app):
        super().__init__(app)
        # Import here to avoid circular dependency
        from ..models.tenant import Tenant
        self.Tenant = Tenant
        self.select = None  # Will be imported lazily

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

        # Validate tenant exists and is active (prevents header spoofing)
        try:
            # Lazy import to avoid circular dependency
            if not self.select:
                from sqlalchemy import select
                self.select = select

            async with db_manager.get_db_context() as session:
                # Query without RLS context to validate tenant
                result = await session.execute(
                    self.select(self.Tenant).where(
                        self.Tenant.id == tenant_id,
                        self.Tenant.is_active == True
                    )
                )
                tenant = result.scalar_one_or_none()

                if not tenant:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Invalid or inactive tenant"
                    )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Tenant validation failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Tenant validation error"
            )

        # Store tenant in request state for downstream middleware/routes
        request.state.tenant_id = tenant_id

        # Process request (RLS context will be set per-session by dependency injection)
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
            "/",  # Root endpoint
            "/api/health",  # Health check
            "/health",  # Health check
            "/docs",  # OpenAPI docs
            "/api/docs",  # OpenAPI docs
            "/redoc",  # ReDoc
            "/api/redoc",  # ReDoc
            "/openapi.json",  # OpenAPI schema
            "/api/openapi.json",  # OpenAPI schema
            "/api/v1/auth/register",  # User registration
            "/api/v1/auth/login",  # User login
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


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Premium security headers middleware (2025 best practices).
    Adds security headers to all responses for defense-in-depth.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add security headers to response."""
        response = await call_next(request)

        # OWASP recommended security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Content Security Policy (API-appropriate)
        # For pure API backends, CSP should be restrictive since we're not serving HTML
        # The frontend (Next.js) will set its own CSP headers
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; "  # API shouldn't load any resources
            "frame-ancestors 'none'"  # Prevent iframe embedding
        )

        # HSTS (HTTP Strict Transport Security)
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains; preload"
        )

        # Permissions Policy (formerly Feature Policy)
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=(), payment=()"
        )

        return response


class AuditMiddleware(BaseHTTPMiddleware):
    """
    Premium audit logging middleware for GDPR/SOC2 compliance.
    Logs all API requests with tenant context, performance metrics, and cost tracking.
    """

    def __init__(self, app, db_session_factory=None):
        super().__init__(app)
        self.db_session_factory = db_session_factory

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Log request and response for audit trail."""
        import time
        import uuid
        from sqlalchemy import text

        # Generate unique request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        # Extract tenant and user context
        tenant_id = getattr(request.state, "tenant_id", None)
        user_id = getattr(request.state, "user_id", None)

        # Start timer
        start_time = time.time()

        # Process request
        response = await call_next(request)

        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000

        # Log to database (async, non-blocking)
        if self.db_session_factory and tenant_id:
            try:
                async with self.db_session_factory() as session:
                    await session.execute(
                        text("""
                            INSERT INTO audit_logs
                            (id, tenant_id, user_id, action, resource, method, path,
                             status_code, duration_ms, ip_address, user_agent, request_id)
                            VALUES
                            (:id, :tenant_id, :user_id, :action, :resource, :method, :path,
                             :status_code, :duration_ms, :ip_address, :user_agent, :request_id)
                        """),
                        {
                            "id": uuid.uuid4(),
                            "tenant_id": tenant_id,
                            "user_id": user_id,
                            "action": request.method,
                            "resource": request.url.path,
                            "method": request.method,
                            "path": request.url.path,
                            "status_code": response.status_code,
                            "duration_ms": duration_ms,
                            "ip_address": request.client.host if request.client else None,
                            "user_agent": request.headers.get("user-agent"),
                            "request_id": request_id
                        }
                    )
                    await session.commit()
            except Exception as e:
                # Don't fail request if audit logging fails
                import logging
                logging.error(f"Audit logging failed: {e}")

        # Add request ID and performance headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"

        return response
