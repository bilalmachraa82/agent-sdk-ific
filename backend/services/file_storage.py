"""
Production-ready file storage service for EVF Portugal 2030.
Supports local filesystem and S3 with encryption, integrity validation, and multi-tenant isolation.
"""

import os
import hashlib
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, BinaryIO, Dict, Any
from uuid import UUID, uuid4
from enum import Enum
from io import BytesIO

from fastapi import UploadFile, HTTPException, status
from pydantic import BaseModel, Field, validator
import aioboto3
from botocore.exceptions import ClientError, BotoCoreError

from backend.core.config import settings
from backend.core.encryption import encryption_manager

logger = logging.getLogger(__name__)


# Constants
ALLOWED_EXTENSIONS = {
    "saft": {".xml"},
    "excel": {".xlsx", ".xls"},
    "pdf": {".pdf"},
    "csv": {".csv"},
    "json": {".json"},
}

MIME_TYPES = {
    ".xml": "application/xml",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".xls": "application/vnd.ms-excel",
    ".pdf": "application/pdf",
    ".csv": "text/csv",
    ".json": "application/json",
}


class FileType(str, Enum):
    """Supported file types for EVF processing."""
    SAFT = "saft"
    EXCEL = "excel"
    PDF = "pdf"
    CSV = "csv"
    JSON = "json"


class StorageBackend(str, Enum):
    """Available storage backends."""
    LOCAL = "local"
    S3 = "s3"


class FileMetadata(BaseModel):
    """Metadata for uploaded files with encryption and integrity validation."""

    id: UUID = Field(default_factory=uuid4, description="Unique file identifier")
    tenant_id: UUID = Field(..., description="Tenant owning this file")
    file_name: str = Field(..., description="Original file name")
    file_type: FileType = Field(..., description="Type of file")
    file_extension: str = Field(..., description="File extension")
    mime_type: str = Field(..., description="MIME type")
    file_size_bytes: int = Field(..., ge=0, description="Original file size in bytes")
    encrypted_size_bytes: int = Field(..., ge=0, description="Encrypted file size in bytes")
    sha256_hash: str = Field(..., description="SHA-256 hash of original file for integrity")
    storage_path: str = Field(..., description="Path/key in storage backend")
    storage_backend: StorageBackend = Field(..., description="Storage backend used")
    is_encrypted: bool = Field(default=True, description="Whether file is encrypted")
    upload_timestamp: datetime = Field(default_factory=datetime.utcnow)
    uploaded_by_user_id: Optional[UUID] = Field(None, description="User who uploaded")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    class Config:
        json_encoders = {
            UUID: str,
            datetime: lambda v: v.isoformat(),
        }

    @validator("file_extension")
    def validate_extension(cls, v):
        """Ensure extension starts with a dot."""
        if not v.startswith("."):
            return f".{v}"
        return v.lower()


class FileStorageError(Exception):
    """Base exception for file storage errors."""
    pass


class FileNotFoundError(FileStorageError):
    """File not found in storage."""
    pass


class FileSizeLimitError(FileStorageError):
    """File exceeds maximum allowed size."""
    pass


class FileTypeNotAllowedError(FileStorageError):
    """File type not allowed."""
    pass


class StorageQuotaExceededError(FileStorageError):
    """Storage quota exceeded for tenant."""
    pass


