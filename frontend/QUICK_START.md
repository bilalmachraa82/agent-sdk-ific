# Frontend Quick Start Guide

## Installation & Running

```bash
# 1. Install dependencies
npm install

# 2. Start development server
npm run dev

# 3. Open browser
# http://localhost:3000/demo
```

## Demo Credentials

```
Email: demo@evfportugal.pt
Password: demo123
```

## API Configuration

Already configured in `.env.local`:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Files to Know

```
lib/
├── api-client.ts      # All API methods
├── types.ts           # TypeScript types
├── api-utils.ts       # Helper functions
└── store.ts           # Global state (Zustand)

app/
├── demo/page.tsx      # Complete workflow demo
├── auth/login/        # Login page
└── dashboard/         # Dashboard pages
```

## API Client Quick Reference

```typescript
import apiClient from '@/lib/api-client';

// Authentication
await apiClient.login(email, password);
apiClient.logout();

// EVF Operations
await apiClient.uploadSAFT(file, fundType, onProgress);
await apiClient.startProcessing(evfId);
await apiClient.getEVFStatus(evfId);
await apiClient.getFinancialMetrics(evfId);
await apiClient.getComplianceResults(evfId);
await apiClient.downloadExcel(evfId);
```

## Testing Workflow

1. Start backend: `uvicorn main:app --reload --port 8000`
2. Start frontend: `npm run dev`
3. Navigate to: `http://localhost:3000/demo`
4. Login with demo credentials
5. Upload SAF-T file
6. Watch real-time processing
7. Download Excel report

## Backend Must Have

- POST `/api/v1/auth/login` with `username` and `password` fields
- CORS enabled for `http://localhost:3000`
- X-Tenant-ID header support
- All EVF endpoints implemented

## Common Issues

**CORS Error**: Add CORS middleware to backend for localhost:3000
**Login Fails**: Backend must use `username` field, not `email`
**Upload Fails**: Check backend file size limits
**Status Not Updating**: Verify polling is running (2-second intervals)

## Need Help?

See `FRONTEND_SETUP.md` for detailed documentation.
