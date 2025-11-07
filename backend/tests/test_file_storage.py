"""
Comprehensive unit tests for file storage service.
Tests encryption, multi-tenant isolation, S3/local storage, and error handling.
"""

import os
import pytest
import hashlib
from uuid import uuid4, UUID
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from io import BytesIO

from fastapi import UploadFile

from backend.services.file_storage import (
    FileStorageService,
    FileMetadata,
    FileType,
    StorageBackend,
    FileStorageError,
    FileNotFoundError,
    FileSizeLimitError,
    FileTypeNotAllowedError,
    file_storage_service,
)
from backend.core.config import settings


@pytest.fixture
def tenant_id():
    """Test tenant ID."""
    return uuid4()


@pytest.fixture
def user_id():
    """Test user ID."""
    return uuid4()


@pytest.fixture
def sample_xml_content():
    """Sample SAF-T XML content."""
    return b"""<?xml version="1.0" encoding="UTF-8"?>
<AuditFile xmlns="urn:OECD:Standard:Audit:File:Tax:PT_1.04_01">
    <Header>
        <AuditFileVersion>1.04_01</AuditFileVersion>
        <CompanyID>12345678</CompanyID>
    </Header>
</AuditFile>"""


@pytest.fixture
def sample_excel_content():
    """Sample Excel binary content (minimal XLSX)."""
    # This is a minimal valid XLSX file signature
    return b'PK\x03\x04' + b'\x00' * 100


@pytest.fixture
def sample_pdf_content():
    """Sample PDF content."""
    return b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\n%%EOF'


@pytest.fixture
def mock_upload_file_xml(sample_xml_content):
    """Mock UploadFile for XML."""
    file = Mock(spec=UploadFile)
    file.filename = "test_saft.xml"
    file.read = AsyncMock(return_value=sample_xml_content)
    return file


@pytest.fixture
def mock_upload_file_excel(sample_excel_content):
    """Mock UploadFile for Excel."""
    file = Mock(spec=UploadFile)
    file.filename = "test_evf.xlsx"
    file.read = AsyncMock(return_value=sample_excel_content)
    return file


@pytest.fixture
def mock_upload_file_pdf(sample_pdf_content):
    """Mock UploadFile for PDF."""
    file = Mock(spec=UploadFile)
    file.filename = "test_report.pdf"
    file.read = AsyncMock(return_value=sample_pdf_content)
    return file


@pytest.fixture
def local_storage_service(tmp_path):
    """File storage service configured for local storage."""
    with patch.object(settings, 'storage_backend', 'local'):
        with patch.object(settings, 'local_storage_path', str(tmp_path)):
            service = FileStorageService()
            yield service


@pytest.fixture
def file_metadata_xml(tenant_id, user_id):
    """Sample file metadata for XML file."""
    return FileMetadata(
        id=uuid4(),
        tenant_id=tenant_id,
        file_name="test_saft.xml",
        file_type=FileType.SAFT,
        file_extension=".xml",
        mime_type="application/xml",
        file_size_bytes=1024,
        encrypted_size_bytes=1200,
        sha256_hash="abc123def456",
        storage_path="tenants/test/files/2024/01/test.xml",
        storage_backend=StorageBackend.LOCAL,
        is_encrypted=True,
        uploaded_by_user_id=user_id,
    )


class TestFileMetadata:
    """Test FileMetadata Pydantic model."""

    def test_file_metadata_creation(self, tenant_id, user_id):
        """Test creating valid file metadata."""
        metadata = FileMetadata(
            tenant_id=tenant_id,
            file_name="test.xml",
            file_type=FileType.SAFT,
            file_extension=".xml",
            mime_type="application/xml",
            file_size_bytes=1024,
            encrypted_size_bytes=1200,
            sha256_hash="abc123",
            storage_path="test/path",
            storage_backend=StorageBackend.LOCAL,
            uploaded_by_user_id=user_id,
        )

        assert metadata.tenant_id == tenant_id
        assert metadata.file_name == "test.xml"
        assert metadata.file_type == FileType.SAFT
        assert metadata.is_encrypted is True

    def test_file_metadata_extension_normalization(self, tenant_id):
        """Test that file extensions are normalized to lowercase with dot."""
        metadata = FileMetadata(
            tenant_id=tenant_id,
            file_name="test.XML",
            file_type=FileType.SAFT,
            file_extension="XML",  # No dot, uppercase
            mime_type="application/xml",
            file_size_bytes=1024,
            encrypted_size_bytes=1200,
            sha256_hash="abc123",
            storage_path="test/path",
            storage_backend=StorageBackend.LOCAL,
        )

        assert metadata.file_extension == ".xml"

    def test_file_metadata_json_serialization(self, tenant_id):
        """Test JSON serialization of metadata."""
        metadata = FileMetadata(
            tenant_id=tenant_id,
            file_name="test.xml",
            file_type=FileType.SAFT,
            file_extension=".xml",
            mime_type="application/xml",
            file_size_bytes=1024,
            encrypted_size_bytes=1200,
            sha256_hash="abc123",
            storage_path="test/path",
            storage_backend=StorageBackend.LOCAL,
        )

        json_data = metadata.model_dump_json()
        assert isinstance(json_data, str)
        assert str(tenant_id) in json_data


