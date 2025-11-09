"""
OpenTelemetry Distributed Tracing Infrastructure

Provides distributed tracing across all backend components:
- FastAPI HTTP requests
- SQLAlchemy database queries
- Redis cache operations
- HTTPX external API calls
- Custom agent operations

Features:
- Automatic instrumentation for common frameworks
- Custom span decorators for business logic
- Context propagation across async boundaries
- Tenant ID injection into spans
- Correlation ID tracking
- Performance monitoring
"""

import functools
from typing import Callable, Optional, Any, TypeVar
from contextvars import ContextVar
import sys

# ParamSpec is only available in Python 3.10+
if sys.version_info >= (3, 10):
    from typing import ParamSpec
else:
    from typing_extensions import ParamSpec

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider, SpanProcessor
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.trace.status import Status, StatusCode

import structlog

# Type hints for decorators
P = ParamSpec("P")
T = TypeVar("T")

# Context variables for trace enrichment
_current_tenant_id: ContextVar[Optional[str]] = ContextVar("tenant_id", default=None)
_current_user_id: ContextVar[Optional[str]] = ContextVar("user_id", default=None)
_correlation_id: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)

logger = structlog.get_logger(__name__)


class TracingConfig:
    """Configuration for OpenTelemetry tracing."""

    def __init__(
        self,
        service_name: str = "evf-portugal-2030",
        service_version: str = "1.0.0",
        environment: str = "development",
        otlp_endpoint: Optional[str] = None,
        enable_console_export: bool = False,
        sample_rate: float = 1.0,
    ):
        self.service_name = service_name
        self.service_version = service_version
        self.environment = environment
        self.otlp_endpoint = otlp_endpoint
        self.enable_console_export = enable_console_export
        self.sample_rate = sample_rate


class TracingManager:
    """
    Manages OpenTelemetry tracing lifecycle and configuration.

    Usage:
        tracing = TracingManager(config)
        tracing.setup()
        app = FastAPI()
        tracing.instrument_fastapi(app)
    """

    def __init__(self, config: TracingConfig):
        self.config = config
        self.tracer_provider: Optional[TracerProvider] = None
        self.tracer: Optional[trace.Tracer] = None
        self._instrumented = False

    def setup(self) -> None:
        """
        Initialize OpenTelemetry tracing with configured exporters.

        Sets up:
        - Resource attributes (service name, version, environment)
        - Span processors (OTLP, console)
        - Tracer provider
        - Global tracer
        """
        # Create resource with service information
        resource = Resource.create({
            SERVICE_NAME: self.config.service_name,
            SERVICE_VERSION: self.config.service_version,
            "deployment.environment": self.config.environment,
            "telemetry.sdk.name": "opentelemetry",
            "telemetry.sdk.language": "python",
        })

        # Create tracer provider
        self.tracer_provider = TracerProvider(resource=resource)

        # Add OTLP exporter if endpoint configured
        if self.config.otlp_endpoint:
            otlp_exporter = OTLPSpanExporter(
                endpoint=self.config.otlp_endpoint,
                insecure=True  # Use secure=True in production with TLS
            )
            self.tracer_provider.add_span_processor(
                BatchSpanProcessor(otlp_exporter)
            )
            logger.info(
                "OTLP trace exporter configured",
                endpoint=self.config.otlp_endpoint
            )

        # Add console exporter for development
        if self.config.enable_console_export:
            console_exporter = ConsoleSpanExporter()
            self.tracer_provider.add_span_processor(
                BatchSpanProcessor(console_exporter)
            )
            logger.info("Console trace exporter enabled")

        # Set as global tracer provider
        trace.set_tracer_provider(self.tracer_provider)

        # Get tracer instance
        self.tracer = trace.get_tracer(
            __name__,
            self.config.service_version
        )

        logger.info(
            "OpenTelemetry tracing initialized",
            service_name=self.config.service_name,
            environment=self.config.environment
        )

    def instrument_fastapi(self, app: Any) -> None:
        """
        Instrument FastAPI application for automatic tracing.

        Captures:
        - HTTP method, path, status code
        - Request/response headers
        - Query parameters
        - Request duration
        """
        if not self._instrumented:
            FastAPIInstrumentor.instrument_app(app)
            logger.info("FastAPI instrumented for tracing")
            self._instrumented = True

    def instrument_sqlalchemy(self, engine: Any) -> None:
        """
        Instrument SQLAlchemy engine for automatic query tracing.

        Captures:
        - SQL queries (parameterized)
        - Query duration
        - Database connection info
        - Transaction boundaries
        """
        SQLAlchemyInstrumentor().instrument(
            engine=engine,
            enable_commenter=True,  # Add trace context to SQL comments
            commenter_options={"db_framework": True}
        )
        logger.info("SQLAlchemy instrumented for tracing")

    def instrument_redis(self) -> None:
        """
        Instrument Redis client for automatic cache tracing.

        Captures:
        - Redis commands (GET, SET, etc.)
        - Command duration
        - Cache hit/miss patterns
        """
        RedisInstrumentor().instrument()
        logger.info("Redis instrumented for tracing")

    def instrument_httpx(self) -> None:
        """
        Instrument HTTPX client for automatic external API tracing.

        Captures:
        - HTTP method, URL, status code
        - Request/response headers
        - Request duration
        - External service dependencies
        """
        HTTPXClientInstrumentor().instrument()
        logger.info("HTTPX instrumented for tracing")

    def shutdown(self) -> None:
        """Gracefully shutdown tracing and flush pending spans."""
        if self.tracer_provider:
            self.tracer_provider.shutdown()
            logger.info("OpenTelemetry tracing shut down")


