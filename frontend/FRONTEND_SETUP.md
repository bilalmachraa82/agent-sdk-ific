# Frontend Setup & Configuration Guide

## Overview

The frontend is now fully configured to connect to the FastAPI backend at `http://localhost:8000`. All authentication, API calls, and error handling are implemented.

## Files Created/Updated

### 1. Environment Configuration
- `.env.local` - Environment variables with API URL configuration

### 2. API Integration
- `lib/api-client.ts` - Complete API client with:
  - JWT authentication (login, refresh, logout)
  - Token storage in localStorage
  - Automatic token refresh on 401 errors
  - Multi-tenant support (X-Tenant-ID header)
  - All EVF endpoints (upload, process, status, download)
  - Dashboard stats and tenant usage endpoints

### 3. TypeScript Types
- `lib/types.ts` - Complete type definitions for:
  - Authentication (LoginRequest, LoginResponse, etc.)
  - EVF Projects (EVFProject, EVFStatus, FundType)
  - Financial Metrics (FinancialMetrics, CashFlow)
  - Compliance (ComplianceResult, ComplianceRule)
  - Processing Status (ProcessingStatus, ProcessingStage)
  - Audit Logs (AuditLog, AuditSummary)
  - Dashboard (DashboardStats, TenantUsage)
  - Paginated responses and error types

### 4. Utility Functions
- `lib/api-utils.ts` - Helper functions:
  - Error parsing and formatting
  - File size/date/currency formatting
  - File validation (type, size)
  - Retry logic with exponential backoff
  - Debounce, sleep, clipboard utilities
  - EVF compliance checking

### 5. Demo Page
- `app/demo/page.tsx` - Complete workflow demonstration:
  - Login form with demo credentials
  - EVF project list with refresh
  - File upload with progress bar
  - Real-time processing status with polling
  - Financial metrics display
  - Compliance results display
  - Excel report download

## Running the Frontend

### 1. Install Dependencies
```bash
cd frontend
npm install
```

### 2. Configure Environment
The `.env.local` file is already created with:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 3. Start Development Server
```bash
npm run dev
```

The frontend will start at `http://localhost:3000`

### 4. Access the Demo
Navigate to: `http://localhost:3000/demo`

## Demo Page Features

### Authentication
- Login with demo credentials:
  - Email: `demo@evfportugal.pt`
  - Password: `demo123`
- Automatic token storage and refresh
- Logout functionality

### File Upload
1. Select fund type (PT2030, PRR, or SITCE)
2. Choose SAF-T file (XML or ZIP)
3. Upload with progress indicator
4. Automatic processing start

### Processing Status
- Real-time progress updates (polls every 2 seconds)
- Current agent display
- Stage-by-stage progress
- Error display if processing fails

### Results Display
- **Financial Metrics:**
  - VALF (approval indicator)
  - TRF (approval indicator)
  - Payback period
  - Cash flows

- **Compliance Check:**
  - Validation score (0-100)
  - Errors list
  - Warnings list
  - Suggestions

### Export
- Download Excel report with all results
- Automatic filename generation

## API Client Usage

### Basic Authentication
```typescript
import apiClient from '@/lib/api-client';

// Login
const response = await apiClient.login('user@example.com', 'password');

// Check authentication
const isAuth = apiClient.isAuthenticated();

// Logout
apiClient.logout();
```

### EVF Operations
```typescript
// List EVF projects
const { items, total } = await apiClient.getEVFList({
  status: 'completed',
  limit: 10,
  offset: 0,
});

// Upload SAF-T file
const result = await apiClient.uploadSAFT(
  file,
  'PT2030',
  (progress) => console.log(`Upload: ${progress}%`)
);

// Start processing
await apiClient.startProcessing(evfId);

// Get processing status
const status = await apiClient.getEVFStatus(evfId);

// Get results
const metrics = await apiClient.getFinancialMetrics(evfId);
const compliance = await apiClient.getComplianceResults(evfId);

// Download Excel
const blob = await apiClient.downloadExcel(evfId);
```

### Error Handling
```typescript
import { parseAPIError } from '@/lib/api-utils';

try {
  await apiClient.uploadSAFT(file, 'PT2030');
} catch (error) {
  const message = parseAPIError(error);
  console.error(message);
}
```

## State Management

The app uses Zustand for global state management (`lib/store.ts`):

```typescript
import { useStore } from '@/lib/store';

function MyComponent() {
  const { user, tenant, setUser, logout } = useStore();

  // User and tenant are automatically persisted
  console.log(user?.email);
  console.log(tenant?.name);
}
```

