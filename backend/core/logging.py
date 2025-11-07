"""
Structured logging configuration for EVF Portugal 2030
Uses structlog for JSON structured logging
"""

import logging
import sys
from typing import Any, Dict

import structlog
from structlog.processors import CallsiteParameter, CallsiteParameterAdder

from backend.core.config import settings


def setup_logging(module_name: str) -> structlog.BoundLogger:
    """
    Configure structured logging for the application.

    Args:
        module_name: Name of the module requesting logger

    Returns:
        Configured structlog logger
    """

    # Configure structlog processors
    processors = [
        # Add timestamp
        structlog.processors.TimeStamper(fmt="iso"),

        # Add log level
        structlog.stdlib.add_log_level,

        # Add logger name
        structlog.stdlib.add_logger_name,

        # Add call site info in development
        CallsiteParameterAdder(
            parameters=[
                CallsiteParameter.FILENAME,
                CallsiteParameter.FUNC_NAME,
                CallsiteParameter.LINENO,
            ]
        ) if settings.ENVIRONMENT == "development" else lambda _, __, event_dict: event_dict,

        # Format stack traces
        structlog.processors.format_exc_info,

        # Render as JSON in production, console in development
        structlog.processors.JSONRenderer() if settings.ENVIRONMENT == "production"
        else structlog.dev.ConsoleRenderer(colors=True)
    ]

    # Configure Python's logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.LOG_LEVEL),
    )

    # Configure structlog
    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Return logger for module
    return structlog.get_logger(module_name)


def log_event(
    logger: structlog.BoundLogger,
    event: str,
    level: str = "info",
    **kwargs: Any
) -> None:
    """
    Log an event with structured data.

    Args:
        logger: The logger instance
        event: Event description
        level: Log level (debug, info, warning, error, critical)
        **kwargs: Additional structured data to log
    """

    # Add common context
    context = {
        "environment": settings.ENVIRONMENT,
        "service": "evf-backend",
        **kwargs
    }

    # Log at appropriate level
    getattr(logger, level)(event, **context)


def create_audit_log(
    action: str,
    entity_type: str,
    entity_id: str,
    tenant_id: str,
    user_id: str,
    metadata: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Create an audit log entry.

    Args:
        action: The action performed (CREATE, UPDATE, DELETE, etc.)
        entity_type: Type of entity affected (evf, user, tenant, etc.)
        entity_id: ID of the affected entity
        tenant_id: Tenant performing the action
        user_id: User performing the action
        metadata: Additional metadata about the action

    Returns:
        Audit log entry dict
    """

    return {
        "action": action,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "tenant_id": tenant_id,
        "user_id": user_id,
        "metadata": metadata or {},
        "timestamp": structlog.processors.TimeStamper(fmt="iso")(None, None, {})["timestamp"]
    }


# Performance logging decorator
def log_performance(logger: structlog.BoundLogger):
    """
    Decorator to log function performance.

    Args:
        logger: Logger instance to use
    """
    import functools
    import time
    from typing import Callable

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()

            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time

                logger.info(
                    "Function executed",
                    function=func.__name__,
                    duration_seconds=duration,
                    status="success"
                )

                return result

            except Exception as e:
                duration = time.time() - start_time

                logger.error(
                    "Function failed",
                    function=func.__name__,
                    duration_seconds=duration,
                    status="error",
                    error=str(e)
                )

                raise

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()

            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time

                logger.info(
                    "Function executed",
                    function=func.__name__,
                    duration_seconds=duration,
                    status="success"
                )

                return result

            except Exception as e:
                duration = time.time() - start_time

                logger.error(
                    "Function failed",
                    function=func.__name__,
                    duration_seconds=duration,
                    status="error",
                    error=str(e)
                )

                raise

        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


import asyncio