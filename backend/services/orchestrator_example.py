"""
Example usage of EVF Agent Orchestrator

Demonstrates how to use the orchestrator in API endpoints and background tasks.
"""

import asyncio
from uuid import UUID
from fastapi import BackgroundTasks, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.services.orchestrator import (
    EVFOrchestrator,
    OrchestratorConfig,
    ProcessingStatus,
)
from backend.services.cache_service import CacheService


# ===== Example 1: Simple Processing =====

async def process_evf_simple(
    project_id: UUID,
    tenant_id: UUID,
    session: AsyncSession
):
    """
    Simple EVF processing with default configuration.

    Use this for synchronous processing (user waits for result).
    """
    # Create orchestrator
    orchestrator = EVFOrchestrator()

    # Process EVF
    result = await orchestrator.process_evf(
        project_id=project_id,
        tenant_id=tenant_id,
        session=session
    )

    # Check result
    if result.status == ProcessingStatus.COMPLETED:
        print(f"✅ Processing completed successfully!")
        print(f"   VALF: {result.valf}")
        print(f"   TRF: {result.trf}%")
        print(f"   PT2030 Compliant: {result.pt2030_compliant}")
        print(f"   Duration: {result.processing_duration_seconds}s")
        print(f"   Cost: €{result.total_cost_euros}")
    else:
        print(f"❌ Processing failed: {result.errors}")

    return result


# ===== Example 2: Custom Configuration =====

async def process_evf_custom_config(
    project_id: UUID,
    tenant_id: UUID,
    session: AsyncSession
):
    """
    EVF processing with custom configuration.

    Use this when you need specific retry logic or cost limits.
    """
    # Custom configuration
    config = OrchestratorConfig(
        max_retries=5,  # More retries for critical projects
        retry_delay_seconds=10,  # Longer delay between retries
        timeout_seconds=600,  # 10 minute timeout
        cost_limit_euros=10.00,  # Higher cost limit
        enable_caching=True,  # Enable result caching
    )

    # Create orchestrator with config
    orchestrator = EVFOrchestrator(config=config)

    # Process
    result = await orchestrator.process_evf(
        project_id=project_id,
        tenant_id=tenant_id,
        session=session
    )

    return result


# ===== Example 3: Background Processing with Progress Tracking =====

async def process_evf_background(
    project_id: UUID,
    tenant_id: UUID,
    background_tasks: BackgroundTasks,
    session: AsyncSession
):
    """
    Start EVF processing in background and return immediately.

    Use this for async processing (user can poll for status).
    """
    # Create orchestrator
    orchestrator = EVFOrchestrator()

    # Define background task
    async def background_process():
        async with get_db() as bg_session:
            try:
                result = await orchestrator.process_evf(
                    project_id=project_id,
                    tenant_id=tenant_id,
                    session=bg_session
                )
                print(f"Background processing completed: {result.status}")
            except Exception as e:
                print(f"Background processing failed: {e}")

    # Add to background tasks
    background_tasks.add_task(background_process)

    return {
        "message": "Processing started",
        "project_id": str(project_id),
        "status": "in_progress"
    }


async def get_evf_status(
    project_id: UUID,
    session: AsyncSession
):
    """
    Get current processing status.

    Use this to poll for status during background processing.
    """
    orchestrator = EVFOrchestrator()

    try:
        status = await orchestrator.get_processing_status(
            project_id=project_id,
            session=session
        )

        return {
            "project_id": str(status.project_id),
            "status": status.status,
            "current_step": status.current_step,
            "progress_percentage": status.progress_percentage,
            "current_agent": status.current_agent,
            "estimated_completion": status.estimated_completion_at,
            "error_message": status.error_message,
        }
    except ValueError:
        raise HTTPException(
            status_code=404,
            detail=f"Project {project_id} not found or not processing"
        )


# ===== Example 4: Processing with Cancellation =====

