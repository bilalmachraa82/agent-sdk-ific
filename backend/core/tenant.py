"""
Multi-tenant context management.
Extracts tenant from request and maintains isolation throughout the request lifecycle.
"""

from typing import Optional
from uuid import UUID
import logging
from starlette.requests import Request
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class TenantContext:
    """Represents the tenant context for the current request."""

    def __init__(self, tenant_id: UUID, tenant_slug: str):
        self.tenant_id = tenant_id
        self.tenant_slug = tenant_slug

    def __str__(self):
        return f"TenantContext(id={self.tenant_id}, slug={self.tenant_slug})"

    def to_dict(self):
        return {
            "tenant_id": str(self.tenant_id),
            "tenant_slug": self.tenant_slug,
        }


class TenantMiddleware(BaseHTTPMiddleware):
    """
    Middleware to extract and validate tenant context from requests.
    Supports extraction from:
    1. X-Tenant-ID header
    2. Subdomain (tenant.example.com)
    3. Request path (/:tenant_slug/...)
    """

    async def dispatch(self, request: Request, call_next):
        """Extract tenant context and set it in request state."""
        tenant_id = None
        tenant_slug = None

        # 1. Try X-Tenant-ID header
        tenant_id_header = request.headers.get("X-Tenant-ID")
        if tenant_id_header:
            try:
                tenant_id = UUID(tenant_id_header)
                logger.debug(f"Tenant context from header: {tenant_id}")
            except ValueError:
                logger.warning(f"Invalid tenant ID in header: {tenant_id_header}")

        # 2. Try subdomain extraction
        host = request.headers.get("host", "")
        if "." in host and not tenant_slug:
            potential_slug = host.split(".")[0]
            # Avoid matching localhost and known domains
            if potential_slug not in ["localhost", "api", "www", "admin"]:
                tenant_slug = potential_slug
                logger.debug(f"Tenant context from subdomain: {tenant_slug}")

        # 3. Try path extraction (/:tenant_slug/...)
        path_parts = request.url.path.strip("/").split("/")
        if path_parts and not tenant_id:
            potential_slug = path_parts[0]
            # Avoid matching API paths
            if potential_slug not in ["api", "health", "docs", "openapi.json"]:
                tenant_slug = potential_slug
                logger.debug(f"Tenant context from path: {tenant_slug}")

        # Store in request state
        request.state.tenant_id = tenant_id
        request.state.tenant_slug = tenant_slug

        # Add tenant context to scope for async context vars
        if tenant_id:
            request.scope["tenant_id"] = str(tenant_id)
        if tenant_slug:
            request.scope["tenant_slug"] = tenant_slug

        response = await call_next(request)
        return response


async def get_current_tenant(request: Request) -> TenantContext:
    """
    Dependency to get current tenant context from request.
    Use in FastAPI route dependencies.
    """
    tenant_id = getattr(request.state, "tenant_id", None)
    tenant_slug = getattr(request.state, "tenant_slug", None)

    if not tenant_id and not tenant_slug:
        raise ValueError("No tenant context found in request")

    return TenantContext(tenant_id=tenant_id, tenant_slug=tenant_slug)


async def set_tenant_rls_context(session: AsyncSession, tenant_id: str):
    """
    Set the PostgreSQL RLS context for the session.
    Must be called after getting a session and before running queries.

    Args:
        session: AsyncSession instance
        tenant_id: The tenant UUID as a string
    """
    from sqlalchemy import text

    try:
        # Set the tenant context variable for RLS policies
        await session.execute(
            text(f"SET app.current_tenant = '{tenant_id}'::uuid;")
        )
        logger.debug(f"RLS context set for tenant: {tenant_id}")
    except Exception as e:
        logger.error(f"Failed to set RLS context: {e}")
        raise


async def enforce_tenant_isolation(
    session: AsyncSession,
    user_tenant_id: str,
    requested_tenant_id: str
) -> bool:
    """
    Enforce tenant isolation at application level.
    Returns True if the requested tenant matches the user's tenant.

    Args:
        session: AsyncSession instance
        user_tenant_id: The user's assigned tenant ID
        requested_tenant_id: The requested tenant ID

    Returns:
        True if isolation is maintained
    """
    if str(user_tenant_id) != str(requested_tenant_id):
        logger.warning(
            f"Tenant isolation violation: user {user_tenant_id} "
            f"requested {requested_tenant_id}"
        )
        return False
    return True
