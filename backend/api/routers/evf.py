"""
EVF project management endpoints
Handles creation, processing, and management of EVF projects
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.core.database import get_db
from backend.api.routers.auth import get_current_active_user
from backend.models.tenant import User
from backend.models.evf import EVFProject, EVFStatus
from backend.core.logging import setup_logging

router = APIRouter()
logger = setup_logging(__name__)


@router.get("/projects")
async def list_evf_projects(
    skip: int = 0,
    limit: int = 100,
    status: Optional[EVFStatus] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List all EVF projects for the current tenant.
    """
    query = select(EVFProject).where(
        EVFProject.tenant_id == current_user.tenant_id,
        EVFProject.deleted_at.is_(None)
    )

    if status:
        query = query.where(EVFProject.status == status)

    query = query.offset(skip).limit(limit).order_by(EVFProject.created_at.desc())

    result = await db.execute(query)
    projects = result.scalars().all()

    return projects


@router.get("/projects/{project_id}")
async def get_evf_project(
    project_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific EVF project by ID.
    """
    result = await db.execute(
        select(EVFProject).where(
            EVFProject.id == project_id,
            EVFProject.tenant_id == current_user.tenant_id,
            EVFProject.deleted_at.is_(None)
        )
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    return project


@router.post("/projects")
async def create_evf_project(
    name: str,
    description: Optional[str] = None,
    fund_type: str = "PT2030",
    company_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new EVF project.
    """
    project = EVFProject(
        name=name,
        description=description,
        fund_type=fund_type,
        company_id=company_id,
        tenant_id=current_user.tenant_id,
        created_by=current_user.id,
        status=EVFStatus.DRAFT
    )

    db.add(project)
    await db.commit()
    await db.refresh(project)

    logger.info(
        "EVF project created",
        project_id=str(project.id),
        tenant_id=str(current_user.tenant_id),
        user_id=str(current_user.id)
    )

    return project


@router.post("/projects/{project_id}/upload")
async def upload_saft_file(
    project_id: UUID,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload SAF-T file for processing.
    """
    # Get project
    result = await db.execute(
        select(EVFProject).where(
            EVFProject.id == project_id,
            EVFProject.tenant_id == current_user.tenant_id,
            EVFProject.deleted_at.is_(None)
        )
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    # Validate file
    if not file.filename.endswith('.xml'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only SAF-T XML files are accepted"
        )

    # TODO: Save file to secure storage
    # TODO: Calculate file hash
    # TODO: Trigger background processing

    project.status = EVFStatus.UPLOADING
    await db.commit()

    logger.info(
        "SAF-T file uploaded",
        project_id=str(project_id),
        filename=file.filename,
        size=file.size
    )

    return {
        "message": "File uploaded successfully",
        "project_id": project_id,
        "filename": file.filename,
        "status": project.status
    }


@router.post("/projects/{project_id}/process")
async def process_evf_project(
    project_id: UUID,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Start processing an EVF project.
    """
    # Get project
    result = await db.execute(
        select(EVFProject).where(
            EVFProject.id == project_id,
            EVFProject.tenant_id == current_user.tenant_id,
            EVFProject.deleted_at.is_(None)
        )
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    if not project.saft_file_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="SAF-T file must be uploaded before processing"
        )

    # TODO: Add background task to orchestrate agents
    # background_tasks.add_task(orchestrate_evf_processing, project_id)

    project.status = EVFStatus.PROCESSING
    await db.commit()

    logger.info(
        "EVF processing started",
        project_id=str(project_id),
        tenant_id=str(current_user.tenant_id)
    )

    return {
        "message": "Processing started",
        "project_id": project_id,
        "status": project.status
    }


@router.delete("/projects/{project_id}")
async def delete_evf_project(
    project_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Soft delete an EVF project.
    """
    # Get project
    result = await db.execute(
        select(EVFProject).where(
            EVFProject.id == project_id,
            EVFProject.tenant_id == current_user.tenant_id,
            EVFProject.deleted_at.is_(None)
        )
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    # Soft delete
    from datetime import datetime
    project.deleted_at = datetime.utcnow()
    await db.commit()

    logger.info(
        "EVF project deleted",
        project_id=str(project_id),
        tenant_id=str(current_user.tenant_id)
    )

    return {"message": "Project deleted successfully"}