async def process_evf_with_cancel(
    project_id: UUID,
    tenant_id: UUID,
    session: AsyncSession,
    timeout_seconds: int = 300
):
    """
    Process EVF with automatic cancellation after timeout.

    Use this to prevent runaway processing.
    """
    orchestrator = EVFOrchestrator()

    # Start processing
    task = asyncio.create_task(
        orchestrator.process_evf(
            project_id=project_id,
            tenant_id=tenant_id,
            session=session
        )
    )

    try:
        # Wait for completion or timeout
        result = await asyncio.wait_for(task, timeout=timeout_seconds)
        return result

    except asyncio.TimeoutError:
        # Cancel on timeout
        print(f"Processing timeout, cancelling...")
        await orchestrator.cancel_processing(project_id, session)
        raise HTTPException(
            status_code=408,
            detail=f"Processing timeout after {timeout_seconds}s"
        )


# ===== Example 5: Batch Processing =====

async def process_multiple_evfs(
    project_ids: list[UUID],
    tenant_id: UUID,
    session: AsyncSession,
    max_concurrent: int = 3
):
    """
    Process multiple EVF projects concurrently.

    Use this for batch operations (e.g., monthly processing).
    """
    orchestrator = EVFOrchestrator()

    # Create semaphore to limit concurrency
    semaphore = asyncio.Semaphore(max_concurrent)

    async def process_one(project_id: UUID):
        async with semaphore:
            try:
                result = await orchestrator.process_evf(
                    project_id=project_id,
                    tenant_id=tenant_id,
                    session=session
                )
                return {
                    "project_id": str(project_id),
                    "status": "success",
                    "valf": result.valf,
                    "trf": result.trf,
                }
            except Exception as e:
                return {
                    "project_id": str(project_id),
                    "status": "failed",
                    "error": str(e)
                }

    # Process all projects concurrently
    tasks = [process_one(pid) for pid in project_ids]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Summarize results
    successful = sum(1 for r in results if isinstance(r, dict) and r["status"] == "success")
    failed = len(results) - successful

    return {
        "total": len(project_ids),
        "successful": successful,
        "failed": failed,
        "results": results
    }


# ===== Example 6: Processing with Real-time Updates (WebSocket) =====

async def process_evf_with_websocket(
    project_id: UUID,
    tenant_id: UUID,
    session: AsyncSession,
    websocket  # WebSocket connection
):
    """
    Process EVF with real-time progress updates via WebSocket.

    Use this for real-time UI updates.
    """
    orchestrator = EVFOrchestrator()

    # Monkey-patch progress updates to send via WebSocket
    original_update = orchestrator._update_progress

    async def websocket_update(progress, step, percentage):
        # Send update via WebSocket
        await websocket.send_json({
            "type": "progress",
            "step": step,
            "percentage": percentage,
            "current_agent": progress.current_agent,
        })

        # Call original update
        await original_update(progress, step, percentage)

    orchestrator._update_progress = websocket_update

    try:
        # Start processing
        await websocket.send_json({
            "type": "started",
            "project_id": str(project_id)
        })

        result = await orchestrator.process_evf(
            project_id=project_id,
            tenant_id=tenant_id,
            session=session
        )

        # Send completion
        await websocket.send_json({
            "type": "completed",
            "status": result.status,
            "valf": float(result.valf) if result.valf else None,
            "trf": float(result.trf) if result.trf else None,
            "compliant": result.pt2030_compliant,
        })

        return result

    except Exception as e:
        # Send error
        await websocket.send_json({
            "type": "error",
            "message": str(e)
        })
        raise


# ===== Example 7: Processing with Result Caching =====

