# EVF Portugal 2030 - Frontend Architecture

## Visual Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         EVF Portugal 2030 Frontend                       │
│                    Next.js 14 + TypeScript + Tailwind                    │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                            User Interface Layer                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐           │
│  │  Landing Page  │  │   Auth Pages   │  │   Dashboard    │           │
│  │   (Redirect)   │  │     (Login)    │  │    (Main UI)   │           │
│  └────────────────┘  └────────────────┘  └────────────────┘           │
│                                                                          │
│  Dashboard Routes (Protected):                                          │
│  ┌──────────────────────────────────────────────────────────┐          │
│  │  /dashboard           - Home with stats & recent EVFs    │          │
│  │  /dashboard/evfs      - Full EVF list with filters       │          │
│  │  /dashboard/evf/[id]  - EVF detail with tabs            │          │
│  │  /dashboard/upload    - File upload interface            │          │
│  │  /dashboard/settings  - Tenant & usage settings          │          │
│  └──────────────────────────────────────────────────────────┘          │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                          Component Architecture                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Feature Components:                                                     │
│  ┌────────────────────────────────────────────────────────────┐        │
│  │  FileUpload          - Drag & drop, validation, progress   │        │
│  │  DashboardStats      - KPI cards with real-time data       │        │
│  │  EVFList             - Table with filtering & sorting      │        │
│  │  FinancialMetrics    - VALF/TRF/Payback + Charts          │        │
│  │  ComplianceViewer    - PT2030 validation results           │        │
│  │  ProcessingStatus    - Real-time 5-agent workflow          │        │
│  │  AuditTrail          - Complete operation log              │        │
│  └────────────────────────────────────────────────────────────┘        │
│                                                                          │
│  UI Components (Shadcn/ui):                                             │
│  ┌────────────────────────────────────────────────────────────┐        │
│  │  Button, Card, Badge, Table, Progress                      │        │
│  │  (Accessible, customizable, no runtime overhead)           │        │
│  └────────────────────────────────────────────────────────────┘        │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                          State Management Layer                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────────────┐         ┌──────────────────────┐            │
│  │   Zustand Store      │         │   React Query        │            │
│  │   (Global State)     │         │  (Server State)      │            │
│  ├──────────────────────┤         ├──────────────────────┤            │
│  │ • User/Tenant        │         │ • EVF Data           │            │
│  │ • Authentication     │         │ • Metrics            │            │
│  │ • UI State           │         │ • Compliance         │            │
│  │ • Upload Progress    │         │ • Processing Status  │            │
│  │ • Notifications      │         │ • Dashboard Stats    │            │
│  └──────────────────────┘         └──────────────────────┘            │
│           │                                   │                         │
│           └───────────┬───────────────────────┘                         │
│                       │                                                 │
│                       ▼                                                 │
│              ┌─────────────────┐                                        │
│              │  LocalStorage   │                                        │
│              │  (Persistence)  │                                        │
│              └─────────────────┘                                        │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                            API Integration Layer                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌────────────────────────────────────────────────────────────┐        │
│  │                    API Client (Axios)                       │        │
│  ├────────────────────────────────────────────────────────────┤        │
│  │  • JWT Token Management (auto-refresh)                     │        │
│  │  • Multi-tenant Header Injection (X-Tenant-ID)             │        │
│  │  • Upload Progress Tracking                                 │        │
│  │  • Error Handling & Retries                                 │        │
│  │  • Type-safe Request/Response                               │        │
│  └────────────────────────────────────────────────────────────┘        │
│                              │                                          │
│                              ▼                                          │
│  ┌────────────────────────────────────────────────────────────┐        │
│  │              Backend API Endpoints                          │        │
│  ├────────────────────────────────────────────────────────────┤        │
│  │  POST   /api/v1/auth/login                                 │        │
│  │  POST   /api/v1/evf/upload                                 │        │
│  │  GET    /api/v1/evf                                        │        │
│  │  GET    /api/v1/evf/{id}                                   │        │
│  │  GET    /api/v1/evf/{id}/status                            │        │
│  │  GET    /api/v1/evf/{id}/metrics                           │        │
│  │  GET    /api/v1/evf/{id}/compliance                        │        │
│  │  GET    /api/v1/evf/{id}/audit                             │        │
│  │  GET    /api/v1/evf/{id}/excel                             │        │
│  │  GET    /api/v1/dashboard/stats                            │        │
│  │  GET    /api/v1/tenant/usage                               │        │
│  └────────────────────────────────────────────────────────────┘        │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                           Utility Layer                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐     │
│  │   Formatting     │  │   Validation     │  │     Helpers      │     │
│  ├──────────────────┤  ├──────────────────┤  ├──────────────────┤     │
│  │ • Currency       │  │ • NIF            │  │ • Class merge    │     │
│  │ • Percentage     │  │ • VALF check     │  │ • Download blob  │     │
│  │ • Date/Time      │  │ • TRF check      │  │ • Debounce       │     │
│  │ • File size      │  │ • Compliance     │  │ • Generate ID    │     │
│  │ • Duration       │  │   score          │  │ • Status color   │     │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘     │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## Data Flow Diagram

