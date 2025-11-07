# File Storage Service

Production-ready file storage service for EVF Portugal 2030 with encryption, integrity validation, and multi-tenant isolation.

## Features

### Core Capabilities
- **Multi-Backend Support**: Local filesystem and AWS S3
- **AES-256-GCM Encryption**: All files encrypted at rest
- **SHA-256 Integrity**: Cryptographic hash validation
- **Multi-Tenant Isolation**: Files organized by tenant_id
- **Async Operations**: Non-blocking file operations
- **Comprehensive Error Handling**: Detailed exception hierarchy

### Supported File Types
- **SAF-T XML** (`.xml`) - Portuguese tax files
- **Excel** (`.xlsx`, `.xls`) - Financial models and reports
- **PDF** (`.pdf`) - Generated proposals and reports
- **CSV** (`.csv`) - Data imports/exports
- **JSON** (`.json`) - Structured data

### Security Features
- AES-256-GCM encryption using `cryptography` library
- SHA-256 hash for file integrity validation
- Tenant-based file isolation (files cannot be accessed across tenants)
- File size validation (configurable limit, default 500MB)
- File type validation (only allowed extensions)
- Server-side encryption for S3 (AES-256)

## Installation

### Dependencies
```bash
pip install aioboto3 boto3 cryptography
```

Or add to `requirements.txt`:
```
aioboto3==13.2.0
boto3==1.35.36
cryptography==43.0.1
```

### Configuration

Add to `.env`:
```bash
# Storage Backend (local or s3)
STORAGE_BACKEND=s3

# S3 Configuration (if using S3)
S3_BUCKET_NAME=evf-portugal-2030
S3_REGION=eu-west-1
S3_ACCESS_KEY=your-access-key
S3_SECRET_KEY=your-secret-key
S3_ENDPOINT_URL=  # Optional, for S3-compatible services

# Local Storage (if using local)
LOCAL_STORAGE_PATH=storage/uploads

# File Limits
MAX_FILE_SIZE_MB=500

# Encryption
ENCRYPTION_KEY=your-32-byte-encryption-key-change-in-production
```

## Usage

### Basic Upload

```python
from uuid import UUID
from fastapi import UploadFile
from backend.services.file_storage import file_storage_service

# Upload a SAF-T XML file
tenant_id = UUID("...")
user_id = UUID("...")

async def upload_saft(file: UploadFile):
    metadata = await file_storage_service.upload_file(
        tenant_id=tenant_id,
        file=file,
        file_type="saft",  # or "excel", "pdf", "csv", "json"
        user_id=user_id,
        additional_metadata={
            "project_id": "proj_123",
            "description": "Company SAF-T 2024"
        }
    )

    print(f"File uploaded: {metadata.id}")
    print(f"SHA-256: {metadata.sha256_hash}")
    print(f"Storage path: {metadata.storage_path}")

    return metadata
```

### Download File

```python
from backend.services.file_storage import file_storage_service
from backend.models.file import File

async def download_file_example(file_id: UUID, tenant_id: UUID):
    # Fetch metadata from database
    db_file = await db.query(File).filter(
        File.id == file_id,
        File.tenant_id == tenant_id
    ).first()

    # Convert to FileMetadata
    from backend.services.file_storage import FileMetadata
    metadata = FileMetadata(**db_file.to_metadata_dict())

    # Download file content
    content = await file_storage_service.download_file(
        tenant_id=tenant_id,
        file_id=file_id,
        metadata=metadata
    )

    return content  # Decrypted bytes
```

### Delete File

```python
async def delete_file_example(file_id: UUID, tenant_id: UUID):
    # Fetch metadata from database
    db_file = await db.query(File).filter(
        File.id == file_id,
        File.tenant_id == tenant_id
    ).first()

    metadata = FileMetadata(**db_file.to_metadata_dict())

    # Delete from storage
    success = await file_storage_service.delete_file(
        tenant_id=tenant_id,
        file_id=file_id,
        metadata=metadata
    )

    # Mark as deleted in database (soft delete)
    db_file.is_deleted = True
    db_file.deleted_at = datetime.utcnow()
    await db.commit()

    return success
```

### Complete API Endpoint Example

