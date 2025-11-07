# File Storage API Documentation

Complete API reference for file upload, download, and management operations.

## Base URL

```
http://localhost:8000/api/v1
```

Production:
```
https://api.evfportugal2030.pt/api/v1
```

## Authentication

All endpoints require authentication via JWT token in the `Authorization` header and tenant context via `X-Tenant-ID` header.

```http
Authorization: Bearer <jwt_token>
X-Tenant-ID: <tenant_uuid>
```

---

## Endpoints

### 1. Upload File

Upload and encrypt a file.

**Endpoint:** `POST /files/upload`

**Headers:**
- `Authorization: Bearer <token>`
- `X-Tenant-ID: <tenant_uuid>`
- `Content-Type: multipart/form-data`

**Form Data:**
- `file` (required): File to upload (binary)
- `file_type` (required): Type of file (saft, excel, pdf, csv, json)
- `description` (optional): File description
- `project_id` (optional): Associated EVF project ID

**Response:** `201 Created`

```json
{
  "file_id": "550e8400-e29b-41d4-a716-446655440000",
  "file_name": "company_saft_2024.xml",
  "file_type": "saft",
  "file_size_bytes": 1048576,
  "sha256_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "upload_timestamp": "2024-11-07T10:30:00Z"
}
```

**Errors:**
- `400 Bad Request`: Invalid file type or missing required fields
- `413 Payload Too Large`: File exceeds maximum size (500MB)
- `500 Internal Server Error`: Storage error

**cURL Example:**

```bash
curl -X POST "http://localhost:8000/api/v1/files/upload" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "X-Tenant-ID: 660e8400-e29b-41d4-a716-446655440000" \
  -F "file=@/path/to/company_saft_2024.xml" \
  -F "file_type=saft" \
  -F "description=Annual SAF-T file for 2024" \
  -F "project_id=proj_123"
```

**Python Example:**

```python
import httpx

async with httpx.AsyncClient() as client:
    with open("company_saft_2024.xml", "rb") as f:
        response = await client.post(
            "http://localhost:8000/api/v1/files/upload",
            headers={
                "Authorization": f"Bearer {token}",
                "X-Tenant-ID": str(tenant_id),
            },
            files={"file": f},
            data={
                "file_type": "saft",
                "description": "Annual SAF-T file",
                "project_id": "proj_123"
            }
        )
    print(response.json())
```

---

### 2. List Files

Get paginated list of files for the current tenant.

**Endpoint:** `GET /files/`

**Headers:**
- `Authorization: Bearer <token>`
- `X-Tenant-ID: <tenant_uuid>`

**Query Parameters:**
- `file_type` (optional): Filter by file type (saft, excel, pdf, csv, json)
- `project_id` (optional): Filter by project ID
- `skip` (optional): Pagination offset (default: 0)
- `limit` (optional): Number of results (default: 50, max: 100)

**Response:** `200 OK`

```json
{
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
      "metadata": {
        "project_id": "proj_123",
        "description": "Annual SAF-T file"
      }
    }
  ],
  "total": 42,
  "skip": 0,
  "limit": 50
}
```

**cURL Example:**

```bash
# List all files
curl -X GET "http://localhost:8000/api/v1/files/" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "X-Tenant-ID: 660e8400-e29b-41d4-a716-446655440000"

# Filter by file type
curl -X GET "http://localhost:8000/api/v1/files/?file_type=saft&skip=0&limit=20" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "X-Tenant-ID: 660e8400-e29b-41d4-a716-446655440000"

# Filter by project
curl -X GET "http://localhost:8000/api/v1/files/?project_id=proj_123" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "X-Tenant-ID: 660e8400-e29b-41d4-a716-446655440000"
```

---

### 3. Get File Metadata

Get detailed metadata for a specific file.

**Endpoint:** `GET /files/{file_id}`

**Headers:**
- `Authorization: Bearer <token>`
- `X-Tenant-ID: <tenant_uuid>`

**Path Parameters:**
- `file_id` (required): UUID of the file

**Response:** `200 OK`

