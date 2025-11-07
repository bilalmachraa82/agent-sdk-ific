# EVF Portugal 2030 - Frontend

Professional B2B SaaS platform for automating Portuguese funding (PT2030/PRR/SITCE) application processing.

## Tech Stack

- **Framework**: Next.js 14 with App Router
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **UI Components**: Shadcn/ui
- **State Management**: Zustand
- **Data Fetching**: TanStack Query (React Query)
- **Charts**: Recharts
- **Icons**: Lucide React

## Features

### 1. File Upload Interface
- Drag & drop for SAF-T/Excel/CSV files
- Real-time upload progress
- Client-side validation
- File type and size checks

### 2. Dashboard
- Key metrics visualization (EVFs processed, costs, time)
- Recent projects list
- Quick actions and filters
- Real-time status updates

### 3. EVF Management
- Complete EVF list with filtering/sorting
- Detailed view with tabs (Overview, Metrics, Compliance, Processing)
- Financial metrics visualization (VALF, TRF, Payback)
- Cash flow projections (10-year charts)

### 4. Compliance Viewer
- PT2030/PRR rule validation results
- Errors, warnings, and suggestions display
- Compliance score with visual indicators
- Action recommendations

### 5. Processing Status
- Real-time agent progress tracking
- 5-agent workflow visualization
- Error reporting and retry options
- Completion notifications

### 6. Multi-tenant Support
- Tenant context in all API calls
- Isolated data per organization
- Usage tracking and limits
- Tenant-specific settings

## Getting Started

### Prerequisites

- Node.js 18+
- npm/pnpm/yarn

### Installation

```bash
# Install dependencies
npm install
# or
pnpm install
# or
yarn install
```

### Configuration

Create a `.env.local` file:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Development

```bash
# Run development server
npm run dev
# or
pnpm dev
# or
yarn dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

### Build

```bash
# Create production build
npm run build

# Start production server
npm start
```

## Project Structure

```
frontend/
├── app/                      # Next.js App Router
│   ├── dashboard/           # Authenticated routes
│   │   ├── layout.tsx      # Dashboard layout with sidebar
│   │   ├── page.tsx        # Dashboard home
│   │   ├── evfs/           # EVF list page
│   │   ├── evf/[id]/       # EVF detail page
│   │   ├── upload/         # File upload page
│   │   └── settings/       # Settings page
│   ├── auth/
│   │   └── login/          # Login page
│   ├── layout.tsx          # Root layout
│   ├── page.tsx            # Landing/redirect page
│   └── globals.css         # Global styles
├── components/              # React components
│   ├── ui/                 # Shadcn/ui base components
│   │   ├── button.tsx
│   │   ├── card.tsx
│   │   ├── badge.tsx
│   │   ├── table.tsx
│   │   └── progress.tsx
│   ├── file-upload.tsx     # File upload component
│   ├── dashboard-stats.tsx # Dashboard statistics
│   ├── evf-list.tsx        # EVF table list
│   ├── financial-metrics.tsx # Charts and metrics
│   ├── compliance-viewer.tsx # Compliance results
│   └── processing-status.tsx # Real-time status
├── lib/                     # Utilities and services
│   ├── api-client.ts       # Backend API client
│   ├── store.ts            # Zustand global state
│   └── utils.ts            # Helper functions
└── public/                  # Static assets
```

## Key Components

### API Client (`lib/api-client.ts`)
- Axios-based HTTP client
- Automatic JWT token management
- Token refresh on 401
- Multi-tenant header injection
- Type-safe request/response

### Store (`lib/store.ts`)
- Zustand for global state
- Persisted auth state
- Upload progress tracking
- Notification system
- Sidebar state

### File Upload (`components/file-upload.tsx`)
- Drag & drop interface
- Client-side validation
- Upload progress tracking
- Error handling
- Multiple file format support

### Financial Metrics (`components/financial-metrics.tsx`)
- VALF, TRF, Payback display
- Cash flow charts (Recharts)
- Compliance indicators
- Financial ratios grid
- Responsive design

### Processing Status (`components/processing-status.tsx`)
- Real-time polling (2s intervals)
- 5-agent workflow display
- Progress visualization
- Error reporting
- Auto-refresh on completion

## Performance Optimizations

### Code Splitting
- Automatic route-based splitting
- Dynamic imports for heavy components
- Lazy loading for charts

### Caching
- React Query with staleTime
- Optimistic updates
- Background refetching
- Cache invalidation strategies

### Image Optimization
- Next.js Image component
- WebP format conversion
- Responsive images
- Lazy loading

### Bundle Optimization
- Tree shaking
- Minification
- Compression (gzip/brotli)
- SWC compiler

## Accessibility

- Semantic HTML
- ARIA labels
- Keyboard navigation
- Focus management
- Color contrast (WCAG AA)
- Screen reader support

## API Integration

All API calls go through the `api-client.ts` singleton:

```typescript
import apiClient from '@/lib/api-client';

// Upload file
const result = await apiClient.uploadSAFT(file, 'PT2030', (progress) => {
  console.log(`Upload progress: ${progress}%`);
});

// Get EVF details
const evf = await apiClient.getEVFById(evfId);

// Download Excel
const blob = await apiClient.downloadExcel(evfId);
```

## State Management

Zustand store for global state:

```typescript
import { useStore } from '@/lib/store';

function MyComponent() {
  const { user, tenant, addNotification } = useStore();

  // Use state...
}
```

## Testing

```bash
# Run tests (when implemented)
npm test

# Type checking
npm run type-check

# Linting
npm run lint
```

## Deployment

### Vercel (Recommended)

```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
vercel --prod
```

### Docker

```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build
CMD ["npm", "start"]
```

## Environment Variables

- `NEXT_PUBLIC_API_URL` - Backend API URL
- `NEXT_PUBLIC_APP_NAME` - Application name
- `NEXT_PUBLIC_APP_URL` - Frontend URL

## Browser Support

- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)

## License

Proprietary - All rights reserved

## Support

For support, email support@evfportugal.pt
