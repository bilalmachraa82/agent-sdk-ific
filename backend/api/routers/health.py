"""
Health check endpoints for monitoring and status
"""

from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from backend.core.database import get_db
from backend.core.config import settings
from backend.core.logging import setup_logging

router = APIRouter()
logger = setup_logging(__name__)


@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """
    Basic health check endpoint.
    Returns service status and version information.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.app_version,
        "environment": settings.environment,
        "service": "evf-backend"
    }


@router.get("/health/ready")
async def readiness_check(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """
    Readiness probe for Kubernetes.
    Checks if the service is ready to accept traffic.
    """
    checks = {
        "database": False,
        "cache": False,
        "vector_store": False
    }

    errors = []

    # Check database connection
    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = True
    except Exception as e:
        logger.error("Database health check failed", error=str(e))
        errors.append(f"Database: {str(e)}")

    # Check Redis connection (if configured)
    if settings.redis_url:
        try:
            # TODO: Implement Redis health check
            checks["cache"] = True
        except Exception as e:
            logger.error("Redis health check failed", error=str(e))
            errors.append(f"Redis: {str(e)}")

    # Check Qdrant connection (if configured)
    if settings.qdrant_url:
        try:
            # TODO: Implement Qdrant health check
            checks["vector_store"] = True
        except Exception as e:
            logger.error("Qdrant health check failed", error=str(e))
            errors.append(f"Qdrant: {str(e)}")

    # Determine overall status
    all_healthy = all(checks.values())
    status_code = 200 if all_healthy else 503

    return {
        "status": "ready" if all_healthy else "not_ready",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": checks,
        "errors": errors if errors else None
    }


@router.get("/health/live")
async def liveness_check() -> Dict[str, Any]:
    """
    Liveness probe for Kubernetes.
    Simple check to verify the service is alive.
    """
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/health/metrics")
async def health_metrics(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """
    Return basic metrics about the system.
    """
    metrics = {}

    # Get database metrics
    try:
        # Count EVFs
        result = await db.execute(
            text("SELECT COUNT(*) as count FROM evf_projects WHERE deleted_at IS NULL")
        )
        evf_count = result.scalar() or 0
        metrics["total_evfs"] = evf_count

        # Count active tenants
        result = await db.execute(
            text("SELECT COUNT(DISTINCT tenant_id) as count FROM evf_projects WHERE deleted_at IS NULL")
        )
        tenant_count = result.scalar() or 0
        metrics["active_tenants"] = tenant_count

    except Exception as e:
        logger.error("Failed to collect metrics", error=str(e))
        metrics["error"] = "Failed to collect metrics"

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "metrics": metrics,
        "version": settings.app_version,
        "environment": settings.environment
    }