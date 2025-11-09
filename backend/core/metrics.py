"""
Prometheus Metrics Infrastructure

Provides comprehensive metrics collection for:
- Security events (key rotation, Argon2id adoption, RLS violations)
- Performance (auth latency, EVF processing time)
- Business metrics (token spend, agent runtime)
- System health (DB connections, cache hit rate)

Metrics Types:
- Counter: Monotonically increasing values (requests, errors, events)
- Histogram: Distribution of values (latency, duration)
- Gauge: Point-in-time values (connections, queue depth)

Integration:
- FastAPI middleware for automatic HTTP metrics
- Custom decorators for function instrumentation
- Manual tracking for business metrics
"""

import time
import functools
from typing import Callable, Optional, Any, TypeVar, List
from contextvars import ContextVar

from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    Summary,
    CollectorRegistry,
    generate_latest,
    CONTENT_TYPE_LATEST,
    multiprocess,
    REGISTRY
)
from prometheus_client.exposition import CONTENT_TYPE_LATEST as PROM_CONTENT_TYPE
import structlog

# Type hints
T = TypeVar("T")

logger = structlog.get_logger(__name__)

# Context variables for label enrichment
_current_tenant_id: ContextVar[Optional[str]] = ContextVar("tenant_id", default=None)
_current_operation: ContextVar[Optional[str]] = ContextVar("operation", default=None)


# ==============================================================================
# HTTP REQUEST METRICS
# ==============================================================================

http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"]
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint", "status"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

http_requests_in_progress = Gauge(
    "http_requests_in_progress",
    "Number of HTTP requests currently being processed",
    ["method", "endpoint"]
)


# ==============================================================================
# AUTHENTICATION METRICS
# ==============================================================================

auth_attempts_total = Counter(
    "auth_attempts_total",
    "Total authentication attempts",
    ["method", "status", "tenant_id"]
)

auth_duration_seconds = Histogram(
    "auth_duration_seconds",
    "Authentication operation duration",
    ["method", "operation"],
    buckets=[0.01, 0.05, 0.1, 0.15, 0.2, 0.3, 0.5, 1.0]  # Target: <100ms
)

password_hash_duration_seconds = Histogram(
    "password_hash_duration_seconds",
    "Password hashing duration",
    ["algorithm"],
    buckets=[0.05, 0.1, 0.15, 0.2, 0.3, 0.5, 1.0]  # Target: <150ms
)

password_algorithm_usage = Counter(
    "password_algorithm_usage",
    "Password algorithm usage count",
    ["algorithm", "operation"]  # algorithm: argon2id/bcrypt, operation: hash/verify/migrate
)

argon2id_adoption_percentage = Gauge(
    "argon2id_adoption_percentage",
    "Percentage of users using Argon2id hashing",
    ["tenant_id"]
)

jwt_operations_total = Counter(
    "jwt_operations_total",
    "JWT operations count",
    ["operation", "algorithm", "status"]  # operation: sign/verify, algorithm: RS256/HS256
)

jwt_key_rotation_events = Counter(
    "jwt_key_rotation_events",
    "JWT key rotation events",
    ["event_type", "status"]  # event_type: scheduled/manual/emergency
)

jwt_key_age_days = Gauge(
    "jwt_key_age_days",
    "Age of current JWT signing key in days",
    ["key_id"]
)


# ==============================================================================
# RLS (ROW-LEVEL SECURITY) METRICS
# ==============================================================================

rls_enforcement_checks_total = Counter(
    "rls_enforcement_checks_total",
    "RLS enforcement checks performed",
    ["status", "operation"]  # status: enforced/violated/bypassed
)

rls_violations_total = Counter(
    "rls_violations_total",
    "RLS violations detected",
    ["violation_type", "tenant_id", "severity"]  # violation_type: NOT_ENFORCED/TENANT_MISMATCH/VERIFICATION_FAILED
)

rls_context_operations_total = Counter(
    "rls_context_operations_total",
    "RLS context operations",
    ["operation", "source"]  # operation: set/clear, source: http/background_task/agent
)