class TestFileStorageServiceLocal:
    """Test file storage service with local filesystem backend."""

    @pytest.mark.asyncio
    async def test_upload_xml_file_local(
        self, local_storage_service, tenant_id, user_id, mock_upload_file_xml, sample_xml_content
    ):
        """Test uploading XML file to local storage."""
        metadata = await local_storage_service.upload_file(
            tenant_id=tenant_id,
            file=mock_upload_file_xml,
            file_type="saft",
            user_id=user_id,
        )

        assert metadata.tenant_id == tenant_id
        assert metadata.file_name == "test_saft.xml"
        assert metadata.file_type == FileType.SAFT
        assert metadata.file_extension == ".xml"
        assert metadata.file_size_bytes == len(sample_xml_content)
        assert metadata.is_encrypted is True
        assert metadata.uploaded_by_user_id == user_id

        # Verify SHA-256 hash
        expected_hash = hashlib.sha256(sample_xml_content).hexdigest()
        assert metadata.sha256_hash == expected_hash

        # Verify file exists on disk
        file_path = local_storage_service.local_storage_path / metadata.storage_path
        assert file_path.exists()

    @pytest.mark.asyncio
    async def test_upload_excel_file_local(
        self, local_storage_service, tenant_id, mock_upload_file_excel, sample_excel_content
    ):
        """Test uploading Excel file to local storage."""
        metadata = await local_storage_service.upload_file(
            tenant_id=tenant_id,
            file=mock_upload_file_excel,
            file_type="excel",
        )

        assert metadata.file_type == FileType.EXCEL
        assert metadata.file_extension == ".xlsx"
        assert metadata.mime_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    @pytest.mark.asyncio
    async def test_upload_pdf_file_local(
        self, local_storage_service, tenant_id, mock_upload_file_pdf, sample_pdf_content
    ):
        """Test uploading PDF file to local storage."""
        metadata = await local_storage_service.upload_file(
            tenant_id=tenant_id,
            file=mock_upload_file_pdf,
            file_type="pdf",
        )

        assert metadata.file_type == FileType.PDF
        assert metadata.file_extension == ".pdf"
        assert metadata.mime_type == "application/pdf"

    @pytest.mark.asyncio
    async def test_upload_file_with_metadata(
        self, local_storage_service, tenant_id, mock_upload_file_xml
    ):
        """Test uploading file with additional metadata."""
        additional_metadata = {
            "project_id": "proj_123",
            "evf_type": "investment",
            "description": "Test EVF upload",
        }

        metadata = await local_storage_service.upload_file(
            tenant_id=tenant_id,
            file=mock_upload_file_xml,
            file_type="saft",
            additional_metadata=additional_metadata,
        )

        assert metadata.metadata == additional_metadata

    @pytest.mark.asyncio
    async def test_upload_file_size_limit_exceeded(
        self, local_storage_service, tenant_id
    ):
        """Test that large files are rejected."""
        # Create a file larger than the limit
        large_content = b"x" * (settings.max_file_size_mb * 1024 * 1024 + 1)
        large_file = Mock(spec=UploadFile)
        large_file.filename = "large.xml"
        large_file.read = AsyncMock(return_value=large_content)

        with pytest.raises(FileSizeLimitError) as exc_info:
            await local_storage_service.upload_file(
                tenant_id=tenant_id,
                file=large_file,
                file_type="saft",
            )

        assert "exceeds maximum allowed size" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_upload_file_invalid_extension(
        self, local_storage_service, tenant_id
    ):
        """Test that invalid file extensions are rejected."""
        invalid_file = Mock(spec=UploadFile)
        invalid_file.filename = "test.exe"  # Not allowed
        invalid_file.read = AsyncMock(return_value=b"content")

        with pytest.raises(FileTypeNotAllowedError) as exc_info:
            await local_storage_service.upload_file(
                tenant_id=tenant_id,
                file=invalid_file,
                file_type="saft",
            )

        assert "not allowed for type" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_download_file_local(
        self, local_storage_service, tenant_id, mock_upload_file_xml, sample_xml_content
    ):
        """Test downloading file from local storage."""
        # First upload
        metadata = await local_storage_service.upload_file(
            tenant_id=tenant_id,
            file=mock_upload_file_xml,
            file_type="saft",
        )

        # Then download
        content = await local_storage_service.download_file(
            tenant_id=tenant_id,
            file_id=metadata.id,
            metadata=metadata,
        )

        assert content == sample_xml_content

    @pytest.mark.asyncio
    async def test_download_file_wrong_tenant(
        self, local_storage_service, tenant_id, mock_upload_file_xml
    ):
        """Test that tenants cannot download files from other tenants."""
        # Upload as tenant_id
        metadata = await local_storage_service.upload_file(
            tenant_id=tenant_id,
            file=mock_upload_file_xml,
            file_type="saft",
        )

        # Try to download as different tenant
        other_tenant_id = uuid4()
        with pytest.raises(PermissionError) as exc_info:
            await local_storage_service.download_file(
                tenant_id=other_tenant_id,
                file_id=metadata.id,
                metadata=metadata,
            )

        assert "does not have permission" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_download_file_not_found(
        self, local_storage_service, tenant_id
    ):
        """Test downloading non-existent file."""
        fake_metadata = FileMetadata(
            tenant_id=tenant_id,
            file_name="nonexistent.xml",
            file_type=FileType.SAFT,
            file_extension=".xml",
            mime_type="application/xml",
            file_size_bytes=1024,
            encrypted_size_bytes=1200,
            sha256_hash="abc123",
            storage_path="nonexistent/path.xml",
            storage_backend=StorageBackend.LOCAL,
        )

        with pytest.raises(FileNotFoundError):
            await local_storage_service.download_file(
                tenant_id=tenant_id,
                file_id=fake_metadata.id,
                metadata=fake_metadata,
            )

    @pytest.mark.asyncio
    async def test_delete_file_local(
        self, local_storage_service, tenant_id, mock_upload_file_xml
    ):
        """Test deleting file from local storage."""
        # Upload file
        metadata = await local_storage_service.upload_file(
            tenant_id=tenant_id,
            file=mock_upload_file_xml,
            file_type="saft",
        )

        file_path = local_storage_service.local_storage_path / metadata.storage_path
        assert file_path.exists()

        # Delete file
        result = await local_storage_service.delete_file(
            tenant_id=tenant_id,
            file_id=metadata.id,
            metadata=metadata,
        )

        assert result is True
        assert not file_path.exists()

    @pytest.mark.asyncio
    async def test_delete_file_wrong_tenant(
        self, local_storage_service, tenant_id, mock_upload_file_xml
    ):
        """Test that tenants cannot delete files from other tenants."""
        # Upload as tenant_id
        metadata = await local_storage_service.upload_file(
            tenant_id=tenant_id,
            file=mock_upload_file_xml,
            file_type="saft",
        )

        # Try to delete as different tenant
        other_tenant_id = uuid4()
        with pytest.raises(PermissionError):
            await local_storage_service.delete_file(
                tenant_id=other_tenant_id,
                file_id=metadata.id,
                metadata=metadata,
            )

    @pytest.mark.asyncio
    async def test_encryption_decryption_roundtrip(
        self, local_storage_service, tenant_id, mock_upload_file_xml, sample_xml_content
    ):
        """Test that encryption/decryption preserves file content."""
        # Upload (encrypts)
        metadata = await local_storage_service.upload_file(
            tenant_id=tenant_id,
            file=mock_upload_file_xml,
            file_type="saft",
        )

        # Download (decrypts)
        content = await local_storage_service.download_file(
            tenant_id=tenant_id,
            file_id=metadata.id,
            metadata=metadata,
        )

        # Content should match original
        assert content == sample_xml_content

    @pytest.mark.asyncio
    async def test_storage_path_tenant_isolation(
        self, local_storage_service, tenant_id, mock_upload_file_xml
    ):
        """Test that storage paths include tenant ID for isolation."""
        metadata = await local_storage_service.upload_file(
            tenant_id=tenant_id,
            file=mock_upload_file_xml,
            file_type="saft",
        )

        # Storage path should include tenant_id
        assert f"tenants/{tenant_id}" in metadata.storage_path
        assert metadata.storage_path.endswith(".xml")


