"""
Async SQLAlchemy database configuration with multi-tenant support and RLS context.
Handles connection pooling, session management, and tenant isolation.

Enhanced with SET LOCAL enforcement, invariant checks, and context propagation.
"""

from typing import AsyncGenerator, Optional, Callable, TypeVar, Any
from contextlib import asynccontextmanager
from contextvars import ContextVar
from functools import wraps
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
    AsyncEngine,
)
from sqlalchemy.pool import NullPool, QueuePool
from sqlalchemy import text, event
import logging
import structlog
import inspect

from .config import settings

T = TypeVar('T')

logger = logging.getLogger(__name__)
structured_logger = structlog.get_logger(__name__)

# Context variables for tenant isolation
_current_tenant_id: ContextVar[Optional[str]] = ContextVar('current_tenant_id', default=None)
_rls_enforced: ContextVar[bool] = ContextVar('rls_enforced', default=False)


# ============================================================================
# RLS INVARIANT ENFORCEMENT
# ============================================================================
# These helpers ensure tenant isolation across ALL database entry points:
# - FastAPI routes
# - Background tasks
# - LangGraph agents
# - Direct asyncpg connections
# ============================================================================


class RLSViolationError(Exception):
    """Raised when RLS context is not properly enforced."""
    pass


def assert_rls_enforced(allow_system: bool = False) -> None:
    """
    Assert that RLS context is currently enforced.

    This is a mandatory invariant check that MUST be called before any
    database query execution to ensure tenant isolation.

    Args:
        allow_system: If True, allows system-level queries without tenant context
                     (e.g., migrations, health checks). Use with extreme caution.

    Raises:
        RLSViolationError: If RLS is not enforced and allow_system=False

    Usage:
        # In any function that queries the database:
        async def get_user_data(db: AsyncSession):
            assert_rls_enforced()  # Critical security check
            result = await db.execute(select(User))
            return result.scalars().all()
    """
    if not allow_system and not _rls_enforced.get():
        tenant_id = _current_tenant_id.get()
        structured_logger.error(
            "RLS violation: Query attempted without tenant context",
            tenant_id=tenant_id,
            rls_enforced=False,
            security_event="RLS_NOT_ENFORCED"
        )
        raise RLSViolationError(
            "Security violation: Database query attempted without RLS enforcement. "
            "Ensure set_tenant_context() is called before query execution."
        )


def require_rls(func: Callable[..., T]) -> Callable[..., T]:
    """
    Decorator to enforce RLS context before function execution.

    This decorator wraps async functions that perform database queries,
    ensuring RLS is enforced before allowing execution.

    Usage:
        @require_rls
        async def get_evf_list(db: AsyncSession):
            # RLS automatically checked before execution
            return await db.execute(select(EVF))

    Args:
        func: Async function to wrap

    Returns:
        Wrapped function with RLS enforcement
    """
    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> T:
        # Check RLS enforcement before executing function
        assert_rls_enforced()

        # Log function execution for audit trail
        structured_logger.debug(
            "RLS-protected function executed",
            function=func.__name__,
            tenant_id=_current_tenant_id.get()
        )

        # Execute original function
        return await func(*args, **kwargs)

    return wrapper