rls_overhead_seconds = Histogram(
    "rls_overhead_seconds",
    "RLS enforcement overhead",
    buckets=[0.001, 0.002, 0.005, 0.01, 0.02, 0.05]  # Target: <5ms
)


# ==============================================================================
# DATABASE METRICS
# ==============================================================================

db_query_duration_seconds = Histogram(
    "db_query_duration_seconds",
    "Database query duration",
    ["operation", "table"],
    buckets=[0.001, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0]
)

db_connections_total = Gauge(
    "db_connections_total",
    "Total database connections",
    ["pool", "state"]  # pool: main/replica, state: idle/active/waiting
)

db_transactions_total = Counter(
    "db_transactions_total",
    "Database transactions",
    ["status", "isolation_level"]  # status: commit/rollback
)


# ==============================================================================
# EVF PROCESSING METRICS
# ==============================================================================

evf_processing_duration_seconds = Histogram(
    "evf_processing_duration_seconds",
    "EVF processing time",
    ["stage", "tenant_id"],
    buckets=[1, 5, 10, 30, 60, 120, 180, 300, 600]  # Target: <180s (3 min)
)

evf_operations_total = Counter(
    "evf_operations_total",
    "EVF operations count",
    ["operation", "status", "tenant_id"]  # operation: create/process/validate/export
)

evf_validation_results = Counter(
    "evf_validation_results",
    "EVF validation results",
    ["check_type", "result", "tenant_id"]  # check_type: valf/trf/compliance
)

evf_processing_errors = Counter(
    "evf_processing_errors",
    "EVF processing errors",
    ["error_type", "stage", "tenant_id"]
)


# ==============================================================================
# AI AGENT METRICS
# ==============================================================================

agent_executions_total = Counter(
    "agent_executions_total",
    "Agent execution count",
    ["agent_name", "status", "tenant_id"]  # agent_name: InputAgent/ComplianceAgent/etc.
)

agent_duration_seconds = Histogram(
    "agent_duration_seconds",
    "Agent execution duration",
    ["agent_name", "tenant_id"],
    buckets=[0.1, 0.5, 1, 5, 10, 30, 60, 120]
)

agent_token_usage = Counter(
    "agent_token_usage",
    "AI agent token usage",
    ["agent_name", "token_type", "tenant_id"]  # token_type: input/output
)

agent_cost_usd = Counter(
    "agent_cost_usd",
    "AI agent cost in USD",
    ["agent_name", "model", "tenant_id"]
)

agent_errors_total = Counter(
    "agent_errors_total",
    "Agent errors",
    ["agent_name", "error_type", "tenant_id"]
)

langgraph_state_transitions = Counter(
    "langgraph_state_transitions",
    "LangGraph state transitions",
    ["graph_name", "from_state", "to_state", "tenant_id"]
)


# ==============================================================================
# CACHE METRICS
# ==============================================================================

cache_operations_total = Counter(
    "cache_operations_total",
    "Cache operations",
    ["operation", "status"]  # operation: get/set/delete, status: hit/miss/error
)

cache_hit_rate = Gauge(
    "cache_hit_rate",
    "Cache hit rate percentage",
    ["cache_type"]  # cache_type: redis/memory
)


# ==============================================================================
# SECURITY EVENT METRICS
# ==============================================================================

security_events_total = Counter(
    "security_events_total",
    "Security events detected",
    ["event_type", "severity", "tenant_id"]
)

rate_limit_events = Counter(
    "rate_limit_events",
    "Rate limiting events",
    ["endpoint", "action", "tenant_id"]  # action: allowed/blocked/warned
)

suspicious_activity_events = Counter(
    "suspicious_activity_events",
    "Suspicious activity detected",
    ["activity_type", "tenant_id"]
)


# ==============================================================================
# BUSINESS METRICS
# ==============================================================================

tenant_active_users = Gauge(
    "tenant_active_users",
    "Number of active users per tenant",
    ["tenant_id"]
)

tenant_storage_bytes = Gauge(
    "tenant_storage_bytes",
    "Storage used by tenant in bytes",
    ["tenant_id", "storage_type"]  # storage_type: database/files/vectors
)

