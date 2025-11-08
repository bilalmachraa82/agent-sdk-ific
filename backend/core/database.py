"""
Async SQLAlchemy database configuration with multi-tenant support and RLS context.
Handles connection pooling, session management, and tenant isolation.
"""

from typing import AsyncGenerator, Optional
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
    AsyncEngine,
)
from sqlalchemy.pool import NullPool, QueuePool
from sqlalchemy import text, event
import logging

from .config import settings

logger = logging.getLogger(__name__)


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

    async def set_tenant_context(self, session: AsyncSession, tenant_id: str):
        """
        Set the tenant context for Row-Level Security.
        Must be called after getting a session.
        Uses parameterized query to prevent SQL injection.
        """
        try:
            await session.execute(
                text("SET app.current_tenant = :tenant_id::uuid").bindparams(tenant_id=tenant_id)
            )
            logger.debug(f"Tenant context set to: {tenant_id}")
        except Exception as e:
            logger.error(f"Failed to set tenant context: {e}")
            raise

    async def clear_tenant_context(self, session: AsyncSession):
        """Clear the tenant context."""
        try:
            await session.execute(text("SET app.current_tenant = NULL;"))
            logger.debug("Tenant context cleared")
        except Exception as e:
            logger.error(f"Failed to clear tenant context: {e}")
            raise


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
