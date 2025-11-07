# EVF Portugal 2030 Frontend - Implementation Guide

## Overview

This is a production-ready Next.js 14 frontend for the EVF Portugal 2030 platform. It provides a professional B2B SaaS interface for financial consultants to process Portuguese funding applications.

## Architecture

### Tech Stack
- **Next.js 14** with App Router for optimal performance
- **TypeScript** for type safety
- **Tailwind CSS** for responsive design
- **Shadcn/ui** for consistent component design
- **Zustand** for lightweight state management
- **React Query** for server state and caching
- **Recharts** for financial data visualization

### Design Principles
1. **Mobile-first responsive design** - Works on desktop, tablet, and mobile
2. **Component-first architecture** - Reusable, composable UI pieces
3. **Performance optimization** - <3s initial load, smooth 60fps animations
4. **Accessibility** - WCAG AA compliance with ARIA labels
5. **Multi-tenant isolation** - Tenant context in all API calls

## Key Features Implemented

### 1. Authentication & Multi-tenancy
- **Login page** (`app/auth/login/page.tsx`)
  - Email/password authentication
  - JWT token management
  - Auto-refresh on token expiry
  - Demo account support

- **Tenant context** (`lib/store.ts`, `lib/api-client.ts`)
  - Tenant ID in all API requests
  - Isolated data per organization
  - Automatic header injection

### 2. Dashboard (`app/dashboard/page.tsx`)
- **Real-time statistics**
  - EVFs processed count
  - Active processing count
  - Total costs tracking
  - Average processing time

- **Recent projects list**
  - Filterable by status and fund type
  - Quick actions (view, download)
  - Status indicators

### 3. File Upload (`components/file-upload.tsx`)
- **Drag & drop interface**
  - Support for SAF-T XML, Excel, CSV
  - File size validation (max 50MB)
  - File type validation
  - Visual feedback during drag

- **Upload progress**
  - Real-time progress bar
  - Percentage display
  - Success/error notifications

- **Client-side validation**
  - File format checking
  - Size limits enforcement
  - Quality score simulation

### 4. EVF Management

#### EVF List (`components/evf-list.tsx`)
- **Table view** with sorting/filtering
  - Filter by status (draft, processing, completed, failed)
  - Filter by fund type (PT2030, PRR, SITCE)
  - Auto-refresh every 5 seconds

- **Status indicators**
  - Color-coded badges
  - Compliance indicators (VALF, TRF)
  - Visual status changes

#### EVF Detail (`app/dashboard/evf/[id]/page.tsx`)
- **Tabbed interface**
  - Overview tab with project info
  - Metrics tab with charts
  - Compliance tab with validation results
  - Processing tab with real-time status

- **Actions**
  - Download Excel/PDF
  - Delete project
  - View audit trail

### 5. Financial Metrics (`components/financial-metrics.tsx`)
- **Key metrics display**
  - VALF (NPV) with compliance indicator
  - TRF (IRR) with compliance indicator
  - Payback period calculation

- **Cash flow visualization**
  - 10-year projection chart
  - Interactive tooltips
  - Responsive design

- **Additional ratios**
  - Grid view of financial ratios
  - Calculated metrics

### 6. Compliance Viewer (`components/compliance-viewer.tsx`)
- **Validation results**
  - Overall compliance score (0-100)
  - Valid/invalid badge
  - Progress visualization

- **Error reporting**
  - Critical errors list
  - Warnings list
  - Suggestions for correction

- **PT2030 rules checking**
  - VALF must be negative
  - TRF must be < 4%
  - Required fields validation

### 7. Processing Status (`components/processing-status.tsx`)
- **Real-time tracking**
  - Polls backend every 2 seconds
  - 5-agent workflow visualization
  - Progress percentage

- **Agent steps**
  1. InputAgent - Data validation (~30s)
  2. ComplianceAgent - Rule checking (~45s)
  3. FinancialModelAgent - Calculations (~1m)
  4. NarrativeAgent - Text generation (~2m)
  5. AuditAgent - Final audit (~15s)

- **Status indicators**
  - Completed (green check)
  - Current (blue spinner)
  - Pending (gray clock)
  - Failed (red X)

### 8. Audit Trail (`components/audit-trail.tsx`)
- **Complete log history**
  - All agent operations
  - Token consumption tracking
  - Cost per operation
  - Processing time per step

- **Summary statistics**
  - Total tokens used
  - Total cost in euros
  - Total processing time

- **Technical details**
  - Operation IDs
  - User IDs
  - Timestamps