```python
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/files", tags=["files"])

@router.post("/upload")
async def upload_file_endpoint(
    file: UploadFile = File(...),
    file_type: str = "saft",
    tenant_id: UUID = Depends(get_current_tenant),
    user_id: UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload and encrypt a file."""
    try:
        # Upload to storage
        metadata = await file_storage_service.upload_file(
            tenant_id=tenant_id,
            file=file,
            file_type=file_type,
            user_id=user_id,
        )

        # Save metadata to database
        db_file = File(
            id=metadata.id,
            tenant_id=tenant_id,
            file_name=metadata.file_name,
            file_type=metadata.file_type,
            file_extension=metadata.file_extension,
            mime_type=metadata.mime_type,
            file_size_bytes=metadata.file_size_bytes,
            encrypted_size_bytes=metadata.encrypted_size_bytes,
            sha256_hash=metadata.sha256_hash,
            storage_path=metadata.storage_path,
            storage_backend=metadata.storage_backend,
            is_encrypted=metadata.is_encrypted,
            uploaded_by_user_id=user_id,
        )
        db.add(db_file)
        await db.commit()

        return {
            "file_id": metadata.id,
            "file_name": metadata.file_name,
            "size_bytes": metadata.file_size_bytes,
            "sha256": metadata.sha256_hash,
        }

    except FileSizeLimitError as e:
        raise HTTPException(status_code=413, detail=str(e))
    except FileTypeNotAllowedError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileStorageError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{file_id}/download")
async def download_file_endpoint(
    file_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """Download and decrypt a file."""
    from fastapi.responses import Response

    # Fetch from database
    db_file = await db.query(File).filter(
        File.id == file_id,
        File.tenant_id == tenant_id,
        File.is_deleted == False,
    ).first()

    if not db_file:
        raise HTTPException(status_code=404, detail="File not found")

    # Convert to metadata
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
    await db.commit()

    return Response(
        content=content,
        media_type=metadata.mime_type,
        headers={
            "Content-Disposition": f"attachment; filename={metadata.file_name}"
        }
    )


@router.delete("/{file_id}")
async def delete_file_endpoint(
    file_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant),
    user_id: UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a file."""
    db_file = await db.query(File).filter(
        File.id == file_id,
        File.tenant_id == tenant_id,
        File.is_deleted == False,
    ).first()

    if not db_file:
        raise HTTPException(status_code=404, detail="File not found")

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
    await db.commit()

    return {"success": True}
```

## Architecture

### Storage Path Format

Files are organized by tenant for isolation:

```
tenants/{tenant_id}/files/{YYYY}/{MM}/{file_id}{extension}
```

Example:
```
tenants/550e8400-e29b-41d4-a716-446655440000/files/2024/11/a1b2c3d4-...-.xml
```

### Encryption Flow

1. **Upload**:
   - Read file content
   - Calculate SHA-256 hash (before encryption)
   - Encrypt with AES-256-GCM
   - Store encrypted content
   - Save metadata (including hash)

2. **Download**:
   - Fetch encrypted content
   - Decrypt with AES-256-GCM
   - Validate SHA-256 hash
   - Return original content

### Multi-Tenant Isolation

- Every file includes `tenant_id`
- Storage paths include tenant ID
- Download/delete operations validate tenant ownership
- Database queries filtered by `tenant_id`

## Error Handling

### Exception Hierarchy

```python
FileStorageError (base)
├── FileNotFoundError
├── FileSizeLimitError
├── FileTypeNotAllowedError
└── StorageQuotaExceededError
```

### Example Error Handling

```python
try:
    metadata = await file_storage_service.upload_file(...)
except FileSizeLimitError as e:
    # File too large
    return {"error": "file_too_large", "message": str(e)}
except FileTypeNotAllowedError as e:
    # Invalid file type
    return {"error": "invalid_file_type", "message": str(e)}
except FileStorageError as e:
    # General storage error
    logger.error(f"Storage error: {e}")
    return {"error": "storage_error", "message": "Failed to store file"}
```

## Database Schema

### File Model

