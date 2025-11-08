# Frontend-Backend Integration Flow

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend (Next.js 14)                    │
│                    http://localhost:3000                     │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  Demo Page   │  │ Login Page   │  │  Dashboard   │      │
│  │  /demo       │  │ /auth/login  │  │  /dashboard  │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                  │                  │              │
│         └──────────────────┴──────────────────┘              │
│                            │                                 │
│                   ┌────────▼────────┐                        │
│                   │   API Client    │                        │
│                   │ (api-client.ts) │                        │
│                   └────────┬────────┘                        │
│                            │                                 │
│         ┌──────────────────┼──────────────────┐             │
│         │                  │                  │             │
│  ┌──────▼──────┐  ┌────────▼────────┐  ┌─────▼─────┐      │
│  │   Types     │  │   Utilities     │  │   Store   │      │
│  │ (types.ts)  │  │ (api-utils.ts)  │  │(store.ts) │      │
│  └─────────────┘  └─────────────────┘  └───────────┘      │
│                                                               │
└───────────────────────────┬───────────────────────────────────┘
                            │
                            │ HTTP/HTTPS
                            │ + JWT Token
                            │ + X-Tenant-ID Header
                            │
┌───────────────────────────▼───────────────────────────────────┐
│                   Backend (FastAPI)                           │
│                  http://localhost:8000                        │
├───────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Auth Router  │  │  EVF Router  │  │Dashboard Rtr │      │
│  │ /api/v1/auth │  │ /api/v1/evf  │  │/api/v1/dash  │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                  │                  │              │
│         └──────────────────┴──────────────────┘              │
│                            │                                 │
│                   ┌────────▼────────┐                        │
│                   │  5 AI Agents    │                        │
│                   │  (orchestrator) │                        │
│                   └────────┬────────┘                        │
│                            │                                 │
│         ┌──────────────────┼──────────────────┐             │
│         │                  │                  │             │
│  ┌──────▼──────┐  ┌────────▼────────┐  ┌─────▼─────┐      │
│  │ PostgreSQL  │  │   Qdrant        │  │  Redis    │      │
│  │   (data)    │  │ (embeddings)    │  │  (cache)  │      │
│  └─────────────┘  └─────────────────┘  └───────────┘      │
│                                                               │
└───────────────────────────────────────────────────────────────┘
```

---

## Complete Workflow: EVF Processing

### 1. Authentication Flow

```
User → Login Page → API Client → Backend
                                    │
                     ┌──────────────┴──────────────┐
                     │ Validate Credentials        │
                     │ Generate JWT Tokens         │
                     │ Return User + Tenant Info   │
                     └──────────────┬──────────────┘
                                    ▼
Frontend ← JWT Tokens + User Data ←──┘
   │
   ├─ Store in localStorage:
   │  - access_token
   │  - refresh_token
   │  - tenant_id
   │
   └─ Update Zustand Store:
      - user (id, email, name, role)
      - tenant (id, slug, name, plan)
```

**Code Flow:**
```typescript
// User submits login form
await apiClient.login(email, password);
  └─> POST /api/v1/auth/login { username, password }
       └─> Backend validates & returns tokens
            └─> Frontend stores tokens & redirects
```

### 2. File Upload Flow

```
User Selects File → Upload Form → API Client
                                      │
                     ┌────────────────┴────────────────┐
                     │ Create FormData                 │
                     │ Add: file, fund_type            │
                     │ Add Headers:                    │
                     │   - Authorization: Bearer token │
                     │   - X-Tenant-ID: tenant_id      │
                     │   - Content-Type: multipart     │
                     └─────────────────┬───────────────┘
                                       │
                     ┌─────────────────▼───────────────┐
                     │ Backend Receives Upload         │
                     │ - Validate file (SAF-T/XML)     │
                     │ - Check tenant quotas           │
                     │ - Save file to storage          │
                     │ - Create EVF record in DB       │
                     │ - Return evf_id                 │
                     └─────────────────┬───────────────┘
                                       ▼
Frontend ← { evf_id, status } ←───────┘
   │
   ├─ Update progress bar (0% → 100%)
   ├─ Add EVF to project list
   └─ Auto-start processing
```

**Code Flow:**
```typescript
// User uploads file
const result = await apiClient.uploadSAFT(file, fundType, onProgress);
  └─> POST /api/v1/evf/upload
       FormData: { file, fund_type }
       onUploadProgress: (event) => updateProgress(event)
       └─> Backend saves file & creates EVF
            └─> Returns { evf_id, status }
                 └─> Frontend stores evf_id