```json
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
  "metadata": {
    "project_id": "proj_123",
    "description": "Annual SAF-T file for 2024"
  }
}
```

**Errors:**
- `404 Not Found`: File not found or deleted

**cURL Example:**

```bash
curl -X GET "http://localhost:8000/api/v1/files/550e8400-e29b-41d4-a716-446655440000" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "X-Tenant-ID: 660e8400-e29b-41d4-a716-446655440000"
```

---

### 4. Download File

Download and decrypt a file.

**Endpoint:** `GET /files/{file_id}/download`

**Headers:**
- `Authorization: Bearer <token>`
- `X-Tenant-ID: <tenant_uuid>`

**Path Parameters:**
- `file_id` (required): UUID of the file

**Response:** `200 OK`

**Headers:**
- `Content-Type`: MIME type of file (e.g., `application/xml`)
- `Content-Disposition`: `attachment; filename="company_saft_2024.xml"`
- `X-File-SHA256`: SHA-256 hash for integrity verification

**Body:** Binary file content (decrypted)

**Errors:**
- `403 Forbidden`: No permission to access file
- `404 Not Found`: File not found or deleted
- `500 Internal Server Error`: Download or decryption error

**cURL Example:**

```bash
# Download file
curl -X GET "http://localhost:8000/api/v1/files/550e8400-e29b-41d4-a716-446655440000/download" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "X-Tenant-ID: 660e8400-e29b-41d4-a716-446655440000" \
  -o downloaded_file.xml

# Verify SHA-256 hash
curl -X GET "http://localhost:8000/api/v1/files/550e8400-e29b-41d4-a716-446655440000/download" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "X-Tenant-ID: 660e8400-e29b-41d4-a716-446655440000" \
  -D - -o /dev/null | grep "X-File-SHA256"
```

**Python Example:**

```python
import httpx
import hashlib

async with httpx.AsyncClient() as client:
    response = await client.get(
        f"http://localhost:8000/api/v1/files/{file_id}/download",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Tenant-ID": str(tenant_id),
        }
    )

    # Save file
    with open("downloaded_file.xml", "wb") as f:
        f.write(response.content)

    # Verify integrity
    calculated_hash = hashlib.sha256(response.content).hexdigest()
    expected_hash = response.headers["X-File-SHA256"]

    if calculated_hash == expected_hash:
        print("✓ File integrity verified")
    else:
        print("✗ File integrity check failed!")
```

---

### 5. Delete File

Delete a file (soft delete).

**Endpoint:** `DELETE /files/{file_id}`

**Headers:**
- `Authorization: Bearer <token>`
- `X-Tenant-ID: <tenant_uuid>`

**Path Parameters:**
- `file_id` (required): UUID of the file

**Response:** `204 No Content`

**Errors:**
- `403 Forbidden`: No permission to delete file
- `404 Not Found`: File not found or already deleted
- `500 Internal Server Error`: Deletion error

**cURL Example:**

```bash
curl -X DELETE "http://localhost:8000/api/v1/files/550e8400-e29b-41d4-a716-446655440000" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "X-Tenant-ID: 660e8400-e29b-41d4-a716-446655440000"
```

---

## File Types and Extensions

| File Type | Extensions     | MIME Type                                                          | Use Case                          |
|-----------|----------------|---------------------------------------------------------------------|-----------------------------------|
| `saft`    | `.xml`         | `application/xml`                                                   | Portuguese SAF-T tax files        |
| `excel`   | `.xlsx`, `.xls`| `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` | Financial models, EVF templates   |
| `pdf`     | `.pdf`         | `application/pdf`                                                   | Generated proposals, reports      |
| `csv`     | `.csv`         | `text/csv`                                                          | Data imports/exports              |
| `json`    | `.json`        | `application/json`                                                  | Structured data, API responses    |

---

## Error Codes