# Global tracing manager instance
_tracing_manager: Optional[TracingManager] = None


def get_tracer() -> trace.Tracer:
    """
    Get the global tracer instance.

    Returns:
        Configured OpenTelemetry tracer

    Raises:
        RuntimeError: If tracing not initialized
    """
    if _tracing_manager is None or _tracing_manager.tracer is None:
        raise RuntimeError(
            "Tracing not initialized. Call setup_tracing() first."
        )
    return _tracing_manager.tracer


def setup_tracing(config: TracingConfig) -> TracingManager:
    """
    Initialize global tracing configuration.

    Args:
        config: Tracing configuration

    Returns:
        Configured TracingManager instance

    Usage:
        config = TracingConfig(
            service_name="evf-backend",
            otlp_endpoint="http://localhost:4317"
        )
        tracing = setup_tracing(config)
        tracing.instrument_fastapi(app)
    """
    global _tracing_manager

    _tracing_manager = TracingManager(config)
    _tracing_manager.setup()

    return _tracing_manager


def set_tenant_context(tenant_id: str) -> None:
    """
    Set tenant ID in trace context for span enrichment.

    Args:
        tenant_id: Current tenant identifier
    """
    _current_tenant_id.set(tenant_id)

    # Add to current span if active
    current_span = trace.get_current_span()
    if current_span.is_recording():
        current_span.set_attribute("tenant.id", tenant_id)


def set_user_context(user_id: str) -> None:
    """
    Set user ID in trace context for span enrichment.

    Args:
        user_id: Current user identifier
    """
    _current_user_id.set(user_id)

    # Add to current span if active
    current_span = trace.get_current_span()
    if current_span.is_recording():
        current_span.set_attribute("user.id", user_id)


def set_correlation_id(correlation_id: str) -> None:
    """
    Set correlation ID for request tracking across services.

    Args:
        correlation_id: Unique request identifier
    """
    _correlation_id.set(correlation_id)

    # Add to current span if active
    current_span = trace.get_current_span()
    if current_span.is_recording():
        current_span.set_attribute("correlation.id", correlation_id)