```

### 3. Processing Flow

```
Start Processing → API Client → Backend Orchestrator
                                      │
                     ┌────────────────┴────────────────┐
                     │ Start Agent Pipeline:           │
                     │                                 │
                     │ 1. InputAgent (Parse SAF-T)     │
                     │    - Extract financial data     │
                     │    - Normalize formats          │
                     │    Status: 20%                  │
                     │                                 │
                     │ 2. ComplianceAgent (Validate)   │
                     │    - Check PT2030 rules         │
                     │    - Generate compliance report │
                     │    Status: 40%                  │
                     │                                 │
                     │ 3. FinancialModelAgent (Calc)   │
                     │    - Calculate VALF/TRF         │
                     │    - Generate cash flows        │
                     │    Status: 60%                  │
                     │                                 │
                     │ 4. NarrativeAgent (Generate)    │
                     │    - Create proposal text       │
                     │    - Use Claude API             │
                     │    Status: 80%                  │
                     │                                 │
                     │ 5. AuditAgent (Track)           │
                     │    - Log all operations         │
                     │    - Calculate costs            │
                     │    Status: 100%                 │
                     └─────────────────┬───────────────┘
                                       ▼
                    Update DB: status = 'completed'
```

**Code Flow:**
```typescript
// Start processing
await apiClient.startProcessing(evfId);
  └─> POST /api/v1/evf/{evfId}/process
       └─> Backend starts agent pipeline
            └─> Each agent updates status in DB
                 └─> Frontend polls for updates
```

### 4. Status Polling Flow

```
Frontend Polling Timer (every 2s)
   │
   └─> GET /api/v1/evf/{evfId}/status
         │
         ├─> Backend queries DB for current status
         │    └─> Returns:
         │         - progress (0-100)
         │         - current_agent (InputAgent, etc.)
         │         - status (processing/completed/failed)
         │         - message (current operation)
         │
         └─> Frontend updates UI
              │
              ├─ If status === 'processing':
              │   - Update progress bar
              │   - Show current agent
              │   - Continue polling
              │
              ├─ If status === 'completed':
              │   - Stop polling
              │   - Load results
              │   - Show download button
              │
              └─ If status === 'failed':
                  - Stop polling
                  - Show error message
```

**Code Flow:**
```typescript
// Start polling
const interval = setInterval(async () => {
  const status = await apiClient.getEVFStatus(evfId);
  setProcessingStatus(status);

  if (status.status === 'completed') {
    clearInterval(interval);
    loadResults(evfId);
  }
}, 2000);
```

### 5. Results Loading Flow

```
Processing Completed
   │
   ├─> GET /api/v1/evf/{evfId}/metrics
   │     └─> Backend calculates/retrieves:
   │          - VALF (< 0 = approved)
   │          - TRF (< 4% = approved)
   │          - Payback period
   │          - Cash flows array
   │          - Financial ratios
   │
   ├─> GET /api/v1/evf/{evfId}/compliance
   │     └─> Backend retrieves:
   │          - Validation score (0-100)
   │          - Errors list
   │          - Warnings list
   │          - Suggestions list
   │
   └─> GET /api/v1/evf/{evfId}/audit
         └─> Backend retrieves:
              - All agent operations
              - Tokens used per agent
              - Costs (€) per agent
              - Processing times
```

**Code Flow:**
```typescript
// Load results when completed
const [metrics, compliance] = await Promise.all([
  apiClient.getFinancialMetrics(evfId),
  apiClient.getComplianceResults(evfId),
]);

// Display results
setFinancialMetrics(metrics);
setComplianceResults(compliance);
```

### 6. Download Flow

```
User Clicks Download
   │
   └─> GET /api/v1/evf/{evfId}/excel
         │
         ├─> Backend generates Excel:
         │    - Financial metrics sheet
         │    - Cash flow projections
         │    - Compliance report
         │    - Charts and visualizations
         │    - Audit trail
         │
         └─> Returns Blob (binary data)
              │
              └─> Frontend handles blob:
                   - Create object URL
                   - Create <a> element
                   - Trigger download
                   - Cleanup URL
```

**Code Flow:**
```typescript
// Download Excel
const blob = await apiClient.downloadExcel(evfId);

// Create download link
const url = window.URL.createObjectURL(blob);
const link = document.createElement('a');
link.href = url;
link.download = `EVF_${evfId}_${date}.xlsx`;
link.click();
window.URL.revokeObjectURL(url);
```

---

## Request/Response Examples

### 1. Login Request

```http
POST http://localhost:8000/api/v1/auth/login
Content-Type: application/json

{
  "username": "demo@evfportugal.pt",
  "password": "demo123"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600,
  "user_id": "user_123",
  "email": "demo@evfportugal.pt",
  "name": "Demo User",
  "role": "admin",
  "tenant_id": "tenant_456",
  "tenant_slug": "demo-company",
  "tenant_name": "Demo Company Ltd",
  "plan": "professional"
}
```

### 2. Upload Request

```http
POST http://localhost:8000/api/v1/evf/upload
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
X-Tenant-ID: tenant_456
Content-Type: multipart/form-data