tenant_quota_usage_percentage = Gauge(
    "tenant_quota_usage_percentage",
    "Tenant quota usage percentage",
    ["tenant_id", "quota_type"]  # quota_type: api_calls/storage/tokens
)


# ==============================================================================
# METRIC HELPER FUNCTIONS
# ==============================================================================

def set_tenant_context(tenant_id: str) -> None:
    """Set tenant ID in metrics context for label enrichment."""
    _current_tenant_id.set(tenant_id)


def set_operation_context(operation: str) -> None:
    """Set operation name in metrics context."""
    _current_operation.set(operation)


def record_auth_attempt(
    method: str,
    status: str,
    duration: float,
    tenant_id: Optional[str] = None
) -> None:
    """
    Record authentication attempt metrics.

    Args:
        method: Auth method (password/jwt/oauth)
        status: success/failure/error
        duration: Duration in seconds
        tenant_id: Optional tenant identifier
    """
    tenant = tenant_id or _current_tenant_id.get() or "unknown"

    auth_attempts_total.labels(
        method=method,
        status=status,
        tenant_id=tenant
    ).inc()

    auth_duration_seconds.labels(
        method=method,
        operation="authenticate"
    ).observe(duration)


def record_password_operation(
    algorithm: str,
    operation: str,
    duration: float
) -> None:
    """
    Record password hashing/verification metrics.

    Args:
        algorithm: argon2id/bcrypt
        operation: hash/verify/migrate
        duration: Duration in seconds
    """
    password_algorithm_usage.labels(
        algorithm=algorithm,
        operation=operation
    ).inc()

    password_hash_duration_seconds.labels(
        algorithm=algorithm
    ).observe(duration)


def record_rls_check(
    status: str,
    operation: str,
    overhead: Optional[float] = None
) -> None:
    """
    Record RLS enforcement check.

    Args:
        status: enforced/violated/bypassed
        operation: Operation type
        overhead: Optional overhead duration in seconds
    """
    rls_enforcement_checks_total.labels(
        status=status,
        operation=operation
    ).inc()

    if overhead is not None:
        rls_overhead_seconds.observe(overhead)


def record_rls_violation(
    violation_type: str,
    tenant_id: Optional[str] = None,
    severity: str = "critical"
) -> None:
    """
    Record RLS violation (CRITICAL SECURITY EVENT).

    Args:
        violation_type: NOT_ENFORCED/TENANT_MISMATCH/VERIFICATION_FAILED
        tenant_id: Affected tenant
        severity: critical/high/medium
    """
    tenant = tenant_id or _current_tenant_id.get() or "unknown"

    rls_violations_total.labels(
        violation_type=violation_type,
        tenant_id=tenant,
        severity=severity
    ).inc()

    # Also record as security event
    security_events_total.labels(
        event_type=f"rls_violation_{violation_type.lower()}",
        severity=severity,
        tenant_id=tenant
    ).inc()

    logger.error(
        "RLS violation recorded",
        violation_type=violation_type,
        tenant_id=tenant,
        severity=severity,
        metric="rls_violations_total"
    )


def record_evf_operation(
    operation: str,
    status: str,
    duration: Optional[float] = None,
    stage: Optional[str] = None,
    tenant_id: Optional[str] = None
) -> None:
    """
    Record EVF processing metrics.

    Args:
        operation: create/process/validate/export
        status: success/failure/error
        duration: Optional duration in seconds
        stage: Optional processing stage
        tenant_id: Optional tenant identifier
    """
    tenant = tenant_id or _current_tenant_id.get() or "unknown"

    evf_operations_total.labels(
        operation=operation,
        status=status,
        tenant_id=tenant
    ).inc()

    if duration is not None and stage is not None:
        evf_processing_duration_seconds.labels(
            stage=stage,
            tenant_id=tenant
        ).observe(duration)


