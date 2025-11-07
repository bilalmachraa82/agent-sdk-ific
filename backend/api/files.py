"""
File upload/download API endpoints for EVF Portugal 2030.
Handles SAF-T XML, Excel, PDF file operations with encryption and multi-tenant isolation.
"""

from datetime import datetime
from uuid import UUID
from typing import Optional, List
import logging

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status, Query
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from backend.core.database import get_db
from backend.core.tenant import get_current_tenant, get_current_user
from backend.models.file import File as FileModel, FileAccessLog
from backend.services.file_storage import (
    file_storage_service,
    FileMetadata,
    FileType,
    FileSizeLimitError,
    FileTypeNotAllowedError,
    FileStorageError,
)
from backend.schemas.file import (
    FileUploadResponse,
    FileListResponse,
    FileDetailResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/files", tags=["files"])


@router.post("/upload", response_model=FileUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(..., description="File to upload"),
    file_type: str = Query(..., description="Type of file (saft, excel, pdf, csv, json)"),
    description: Optional[str] = Query(None, description="Optional file description"),
    project_id: Optional[str] = Query(None, description="Associated EVF project ID"),
    tenant_id: UUID = Depends(get_current_tenant),
    user_id: UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload and encrypt a file.

    - **file**: File to upload (multipart/form-data)
    - **file_type**: Type of file (saft, excel, pdf, csv, json)
    - **description**: Optional description
    - **project_id**: Optional associated EVF project ID

    Returns file metadata including ID, hash, and storage location.
    """
    try:
        logger.info(
            f"Upload request: tenant={tenant_id}, user={user_id}, "
            f"file={file.filename}, type={file_type}"
        )

        # Prepare additional metadata
        additional_metadata = {}
        if description:
            additional_metadata["description"] = description
        if project_id:
            additional_metadata["project_id"] = project_id

        # Upload to storage
        metadata = await file_storage_service.upload_file(
            tenant_id=tenant_id,
            file=file,
            file_type=file_type,
            user_id=user_id,
            additional_metadata=additional_metadata,
        )

        # Save metadata to database
        db_file = FileModel(
            id=metadata.id,
            tenant_id=tenant_id,
            file_name=metadata.file_name,
            file_type=metadata.file_type.value,
            file_extension=metadata.file_extension,
            mime_type=metadata.mime_type,
            file_size_bytes=metadata.file_size_bytes,
            encrypted_size_bytes=metadata.encrypted_size_bytes,
            sha256_hash=metadata.sha256_hash,
            storage_path=metadata.storage_path,
            storage_backend=metadata.storage_backend.value,
            is_encrypted=metadata.is_encrypted,
            uploaded_by_user_id=user_id,
            custom_metadata=metadata.metadata,
        )
        db.add(db_file)

        # Log file access
        access_log = FileAccessLog(
            tenant_id=tenant_id,
            file_id=metadata.id,
            access_type="upload",
            user_id=user_id,
            success=True,
        )
        db.add(access_log)

        await db.commit()

        logger.info(f"File uploaded successfully: {metadata.id}")

        return FileUploadResponse(
            file_id=metadata.id,
            file_name=metadata.file_name,
            file_type=metadata.file_type.value,
            file_size_bytes=metadata.file_size_bytes,
            sha256_hash=metadata.sha256_hash,
            upload_timestamp=metadata.upload_timestamp,
        )

    except FileSizeLimitError as e:
        logger.warning(f"File size limit exceeded: {e}")
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=str(e),
        )
    except FileTypeNotAllowedError as e:
        logger.warning(f"Invalid file type: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except FileStorageError as e:
        logger.error(f"File storage error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to store file. Please try again.",
        )
    except Exception as e:
        logger.error(f"Unexpected error during file upload: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred.",
        )


@router.get("/", response_model=FileListResponse)
async def list_files(
    file_type: Optional[str] = Query(None, description="Filter by file type"),
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Number of records to return"),
    tenant_id: UUID = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    List all files for the current tenant.

    - **file_type**: Optional filter by file type (saft, excel, pdf, etc.)
    - **project_id**: Optional filter by project ID
    - **skip**: Pagination offset
    - **limit**: Number of results (max 100)

    Returns list of files with metadata.
    """
    try:
        # Build query
        query = select(FileModel).where(
            and_(
                FileModel.tenant_id == tenant_id,
                FileModel.is_deleted == False,
            )
        )

        # Apply filters
        if file_type:
            query = query.where(FileModel.file_type == file_type)

        if project_id:
            query = query.where(
                FileModel.custom_metadata["project_id"].astext == project_id
            )

        # Get total count
        count_query = select(FileModel).where(
            and_(
                FileModel.tenant_id == tenant_id,
                FileModel.is_deleted == False,
            )
        )
        if file_type:
            count_query = count_query.where(FileModel.file_type == file_type)
        if project_id:
            count_query = count_query.where(
                FileModel.custom_metadata["project_id"].astext == project_id
            )

        result = await db.execute(count_query)
        total = len(result.scalars().all())

        # Apply pagination
        query = query.order_by(FileModel.created_at.desc()).offset(skip).limit(limit)

        # Execute query
        result = await db.execute(query)
        files = result.scalars().all()

        return FileListResponse(
            files=[
                FileDetailResponse(
                    id=f.id,
                    tenant_id=f.tenant_id,
                    file_name=f.file_name,
                    file_type=f.file_type,
                    file_size_bytes=f.file_size_bytes,
                    sha256_hash=f.sha256_hash,
                    upload_timestamp=f.upload_timestamp,
                    uploaded_by_user_id=f.uploaded_by_user_id,
                    access_count=f.access_count,
                    last_accessed_at=f.last_accessed_at,
                    metadata=f.custom_metadata or {},
                )
                for f in files
            ],
            total=total,
            skip=skip,
            limit=limit,
        )

    except Exception as e:
        logger.error(f"Error listing files: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve files.",
        )


@router.get("/{file_id}", response_model=FileDetailResponse)
async def get_file_metadata(
    file_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Get metadata for a specific file.

    Returns detailed file metadata including access statistics.
    """
    try:
        result = await db.execute(
            select(FileModel).where(
                and_(
                    FileModel.id == file_id,
                    FileModel.tenant_id == tenant_id,
                    FileModel.is_deleted == False,
                )
            )
        )
        file = result.scalar_one_or_none()

        if not file:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found",
            )

        return FileDetailResponse(
            id=file.id,
            tenant_id=file.tenant_id,
            file_name=file.file_name,
            file_type=file.file_type,
            file_size_bytes=file.file_size_bytes,
            sha256_hash=file.sha256_hash,
            upload_timestamp=file.upload_timestamp,
            uploaded_by_user_id=file.uploaded_by_user_id,
            access_count=file.access_count,
            last_accessed_at=file.last_accessed_at,
            metadata=file.custom_metadata or {},
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving file metadata: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve file metadata.",
        )


@router.get("/{file_id}/download")
async def download_file(
    file_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant),
    user_id: UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Download and decrypt a file.

    Returns the original file content with appropriate content-type header.
    """
    try:
        # Fetch file metadata from database
        result = await db.execute(
            select(FileModel).where(
                and_(
                    FileModel.id == file_id,
                    FileModel.tenant_id == tenant_id,
                    FileModel.is_deleted == False,
                )
            )
        )
        db_file = result.scalar_one_or_none()

        if not db_file:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found",
            )

        # Convert to FileMetadata
        metadata = FileMetadata(**db_file.to_metadata_dict())

        # Download content
        content = await file_storage_service.download_file(
            tenant_id=tenant_id,
            file_id=file_id,
            metadata=metadata,
        )

        # Update access tracking
        db_file.last_accessed_at = datetime.utcnow()
        db_file.access_count += 1

        # Log file access
        access_log = FileAccessLog(
            tenant_id=tenant_id,
            file_id=file_id,
            access_type="download",
            user_id=user_id,
            success=True,
        )
        db.add(access_log)

        await db.commit()

        logger.info(f"File downloaded: {file_id} by user {user_id}")

        return Response(
            content=content,
            media_type=metadata.mime_type,
            headers={
                "Content-Disposition": f'attachment; filename="{metadata.file_name}"',
                "X-File-SHA256": metadata.sha256_hash,
            },
        )

    except HTTPException:
        raise
    except PermissionError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this file",
        )
    except FileStorageError as e:
        logger.error(f"File download error: {e}")

        # Log failed access
        access_log = FileAccessLog(
            tenant_id=tenant_id,
            file_id=file_id,
            access_type="download",
            user_id=user_id,
            success=False,
            error_message=str(e),
        )
        db.add(access_log)
        await db.commit()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to download file. Please try again.",
        )
    except Exception as e:
        logger.error(f"Unexpected error during file download: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred.",
        )