| Status Code | Error Type              | Description                                    |
|-------------|------------------------|------------------------------------------------|
| 400         | Bad Request            | Invalid file type or missing required fields   |
| 401         | Unauthorized           | Missing or invalid JWT token                   |
| 403         | Forbidden              | No permission to access file (wrong tenant)    |
| 404         | Not Found              | File not found or deleted                      |
| 413         | Payload Too Large      | File exceeds maximum size (500MB)              |
| 500         | Internal Server Error  | Storage, encryption, or server error           |

---

## Rate Limits

- **Upload**: 100 requests per minute per tenant
- **Download**: 200 requests per minute per tenant
- **Delete**: 50 requests per minute per tenant
- **List**: 100 requests per minute per tenant

Rate limit headers included in all responses:
```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1699367400
```

---

## Security

### Encryption
- All files encrypted at rest with AES-256-GCM
- Encryption key stored securely (never in database)
- SHA-256 hash calculated before encryption for integrity

### Multi-Tenant Isolation
- Files accessible only to owning tenant
- Storage paths include tenant ID
- All operations validate tenant ownership

### Audit Logging
- All file operations logged (upload, download, delete)
- Logs include: user ID, IP address, timestamp, success/failure
- Logs retained for 10 years for compliance

---

## Best Practices

### 1. Always Verify File Integrity
```bash
# After download, verify SHA-256 hash matches
sha256sum downloaded_file.xml
# Compare with X-File-SHA256 header
```

### 2. Handle Large Files
```python
# For files >100MB, consider streaming
async with httpx.AsyncClient() as client:
    async with client.stream('GET', url) as response:
        with open('large_file.xml', 'wb') as f:
            async for chunk in response.aiter_bytes():
                f.write(chunk)
```

### 3. Retry Logic
```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def upload_with_retry(file):
    return await client.post("/files/upload", files={"file": file})
```

### 4. Batch Operations
```python
# Upload multiple files concurrently
import asyncio

async def upload_batch(files):
    tasks = [upload_file(f) for f in files]
    return await asyncio.gather(*tasks, return_exceptions=True)
```

---

## Testing

### Postman Collection

Import this collection to test all endpoints:

```json
{
  "info": {
    "name": "EVF Portugal 2030 - File Storage API",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "item": [
    {
      "name": "Upload File",
      "request": {
        "method": "POST",
        "header": [
          {"key": "Authorization", "value": "Bearer {{jwt_token}}"},
          {"key": "X-Tenant-ID", "value": "{{tenant_id}}"}
        ],
        "body": {
          "mode": "formdata",
          "formdata": [
            {"key": "file", "type": "file", "src": "/path/to/file.xml"},
            {"key": "file_type", "value": "saft"},
            {"key": "description", "value": "Test file"}
          ]
        },
        "url": "{{base_url}}/files/upload"
      }
    }
  ]
}
```

### Integration Test Example

```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_file_upload_download_delete():
    async with AsyncClient(base_url="http://localhost:8000") as client:
        # Upload
        with open("test.xml", "rb") as f:
            upload_response = await client.post(
                "/api/v1/files/upload",
                headers={
                    "Authorization": f"Bearer {token}",
                    "X-Tenant-ID": str(tenant_id)
                },
                files={"file": f},
                data={"file_type": "saft"}
            )
        assert upload_response.status_code == 201
        file_id = upload_response.json()["file_id"]

        # Download
        download_response = await client.get(
            f"/api/v1/files/{file_id}/download",
            headers={
                "Authorization": f"Bearer {token}",
                "X-Tenant-ID": str(tenant_id)
            }
        )
        assert download_response.status_code == 200

        # Delete
        delete_response = await client.delete(
            f"/api/v1/files/{file_id}",
            headers={
                "Authorization": f"Bearer {token}",
                "X-Tenant-ID": str(tenant_id)
            }
        )
        assert delete_response.status_code == 204
```

---

## Support

For API support:
- Documentation: `/api/v1/docs` (Swagger UI)
- ReDoc: `/api/v1/redoc`
- OpenAPI Schema: `/api/v1/openapi.json`

---

**Last Updated**: November 7, 2024
**API Version**: v1
**Base URL**: `https://api.evfportugal2030.pt/api/v1`
