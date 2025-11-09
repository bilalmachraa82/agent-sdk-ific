# RLS Invariant Enforcement Guide

**Status**: ✅ Implemented
**Date**: November 9, 2025
**Priority**: CRITICAL - Security Foundation

---

## Overview

This guide documents the **mandatory RLS (Row-Level Security) invariant enforcement** system implemented to ensure tenant isolation across **ALL** database entry points in the EVF Portugal 2030 platform.

### The Problem

PostgreSQL RLS with `SET LOCAL app.current_tenant` only works when:
1. The tenant context is explicitly set before queries
2. ALL database connections (SQLAlchemy, asyncpg, background tasks, LangGraph agents) properly set the context

**Without invariant enforcement**, it's possible to:
- Accidentally query the database without setting tenant context
- Bypass RLS through direct asyncpg connections
- Leak data between tenants in background tasks
- Expose tenant data in agent operations

### The Solution

We've implemented a **three-layer defense** system:

1. **`assert_rls_enforced()`** - Mandatory function call before any query
2. **`@require_rls`** - Decorator for automatic RLS enforcement
3. **`rls_enforced_session()`** - Context manager for background tasks and agents

---

## Layer 1: `assert_rls_enforced()`

### Purpose
A mandatory assertion that MUST be called before executing any database query to verify RLS is active.

### Usage

```python
from backend.core.database import assert_rls_enforced, get_db
from sqlalchemy import select
from backend.models.tenant import EVF

async def get_evf_by_id(db: AsyncSession, evf_id: str):
    # MANDATORY: Check RLS enforcement before query
    assert_rls_enforced()

    # Query is now safe - RLS will filter by tenant
    result = await db.execute(
        select(EVF).where(EVF.id == evf_id)
    )
    return result.scalar_one_or_none()
```

### Parameters

- **`allow_system`** (bool, default=False): If True, allows system-level queries without tenant context
  - ⚠️ Use with **extreme caution**
  - Only for migrations, health checks, or system operations
  - Example: `assert_rls_enforced(allow_system=True)`

### Exception

Raises `RLSViolationError` if RLS is not enforced:

```python
RLSViolationError: Security violation: Database query attempted without RLS enforcement.
Ensure set_tenant_context() is called before query execution.
```

### Security Event Logging

When RLS violation is detected:

```json
{
  "event": "RLS_NOT_ENFORCED",
  "level": "error",
  "tenant_id": null,
  "rls_enforced": false,
  "message": "RLS violation: Query attempted without tenant context"
}
```

---

## Layer 2: `@require_rls` Decorator

### Purpose
Automatically enforces RLS before function execution, reducing boilerplate and preventing human error.

### Usage

```python
from backend.core.database import require_rls, get_db_with_tenant
from fastapi import Depends

@router.get("/evf")
@require_rls
async def list_evfs(db: AsyncSession = Depends(get_db_with_tenant)):
    # No need to call assert_rls_enforced() - decorator handles it
    # RLS is automatically enforced before this function runs

    result = await db.execute(select(EVF))
    return result.scalars().all()
```

### When to Use

✅ **Use when:**
- Writing FastAPI route handlers
- Implementing service layer functions that query the database
- You want automatic RLS enforcement without manual checks

❌ **Don't use when:**
- System-level operations (migrations, health checks)
- Functions that don't access the database
- Testing (use `allow_system=True` instead)

### Logging

The decorator logs every execution for audit trail:

```json
{
  "event": "RLS-protected function executed",
  "level": "debug",
  "function": "list_evfs",
  "tenant_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

---

## Layer 3: `rls_enforced_session()` Context Manager

### Purpose
Ensures RLS enforcement for database operations **outside** FastAPI request context:
- Background tasks (Celery, asyncio)
- LangGraph agents
- Scheduled jobs
- Data migration scripts

### Usage

```python
from backend.core.database import rls_enforced_session, db_manager

