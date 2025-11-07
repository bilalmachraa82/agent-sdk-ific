# File Storage Quick Start Guide

## 5-Minute Setup

### 1. Install Dependencies
```bash
pip install aioboto3 boto3 cryptography
```

### 2. Configure Environment (.env)
```bash
# Local storage (development)
STORAGE_BACKEND=local
LOCAL_STORAGE_PATH=storage/uploads
MAX_FILE_SIZE_MB=500
ENCRYPTION_KEY=your-32-byte-key-here

# OR S3 storage (production)
STORAGE_BACKEND=s3
S3_BUCKET_NAME=evf-portugal-2030
S3_REGION=eu-west-1
S3_ACCESS_KEY=your-access-key
S3_SECRET_KEY=your-secret-key
```

### 3. Run Database Migration
```bash
cd backend
alembic revision --autogenerate -m "Add file storage tables"
alembic upgrade head
```

### 4. Test Implementation
```bash
python backend/services/validate_file_storage.py
```

## Basic Usage

### Upload a File
```python
from backend.services.file_storage import file_storage_service

# In your FastAPI endpoint
@router.post("/upload")
async def upload(file: UploadFile, tenant_id: UUID, user_id: UUID):
    metadata = await file_storage_service.upload_file(
        tenant_id=tenant_id,
        file=file,
        file_type="saft",  # or "excel", "pdf", "csv", "json"
        user_id=user_id
    )
    return {"file_id": metadata.id, "hash": metadata.sha256_hash}
```

### Download a File
```python
from backend.services.file_storage import FileMetadata

@router.get("/download/{file_id}")
async def download(file_id: UUID, tenant_id: UUID, db: AsyncSession):
    # Get metadata from database
    db_file = await db.get(File, file_id)
    metadata = FileMetadata(**db_file.to_metadata_dict())

    # Download content
    content = await file_storage_service.download_file(
        tenant_id=tenant_id,
        file_id=file_id,
        metadata=metadata
    )

    return Response(content=content, media_type=metadata.mime_type)
```

### Delete a File
```python
@router.delete("/delete/{file_id}")
async def delete(file_id: UUID, tenant_id: UUID, db: AsyncSession):
    db_file = await db.get(File, file_id)
    metadata = FileMetadata(**db_file.to_metadata_dict())

    await file_storage_service.delete_file(
        tenant_id=tenant_id,
        file_id=file_id,
        metadata=metadata
    )

    db_file.is_deleted = True
    await db.commit()
    return {"success": True}
```

## Common Patterns

### Save to Database After Upload
```python
from backend.models.file import File

metadata = await file_storage_service.upload_file(...)

db_file = File(
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
)
db.add(db_file)
await db.commit()
```

### List Files with Pagination
```python
from sqlalchemy import select

query = select(File).where(
    File.tenant_id == tenant_id,
    File.is_deleted == False
).order_by(File.created_at.desc()).offset(skip).limit(limit)

result = await db.execute(query)
files = result.scalars().all()
```

### Add Custom Metadata
```python
metadata = await file_storage_service.upload_file(
    tenant_id=tenant_id,
    file=file,
    file_type="saft",
    additional_metadata={
        "project_id": "proj_123",
        "description": "Annual SAF-T file",
        "fiscal_year": 2024,
        "company_id": "comp_456"
    }
)
```

## Error Handling

```python
from backend.services.file_storage import (
    FileSizeLimitError,
    FileTypeNotAllowedError,
    FileStorageError,
    FileNotFoundError
)

try:
    metadata = await file_storage_service.upload_file(...)
except FileSizeLimitError:
    raise HTTPException(413, "File too large")
except FileTypeNotAllowedError:
    raise HTTPException(400, "Invalid file type")
except FileStorageError:
    raise HTTPException(500, "Storage error")
```

## Supported File Types

| Type   | Extensions     | MIME Type                                                          |
|--------|----------------|---------------------------------------------------------------------|
| saft   | .xml           | application/xml                                                     |
| excel  | .xlsx, .xls    | application/vnd.openxmlformats-officedocument.spreadsheetml.sheet  |
| pdf    | .pdf           | application/pdf                                                     |
| csv    | .csv           | text/csv                                                            |
| json   | .json          | application/json                                                    |

## Security Checklist

- ✅ All files encrypted with AES-256-GCM
- ✅ SHA-256 integrity validation
- ✅ Multi-tenant isolation (tenant_id required)
- ✅ File size limits enforced
- ✅ File type validation
- ✅ Audit logging for all operations
- ✅ Permission validation

## Testing

```bash
# Run tests
pytest backend/tests/test_file_storage.py -v

# Test coverage
pytest backend/tests/test_file_storage.py --cov=backend.services.file_storage

# Validate implementation
python backend/services/validate_file_storage.py
```

## Troubleshooting

**File not found after upload**
- Check storage path exists
- Verify S3 credentials if using S3
- Check database for file record

**Encryption error**
- Verify ENCRYPTION_KEY is set in .env
- Key must be at least 8 characters
- Use strong random keys in production

**Permission denied**
- Ensure tenant_id matches
- Check user has access to tenant
- Verify file is not deleted (is_deleted=False)

**File too large**
- Check MAX_FILE_SIZE_MB setting
- Default is 500MB
- Increase if needed for your use case

## Next Steps

1. Read full documentation: `FILE_STORAGE_README.md`
2. Review API examples: `backend/api/files.py`
3. Check implementation summary: `FILE_STORAGE_IMPLEMENTATION.md`
4. Run validation script: `validate_file_storage.py`

## Quick Links

- **Service**: `backend/services/file_storage.py`
- **API**: `backend/api/files.py`
- **Models**: `backend/models/file.py`
- **Schemas**: `backend/schemas/file.py`
- **Tests**: `backend/tests/test_file_storage.py`
- **Docs**: `backend/services/FILE_STORAGE_README.md`

---

**Need Help?** Check the full documentation or run the validation script for detailed diagnostics.