class FileStorageService:
    """
    Production-ready file storage service with encryption and multi-tenant isolation.

    Features:
    - Local filesystem and S3 backend support
    - AES-256-GCM encryption at rest
    - SHA-256 integrity validation
    - Multi-tenant file isolation
    - Async operations throughout
    - Comprehensive error handling
    """

    def __init__(self):
        """Initialize file storage service."""
        self.backend = StorageBackend(settings.storage_backend)
        self.max_file_size_bytes = settings.max_file_size_mb * 1024 * 1024
        self.encryption_enabled = True

        # S3 configuration
        if self.backend == StorageBackend.S3:
            self.s3_bucket = settings.s3_bucket_name
            self.s3_region = settings.s3_region
            self.s3_session = aioboto3.Session()
            logger.info(f"Initialized S3 storage backend: bucket={self.s3_bucket}")
        else:
            # Local storage configuration
            self.local_storage_path = Path(settings.local_storage_path)
            self.local_storage_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Initialized local storage backend: path={self.local_storage_path}")

    async def upload_file(
        self,
        tenant_id: UUID,
        file: UploadFile,
        file_type: str,
        user_id: Optional[UUID] = None,
        additional_metadata: Optional[Dict[str, Any]] = None,
    ) -> FileMetadata:
        """
        Upload and encrypt a file for a specific tenant.

        Args:
            tenant_id: Tenant UUID owning this file
            file: FastAPI UploadFile object
            file_type: Type of file (saft, excel, pdf, etc.)
            user_id: Optional user ID who uploaded the file
            additional_metadata: Optional additional metadata to store

        Returns:
            FileMetadata object with storage information

        Raises:
            FileSizeLimitError: File exceeds maximum size
            FileTypeNotAllowedError: File extension not allowed
            FileStorageError: General storage error
        """
        try:
            # Validate file type
            file_type_enum = FileType(file_type)
            file_extension = self._get_file_extension(file.filename)

            if file_extension not in ALLOWED_EXTENSIONS.get(file_type, set()):
                raise FileTypeNotAllowedError(
                    f"File extension {file_extension} not allowed for type {file_type}. "
                    f"Allowed: {ALLOWED_EXTENSIONS.get(file_type, set())}"
                )

            # Read file content
            content = await file.read()
            original_size = len(content)

            # Validate file size
            if original_size > self.max_file_size_bytes:
                raise FileSizeLimitError(
                    f"File size {original_size / 1024 / 1024:.2f}MB exceeds "
                    f"maximum allowed size {settings.max_file_size_mb}MB"
                )

            # Calculate SHA-256 hash for integrity
            sha256_hash = hashlib.sha256(content).hexdigest()

            # Encrypt file content
            if self.encryption_enabled:
                encrypted_content = await self._encrypt_content(content)
                content_to_store = encrypted_content
            else:
                content_to_store = content

            encrypted_size = len(content_to_store)

            # Generate storage path
            file_id = uuid4()
            storage_path = self._generate_storage_path(tenant_id, file_id, file_extension)

            # Store file based on backend
            if self.backend == StorageBackend.S3:
                await self._upload_to_s3(storage_path, content_to_store)
            else:
                await self._upload_to_local(storage_path, content_to_store)

            # Create metadata
            metadata = FileMetadata(
                id=file_id,
                tenant_id=tenant_id,
                file_name=file.filename,
                file_type=file_type_enum,
                file_extension=file_extension,
                mime_type=MIME_TYPES.get(file_extension, "application/octet-stream"),
                file_size_bytes=original_size,
                encrypted_size_bytes=encrypted_size,
                sha256_hash=sha256_hash,
                storage_path=storage_path,
                storage_backend=self.backend,
                is_encrypted=self.encryption_enabled,
                uploaded_by_user_id=user_id,
                metadata=additional_metadata or {},
            )

            logger.info(
                f"Uploaded file {file_id} for tenant {tenant_id}: "
                f"{file.filename} ({original_size / 1024:.2f}KB)"
            )

            return metadata

        except (FileSizeLimitError, FileTypeNotAllowedError):
            raise
        except Exception as e:
            logger.error(f"Failed to upload file for tenant {tenant_id}: {e}")
            raise FileStorageError(f"File upload failed: {str(e)}")

    async def download_file(
        self,
        tenant_id: UUID,
        file_id: UUID,
        metadata: FileMetadata,
    ) -> bytes:
        """
        Download and decrypt a file for a specific tenant.

        Args:
            tenant_id: Tenant UUID requesting the file
            file_id: File UUID to download
            metadata: File metadata with storage information

        Returns:
            Decrypted file content as bytes

        Raises:
            FileNotFoundError: File not found in storage
            PermissionError: Tenant doesn't own this file
            FileStorageError: General storage error
        """
        try:
            # Validate tenant ownership
            if metadata.tenant_id != tenant_id:
                raise PermissionError(
                    f"Tenant {tenant_id} does not have permission to access file {file_id}"
                )

            # Download file based on backend
            if self.backend == StorageBackend.S3:
                encrypted_content = await self._download_from_s3(metadata.storage_path)
            else:
                encrypted_content = await self._download_from_local(metadata.storage_path)

            # Decrypt content if encrypted
            if metadata.is_encrypted:
                content = await self._decrypt_content(encrypted_content)
            else:
                content = encrypted_content

            # Validate integrity
            calculated_hash = hashlib.sha256(content).hexdigest()
            if calculated_hash != metadata.sha256_hash:
                logger.error(
                    f"Integrity check failed for file {file_id}: "
                    f"expected {metadata.sha256_hash}, got {calculated_hash}"
                )
                raise FileStorageError("File integrity check failed - file may be corrupted")

            logger.info(
                f"Downloaded file {file_id} for tenant {tenant_id}: "
                f"{metadata.file_name} ({len(content) / 1024:.2f}KB)"
            )

            return content

        except PermissionError:
            raise
        except FileNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to download file {file_id} for tenant {tenant_id}: {e}")
            raise FileStorageError(f"File download failed: {str(e)}")

    async def delete_file(
        self,
        tenant_id: UUID,
        file_id: UUID,
        metadata: FileMetadata,
    ) -> bool:
        """
        Delete a file from storage.

        Args:
            tenant_id: Tenant UUID requesting deletion
            file_id: File UUID to delete
            metadata: File metadata with storage information

        Returns:
            True if deleted successfully

        Raises:
            PermissionError: Tenant doesn't own this file
            FileStorageError: General storage error
        """
        try:
            # Validate tenant ownership
            if metadata.tenant_id != tenant_id:
                raise PermissionError(
                    f"Tenant {tenant_id} does not have permission to delete file {file_id}"
                )

            # Delete file based on backend
            if self.backend == StorageBackend.S3:
                await self._delete_from_s3(metadata.storage_path)
            else:
                await self._delete_from_local(metadata.storage_path)

            logger.info(f"Deleted file {file_id} for tenant {tenant_id}: {metadata.file_name}")
            return True

        except PermissionError:
            raise
        except Exception as e:
            logger.error(f"Failed to delete file {file_id} for tenant {tenant_id}: {e}")
            raise FileStorageError(f"File deletion failed: {str(e)}")

    async def get_file_metadata(
        self,
        tenant_id: UUID,
        file_id: UUID,
        metadata: FileMetadata,
    ) -> FileMetadata:
        """
        Get metadata for a file.

        Args:
            tenant_id: Tenant UUID requesting metadata
            file_id: File UUID
            metadata: File metadata to validate

        Returns:
            FileMetadata object

        Raises:
            PermissionError: Tenant doesn't own this file
        """
        # Validate tenant ownership
        if metadata.tenant_id != tenant_id:
            raise PermissionError(
                f"Tenant {tenant_id} does not have permission to access file {file_id}"
            )

        return metadata

    # Private helper methods

    def _get_file_extension(self, filename: str) -> str:
        """Extract file extension from filename."""
        return Path(filename).suffix.lower()

    def _generate_storage_path(self, tenant_id: UUID, file_id: UUID, extension: str) -> str:
        """
        Generate storage path with tenant isolation.

        Format: tenants/{tenant_id}/files/{YYYY}/{MM}/{file_id}{extension}
        """
        now = datetime.utcnow()
        return (
            f"tenants/{tenant_id}/files/{now.year:04d}/{now.month:02d}/"
            f"{file_id}{extension}"
        )

    async def _encrypt_content(self, content: bytes) -> bytes:
        """Encrypt file content using AES-256-GCM."""
        try:
            # Run encryption in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            encrypted_str = await loop.run_in_executor(
                None,
                encryption_manager.encrypt,
                content.decode('latin-1')  # Preserve binary data
            )
            return encrypted_str.encode('utf-8')
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise FileStorageError(f"File encryption failed: {str(e)}")

    async def _decrypt_content(self, encrypted_content: bytes) -> bytes:
        """Decrypt file content using AES-256-GCM."""
        try:
            # Run decryption in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            decrypted_str = await loop.run_in_executor(
                None,
                encryption_manager.decrypt,
                encrypted_content.decode('utf-8')
            )
            return decrypted_str.encode('latin-1')  # Restore binary data
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise FileStorageError(f"File decryption failed: {str(e)}")

    # S3 operations

    async def _upload_to_s3(self, key: str, content: bytes) -> None:
        """Upload file to S3."""
        try:
            async with self.s3_session.client(
                's3',
                region_name=self.s3_region,
                endpoint_url=settings.s3_endpoint_url,
                aws_access_key_id=settings.s3_access_key,
                aws_secret_access_key=settings.s3_secret_key,
            ) as s3:
                await s3.put_object(
                    Bucket=self.s3_bucket,
                    Key=key,
                    Body=content,
                    ServerSideEncryption='AES256',  # S3 server-side encryption
                    Metadata={
                        'upload-timestamp': datetime.utcnow().isoformat(),
                    }
                )
            logger.debug(f"Uploaded to S3: {key}")
        except (ClientError, BotoCoreError) as e:
            logger.error(f"S3 upload failed for key {key}: {e}")
            raise FileStorageError(f"S3 upload failed: {str(e)}")

    async def _download_from_s3(self, key: str) -> bytes:
        """Download file from S3."""
        try:
            async with self.s3_session.client(
                's3',
                region_name=self.s3_region,
                endpoint_url=settings.s3_endpoint_url,
                aws_access_key_id=settings.s3_access_key,
                aws_secret_access_key=settings.s3_secret_key,
            ) as s3:
                response = await s3.get_object(Bucket=self.s3_bucket, Key=key)
                content = await response['Body'].read()
            logger.debug(f"Downloaded from S3: {key}")
            return content
        except s3.exceptions.NoSuchKey:
            logger.error(f"File not found in S3: {key}")
            raise FileNotFoundError(f"File not found: {key}")
        except (ClientError, BotoCoreError) as e:
            logger.error(f"S3 download failed for key {key}: {e}")
            raise FileStorageError(f"S3 download failed: {str(e)}")

    async def _delete_from_s3(self, key: str) -> None:
        """Delete file from S3."""
        try:
            async with self.s3_session.client(
                's3',
                region_name=self.s3_region,
                endpoint_url=settings.s3_endpoint_url,
                aws_access_key_id=settings.s3_access_key,
                aws_secret_access_key=settings.s3_secret_key,
            ) as s3:
                await s3.delete_object(Bucket=self.s3_bucket, Key=key)
            logger.debug(f"Deleted from S3: {key}")
        except (ClientError, BotoCoreError) as e:
            logger.error(f"S3 deletion failed for key {key}: {e}")
            raise FileStorageError(f"S3 deletion failed: {str(e)}")

    # Local filesystem operations

    async def _upload_to_local(self, path: str, content: bytes) -> None:
        """Upload file to local filesystem."""
        try:
            full_path = self.local_storage_path / path
            full_path.parent.mkdir(parents=True, exist_ok=True)

            # Write file asynchronously
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, full_path.write_bytes, content)

            logger.debug(f"Uploaded to local storage: {path}")
        except Exception as e:
            logger.error(f"Local upload failed for path {path}: {e}")
            raise FileStorageError(f"Local storage upload failed: {str(e)}")

    async def _download_from_local(self, path: str) -> bytes:
        """Download file from local filesystem."""
        try:
            full_path = self.local_storage_path / path

            if not full_path.exists():
                raise FileNotFoundError(f"File not found: {path}")

            # Read file asynchronously
            loop = asyncio.get_event_loop()
            content = await loop.run_in_executor(None, full_path.read_bytes)

            logger.debug(f"Downloaded from local storage: {path}")
            return content
        except FileNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Local download failed for path {path}: {e}")
            raise FileStorageError(f"Local storage download failed: {str(e)}")

    async def _delete_from_local(self, path: str) -> None:
        """Delete file from local filesystem."""
        try:
            full_path = self.local_storage_path / path

            if full_path.exists():
                # Delete file asynchronously
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, full_path.unlink)
                logger.debug(f"Deleted from local storage: {path}")
            else:
                logger.warning(f"File not found for deletion: {path}")
        except Exception as e:
            logger.error(f"Local deletion failed for path {path}: {e}")
            raise FileStorageError(f"Local storage deletion failed: {str(e)}")


# Global file storage service instance
file_storage_service = FileStorageService()


# Convenience functions

async def upload_file(
    tenant_id: UUID,
    file: UploadFile,
    file_type: str,
    user_id: Optional[UUID] = None,
    additional_metadata: Optional[Dict[str, Any]] = None,
) -> FileMetadata:
    """Convenience function to upload a file."""
    return await file_storage_service.upload_file(
        tenant_id, file, file_type, user_id, additional_metadata
    )


async def download_file(
    tenant_id: UUID,
    file_id: UUID,
    metadata: FileMetadata,
) -> bytes:
    """Convenience function to download a file."""
    return await file_storage_service.download_file(tenant_id, file_id, metadata)


async def delete_file(
    tenant_id: UUID,
    file_id: UUID,
    metadata: FileMetadata,
) -> bool:
    """Convenience function to delete a file."""
    return await file_storage_service.delete_file(tenant_id, file_id, metadata)


async def get_file_metadata(
    tenant_id: UUID,
    file_id: UUID,
    metadata: FileMetadata,
) -> FileMetadata:
    """Convenience function to get file metadata."""
    return await file_storage_service.get_file_metadata(tenant_id, file_id, metadata)