```
┌─────────────┐
│    User     │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────┐
│                   Browser (Next.js App)                      │
│                                                              │
│  1. User Action (Upload file, view EVF, etc.)              │
│  2. React Component calls API Client                        │
│  3. API Client adds JWT + Tenant ID headers                │
│  4. Request sent to Backend                                 │
│                                                              │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              FastAPI Backend (Port 8000)                     │
│                                                              │
│  1. Validate JWT token                                      │
│  2. Extract tenant_id from header                           │
│  3. Set PostgreSQL RLS context                              │
│  4. Process request with 5 agents                           │
│  5. Return response                                          │
│                                                              │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              Response Processing                             │
│                                                              │
│  1. React Query caches response                             │
│  2. Zustand updates global state if needed                  │
│  3. Component re-renders with new data                      │
│  4. User sees updated UI                                    │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Component Hierarchy

```
App Layout
└── Providers (React Query)
    └── Page Router
        ├── / (Landing)
        │   └── Redirect to /dashboard or /auth/login
        │
        ├── /auth/login
        │   └── LoginForm
        │       ├── Email Input
        │       ├── Password Input
        │       └── Submit Button
        │
        └── /dashboard (Protected)
            ├── DashboardLayout
            │   ├── Sidebar
            │   │   ├── Logo
            │   │   ├── Tenant Info
            │   │   ├── Navigation Links
            │   │   └── User Profile
            │   │
            │   ├── Header
            │   │   └── Mobile Menu Toggle
            │   │
            │   └── Main Content
            │       ├── /dashboard (Home)
            │       │   ├── DashboardStats
            │       │   │   ├── StatCard (Total EVFs)
            │       │   │   ├── StatCard (Processing)
            │       │   │   ├── StatCard (Cost)
            │       │   │   └── StatCard (Avg Time)
            │       │   └── EVFList (Recent)
            │       │
            │       ├── /dashboard/evfs
            │       │   └── EVFList (Full)
            │       │       ├── Filters
            │       │       └── Table
            │       │           ├── TableHeader
            │       │           └── TableBody
            │       │               └── TableRow (per EVF)
            │       │
            │       ├── /dashboard/upload
            │       │   ├── FundTypeSelector
            │       │   │   ├── PT2030 Card
            │       │   │   ├── PRR Card
            │       │   │   └── SITCE Card
            │       │   ├── FileUpload
            │       │   │   ├── DropZone
            │       │   │   ├── FileInfo
            │       │   │   └── UploadProgress
            │       │   └── InfoCards
            │       │
            │       ├── /dashboard/evf/[id]
            │       │   ├── Header
            │       │   │   ├── Title
            │       │   │   ├── Badges
            │       │   │   └── Actions
            │       │   ├── Tabs
            │       │   │   ├── Overview Tab
            │       │   │   │   ├── Project Info
            │       │   │   │   └── Results Summary
            │       │   │   ├── Metrics Tab
            │       │   │   │   └── FinancialMetrics
            │       │   │   │       ├── Key Metrics Cards
            │       │   │   │       ├── Cash Flow Chart
            │       │   │   │       └── Ratios Grid
            │       │   │   ├── Compliance Tab
            │       │   │   │   └── ComplianceViewer
            │       │   │   │       ├── Score Card
            │       │   │   │       ├── Errors List
            │       │   │   │       ├── Warnings List
            │       │   │   │       └── Suggestions
            │       │   │   └── Processing Tab
            │       │   │       └── ProcessingStatus
            │       │   │           ├── Progress Bar
            │       │   │           └── Agent Steps
            │       │   │               ├── InputAgent
            │       │   │               ├── ComplianceAgent
            │       │   │               ├── FinancialModelAgent
            │       │   │               ├── NarrativeAgent
            │       │   │               └── AuditAgent
            │       │   └── AuditTrail
            │       │       ├── Summary Stats
            │       │       └── Log Table
            │       │
            │       └── /dashboard/settings
            │           ├── Tenant Info Card
            │           ├── User Info Card
            │           └── Usage Stats Card
            │
            └── Notifications
                └── Toast (auto-dismiss)