def record_agent_execution(
    agent_name: str,
    status: str,
    duration: float,
    tokens_input: int = 0,
    tokens_output: int = 0,
    cost_usd: float = 0.0,
    tenant_id: Optional[str] = None
) -> None:
    """
    Record AI agent execution metrics.

    Args:
        agent_name: Name of the agent (InputAgent, ComplianceAgent, etc.)
        status: success/failure/error
        duration: Execution duration in seconds
        tokens_input: Input tokens used
        tokens_output: Output tokens generated
        cost_usd: Cost in USD
        tenant_id: Optional tenant identifier
    """
    tenant = tenant_id or _current_tenant_id.get() or "unknown"

    agent_executions_total.labels(
        agent_name=agent_name,
        status=status,
        tenant_id=tenant
    ).inc()

    agent_duration_seconds.labels(
        agent_name=agent_name,
        tenant_id=tenant
    ).observe(duration)

    if tokens_input > 0:
        agent_token_usage.labels(
            agent_name=agent_name,
            token_type="input",
            tenant_id=tenant
        ).inc(tokens_input)

    if tokens_output > 0:
        agent_token_usage.labels(
            agent_name=agent_name,
            token_type="output",
            tenant_id=tenant
        ).inc(tokens_output)

    if cost_usd > 0:
        agent_cost_usd.labels(
            agent_name=agent_name,
            model="claude-sonnet-4.5",
            tenant_id=tenant
        ).inc(cost_usd)


# ==============================================================================
# METRIC DECORATORS
# ==============================================================================

def track_duration(
    metric: Histogram,
    labels: Optional[dict[str, str]] = None
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator to track function duration with a Histogram metric.

    Args:
        metric: Prometheus Histogram to record to
        labels: Optional labels to add

    Usage:
        @track_duration(auth_duration_seconds, {"method": "password"})
        async def authenticate(username, password):
            pass
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> T:
            start = time.time()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start
                if labels:
                    metric.labels(**labels).observe(duration)
                else:
                    metric.observe(duration)

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> T:
            start = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start
                if labels:
                    metric.labels(**labels).observe(duration)
                else:
                    metric.observe(duration)

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        else:
            return sync_wrapper  # type: ignore

    return decorator


def count_calls(
    metric: Counter,
    labels: Optional[dict[str, str]] = None
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator to count function calls with a Counter metric.

    Args:
        metric: Prometheus Counter to increment
        labels: Optional labels to add

    Usage:
        @count_calls(evf_operations_total, {"operation": "create"})
        async def create_evf(data):
            pass
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> T:
            if labels:
                metric.labels(**labels).inc()
            else:
                metric.inc()
            return await func(*args, **kwargs)

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> T:
            if labels:
                metric.labels(**labels).inc()
            else:
                metric.inc()
            return func(*args, **kwargs)

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        else:
            return sync_wrapper  # type: ignore

    return decorator


# ==============================================================================
# METRICS ENDPOINT
# ==============================================================================

def get_metrics() -> tuple[bytes, str]:
    """
    Generate Prometheus metrics in text format.

    Returns:
        Tuple of (metrics_data, content_type)

    Usage in FastAPI:
        @app.get("/metrics")
        async def metrics():
            data, content_type = get_metrics()
            return Response(content=data, media_type=content_type)
    """
    return generate_latest(REGISTRY), CONTENT_TYPE_LATEST


# ==============================================================================
# EXAMPLE USAGE
# ==============================================================================

if __name__ == "__main__":
    # Example 1: Record authentication attempt
    record_auth_attempt(
        method="password",
        status="success",
        duration=0.085,
        tenant_id="tenant-123"
    )

    # Example 2: Record RLS violation (CRITICAL)
    record_rls_violation(
        violation_type="NOT_ENFORCED",
        tenant_id="tenant-456",
        severity="critical"
    )

    # Example 3: Record EVF processing
    record_evf_operation(
        operation="process",
        status="success",
        duration=125.5,
        stage="financial_model",
        tenant_id="tenant-789"
    )

    # Example 4: Record agent execution
    record_agent_execution(
        agent_name="InputAgent",
        status="success",
        duration=2.3,
        tokens_input=1500,
        tokens_output=800,
        cost_usd=0.012,
        tenant_id="tenant-789"
    )

    # Example 5: Use decorator
    @track_duration(auth_duration_seconds, {"method": "jwt", "operation": "verify"})
    async def verify_jwt(token: str):
        # Verification logic
        await asyncio.sleep(0.02)
        return True

    print("✅ Metrics examples completed")