@asynccontextmanager
async def rls_enforced_session(
    session: AsyncSession,
    tenant_id: str,
    operation: str = "database_operation"
) -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager that ensures RLS is enforced for a session scope.

    This is the recommended way to execute tenant-scoped database operations
    outside of FastAPI request context (e.g., background tasks, agents).

    Usage:
        # In a background task
        async with get_db_context() as db:
            async with rls_enforced_session(db, tenant_id, "process_evf") as tenant_db:
                # All queries here are automatically tenant-isolated
                evfs = await tenant_db.execute(select(EVF))

    Args:
        session: Database session
        tenant_id: Tenant UUID to enforce
        operation: Description of operation for logging

    Yields:
        Session with RLS enforced
    """
    try:
        # Set tenant context
        await db_manager.set_tenant_context(session, tenant_id)

        structured_logger.info(
            "RLS context established for operation",
            operation=operation,
            tenant_id=tenant_id
        )

        # Yield session with enforced RLS
        yield session

    finally:
        # Clear context after operation
        await db_manager.clear_tenant_context(session)

        structured_logger.debug(
            "RLS context cleared after operation",
            operation=operation,
            tenant_id=tenant_id
        )


class AsyncDatabaseManager:
    """Manages async SQLAlchemy connections with multi-tenant support."""

    def __init__(self):
        self.engine: Optional[AsyncEngine] = None
        self.async_session_maker: Optional[async_sessionmaker] = None
        self._initialized = False

    async def initialize(self):
        """Initialize the database engine and session factory."""
        if self._initialized:
            return

        # Create async engine with pooling configuration
        engine_kwargs = {
            "echo": settings.database_echo,
        }

        # Use NullPool for development, QueuePool with settings for production
        if settings.environment == "development":
            engine_kwargs["poolclass"] = NullPool
        else:
            engine_kwargs.update({
                "pool_size": settings.database_min_pool_size,
                "max_overflow": settings.database_max_pool_size - settings.database_min_pool_size,
                "pool_timeout": settings.database_pool_timeout,
                "pool_recycle": settings.database_pool_recycle,
            })

        self.engine = create_async_engine(
            settings.database_url,
            **engine_kwargs
        )

        # Attach RLS enforcement to new connections (use sync_engine for async engines)
        @event.listens_for(self.engine.sync_engine, "connect")
        def set_rls_context(dbapi_conn, connection_record):
            """Set RLS context and enforce Row-Level Security on connection."""
            # Enable RLS enforcement (use synchronous execute for connection events)
            cursor = dbapi_conn.cursor()
            cursor.execute("SET row_security = on;")
            cursor.execute(f"SET app.application_name = '{settings.app_name}';")
            cursor.close()

        self.async_session_maker = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )

        self._initialized = True
        logger.info("Database engine initialized successfully")

    async def close(self):
        """Close the database engine and dispose of connections."""
        if self.engine:
            await self.engine.dispose()
            self._initialized = False
            logger.info("Database engine closed")

    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get an async database session.
        Yields a session that should be used in a context manager.
        """
        if not self._initialized:
            await self.initialize()

        async with self.async_session_maker() as session:
            try:
                yield session
            except Exception as e:
                await session.rollback()
                logger.error(f"Database session error: {e}")
                raise
            finally:
                await session.close()

    @asynccontextmanager
    async def get_db_context(self) -> AsyncGenerator[AsyncSession, None]:
        """Get a database session as a context manager."""
        async for session in self.get_session():
            yield session

    async def set_tenant_context(self, session: AsyncSession, tenant_id: str, enforce_invariants: bool = True):
        """
        Set the tenant context for Row-Level Security with invariant checks.

        Uses SESSION-level SET LOCAL for enhanced security:
        - SET LOCAL ensures context is transaction-scoped
        - Context automatically clears on transaction end
        - Prevents context leakage between requests

        Args:
            session: Database session
            tenant_id: Tenant UUID
            enforce_invariants: If True, verify tenant_id matches context (default: True)

        Raises:
            ValueError: If invariant checks fail (tenant mismatch)
        """
        try:
            # Invariant check: if context already set, must match
            if enforce_invariants:
                context_tenant = _current_tenant_id.get()
                if context_tenant and context_tenant != tenant_id:
                    structured_logger.error(
                        "Tenant context mismatch detected",
                        context_tenant=context_tenant,
                        requested_tenant=tenant_id,
                        security_event="TENANT_MISMATCH"
                    )
                    raise ValueError(
                        f"Security violation: Tenant context mismatch "
                        f"(context={context_tenant}, requested={tenant_id})"
                    )

            # Use SET LOCAL for transaction-scoped context
            # This is more secure than SET as it auto-clears on transaction end
            await session.execute(
                text("SET LOCAL app.current_tenant = :tenant_id::uuid")
                .bindparams(tenant_id=tenant_id)
            )

            # Verify RLS context was set correctly (read-back check)
            result = await session.execute(
                text("SELECT current_setting('app.current_tenant', true);")
            )
            db_tenant = result.scalar()

            if db_tenant != tenant_id:
                structured_logger.error(
                    "RLS context verification failed",
                    expected=tenant_id,
                    actual=db_tenant,
                    security_event="RLS_VERIFICATION_FAILED"
                )
                raise ValueError(
                    f"RLS context verification failed: expected {tenant_id}, got {db_tenant}"
                )

            # Store in context variable for app-level tracking
            _current_tenant_id.set(tenant_id)
            _rls_enforced.set(True)

            structured_logger.debug(
                "Tenant RLS context set",
                tenant_id=tenant_id,
                rls_enforced=True
            )

        except ValueError:
            # Re-raise security violations
            raise
        except Exception as e:
            structured_logger.error(
                "Failed to set tenant context",
                error=str(e),
                tenant_id=tenant_id
            )
            raise

    async def clear_tenant_context(self, session: AsyncSession):
        """
        Clear the tenant context.

        Note: With SET LOCAL, this is automatic on transaction end.
        This method is provided for explicit cleanup if needed.
        """
        try:
            # Clear PostgreSQL context
            await session.execute(text("SET LOCAL app.current_tenant = NULL;"))

            # Clear context variables
            _current_tenant_id.set(None)
            _rls_enforced.set(False)

            structured_logger.debug("Tenant RLS context cleared")
        except Exception as e:
            structured_logger.error("Failed to clear tenant context", error=str(e))
            raise

    def get_current_tenant_id(self) -> Optional[str]:
        """Get current tenant ID from context variable."""
        return _current_tenant_id.get()

    def is_rls_enforced(self) -> bool:
        """Check if RLS is currently enforced."""
        return _rls_enforced.get()


