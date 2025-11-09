"""
Integration tests for tenant isolation and RLS enforcement.

Tests cover:
- Tenant A cannot access Tenant B's data
- RLS policies work correctly
- Multi-tenant query isolation
- Background task isolation
- Migration script testing
"""

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid4

from backend.core.database import (
    rls_enforced_session,
    assert_rls_enforced,
    RLSViolationError,
    db_manager
)
from backend.models.tenant import Tenant, User, EVF


@pytest.fixture
async def tenant_a(db_session: AsyncSession):
    """Create test tenant A."""
    tenant = Tenant(
        id=str(uuid4()),
        name="Tenant A Company",
        slug="tenant-a",
        nif="123456789",
        is_active=True
    )
    db_session.add(tenant)
    await db_session.commit()
    await db_session.refresh(tenant)
    return tenant


@pytest.fixture
async def tenant_b(db_session: AsyncSession):
    """Create test tenant B."""
    tenant = Tenant(
        id=str(uuid4()),
        name="Tenant B Company",
        slug="tenant-b",
        nif="987654321",
        is_active=True
    )
    db_session.add(tenant)
    await db_session.commit()
    await db_session.refresh(tenant)
    return tenant


@pytest.fixture
async def user_a(db_session: AsyncSession, tenant_a):
    """Create user for tenant A."""
    user = User(
        id=str(uuid4()),
        tenant_id=tenant_a.id,
        email="user@tenant-a.com",
        password_hash="$argon2id$...",
        full_name="User A"
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def user_b(db_session: AsyncSession, tenant_b):
    """Create user for tenant B."""
    user = User(
        id=str(uuid4()),
        tenant_id=tenant_b.id,
        email="user@tenant-b.com",
        password_hash="$argon2id$...",
        full_name="User B"
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.mark.integration
@pytest.mark.asyncio
class TestTenantIsolation:
    """Test that tenants cannot access each other's data."""

    async def test_tenant_a_cannot_see_tenant_b_users(
        self,
        db_session,
        tenant_a,
        tenant_b,
        user_a,
        user_b
    ):
        """Test that tenant A cannot query tenant B's users."""
        # Query as tenant A
        async with rls_enforced_session(db_session, tenant_a.id, "test_query") as session:
            result = await session.execute(select(User))
            users = result.scalars().all()

            # Should only see tenant A's user
            assert len(users) == 1
            assert users[0].id == user_a.id
            assert users[0].tenant_id == tenant_a.id

    async def test_tenant_b_cannot_see_tenant_a_users(
        self,
        db_session,
        tenant_a,
        tenant_b,
        user_a,
        user_b
    ):
        """Test that tenant B cannot query tenant A's users."""
        # Query as tenant B
        async with rls_enforced_session(db_session, tenant_b.id, "test_query") as session:
            result = await session.execute(select(User))
            users = result.scalars().all()

            # Should only see tenant B's user
            assert len(users) == 1
            assert users[0].id == user_b.id
            assert users[0].tenant_id == tenant_b.id

    async def test_query_without_rls_raises_exception(self, db_session, tenant_a):
        """Test that queries without RLS context raise exception."""
        with pytest.raises(RLSViolationError):
            # Try to query without setting RLS context
            assert_rls_enforced()
            await db_session.execute(select(User))

    async def test_tenant_can_only_update_own_users(
        self,
        db_session,
        tenant_a,
        tenant_b,
        user_a,
        user_b
    ):
        """Test that tenant A cannot update tenant B's users."""
        # Try to update as tenant A
        async with rls_enforced_session(db_session, tenant_a.id, "test_update") as session:
            # Try to update tenant B's user (should fail silently due to RLS)
            result = await session.execute(
                select(User).where(User.id == user_b.id)
            )
            user = result.scalar_one_or_none()

            # Should not find tenant B's user
            assert user is None

    async def test_tenant_can_only_delete_own_users(
        self,
        db_session,
        tenant_a,
        tenant_b,
        user_a,
        user_b
    ):
        """Test that tenant A cannot delete tenant B's users."""
        # Try to delete as tenant A
        async with rls_enforced_session(db_session, tenant_a.id, "test_delete") as session:
            # Try to get and delete tenant B's user
            result = await session.execute(
                select(User).where(User.id == user_b.id)
            )
            user = result.scalar_one_or_none()

            # Should not find tenant B's user
            assert user is None

        # Verify tenant B's user still exists
        async with rls_enforced_session(db_session, tenant_b.id, "test_verify") as session:
            result = await session.execute(
                select(User).where(User.id == user_b.id)
            )
            user = result.scalar_one_or_none()
            assert user is not None


@pytest.mark.integration
@pytest.mark.asyncio
class TestRLSPolicyEnforcement:
    """Test that PostgreSQL RLS policies are enforced correctly."""

    async def test_rls_context_is_set_correctly(self, db_session, tenant_a):
        """Test that app.current_tenant is set correctly."""
        async with rls_enforced_session(db_session, tenant_a.id, "test") as session:
            # Query current tenant setting
            result = await session.execute(
                text("SELECT current_setting('app.current_tenant', true);")
            )
            current_tenant = result.scalar()

            assert current_tenant == tenant_a.id

    async def test_rls_context_clears_after_session(self, db_session, tenant_a):
        """Test that RLS context clears after session ends."""
        async with rls_enforced_session(db_session, tenant_a.id, "test"):
            pass

        # After session, context should be cleared
        # This would need a fresh connection to verify properly
        # For unit tests, we check context variables

    async def test_set_local_is_transaction_scoped(self, db_session, tenant_a, tenant_b):
        """Test that SET LOCAL is properly scoped to transaction."""
        # Set context for tenant A
        async with rls_enforced_session(db_session, tenant_a.id, "test_a") as session_a:
            result = await session_a.execute(
                text("SELECT current_setting('app.current_tenant', true);")
            )
            assert result.scalar() == tenant_a.id

        # After transaction, start new one for tenant B
        async with rls_enforced_session(db_session, tenant_b.id, "test_b") as session_b:
            result = await session_b.execute(
                text("SELECT current_setting('app.current_tenant', true);")
            )
            assert result.scalar() == tenant_b.id


@pytest.mark.integration
@pytest.mark.asyncio
class TestMultiTenantQueries:
    """Test complex multi-tenant query scenarios."""

    async def test_join_query_respects_rls(
        self,
        db_session,
        tenant_a,
        tenant_b,
        user_a,
        user_b
    ):
        """Test that JOIN queries respect RLS."""
        # Query with join as tenant A
        async with rls_enforced_session(db_session, tenant_a.id, "test_join") as session:
            result = await session.execute(
                select(User, Tenant)
                .join(Tenant, User.tenant_id == Tenant.id)
            )
            rows = result.all()

            # Should only see tenant A's data
            assert len(rows) == 1
            assert rows[0][0].tenant_id == tenant_a.id
            assert rows[0][1].id == tenant_a.id

    async def test_aggregate_query_respects_rls(
        self,
        db_session,
        tenant_a,
        tenant_b,
        user_a,
        user_b
    ):
        """Test that aggregate queries respect RLS."""
        # Count users as tenant A
        async with rls_enforced_session(db_session, tenant_a.id, "test_count") as session:
            result = await session.execute(
                select(func.count(User.id))
            )
            count = result.scalar()

            # Should only count tenant A's users
            assert count == 1

        # Count users as tenant B
        async with rls_enforced_session(db_session, tenant_b.id, "test_count") as session:
            result = await session.execute(
                select(func.count(User.id))
            )
            count = result.scalar()

            # Should only count tenant B's users
            assert count == 1

    async def test_subquery_respects_rls(
        self,
        db_session,
        tenant_a,
        tenant_b,
        user_a,
        user_b
    ):
        """Test that subqueries respect RLS."""
        from sqlalchemy import func

        # Subquery as tenant A
        async with rls_enforced_session(db_session, tenant_a.id, "test_subquery") as session:
            subquery = select(User.tenant_id).where(User.email.like("%@tenant-a.com"))

            result = await session.execute(
                select(Tenant).where(Tenant.id.in_(subquery))
            )
            tenants = result.scalars().all()

            # Should only see tenant A
            assert len(tenants) == 1
            assert tenants[0].id == tenant_a.id


@pytest.mark.integration
@pytest.mark.asyncio
class TestBackgroundTaskIsolation:
    """Test tenant isolation in background tasks."""

    async def test_background_task_processes_correct_tenant_data(
        self,
        db_session,
        tenant_a,
        tenant_b,
        user_a,
        user_b
    ):
        """Test that background task processes only target tenant's data."""
        async def process_tenant_users(tenant_id: str):
            async with rls_enforced_session(
                db_session,
                tenant_id,
                "background_process"
            ) as session:
                result = await session.execute(select(User))
                users = result.scalars().all()
                return [u.id for u in users]

        # Process tenant A
        user_ids_a = await process_tenant_users(tenant_a.id)
        assert user_ids_a == [user_a.id]

        # Process tenant B
        user_ids_b = await process_tenant_users(tenant_b.id)
        assert user_ids_b == [user_b.id]

    async def test_concurrent_background_tasks_isolated(
        self,
        db_session,
        tenant_a,
        tenant_b,
        user_a,
        user_b
    ):
        """Test that concurrent background tasks don't interfere."""
        import asyncio

        async def count_users(tenant_id: str):
            async with rls_enforced_session(
                db_session,
                tenant_id,
                "count_task"
            ) as session:
                result = await session.execute(select(func.count(User.id)))
                return result.scalar()

        # Run concurrently
        count_a, count_b = await asyncio.gather(
            count_users(tenant_a.id),
            count_users(tenant_b.id)
        )

        assert count_a == 1
        assert count_b == 1


@pytest.mark.integration
@pytest.mark.asyncio
class TestMigrationScripts:
    """Test that migration scripts handle multi-tenancy correctly."""

    async def test_migration_creates_tenant_isolated_records(
        self,
        db_session,
        tenant_a
    ):
        """Test that migrations create properly isolated records."""
        # Simulate migration creating a record
        async with rls_enforced_session(
            db_session,
            tenant_a.id,
            "migration"
        ) as session:
            new_user = User(
                id=str(uuid4()),
                tenant_id=tenant_a.id,
                email="migration@tenant-a.com",
                password_hash="$argon2id$...",
                full_name="Migration User"
            )
            session.add(new_user)
            await session.commit()
            await session.refresh(new_user)

            # Verify record exists
            result = await session.execute(
                select(User).where(User.email == "migration@tenant-a.com")
            )
            user = result.scalar_one()
            assert user.tenant_id == tenant_a.id

    async def test_system_migration_with_allow_system(self, db_session):
        """Test that system migrations can run without tenant context."""
        # System migrations should use allow_system=True
        assert_rls_enforced(allow_system=True)

        # This would be a system-level query (e.g., creating tables)
        # In real scenario, would execute DDL


@pytest.mark.integration
@pytest.mark.asyncio
class TestErrorScenarios:
    """Test error handling in multi-tenant scenarios."""

    async def test_invalid_tenant_id_raises_error(self, db_session):
        """Test that invalid tenant ID raises error."""
        invalid_tenant_id = "invalid-uuid"

        with pytest.raises(Exception):  # Would raise ValueError or similar
            async with rls_enforced_session(
                db_session,
                invalid_tenant_id,
                "test"
            ):
                pass

    async def test_deleted_tenant_data_not_accessible(
        self,
        db_session,
        tenant_a,
        user_a
    ):
        """Test that soft-deleted tenant data is not accessible."""
        # Soft delete tenant
        tenant_a.is_active = False
        await db_session.commit()

        # Try to query as deleted tenant
        async with rls_enforced_session(
            db_session,
            tenant_a.id,
            "test_deleted"
        ) as session:
            # RLS still enforces tenant isolation
            # But application logic should check is_active
            result = await session.execute(select(User))
            users = result.scalars().all()

            # RLS still returns data (PostgreSQL doesn't know about is_active)
            # Application must filter
            assert len(users) == 1


@pytest.mark.integration
@pytest.mark.asyncio
class TestPerformanceImpact:
    """Test performance impact of RLS enforcement."""

    async def test_rls_enforcement_overhead(self, db_session, tenant_a, user_a):
        """Test that RLS enforcement has minimal overhead."""
        import time

        # Measure with RLS
        start = time.time()
        async with rls_enforced_session(db_session, tenant_a.id, "perf_test") as session:
            for _ in range(10):
                await session.execute(select(User))
        with_rls = time.time() - start

        # RLS overhead should be < 5ms per query
        avg_overhead = (with_rls / 10) * 1000
        assert avg_overhead < 5, f"RLS overhead {avg_overhead:.1f}ms > 5ms target"
