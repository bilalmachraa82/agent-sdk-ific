"""
Database models for file storage and management.
Stores metadata for uploaded files with encryption and multi-tenant isolation.
"""

from datetime import datetime
from uuid import UUID
from sqlalchemy import Column, String, Integer, Boolean, DateTime, UUID as SQLUUID, Text, JSON
from sqlalchemy.orm import relationship

from .base import Base, BaseTenantModel


class File(Base, BaseTenantModel):
    """
    File storage metadata model.

    Stores metadata for all uploaded files including SAF-T, Excel, PDF, etc.
    Actual file content is stored in S3 or local filesystem (encrypted).
    """

    __tablename__ = "files"

    # File identification
    file_name = Column(
        String(255),
        nullable=False,
        index=True,
        comment="Original file name"
    )

    file_type = Column(
        String(50),
        nullable=False,
        index=True,
        comment="File type (saft, excel, pdf, csv, json)"
    )

    file_extension = Column(
        String(10),
        nullable=False,
        comment="File extension (.xml, .xlsx, .pdf, etc.)"
    )

    mime_type = Column(
        String(100),
        nullable=False,
        comment="MIME type"
    )

    # File size and integrity
    file_size_bytes = Column(
        Integer,
        nullable=False,
        comment="Original file size in bytes"
    )

    encrypted_size_bytes = Column(
        Integer,
        nullable=False,
        comment="Encrypted file size in bytes"
    )

    sha256_hash = Column(
        String(64),
        nullable=False,
        index=True,
        comment="SHA-256 hash for integrity validation"
    )

    # Storage location
    storage_path = Column(
        String(500),
        nullable=False,
        unique=True,
        comment="Path/key in storage backend"
    )

    storage_backend = Column(
        String(20),
        nullable=False,
        comment="Storage backend (local or s3)"
    )

    # Encryption
    is_encrypted = Column(
        Boolean,
        nullable=False,
        default=True,
        comment="Whether file is encrypted at rest"
    )

    # Upload tracking
    upload_timestamp = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        index=True,
        comment="When file was uploaded"
    )

    uploaded_by_user_id = Column(
        SQLUUID(as_uuid=True),
        nullable=True,
        index=True,
        comment="User who uploaded the file"
    )

    # Additional metadata (JSON)
    custom_metadata = Column(
        "metadata",  # Column name in database
        JSON,
        nullable=True,
        comment="Additional metadata (project_id, description, etc.)"
    )

    # File lifecycle
    is_deleted = Column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
        comment="Soft delete flag"
    )

    deleted_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="When file was deleted"
    )

    deleted_by_user_id = Column(
        SQLUUID(as_uuid=True),
        nullable=True,
        comment="User who deleted the file"
    )

    # Access tracking
    last_accessed_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Last time file was accessed"
    )

    access_count = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of times file was accessed"
    )

    # Retention and compliance
    retention_until = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Retention period end date"
    )

    compliance_tags = Column(
        JSON,
        nullable=True,
        comment="Compliance tags (PT2030, PRR, etc.)"
    )

    def __repr__(self):
        return (
            f"<File(id={self.id}, tenant_id={self.tenant_id}, "
            f"file_name='{self.file_name}', file_type='{self.file_type}')>"
        )

    def to_metadata_dict(self):
        """Convert to FileMetadata-compatible dict."""
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "file_name": self.file_name,
            "file_type": self.file_type,
            "file_extension": self.file_extension,
            "mime_type": self.mime_type,
            "file_size_bytes": self.file_size_bytes,
            "encrypted_size_bytes": self.encrypted_size_bytes,
            "sha256_hash": self.sha256_hash,
            "storage_path": self.storage_path,
            "storage_backend": self.storage_backend,
            "is_encrypted": self.is_encrypted,
            "upload_timestamp": self.upload_timestamp,
            "uploaded_by_user_id": self.uploaded_by_user_id,
            "metadata": self.custom_metadata or {},
        }


class FileAccessLog(Base, BaseTenantModel):
    """
    Audit log for file access events.

    Tracks all file downloads, views, and deletions for compliance.
    """

    __tablename__ = "file_access_logs"

    file_id = Column(
        SQLUUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="File that was accessed"
    )

    access_type = Column(
        String(50),
        nullable=False,
        index=True,
        comment="Type of access (download, view, delete)"
    )

    user_id = Column(
        SQLUUID(as_uuid=True),
        nullable=True,
        index=True,
        comment="User who accessed the file"
    )

    ip_address = Column(
        String(45),
        nullable=True,
        comment="IP address of the request"
    )

    user_agent = Column(
        String(500),
        nullable=True,
        comment="User agent string"
    )

    success = Column(
        Boolean,
        nullable=False,
        default=True,
        comment="Whether access was successful"
    )

    error_message = Column(
        Text,
        nullable=True,
        comment="Error message if access failed"
    )

    access_timestamp = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        index=True,
        comment="When access occurred"
    )

    def __repr__(self):
        return (
            f"<FileAccessLog(id={self.id}, file_id={self.file_id}, "
            f"access_type='{self.access_type}', success={self.success})>"
        )