```sql
CREATE TABLE files (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    file_type VARCHAR(50) NOT NULL,
    file_extension VARCHAR(10) NOT NULL,
    mime_type VARCHAR(100) NOT NULL,
    file_size_bytes INTEGER NOT NULL,
    encrypted_size_bytes INTEGER NOT NULL,
    sha256_hash VARCHAR(64) NOT NULL,
    storage_path VARCHAR(500) NOT NULL UNIQUE,
    storage_backend VARCHAR(20) NOT NULL,
    is_encrypted BOOLEAN DEFAULT TRUE,
    upload_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    uploaded_by_user_id UUID,
    metadata JSONB,
    is_deleted BOOLEAN DEFAULT FALSE,
    deleted_at TIMESTAMP WITH TIME ZONE,
    deleted_by_user_id UUID,
    last_accessed_at TIMESTAMP WITH TIME ZONE,
    access_count INTEGER DEFAULT 0,
    retention_until TIMESTAMP WITH TIME ZONE,
    compliance_tags JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_files_tenant_created ON files(tenant_id, created_at);
CREATE INDEX idx_files_file_type ON files(file_type);
CREATE INDEX idx_files_sha256_hash ON files(sha256_hash);
CREATE INDEX idx_files_is_deleted ON files(is_deleted);
```

## Testing

Run tests:
```bash
pytest backend/tests/test_file_storage.py -v
```

Test coverage:
```bash
pytest backend/tests/test_file_storage.py --cov=backend.services.file_storage --cov-report=html
```

## Performance Considerations

### File Size Limits
- Default: 500MB (configurable via `MAX_FILE_SIZE_MB`)
- Larger files use streaming to avoid memory issues

### Async Operations
- All I/O operations are async
- Encryption/decryption runs in thread pool to avoid blocking

### S3 Performance
- Uses aioboto3 for async S3 operations
- Server-side encryption (AES-256)
- Multipart upload for large files (future enhancement)

## Security Best Practices

1. **Encryption Keys**:
   - Use strong, random 32-byte keys
   - Rotate keys regularly (90 days recommended)
   - Store in secure secret management (AWS Secrets Manager, HashiCorp Vault)

2. **Access Control**:
   - Always validate tenant ownership
   - Log all file access (download, delete)
   - Implement rate limiting per tenant

3. **File Validation**:
   - Validate file extensions
   - Scan for malware (future enhancement)
   - Validate file content structure (SAF-T XML schema)

4. **S3 Security**:
   - Use IAM roles instead of access keys when possible
   - Enable S3 bucket versioning
   - Enable S3 server-side encryption
   - Restrict bucket policies to tenant-specific prefixes

## Monitoring

### Key Metrics
- Upload success/failure rate
- Average upload/download time
- Storage usage per tenant
- Encryption/decryption latency
- S3 API costs

### Logging
All operations logged with:
- `tenant_id`
- `file_id`
- `user_id`
- Operation type (upload/download/delete)
- Success/failure status
- Timing metrics

## Migration Guide

### From Local to S3

1. Update configuration:
```bash
STORAGE_BACKEND=s3
S3_BUCKET_NAME=your-bucket
S3_REGION=eu-west-1
```

2. Migrate existing files:
```python
async def migrate_to_s3():
    # Fetch all files with local storage
    local_files = await db.query(File).filter(
        File.storage_backend == "local"
    ).all()

    for file in local_files:
        # Download from local
        content = await local_storage.download(file.storage_path)

        # Upload to S3
        await s3_storage.upload(file.storage_path, content)

        # Update database
        file.storage_backend = "s3"
        await db.commit()
```

## Troubleshooting

### Common Issues

**Issue**: `FileNotFoundError` on download
- **Cause**: File deleted from storage but metadata still in DB
- **Solution**: Verify storage path exists, check S3 bucket policies

**Issue**: Integrity validation fails
- **Cause**: File corrupted or tampered with
- **Solution**: Check encryption keys, verify S3 object integrity

**Issue**: S3 connection timeout
- **Cause**: Network issues or invalid credentials
- **Solution**: Check AWS credentials, verify S3 endpoint URL

**Issue**: File too large error
- **Cause**: File exceeds `MAX_FILE_SIZE_MB`
- **Solution**: Increase limit or implement streaming upload

## License

Proprietary - EVF Portugal 2030 Platform