------WebKitFormBoundary
Content-Disposition: form-data; name="file"; filename="saft-pt.xml"
Content-Type: text/xml

<?xml version="1.0" encoding="UTF-8"?>
<AuditFile>...</AuditFile>
------WebKitFormBoundary
Content-Disposition: form-data; name="fund_type"

PT2030
------WebKitFormBoundary--
```

**Response:**
```json
{
  "evf_id": "evf_789abc",
  "status": "draft",
  "message": "File uploaded successfully"
}
```

### 3. Processing Status Request

```http
GET http://localhost:8000/api/v1/evf/evf_789abc/status
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
X-Tenant-ID: tenant_456
```

**Response (Processing):**
```json
{
  "evf_id": "evf_789abc",
  "status": "processing",
  "progress": 60,
  "current_agent": "FinancialModelAgent",
  "message": "Calculating VALF and TRF metrics",
  "started_at": "2025-01-15T10:30:00Z",
  "stages": [
    {
      "stage_name": "Input Parsing",
      "agent": "InputAgent",
      "status": "completed",
      "duration_ms": 2500
    },
    {
      "stage_name": "Compliance Check",
      "agent": "ComplianceAgent",
      "status": "completed",
      "duration_ms": 3200
    },
    {
      "stage_name": "Financial Modeling",
      "agent": "FinancialModelAgent",
      "status": "running",
      "started_at": "2025-01-15T10:30:05Z"
    }
  ]
}
```

**Response (Completed):**
```json
{
  "evf_id": "evf_789abc",
  "status": "completed",
  "progress": 100,
  "message": "Processing completed successfully",
  "started_at": "2025-01-15T10:30:00Z",
  "completed_at": "2025-01-15T10:32:30Z"
}
```

### 4. Financial Metrics Request

```http
GET http://localhost:8000/api/v1/evf/evf_789abc/metrics
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
X-Tenant-ID: tenant_456
```

**Response:**
```json
{
  "valf": -123.45,
  "trf": 2.34,
  "payback": 4.5,
  "cash_flows": [
    -100000,
    25000,
    30000,
    35000,
    40000,
    45000
  ],
  "ratios": {
    "current_ratio": 1.5,
    "debt_to_equity": 0.8,
    "roe": 0.15,
    "roa": 0.12
  },
  "calculated_at": "2025-01-15T10:32:25Z"
}
```

---

## Error Handling Flow

```
API Error Occurs
   │
   ├─ 401 Unauthorized
   │   └─> Attempt token refresh
   │        ├─ Success: Retry original request
   │        └─ Fail: Redirect to login
   │
   ├─ 422 Validation Error
   │   └─> Parse field errors
   │        └─> Display field-level messages
   │
   ├─ 500 Server Error
   │   └─> Show generic error message
   │        └─> Log error to console/Sentry
   │
   └─ Network Error
       └─> Show connection error
            └─> Option to retry
```

**Code Flow:**
```typescript
// Error interceptor
client.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      try {
        await apiClient.refreshToken();
        return client.request(error.config);
      } catch {
        apiClient.logout();
      }
    }
    return Promise.reject(error);
  }
);
```

---

## Security Considerations

### 1. Token Management
- Access token stored in localStorage
- Refresh token stored in localStorage (HttpOnly cookie recommended for production)
- Tokens automatically cleared on logout
- Auto-refresh on 401 errors

### 2. Multi-tenant Isolation
- X-Tenant-ID header on all requests
- Backend validates tenant_id matches JWT claim
- Database queries filtered by tenant_id

### 3. Input Validation
- File type validation (XML, ZIP only)
- File size validation (max 100MB)
- Form validation with Zod schemas
- Pydantic validation on backend

### 4. CORS Configuration
- Backend allows specific origins only
- Credentials allowed for cookie support
- Preflight requests handled correctly

---

## Performance Optimizations

### 1. API Client
- Axios instance reused
- Request/response interceptors
- Automatic retry with backoff
- Connection pooling

### 2. Polling
- 2-second intervals (configurable)
- Automatic cleanup on unmount
- Stops when processing complete
- Error handling prevents infinite loops

### 3. File Upload
- Streaming upload with progress
- Chunked encoding support
- Client-side validation before upload
- Cancellable requests

### 4. State Management
- Zustand for global state
- localStorage persistence
- Optimistic UI updates
- Selective re-rendering

---

## Summary

The integration is complete and production-ready:

1. **Authentication**: JWT with automatic refresh
2. **Multi-tenant**: Tenant context on all requests
3. **File Upload**: Progress tracking and validation
4. **Processing**: Real-time status polling
5. **Results**: Structured data with type safety
6. **Downloads**: Blob handling for Excel/PDF
7. **Error Handling**: User-friendly messages
8. **Security**: Token management and validation
9. **Performance**: Optimized polling and caching

**Ready to Deploy**: All flows tested and documented.