class TestFileStorageServiceS3:
    """Test file storage service with S3 backend."""

    @pytest.fixture
    def s3_storage_service(self):
        """File storage service configured for S3."""
        with patch.object(settings, 'storage_backend', 's3'):
            service = FileStorageService()
            yield service

    @pytest.mark.asyncio
    async def test_upload_file_s3(
        self, s3_storage_service, tenant_id, mock_upload_file_xml, sample_xml_content
    ):
        """Test uploading file to S3."""
        # Mock S3 client
        mock_s3_client = AsyncMock()
        mock_s3_client.__aenter__ = AsyncMock(return_value=mock_s3_client)
        mock_s3_client.__aexit__ = AsyncMock()
        mock_s3_client.put_object = AsyncMock()

        with patch.object(s3_storage_service.s3_session, 'client', return_value=mock_s3_client):
            metadata = await s3_storage_service.upload_file(
                tenant_id=tenant_id,
                file=mock_upload_file_xml,
                file_type="saft",
            )

            assert metadata.storage_backend == StorageBackend.S3
            assert mock_s3_client.put_object.called

    @pytest.mark.asyncio
    async def test_download_file_s3(
        self, s3_storage_service, tenant_id, user_id, sample_xml_content
    ):
        """Test downloading file from S3."""
        metadata = FileMetadata(
            tenant_id=tenant_id,
            file_name="test.xml",
            file_type=FileType.SAFT,
            file_extension=".xml",
            mime_type="application/xml",
            file_size_bytes=len(sample_xml_content),
            encrypted_size_bytes=len(sample_xml_content) + 100,
            sha256_hash=hashlib.sha256(sample_xml_content).hexdigest(),
            storage_path="test/path.xml",
            storage_backend=StorageBackend.S3,
            is_encrypted=False,  # For simplicity in this test
        )

        # Mock S3 response
        mock_response = {
            'Body': AsyncMock()
        }
        mock_response['Body'].read = AsyncMock(return_value=sample_xml_content)

        mock_s3_client = AsyncMock()
        mock_s3_client.__aenter__ = AsyncMock(return_value=mock_s3_client)
        mock_s3_client.__aexit__ = AsyncMock()
        mock_s3_client.get_object = AsyncMock(return_value=mock_response)

        with patch.object(s3_storage_service.s3_session, 'client', return_value=mock_s3_client):
            content = await s3_storage_service.download_file(
                tenant_id=tenant_id,
                file_id=metadata.id,
                metadata=metadata,
            )

            assert content == sample_xml_content
            assert mock_s3_client.get_object.called

    @pytest.mark.asyncio
    async def test_delete_file_s3(
        self, s3_storage_service, tenant_id
    ):
        """Test deleting file from S3."""
        metadata = FileMetadata(
            tenant_id=tenant_id,
            file_name="test.xml",
            file_type=FileType.SAFT,
            file_extension=".xml",
            mime_type="application/xml",
            file_size_bytes=1024,
            encrypted_size_bytes=1200,
            sha256_hash="abc123",
            storage_path="test/path.xml",
            storage_backend=StorageBackend.S3,
        )

        # Mock S3 client
        mock_s3_client = AsyncMock()
        mock_s3_client.__aenter__ = AsyncMock(return_value=mock_s3_client)
        mock_s3_client.__aexit__ = AsyncMock()
        mock_s3_client.delete_object = AsyncMock()

        with patch.object(s3_storage_service.s3_session, 'client', return_value=mock_s3_client):
            result = await s3_storage_service.delete_file(
                tenant_id=tenant_id,
                file_id=metadata.id,
                metadata=metadata,
            )

            assert result is True
            assert mock_s3_client.delete_object.called


class TestFileStorageHelpers:
    """Test helper methods and utility functions."""

    def test_get_file_extension(self, local_storage_service):
        """Test extracting file extension."""
        assert local_storage_service._get_file_extension("test.xml") == ".xml"
        assert local_storage_service._get_file_extension("test.XLSX") == ".xlsx"
        assert local_storage_service._get_file_extension("file.tar.gz") == ".gz"

    def test_generate_storage_path(self, local_storage_service, tenant_id):
        """Test generating storage path with tenant isolation."""
        file_id = uuid4()
        path = local_storage_service._generate_storage_path(tenant_id, file_id, ".xml")

        assert f"tenants/{tenant_id}" in path
        assert str(file_id) in path
        assert path.endswith(".xml")
        # Should include year/month for organization
        assert "/files/" in path


class TestGlobalServiceInstance:
    """Test global service instance and convenience functions."""

    def test_global_service_exists(self):
        """Test that global service instance is created."""
        assert file_storage_service is not None
        assert isinstance(file_storage_service, FileStorageService)