### 9. Settings (`app/dashboard/settings/page.tsx`)
- **Organization info**
  - Tenant name and slug
  - Plan type (starter/professional/enterprise)
  - Tenant ID

- **User profile**
  - Email and name
  - Role (admin/member/viewer)

- **Usage statistics**
  - EVFs processed this month
  - Tokens consumed
  - Storage used
  - Cost tracking

## Component Library

### UI Components (`components/ui/`)
All components follow Shadcn/ui patterns:

- **Button** - Multiple variants (default, outline, ghost, destructive)
- **Card** - Container with header, content, footer sections
- **Badge** - Status indicators with color variants
- **Table** - Responsive data table
- **Progress** - Animated progress bar
- **Input** - Form inputs (future)
- **Select** - Dropdowns (future)
- **Dialog** - Modals (future)

### Feature Components (`components/`)

#### FileUpload
```typescript
<FileUpload
  fundType="PT2030"
  onUploadComplete={(evfId) => router.push(`/evf/${evfId}`)}
  onError={(error) => console.error(error)}
/>
```

#### FinancialMetrics
```typescript
<FinancialMetrics evfId={evfId} />
```

#### ComplianceViewer
```typescript
<ComplianceViewer evfId={evfId} />
```

#### ProcessingStatus
```typescript
<ProcessingStatus
  evfId={evfId}
  onComplete={() => refetch()}
  onError={() => showError()}
/>
```

## State Management

### Zustand Store (`lib/store.ts`)

```typescript
interface AppState {
  // Auth
  user: User | null;
  tenant: Tenant | null;
  isAuthenticated: boolean;

  // UI
  sidebarOpen: boolean;

  // Uploads
  uploads: Record<string, UploadProgress>;

  // Notifications
  notifications: Notification[];
}
```

Usage:
```typescript
import { useStore } from '@/lib/store';

function MyComponent() {
  const { user, tenant, addNotification } = useStore();

  addNotification({
    type: 'success',
    title: 'Upload complete',
    message: 'Your file was processed successfully',
  });
}
```

### React Query

Configured for optimal caching:
```typescript
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5000,
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});
```

## API Integration

### API Client (`lib/api-client.ts`)

Single axios instance with:
- Automatic JWT injection
- Tenant ID header
- Token refresh on 401
- Error handling
- Upload progress tracking

Example usage:
```typescript
import apiClient from '@/lib/api-client';

// Upload file
const { evf_id } = await apiClient.uploadSAFT(
  file,
  'PT2030',
  (progress) => console.log(`${progress}%`)
);

// Get EVF
const evf = await apiClient.getEVFById(evfId);

// Get metrics
const metrics = await apiClient.getFinancialMetrics(evfId);

// Download Excel
const blob = await apiClient.downloadExcel(evfId);
downloadBlob(blob, 'evf.xlsx');
```

## Utilities (`lib/utils.ts`)

### Formatting
- `formatCurrency(amount)` - EUR formatting
- `formatPercent(value, decimals)` - Percentage
- `formatDate(date, includeTime)` - Portuguese date format
- `formatRelativeTime(date)` - "há 2 horas"
- `formatDuration(ms)` - "1m 30s"
- `formatFileSize(bytes)` - "1.5 MB"

### Validation
- `validateNIF(nif)` - Portuguese tax ID validation
- `isVALFCompliant(valf)` - VALF < 0 check
- `isTRFCompliant(trf)` - TRF < 4% check

### Helpers
- `cn(...classes)` - Merge Tailwind classes
- `downloadBlob(blob, filename)` - Download files
- `debounce(func, wait)` - Debounce function calls
- `generateId()` - Generate unique IDs

## Responsive Design

### Breakpoints
```css
sm: 640px   /* Mobile landscape */
md: 768px   /* Tablet */
lg: 1024px  /* Desktop */
xl: 1280px  /* Large desktop */
2xl: 1536px /* Extra large */
```

### Mobile-first approach
```tsx
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
  {/* Stacks on mobile, 2 cols on tablet, 3 cols on desktop */}
</div>
```

### Sidebar behavior
- Hidden on mobile (hamburger menu)
- Visible on desktop (always shown)
- Slide-in animation
- Overlay on mobile when open

## Performance

### Code Splitting
- Automatic route-based splitting
- Dynamic imports for heavy components:
```typescript
const HeavyChart = dynamic(() => import('@/components/heavy-chart'), {
  loading: () => <Skeleton />,
  ssr: false,
});
```

