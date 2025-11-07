"""
Pydantic schemas for file upload/download operations.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field, validator


class FileUploadResponse(BaseModel):
    """Response schema for file upload."""

    file_id: UUID = Field(..., description="Unique file identifier")
    file_name: str = Field(..., description="Original file name")
    file_type: str = Field(..., description="File type (saft, excel, pdf, etc.)")
    file_size_bytes: int = Field(..., description="File size in bytes")
    sha256_hash: str = Field(..., description="SHA-256 hash for integrity")
    upload_timestamp: datetime = Field(..., description="When file was uploaded")

    class Config:
        json_schema_extra = {
            "example": {
                "file_id": "550e8400-e29b-41d4-a716-446655440000",
                "file_name": "company_saft_2024.xml",
                "file_type": "saft",
                "file_size_bytes": 1048576,
                "sha256_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                "upload_timestamp": "2024-11-07T10:30:00Z",
            }
        }


class FileDetailResponse(BaseModel):
    """Detailed file metadata response."""

    id: UUID = Field(..., description="Unique file identifier")
    tenant_id: UUID = Field(..., description="Tenant owning this file")
    file_name: str = Field(..., description="Original file name")
    file_type: str = Field(..., description="File type")
    file_size_bytes: int = Field(..., description="File size in bytes")
    sha256_hash: str = Field(..., description="SHA-256 hash")
    upload_timestamp: datetime = Field(..., description="Upload timestamp")
    uploaded_by_user_id: Optional[UUID] = Field(None, description="User who uploaded")
    access_count: int = Field(default=0, description="Number of downloads")
    last_accessed_at: Optional[datetime] = Field(None, description="Last download time")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "tenant_id": "660e8400-e29b-41d4-a716-446655440000",
                "file_name": "company_saft_2024.xml",
                "file_type": "saft",
                "file_size_bytes": 1048576,
                "sha256_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                "upload_timestamp": "2024-11-07T10:30:00Z",
                "uploaded_by_user_id": "770e8400-e29b-41d4-a716-446655440000",
                "access_count": 5,
                "last_accessed_at": "2024-11-07T15:45:00Z",
                "metadata": {
                    "project_id": "proj_123",
                    "description": "Annual SAF-T file",
                },
            }
        }


class FileListResponse(BaseModel):
    """Response schema for file listing."""

    files: List[FileDetailResponse] = Field(..., description="List of files")
    total: int = Field(..., description="Total number of files")
    skip: int = Field(..., description="Number of records skipped")
    limit: int = Field(..., description="Number of records returned")

    class Config:
        json_schema_extra = {
            "example": {
                "files": [
                    {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "tenant_id": "660e8400-e29b-41d4-a716-446655440000",
                        "file_name": "company_saft_2024.xml",
                        "file_type": "saft",
                        "file_size_bytes": 1048576,
                        "sha256_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                        "upload_timestamp": "2024-11-07T10:30:00Z",
                        "uploaded_by_user_id": "770e8400-e29b-41d4-a716-446655440000",
                        "access_count": 5,
                        "last_accessed_at": "2024-11-07T15:45:00Z",
                        "metadata": {"project_id": "proj_123"},
                    }
                ],
                "total": 42,
                "skip": 0,
                "limit": 50,
            }
        }


class FileAccessLogResponse(BaseModel):
    """File access log entry."""

    id: UUID = Field(..., description="Log entry ID")
    file_id: UUID = Field(..., description="File that was accessed")
    access_type: str = Field(..., description="Type of access (upload, download, delete)")
    user_id: Optional[UUID] = Field(None, description="User who accessed the file")
    success: bool = Field(..., description="Whether access was successful")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    access_timestamp: datetime = Field(..., description="When access occurred")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "880e8400-e29b-41d4-a716-446655440000",
                "file_id": "550e8400-e29b-41d4-a716-446655440000",
                "access_type": "download",
                "user_id": "770e8400-e29b-41d4-a716-446655440000",
                "success": True,
                "error_message": None,
                "access_timestamp": "2024-11-07T15:45:00Z",
            }
        }


class FileUploadRequest(BaseModel):
    """Request schema for file upload metadata."""

    file_type: str = Field(..., description="Type of file (saft, excel, pdf, csv, json)")
    description: Optional[str] = Field(None, max_length=500, description="File description")
    project_id: Optional[str] = Field(None, description="Associated EVF project ID")

    @validator("file_type")
    def validate_file_type(cls, v):
        """Validate file type is allowed."""
        allowed_types = {"saft", "excel", "pdf", "csv", "json"}
        if v.lower() not in allowed_types:
            raise ValueError(
                f"Invalid file type. Allowed: {', '.join(allowed_types)}"
            )
        return v.lower()

    class Config:
        json_schema_extra = {
            "example": {
                "file_type": "saft",
                "description": "Company annual SAF-T file for 2024",
                "project_id": "proj_123",
            }
        }