@router.delete("/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_file(
    file_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant),
    user_id: UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a file (soft delete).

    Marks the file as deleted in the database and removes it from storage.
    """
    try:
        # Fetch file metadata
        result = await db.execute(
            select(FileModel).where(
                and_(
                    FileModel.id == file_id,
                    FileModel.tenant_id == tenant_id,
                    FileModel.is_deleted == False,
                )
            )
        )
        db_file = result.scalar_one_or_none()

        if not db_file:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found",
            )

        # Convert to FileMetadata
        metadata = FileMetadata(**db_file.to_metadata_dict())

        # Delete from storage
        await file_storage_service.delete_file(
            tenant_id=tenant_id,
            file_id=file_id,
            metadata=metadata,
        )

        # Soft delete in database
        db_file.is_deleted = True
        db_file.deleted_at = datetime.utcnow()
        db_file.deleted_by_user_id = user_id

        # Log file deletion
        access_log = FileAccessLog(
            tenant_id=tenant_id,
            file_id=file_id,
            access_type="delete",
            user_id=user_id,
            success=True,
        )
        db.add(access_log)

        await db.commit()

        logger.info(f"File deleted: {file_id} by user {user_id}")

        return None  # 204 No Content

    except HTTPException:
        raise
    except PermissionError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to delete this file",
        )
    except FileStorageError as e:
        logger.error(f"File deletion error: {e}")

        # Log failed deletion
        access_log = FileAccessLog(
            tenant_id=tenant_id,
            file_id=file_id,
            access_type="delete",
            user_id=user_id,
            success=False,
            error_message=str(e),
        )
        db.add(access_log)
        await db.commit()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete file. Please try again.",
        )
    except Exception as e:
        logger.error(f"Unexpected error during file deletion: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred.",
        )