```

## File Structure Tree

```
frontend/
│
├── Configuration Files
│   ├── package.json              # Dependencies & scripts
│   ├── tsconfig.json            # TypeScript config
│   ├── tailwind.config.ts       # Tailwind CSS config
│   ├── next.config.mjs          # Next.js config
│   ├── postcss.config.mjs       # PostCSS config
│   ├── .eslintrc.json          # ESLint rules
│   ├── .gitignore              # Git ignore rules
│   └── .env.local.example      # Environment template
│
├── Documentation
│   ├── README.md                # Quick start guide
│   ├── IMPLEMENTATION_GUIDE.md  # Detailed docs
│   └── setup.sh                # Setup script
│
├── app/                         # Next.js App Router
│   ├── layout.tsx              # Root layout
│   ├── page.tsx                # Landing page
│   ├── providers.tsx           # Client providers
│   ├── globals.css             # Global styles
│   │
│   ├── auth/
│   │   └── login/
│   │       └── page.tsx        # Login page
│   │
│   └── dashboard/
│       ├── layout.tsx          # Dashboard layout
│       ├── page.tsx            # Dashboard home
│       ├── evfs/
│       │   └── page.tsx        # EVF list page
│       ├── evf/
│       │   └── [id]/
│       │       └── page.tsx    # EVF detail page
│       ├── upload/
│       │   └── page.tsx        # Upload page
│       └── settings/
│           └── page.tsx        # Settings page
│
├── components/                  # React components
│   ├── ui/                     # Base UI components
│   │   ├── button.tsx
│   │   ├── card.tsx
│   │   ├── badge.tsx
│   │   ├── table.tsx
│   │   └── progress.tsx
│   │
│   ├── file-upload.tsx         # File upload component
│   ├── dashboard-stats.tsx     # KPI cards
│   ├── evf-list.tsx           # EVF table
│   ├── financial-metrics.tsx   # Charts & metrics
│   ├── compliance-viewer.tsx   # Compliance results
│   ├── processing-status.tsx   # Real-time status
│   └── audit-trail.tsx        # Audit log
│
├── lib/                        # Utilities & services
│   ├── api-client.ts          # Axios client
│   ├── store.ts               # Zustand store
│   └── utils.ts               # Helper functions
│
└── public/                     # Static assets
    └── (empty - SVG icons used)