async def process_evf_cached(
    project_id: UUID,
    tenant_id: UUID,
    session: AsyncSession,
    cache_service: CacheService
):
    """
    Process EVF with result caching for repeated calculations.

    Use this when the same project might be reprocessed with same inputs.
    """
    # Check cache first
    cache_key = f"evf_result:{project_id}"
    cached_result = await cache_service.get(cache_key)

    if cached_result:
        print("✅ Using cached result")
        return cached_result

    # Process if not cached
    config = OrchestratorConfig(enable_caching=True)
    orchestrator = EVFOrchestrator(config=config, cache_service=cache_service)

    result = await orchestrator.process_evf(
        project_id=project_id,
        tenant_id=tenant_id,
        session=session
    )

    # Cache result for 1 hour
    await cache_service.set(
        cache_key,
        result.model_dump(),
        ttl_seconds=3600
    )

    return result


# ===== Example 8: FastAPI Endpoint Integration =====

from fastapi import APIRouter, Depends, BackgroundTasks
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/evf", tags=["EVF Processing"])


class ProcessEVFRequest(BaseModel):
    project_id: UUID


class ProcessEVFResponse(BaseModel):
    message: str
    project_id: str
    status: str


@router.post("/process", response_model=ProcessEVFResponse)
async def process_evf_endpoint(
    request: ProcessEVFRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_db),
    # tenant_id: UUID = Depends(get_current_tenant),  # From auth middleware
):
    """
    Start EVF processing for a project.

    Returns immediately with processing status.
    Use GET /status/{project_id} to poll for completion.
    """
    tenant_id = UUID("00000000-0000-0000-0000-000000000001")  # Mock for example

    # Validate project exists
    from backend.models.evf import EVFProject
    project = await session.get(EVFProject, request.project_id)
    if not project or project.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Project not found")

    # Start processing in background
    orchestrator = EVFOrchestrator()

    async def background_process():
        async for bg_session in get_db():
            try:
                await orchestrator.process_evf(
                    project_id=request.project_id,
                    tenant_id=tenant_id,
                    session=bg_session
                )
            except Exception as e:
                print(f"Background processing error: {e}")

    background_tasks.add_task(background_process)

    return ProcessEVFResponse(
        message="Processing started",
        project_id=str(request.project_id),
        status="in_progress"
    )


@router.get("/status/{project_id}")
async def get_processing_status_endpoint(
    project_id: UUID,
    session: AsyncSession = Depends(get_db),
):
    """Get current processing status for a project."""
    return await get_evf_status(project_id, session)


@router.post("/cancel/{project_id}")
async def cancel_processing_endpoint(
    project_id: UUID,
    session: AsyncSession = Depends(get_db),
):
    """Cancel ongoing processing for a project."""
    orchestrator = EVFOrchestrator()
    cancelled = await orchestrator.cancel_processing(project_id, session)

    if cancelled:
        return {"message": "Processing cancelled", "project_id": str(project_id)}
    else:
        raise HTTPException(
            status_code=404,
            detail="Project not found or not currently processing"
        )


# ===== Main Example Runner =====

async def main():
    """Run examples."""
    from uuid import uuid4
    from backend.core.database import initialize_database

    # Initialize database
    await initialize_database()

    # Mock IDs for demonstration
    project_id = uuid4()
    tenant_id = uuid4()

    print("EVF Orchestrator Examples")
    print("=" * 50)

    # Note: These examples require proper database setup
    # See test_orchestrator.py for runnable tests

    print("\n✅ Examples loaded successfully!")
    print("\nAvailable examples:")
    print("  1. process_evf_simple() - Simple processing")
    print("  2. process_evf_custom_config() - Custom configuration")
    print("  3. process_evf_background() - Background processing")
    print("  4. get_evf_status() - Status polling")
    print("  5. process_evf_with_cancel() - Processing with cancellation")
    print("  6. process_multiple_evfs() - Batch processing")
    print("  7. process_evf_with_websocket() - Real-time updates")
    print("  8. process_evf_cached() - With caching")
    print("\nSee test_orchestrator.py for runnable tests.")


if __name__ == "__main__":
    asyncio.run(main())