### Image Optimization
```typescript
import Image from 'next/image';

<Image
  src="/logo.png"
  alt="Logo"
  width={200}
  height={50}
  priority // For above-fold images
/>
```

### Caching Strategy
- API responses cached with React Query
- Static pages pre-rendered at build time
- Dynamic pages with ISR (future)

## Accessibility

### Semantic HTML
```tsx
<nav aria-label="Main navigation">
  <ul role="list">
    <li><a href="/dashboard">Dashboard</a></li>
  </ul>
</nav>
```

### ARIA Labels
```tsx
<button aria-label="Eliminar EVF" onClick={handleDelete}>
  <Trash2 />
</button>
```

### Keyboard Navigation
- Tab order preserved
- Focus styles visible
- Keyboard shortcuts (future)

### Color Contrast
- Text meets WCAG AA standards
- Status colors distinguishable
- High contrast mode support (future)

## Testing Strategy (Future)

### Unit Tests
```typescript
// Example with Vitest
describe('formatCurrency', () => {
  it('formats EUR correctly', () => {
    expect(formatCurrency(1234.56)).toBe('€1,234.56');
  });
});
```

### Component Tests
```typescript
// Example with React Testing Library
it('uploads file successfully', async () => {
  render(<FileUpload fundType="PT2030" />);

  const file = new File(['content'], 'test.xml', { type: 'text/xml' });
  const input = screen.getByLabelText('Selecionar Ficheiro');

  fireEvent.change(input, { target: { files: [file] } });

  await waitFor(() => {
    expect(screen.getByText('Válido')).toBeInTheDocument();
  });
});
```

### E2E Tests
```typescript
// Example with Playwright
test('complete EVF workflow', async ({ page }) => {
  await page.goto('/dashboard/upload');
  await page.setInputFiles('input[type="file"]', 'test.xml');
  await page.click('button:has-text("Enviar")');

  await expect(page).toHaveURL(/\/evf\/\w+/);
  await expect(page.locator('text=Concluído')).toBeVisible();
});
```

## Deployment

### Environment Variables

```env
# .env.local
NEXT_PUBLIC_API_URL=https://api.evfportugal.pt
NEXT_PUBLIC_APP_URL=https://app.evfportugal.pt
```

### Vercel Deployment

```bash
# Install Vercel CLI
npm i -g vercel

# Login
vercel login

# Deploy
vercel --prod
```

### Docker Deployment

```dockerfile
FROM node:18-alpine AS deps
WORKDIR /app
COPY package*.json ./
RUN npm ci

FROM node:18-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

FROM node:18-alpine AS runner
WORKDIR /app
ENV NODE_ENV production
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

EXPOSE 3000
CMD ["node", "server.js"]
```

## Performance Targets

### Metrics
- **Initial Load**: < 3 seconds
- **Time to Interactive**: < 5 seconds
- **First Contentful Paint**: < 1.5 seconds
- **API Response Handling**: < 100ms
- **Animations**: 60fps

### Optimization Techniques
1. **Code splitting** - Dynamic imports
2. **Image optimization** - Next.js Image
3. **CSS purging** - Tailwind JIT
4. **Bundle analysis** - @next/bundle-analyzer
5. **Lazy loading** - Below-fold content

## Security

### XSS Prevention
- All user input sanitized
- React automatic escaping
- CSP headers (future)

### CSRF Protection
- JWT tokens in headers
- SameSite cookies
- CORS configuration

### Data Protection
- HTTPS only in production
- Secure token storage
- No sensitive data in localStorage

## Browser Support

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## Future Enhancements

### Phase 2
- [ ] Advanced filtering/search
- [ ] Bulk operations
- [ ] Export to multiple formats
- [ ] Custom report builder

### Phase 3
- [ ] Real-time collaboration
- [ ] Comments and annotations
- [ ] Version history
- [ ] Template management

### Phase 4
- [ ] Mobile apps (React Native)
- [ ] Offline support (PWA)
- [ ] Advanced analytics
- [ ] AI-powered insights

## Maintenance

### Dependencies
```bash
# Check outdated packages
npm outdated

# Update all dependencies
npm update

# Update major versions
npx npm-check-updates -u
npm install
```

### Monitoring
- Vercel Analytics (built-in)
- Sentry for error tracking (future)
- Google Analytics (future)

## Support

For questions or issues:
- Email: dev@evfportugal.pt
- Docs: https://docs.evfportugal.pt
- GitHub: https://github.com/evfportugal/frontend

---

**Version**: 1.0.0
**Last Updated**: 2025-11-07
**Status**: Production Ready