## TypeScript Types

All API responses are fully typed:

```typescript
import type {
  EVFProject,
  FinancialMetrics,
  ComplianceResult,
  ProcessingStatus
} from '@/lib/types';

const project: EVFProject = {
  id: '123',
  tenant_id: 'tenant-1',
  company_name: 'ACME Corp',
  fund_type: 'PT2030',
  status: 'completed',
  valf: -123.45,
  trf: 2.34,
  // ...
};
```

## API Endpoints

The API client implements all backend endpoints:

### Authentication
- `POST /api/v1/auth/login` - Login
- `POST /api/v1/auth/refresh` - Refresh token

### EVF Management
- `GET /api/v1/evf` - List EVF projects
- `POST /api/v1/evf` - Create EVF project
- `GET /api/v1/evf/{id}` - Get EVF details
- `PATCH /api/v1/evf/{id}` - Update EVF
- `DELETE /api/v1/evf/{id}` - Delete EVF
- `POST /api/v1/evf/upload` - Upload SAF-T file
- `POST /api/v1/evf/{id}/process` - Start processing
- `GET /api/v1/evf/{id}/status` - Get processing status
- `GET /api/v1/evf/{id}/metrics` - Get financial metrics
- `GET /api/v1/evf/{id}/compliance` - Get compliance results
- `GET /api/v1/evf/{id}/audit` - Get audit logs
- `GET /api/v1/evf/{id}/excel` - Download Excel report
- `GET /api/v1/evf/{id}/pdf` - Download PDF report

### Dashboard
- `GET /api/v1/dashboard/stats` - Get dashboard statistics

### Tenant
- `GET /api/v1/tenant/usage` - Get tenant usage metrics

## Testing the Integration

### 1. Start Backend
```bash
cd ../backend
uvicorn main:app --reload --port 8000
```

### 2. Start Frontend
```bash
cd frontend
npm run dev
```

### 3. Test Workflow
1. Navigate to `http://localhost:3000/demo`
2. Login with demo credentials
3. Upload a test SAF-T file
4. Watch real-time processing
5. View financial metrics and compliance
6. Download Excel report

## Error Handling

The API client includes comprehensive error handling:

- **401 Unauthorized:** Automatically refreshes token or redirects to login
- **422 Validation Error:** Parses and displays field-level errors
- **500 Server Error:** User-friendly error messages
- **Network Error:** Timeout and connection error handling

## Security Features

1. **JWT Authentication:** Access and refresh tokens
2. **Token Storage:** Secure localStorage with automatic initialization
3. **Multi-tenant Isolation:** X-Tenant-ID header on all requests
4. **Request Interceptors:** Auto-add auth headers
5. **Response Interceptors:** Auto-refresh expired tokens

## Performance Optimizations

1. **Automatic Token Refresh:** No login interruptions
2. **Progress Callbacks:** Real-time upload feedback
3. **Polling with Cleanup:** Efficient status monitoring
4. **Retry Logic:** Built-in exponential backoff for failed requests
5. **Debouncing:** Prevent excessive API calls

## Debugging

Enable detailed logging:
```typescript
// In api-client.ts, add console.log statements
this.client.interceptors.request.use((config) => {
  console.log('Request:', config.method, config.url);
  return config;
});

this.client.interceptors.response.use((response) => {
  console.log('Response:', response.status, response.data);
  return response;
});
```

## Production Deployment

### Environment Variables
```env
# Production API
NEXT_PUBLIC_API_URL=https://api.evfportugal.pt

# App URLs
NEXT_PUBLIC_APP_URL=https://app.evfportugal.pt
```

### Build
```bash
npm run build
npm run start
```

### Deploy to Vercel
```bash
vercel --prod
```

## Troubleshooting

### CORS Issues
Ensure backend has CORS configured for frontend origin:
```python
# backend/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Authentication Issues
- Check browser console for token storage
- Verify backend returns correct token structure
- Confirm X-Tenant-ID header is sent

### Upload Issues
- Check file size limits (backend config)
- Verify Content-Type header for multipart/form-data
- Monitor upload progress callback

## Next Steps

1. **Add Real-time WebSocket:** For live processing updates
2. **Implement Caching:** React Query for data caching
3. **Add Optimistic UI:** Immediate feedback before API response
4. **Implement Analytics:** Track user actions and errors
5. **Add E2E Tests:** Playwright or Cypress tests

## Support

For issues or questions:
- Check backend logs: `backend/logs/`
- Check browser console for frontend errors
- Review API client implementation: `lib/api-client.ts`
- Test endpoints directly with curl or Postman
