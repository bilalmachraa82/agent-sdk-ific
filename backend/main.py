"""
EVF Portugal 2030 - Main FastAPI Application
Multi-tenant B2B SaaS for PT2030/IFIC funding automation
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

from backend.core.config import settings
from backend.core.database import db_manager, initialize_database, close_database
from backend.core.tracing import setup_tracing, TracingConfig
from backend.core.metrics import get_metrics
from backend.core.middleware import (
    TenantMiddleware,
    RateLimitMiddleware,
    AuditMiddleware,
    SecurityHeadersMiddleware
)
from backend.api.routers import auth, evf, admin, health, files
from backend.core.logging import setup_logging

# Setup structured logging
logger = setup_logging(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """
    Manage application lifecycle events.
    Initialize resources on startup, cleanup on shutdown.
    """
    # Startup
    logger.info("Starting EVF Portugal 2030 Backend",
                environment=settings.environment,
                version=settings.app_version)

    # Initialize OpenTelemetry tracing
    tracing_config = TracingConfig(
        service_name=settings.app_name,
        service_version=settings.app_version,
        environment=settings.environment,
        enable_console_export=(settings.environment == "development")
    )
    tracing_manager = setup_tracing(tracing_config)
    logger.info("OpenTelemetry tracing initialized")

    # Initialize database connection pool
    await initialize_database()
    logger.info("Database connection pool initialized")

    # Instrument FastAPI for automatic tracing
    tracing_manager.instrument_fastapi(app)
    tracing_manager.instrument_redis()
    tracing_manager.instrument_httpx()
    logger.info("Framework instrumentation complete")

    # Initialize vector store connection
    # await qdrant_service.initialize()

    # Warm up ML models if needed
    # await narrative_agent.warm_up()

    yield

    # Shutdown
    logger.info("Shutting down EVF Portugal 2030 Backend")
    await close_database()
    tracing_manager.shutdown()


# Create FastAPI application
app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description=settings.api_description,
    docs_url="/api/docs" if settings.environment != "production" else None,
    redoc_url="/api/redoc" if settings.environment != "production" else None,
    openapi_url="/api/openapi.json" if settings.environment != "production" else None,
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.api_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Total-Count", "X-Request-ID"],
)

# IMPORTANT: Middleware order follows OWASP 2025 recommendations
# Execution order: last added = first executed (stack pattern)
# So we add in REVERSE order: Headers → Rate Limit → Audit → Tenant

# 4. Add security headers (outermost - applies to all responses)
app.add_middleware(SecurityHeadersMiddleware)

# 3. Add rate limiting (requires Redis - will add later)
# app.add_middleware(
#     RateLimitMiddleware,
#     redis_client=redis_client  # TODO: Initialize Redis client
# )

# 2. Add audit logging (after tenant context is set)
app.add_middleware(
    AuditMiddleware,
    db_session_factory=lambda: db_manager.get_db_context()
)

# 1. Add tenant isolation (innermost - must run first to set context)
app.add_middleware(TenantMiddleware)

# Include routers
app.include_router(
    health.router,
    prefix="/api",
    tags=["health"]
)

app.include_router(
    auth.router,
    prefix="/api/v1/auth",
    tags=["authentication"]
)

app.include_router(
    evf.router,
    prefix="/api/v1/evf",
    tags=["evf"]
)

app.include_router(
    files.router,
    prefix="/api/v1/files",
    tags=["files"]
)

app.include_router(
    admin.router,
    prefix="/api/v1/admin",
    tags=["admin"]
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Handle all unhandled exceptions globally.
    Log the error and return a generic error response.
    """
    logger.error(
        "Unhandled exception",
        exc_info=exc,
        path=request.url.path,
        method=request.method,
        tenant_id=getattr(request.state, "tenant_id", None)
    )

    if settings.environment == "production":
        # Don't expose internal errors in production
        return JSONResponse(
            status_code=500,
            content={
                "detail": "An internal error occurred. Please try again later.",
                "error_id": getattr(request.state, "request_id", "unknown")
            }
        )
    else:
        # Show detailed error in development
        return JSONResponse(
            status_code=500,
            content={
                "detail": str(exc),
                "type": type(exc).__name__,
                "error_id": getattr(request.state, "request_id", "unknown")
            }
        )


@app.get("/")
async def root():
    """Root endpoint - API information."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "operational",
        "environment": settings.environment,
        "docs": "/api/docs" if settings.environment != "production" else "disabled",
        "health": "/api/health",
        "metrics": "/metrics"
    }


@app.get("/metrics")
async def metrics():
    """
    Prometheus metrics endpoint.

    Exposes metrics in Prometheus text format for scraping.

    Metrics include:
    - HTTP request metrics (count, duration, in-progress)
    - Authentication metrics (attempts, duration, algorithm usage)
    - RLS enforcement metrics (checks, violations, overhead)
    - Database metrics (query duration, connections)
    - EVF processing metrics (duration, operations, errors)
    - AI agent metrics (executions, token usage, cost)
    - Security events (RLS violations, rate limits)

    Returns:
        Prometheus metrics in text format
    """
    data, content_type = get_metrics()
    return Response(content=data, media_type=content_type)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.environment == "development",
        workers=1 if settings.environment == "development" else 4,
        log_level=settings.log_level.lower(),
        access_log=settings.environment != "production",
    )