def trace_operation(
    operation_name: str,
    operation_type: str = "function",
    record_exception: bool = True,
    enrich_with_context: bool = True
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """
    Decorator to trace function execution with custom spans.

    Args:
        operation_name: Name of the operation (e.g., "process_evf")
        operation_type: Type of operation (e.g., "agent", "service", "repository")
        record_exception: Whether to record exceptions in span
        enrich_with_context: Whether to add tenant/user context to span

    Returns:
        Decorated function with tracing

    Usage:
        @trace_operation("process_evf", operation_type="agent")
        async def process_evf(evf_id: str) -> EVF:
            # Function logic here
            pass
    """
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            tracer = get_tracer()

            with tracer.start_as_current_span(operation_name) as span:
                # Set span attributes
                span.set_attribute("operation.type", operation_type)
                span.set_attribute("function.name", func.__name__)
                span.set_attribute("function.module", func.__module__)

                # Add context information
                if enrich_with_context:
                    tenant_id = _current_tenant_id.get()
                    if tenant_id:
                        span.set_attribute("tenant.id", tenant_id)

                    user_id = _current_user_id.get()
                    if user_id:
                        span.set_attribute("user.id", user_id)

                    correlation_id = _correlation_id.get()
                    if correlation_id:
                        span.set_attribute("correlation.id", correlation_id)

                try:
                    result = await func(*args, **kwargs)
                    span.set_status(Status(StatusCode.OK))
                    return result

                except Exception as e:
                    if record_exception:
                        span.record_exception(e)
                        span.set_status(
                            Status(StatusCode.ERROR, str(e))
                        )
                    raise

        @functools.wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            tracer = get_tracer()

            with tracer.start_as_current_span(operation_name) as span:
                # Set span attributes
                span.set_attribute("operation.type", operation_type)
                span.set_attribute("function.name", func.__name__)
                span.set_attribute("function.module", func.__module__)

                # Add context information
                if enrich_with_context:
                    tenant_id = _current_tenant_id.get()
                    if tenant_id:
                        span.set_attribute("tenant.id", tenant_id)

                    user_id = _current_user_id.get()
                    if user_id:
                        span.set_attribute("user.id", user_id)

                    correlation_id = _correlation_id.get()
                    if correlation_id:
                        span.set_attribute("correlation.id", correlation_id)

                try:
                    result = func(*args, **kwargs)
                    span.set_status(Status(StatusCode.OK))
                    return result

                except Exception as e:
                    if record_exception:
                        span.record_exception(e)
                        span.set_status(
                            Status(StatusCode.ERROR, str(e))
                        )
                    raise

        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        else:
            return sync_wrapper  # type: ignore

    return decorator


def add_span_event(
    event_name: str,
    attributes: Optional[dict[str, Any]] = None
) -> None:
    """
    Add an event to the current span.

    Useful for marking important points in execution without creating sub-spans.

    Args:
        event_name: Name of the event
        attributes: Optional event attributes

    Usage:
        add_span_event("evf_validated", {"status": "passed"})
    """
    current_span = trace.get_current_span()
    if current_span.is_recording():
        current_span.add_event(event_name, attributes or {})


def add_span_attributes(attributes: dict[str, Any]) -> None:
    """
    Add custom attributes to the current span.

    Args:
        attributes: Dictionary of attributes to add

    Usage:
        add_span_attributes({
            "evf.id": evf_id,
            "evf.status": "processing",
            "evf.cost_estimate": 0.45
        })
    """
    current_span = trace.get_current_span()
    if current_span.is_recording():
        for key, value in attributes.items():
            current_span.set_attribute(key, value)


# Convenience decorators for common operation types
def trace_agent(agent_name: str) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """
    Trace LangGraph agent execution.

    Usage:
        @trace_agent("InputAgent")
        async def process(self, state: EVFProcessingState):
            pass
    """
    return trace_operation(
        operation_name=f"agent.{agent_name}",
        operation_type="agent"
    )


def trace_service(service_name: str) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """
    Trace service layer operation.

    Usage:
        @trace_service("EVFService")
        async def create_evf(self, data: EVFCreate):
            pass
    """
    return trace_operation(
        operation_name=f"service.{service_name}",
        operation_type="service"
    )


def trace_repository(repo_name: str) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """
    Trace repository/data access operation.

    Usage:
        @trace_repository("EVFRepository")
        async def get_by_id(self, evf_id: str):
            pass
    """
    return trace_operation(
        operation_name=f"repository.{repo_name}",
        operation_type="repository"
    )


def trace_background_task(task_name: str) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """
    Trace background task execution.

    Usage:
        @trace_background_task("process_evf_async")
        async def process_evf_task(evf_id: str):
            pass
    """
    return trace_operation(
        operation_name=f"task.{task_name}",
        operation_type="background_task"
    )


# Example usage patterns
if __name__ == "__main__":
    # Example 1: Basic setup
    config = TracingConfig(
        service_name="evf-backend",
        environment="development",
        enable_console_export=True
    )
    tracing = setup_tracing(config)

    # Example 2: Custom traced function
    @trace_operation("example_operation", operation_type="example")
    async def example_function():
        set_tenant_context("tenant-123")
        add_span_event("processing_started")
        # Do work...
        add_span_attributes({"result": "success", "items_processed": 42})
        return "done"

    # Example 3: Agent tracing
    @trace_agent("ExampleAgent")
    async def process_with_agent(data: dict):
        add_span_event("agent_initialized")
        # Agent logic...
        return {"status": "completed"}