# Background task example
async def process_evf_background(evf_id: str, tenant_id: str):
    # Get database session
    async with db_manager.get_db_context() as db:
        # Enforce RLS for tenant
        async with rls_enforced_session(db, tenant_id, "process_evf") as tenant_db:
            # All queries here are tenant-isolated
            evf = await tenant_db.execute(
                select(EVF).where(EVF.id == evf_id)
            )

            # Process EVF...
            return evf
```

### Parameters

- **`session`** (AsyncSession): Database session
- **`tenant_id`** (str): Tenant UUID to enforce RLS for
- **`operation`** (str): Description of operation for logging (default: "database_operation")

### LangGraph Agent Example

```python
from langgraph.prebuilt import create_react_agent
from backend.core.database import rls_enforced_session

async def evf_compliance_agent(state: dict):
    tenant_id = state["tenant_id"]
    evf_id = state["evf_id"]

    # Ensure RLS enforcement for agent operations
    async with db_manager.get_db_context() as db:
        async with rls_enforced_session(db, tenant_id, "evf_compliance_check") as tenant_db:
            # Agent can safely query database
            evf = await tenant_db.execute(
                select(EVF).where(EVF.id == evf_id)
            )

            # Run compliance checks...
            return {"compliance_status": "approved"}
```

### Logging

```json
{
  "event": "RLS context established for operation",
  "level": "info",
  "operation": "process_evf",
  "tenant_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

When operation completes:

```json
{
  "event": "RLS context cleared after operation",
  "level": "debug",
  "operation": "process_evf",
  "tenant_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

---

## FastAPI Route Integration

### Using `get_db_with_tenant` (Recommended)

For authenticated routes that need tenant isolation:

```python
from fastapi import APIRouter, Depends
from backend.core.database import get_db_with_tenant, assert_rls_enforced

router = APIRouter()

@router.get("/evf")
async def list_evfs(db: AsyncSession = Depends(get_db_with_tenant)):
    # RLS automatically enforced by get_db_with_tenant
    # Still add assertion for defense-in-depth
    assert_rls_enforced()

    result = await db.execute(select(EVF))
    return result.scalars().all()
```

### Using `get_db` (System Operations Only)

For unauthenticated routes or system operations:

```python
from backend.core.database import get_db, assert_rls_enforced

@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    # System operation - explicitly allow without tenant context
    assert_rls_enforced(allow_system=True)

    # Check database connection
    await db.execute(text("SELECT 1"))
    return {"status": "healthy"}
```

---

## Direct asyncpg Connection Example

For raw SQL operations (use sparingly):

```python
import asyncpg
from backend.core.database import assert_rls_enforced, _current_tenant_id, _rls_enforced

async def raw_query_example():
    # Connect to database
    conn = await asyncpg.connect(settings.database_url)

    try:
        # CRITICAL: Set tenant context manually
        tenant_id = "550e8400-e29b-41d4-a716-446655440000"
        await conn.execute("SET LOCAL app.current_tenant = $1::uuid", tenant_id)

        # Update context variables
        _current_tenant_id.set(tenant_id)
        _rls_enforced.set(True)

        # Verify RLS
        assert_rls_enforced()

        # Execute query - RLS will filter results
        rows = await conn.fetch("SELECT * FROM evf")
        return rows

    finally:
        # Clear context
        _current_tenant_id.set(None)
        _rls_enforced.set(False)
        await conn.close()
```

---

## Testing with RLS Enforcement

### Unit Tests

```python
import pytest
from backend.core.database import assert_rls_enforced, RLSViolationError

@pytest.mark.asyncio
async def test_query_without_rls_fails():
    """Ensure queries without RLS enforcement fail."""

    with pytest.raises(RLSViolationError):
        # This should raise RLSViolationError
        assert_rls_enforced()


@pytest.mark.asyncio
async def test_system_query_allowed():
    """System queries with allow_system=True should succeed."""

    # Should not raise exception
    assert_rls_enforced(allow_system=True)
```

### Integration Tests

```python
@pytest.mark.asyncio
async def test_tenant_isolation(db_session, tenant_a, tenant_b):
    """Ensure RLS enforces tenant isolation."""

    # Create EVF for tenant A
    async with rls_enforced_session(db_session, tenant_a.id, "test_create") as db:
        evf_a = EVF(name="EVF A", tenant_id=tenant_a.id)
        db.add(evf_a)
        await db.commit()

    # Query as tenant B - should not see tenant A's data
    async with rls_enforced_session(db_session, tenant_b.id, "test_query") as db:
        result = await db.execute(select(EVF))
        evfs = result.scalars().all()

        # Verify tenant B cannot see tenant A's EVF
        assert len(evfs) == 0
        assert evf_a not in evfs
```

---

## Monitoring & Observability

### Security Events to Monitor

1. **`RLS_NOT_ENFORCED`** - Critical: Query attempted without RLS
2. **`TENANT_MISMATCH`** - Critical: Context variable mismatch
3. **`RLS_VERIFICATION_FAILED`** - Critical: Read-back verification failed
4. **`RLS_CONTEXT_MISMATCH`** - Warning: Verification found mismatch

### Metrics to Track

```python
# Prometheus metrics (to be implemented)
rls_violations_total = Counter(
    "rls_violations_total",
    "Total number of RLS violations detected"
)

rls_operations_total = Counter(
    "rls_operations_total",
    "Total number of RLS-protected operations",
    ["operation"]
)

rls_enforcement_duration_seconds = Histogram(
    "rls_enforcement_duration_seconds",
    "Time taken to enforce RLS context"
)
```

### Dashboard Queries

```sql
-- Find all RLS violations in last 24 hours
SELECT
    timestamp,
    security_event,
    tenant_id,
    path,
    method
FROM audit_logs
WHERE security_event IN ('RLS_NOT_ENFORCED', 'TENANT_MISMATCH', 'RLS_VERIFICATION_FAILED')
AND timestamp > NOW() - INTERVAL '24 hours'
ORDER BY timestamp DESC;
```

---

## Common Pitfalls & Solutions

### ❌ Pitfall 1: Forgetting to Call `assert_rls_enforced()`

```python
# BAD: No RLS check
async def get_evf(db: AsyncSession, evf_id: str):
    return await db.execute(select(EVF).where(EVF.id == evf_id))
```

✅ **Solution:**

```python
# GOOD: RLS check before query
async def get_evf(db: AsyncSession, evf_id: str):
    assert_rls_enforced()
    return await db.execute(select(EVF).where(EVF.id == evf_id))
```

### ❌ Pitfall 2: Using `get_db` Instead of `get_db_with_tenant`

```python
# BAD: get_db doesn't set tenant context
@router.get("/evf")
async def list_evfs(db: AsyncSession = Depends(get_db)):
    return await db.execute(select(EVF))
```

✅ **Solution:**

```python
# GOOD: get_db_with_tenant automatically sets context
@router.get("/evf")
async def list_evfs(db: AsyncSession = Depends(get_db_with_tenant)):
    assert_rls_enforced()
    return await db.execute(select(EVF))
```

### ❌ Pitfall 3: Background Tasks Without RLS

```python
# BAD: Background task without RLS enforcement
async def process_evf(evf_id: str):
    async with get_db() as db:
        evf = await db.execute(select(EVF).where(EVF.id == evf_id))
```

✅ **Solution:**

```python
# GOOD: Use rls_enforced_session for background tasks
async def process_evf(evf_id: str, tenant_id: str):
    async with db_manager.get_db_context() as db:
        async with rls_enforced_session(db, tenant_id, "process_evf") as tenant_db:
            evf = await tenant_db.execute(select(EVF).where(EVF.id == evf_id))
```

---

## Checklist: Adding New Database Queries

When adding new database queries to the codebase, follow this checklist:

- [ ] **1. Identify query type**
  - [ ] FastAPI route → Use `get_db_with_tenant` + `assert_rls_enforced()`
  - [ ] Background task → Use `rls_enforced_session()`
  - [ ] Agent operation → Use `rls_enforced_session()`
  - [ ] System operation → Use `get_db` + `assert_rls_enforced(allow_system=True)`

- [ ] **2. Add RLS enforcement**
  - [ ] Called `assert_rls_enforced()` before query
  - [ ] OR used `@require_rls` decorator
  - [ ] OR wrapped in `rls_enforced_session()` context manager

- [ ] **3. Test tenant isolation**
  - [ ] Created integration test with 2 tenants
  - [ ] Verified tenant A cannot see tenant B's data
  - [ ] Verified RLS violation raises exception

- [ ] **4. Add logging**
  - [ ] Operation logged with tenant_id
  - [ ] Security events logged for violations

---

## Security Audit Procedure

Run this procedure monthly to ensure RLS enforcement is working:

### 1. Code Audit

```bash
# Find database queries without RLS checks
grep -rn "db.execute" backend/ \
  | grep -v "assert_rls_enforced" \
  | grep -v "@require_rls" \
  | grep -v "rls_enforced_session"
```

### 2. Log Audit

```sql
-- Check for RLS violations in last 30 days
SELECT
    DATE(timestamp) as date,
    COUNT(*) as violations
FROM audit_logs
WHERE security_event = 'RLS_NOT_ENFORCED'
AND timestamp > NOW() - INTERVAL '30 days'
GROUP BY DATE(timestamp)
ORDER BY date DESC;
```

Expected: **0 violations**

### 3. Database Audit

```sql
-- Verify all queries have app.current_tenant set
SELECT
    pid,
    usename,
    application_name,
    current_setting('app.current_tenant', true) as tenant_context,
    query
FROM pg_stat_activity
WHERE query NOT LIKE '%pg_stat_activity%'
AND state = 'active';
```

Expected: All active queries should have `tenant_context` set (except system queries)

---

## Emergency Procedures

### RLS Violation Detected

If RLS violation is detected in production:

1. **Immediate Response** (< 5 minutes)
   - Alert security team
   - Review audit logs for affected queries
   - Identify tenant IDs involved

2. **Containment** (< 15 minutes)
   - Deploy hotfix to add RLS enforcement
   - Kill affected database connections
   - Verify fix with integration tests

3. **Investigation** (< 1 hour)
   - Review code changes leading to violation
   - Identify root cause (missing check, wrong dependency, etc.)
   - Check if any data was leaked

4. **Remediation** (< 24 hours)
   - Notify affected tenants if data leak occurred
   - Update code review checklist
   - Add automated tests to prevent recurrence
   - Document incident in security log

---

## Migration Plan

For existing code without RLS enforcement:

### Phase 1: Audit (Week 1)
- [ ] Run code audit script
- [ ] Identify all database query locations
- [ ] Categorize by type (route, task, agent, system)

### Phase 2: Add Enforcement (Week 2)
- [ ] Add `assert_rls_enforced()` to all routes
- [ ] Wrap background tasks in `rls_enforced_session()`
- [ ] Update agent code to use RLS context manager

### Phase 3: Test (Week 3)
- [ ] Run integration tests
- [ ] Verify no RLS violations in staging
- [ ] Load test with multiple tenants

### Phase 4: Deploy (Week 4)
- [ ] Deploy to production with monitoring
- [ ] Monitor for RLS violations
- [ ] Create runbooks for incident response

---

## Further Reading

- [PostgreSQL Row Security Policies](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)
- [SET LOCAL vs SET](https://www.postgresql.org/docs/current/sql-set.html)
- [Context Variables in Python](https://docs.python.org/3/library/contextvars.html)
- [FastAPI Dependency Injection](https://fastapi.tiangolo.com/tutorial/dependencies/)

---

**Last Updated**: November 9, 2025
**Version**: 1.0
**Status**: Production Ready
**Owner**: Backend Security Team
**Review Cycle**: Monthly