# Global database manager instance
db_manager = AsyncDatabaseManager()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for FastAPI routes to get database session.
    Note: Does NOT set tenant context - use get_db_with_tenant for RLS enforcement.
    """
    async for session in db_manager.get_session():
        yield session


async def get_db_with_tenant(request) -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for FastAPI routes with tenant RLS context.
    Automatically sets app.current_tenant for Row-Level Security.

    Usage in routes:
        @router.get("/evf")
        async def list_evfs(db: AsyncSession = Depends(get_db_with_tenant)):
            # All queries here are automatically filtered by tenant_id
            pass
    """
    async for session in db_manager.get_session():
        # Extract tenant_id from request state (set by TenantMiddleware)
        tenant_id = getattr(request.state, "tenant_id", None)

        if tenant_id:
            # Set RLS context for this session
            await db_manager.set_tenant_context(session, tenant_id)

        try:
            yield session
        finally:
            # Clear tenant context after request
            if tenant_id:
                await db_manager.clear_tenant_context(session)


async def initialize_database():
    """Initialize database connection pool."""
    await db_manager.initialize()


async def close_database():
    """Close database connection pool."""
    await db_manager.close()


def get_current_tenant_context() -> Optional[str]:
    """
    Get current tenant ID from context variable.

    Returns:
        Tenant UUID string or None
    """
    return _current_tenant_id.get()


def is_rls_active() -> bool:
    """
    Check if RLS is currently active for the request.

    Returns:
        True if RLS is enforced, False otherwise
    """
    return _rls_enforced.get()


async def verify_rls_context(session: AsyncSession, expected_tenant_id: str) -> bool:
    """
    Verify that RLS context matches expected tenant ID.

    This is a security check to ensure tenant isolation is working.

    Args:
        session: Database session
        expected_tenant_id: Expected tenant UUID

    Returns:
        True if context matches, False otherwise
    """
    try:
        result = await session.execute(
            text("SELECT current_setting('app.current_tenant', true);")
        )
        actual_tenant = result.scalar()

        matches = actual_tenant == expected_tenant_id

        if not matches:
            structured_logger.warning(
                "RLS context mismatch during verification",
                expected=expected_tenant_id,
                actual=actual_tenant,
                security_event="RLS_CONTEXT_MISMATCH"
            )

        return matches

    except Exception as e:
        structured_logger.error(
            "RLS context verification failed",
            error=str(e),
            expected_tenant=expected_tenant_id
        )
        return False