```

## Technology Stack Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend Architecture                     │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  Framework: Next.js 14.2.5                                  │
│  • App Router (latest routing system)                       │
│  • Server Components ready                                   │
│  • Image optimization                                        │
│  • Font optimization                                         │
└─────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  Language: TypeScript 5.5+                                  │
│  • Type safety                                              │
│  • IntelliSense                                             │
│  • Better refactoring                                       │
└─────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  Styling: Tailwind CSS 3.4 + Shadcn/ui                     │
│  • Utility-first CSS                                        │
│  • JIT compiler                                             │
│  • Accessible components                                     │
│  • Customizable design system                               │
└─────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  State Management                                           │
│  ┌─────────────────────┐  ┌─────────────────────┐         │
│  │  Zustand 4.5        │  │  React Query 5.51   │         │
│  │  (Global State)     │  │  (Server State)     │         │
│  └─────────────────────┘  └─────────────────────┘         │
└─────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  HTTP Client: Axios 1.7                                     │
│  • Request/Response interceptors                            │
│  • Upload progress tracking                                 │
│  • Auto-retry                                               │
└─────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  UI Components                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  Lucide      │  │  Recharts    │  │  date-fns    │     │
│  │  React       │  │  2.12        │  │  3.6         │     │
│  │  (Icons)     │  │  (Charts)    │  │  (Dates)     │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

## Performance Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  Performance Optimizations                   │
└─────────────────────────────────────────────────────────────┘

1. Code Splitting
   ┌────────────────────────────────────────┐
   │  Route-based (automatic)               │
   │  • Each page is separate bundle        │
   │  • Lazy load on navigation             │
   └────────────────────────────────────────┘

2. Caching Strategy
   ┌────────────────────────────────────────┐
   │  React Query                           │
   │  • 5s staleTime                        │
   │  • Background refetch                  │
   │  • Optimistic updates ready            │
   └────────────────────────────────────────┘

3. Asset Optimization
   ┌────────────────────────────────────────┐
   │  • SVG icons (no image assets)        │
   │  • Next.js font optimization           │
   │  • Minified CSS/JS                     │
   └────────────────────────────────────────┘

4. Rendering Strategy
   ┌────────────────────────────────────────┐
   │  • CSR for dynamic content             │
   │  • SSR ready for public pages          │
   │  • ISR for semi-static (future)        │
   └────────────────────────────────────────┘
```

## Security Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Security Layers                           │
└─────────────────────────────────────────────────────────────┘

1. Authentication
   ┌────────────────────────────────────────┐
   │  JWT Token                             │
   │  • Stored in localStorage              │
   │  • Auto-refresh on 401                 │
   │  • Expires after inactivity            │
   └────────────────────────────────────────┘

2. API Security
   ┌────────────────────────────────────────┐
   │  Headers                               │
   │  • Authorization: Bearer <token>       │
   │  • X-Tenant-ID: <tenant_id>           │
   │  • Content-Type: application/json      │
   └────────────────────────────────────────┘

3. Input Validation
   ┌────────────────────────────────────────┐
   │  Client-side                           │
   │  • File type checking                  │
   │  • File size limits                    │
   │  • NIF validation                      │
   │  • Form validation (react-hook-form)   │
   └────────────────────────────────────────┘

4. XSS Prevention
   ┌────────────────────────────────────────┐
   │  React                                 │
   │  • Automatic escaping                  │
   │  • dangerouslySetInnerHTML avoided     │
   │  • CSP headers (future)                │
   └────────────────────────────────────────┘
```

## Deployment Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   Production Deployment                      │
└─────────────────────────────────────────────────────────────┘

Development                 Staging                 Production
    │                          │                         │
    ▼                          ▼                         ▼
┌────────┐               ┌────────┐               ┌────────┐
│ Local  │    push      │ Vercel │    promote    │ Vercel │
│ :3000  │─────────────▶│ Preview│──────────────▶│  Prod  │
└────────┘               └────────┘               └────────┘
    │                          │                         │
    │                          ▼                         ▼
    │                    ┌──────────┐            ┌──────────┐
    └───────────────────▶│ Railway  │───────────▶│ Railway  │
                         │ Backend  │            │ Backend  │
                         │  (API)   │            │  (API)   │
                         └──────────┘            └──────────┘
```

---

**Architecture Version**: 1.0.0
**Last Updated**: 2025-11-07
**Status**: Production Ready ✅
