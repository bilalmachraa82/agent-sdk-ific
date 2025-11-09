# EVF Portugal 2030: Premium 2.0 Architecture Blueprint

**Date**: November 9, 2025
**Version**: 2.0 (Post-Sprint 1 Security Foundation)
**Status**: Planning & Prioritization

---

## 🎯 Vision

Transform EVF Portugal 2030 from a secure multi-tenant platform into a **premium AI-powered B2B SaaS** with:
- **World-class UX**: Guided workflows, real-time collaboration, self-service analytics
- **Enterprise-grade reliability**: 99.9% SLA, autoscaling, comprehensive observability
- **AI-first workflows**: Multi-agent orchestration with safety rails and knowledge hygiene
- **Developer-friendly**: Modern stack (Next.js 15, FastAPI, LangGraph), CI/CD automation
- **Compliance-ready**: GDPR, field-level encryption, audit trails

---

## 📐 Architecture Overview

### Current State (Post-Sprint 1)
✅ Multi-tenant FastAPI backend with RLS
✅ RS256 JWT + Argon2id authentication
✅ Next.js 14 frontend with Shadcn/ui
✅ PostgreSQL 16 with Row-Level Security
✅ LangGraph agents (5 specialized sub-agents)
✅ Qdrant vector store for knowledge base
✅ 92% test coverage on security layer

### Target State (Premium 2.0)
```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend (Next.js 15)                    │
│  • App Router + Server Components                            │
│  • Server Actions for mutations                              │
│  • Real-time collaboration (Zustand + React Query)           │
│  • Optimistic UI updates                                     │
└─────────────────────────────────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   API Gateway (FastAPI)                      │
│  • Service Layer (tenants, auth, evf, files)                │
│  • OpenTelemetry tracing                                     │
│  • Rate limiting per tenant                                  │
│  • Feature flags (ConfigCat)                                 │
└─────────────────────────────────────────────────────────────┘
         ▼                    ▼                    ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│ Background Queue │ │  LangGraph Agents│ │  Analytics API   │
│  • Dramatiq      │ │  • 5 sub-agents  │ │  • Materialized  │
│  • File parsing  │ │  • Safety rails  │ │    views         │
│  • Notifications │ │  • Tenant context│ │  • DuckDB export │
└──────────────────┘ └──────────────────┘ └──────────────────┘
         ▼                    ▼                    ▼
┌─────────────────────────────────────────────────────────────┐
│              Data Layer (PostgreSQL 16 + Redis)              │
│  • RLS enforcement (SET LOCAL)                               │
│  • Materialized views (mv_tenant_stats)                      │
│  • Partitioned audit_logs (monthly)                          │
│  • Read replica for analytics                                │
└─────────────────────────────────────────────────────────────┘
         ▼                    ▼                    ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│ Vector Store     │ │ Object Storage   │ │ Monitoring       │
│  • Qdrant Cloud  │ │  • S3/R2         │ │  • Grafana Cloud │
│  • Per-tenant NS │ │  • SAF-T files   │ │  • Prometheus    │
│  • TTL policies  │ │  • PDFs/Excel    │ │  • Sentry        │
└──────────────────┘ └──────────────────┘ └──────────────────┘
```

---

## 🎨 1. Product & UX

### 1.1 Guided Onboarding
**Goal**: Reduce time-to-value from 24h to 1h

**Implementation**:
```typescript
// frontend/app/auth/onboarding/page.tsx
export default function OnboardingWizard() {
  const steps = [
    { id: 'company', component: CompanyInfoStep },
    { id: 'templates', component: TemplateSelectionStep },
    { id: 'saft-sample', component: SAFTUploadStep },
    { id: 'team', component: TeamInviteStep }
  ]

  return <WizardFlow steps={steps} onComplete={provisionTenant} />
}
```

**Backend**:
```python
# backend/services/onboarding.py
async def provision_tenant(data: OnboardingData) -> Tenant:
    """
    1. Create tenant + admin user
    2. Provision default templates
    3. Upload sample SAF-T
    4. Send welcome email
    """
    async with db_transaction() as db:
        tenant = await create_tenant(db, data)
        await provision_templates(db, tenant.id)
        await upload_sample_saft(db, tenant.id, data.saft_file)
        await send_welcome_email(tenant.admin_email)
    return tenant
```

### 1.2 End-User Dashboards
**Goal**: Real-time insights without waiting for reports

**Routes**:
- `/dashboard/insights` - Aggregated metrics (EVFs in progress, avg processing time, cost savings)
- `/dashboard/pipeline` - Visual pipeline (uploaded → parsed → compliance → financial → narrative)
- `/dashboard/cost-analysis` - Cost breakdown per EVF, ROI tracking

**Backend API**:
```python
# backend/api/routers/analytics.py
@router.get("/analytics/insights")
@require_rls
async def get_insights(
    db: AsyncSession = Depends(get_db_with_tenant),
    period: str = Query("30d")
):
    """Get tenant analytics from materialized view."""
    result = await db.execute(
        select(MVTenantStats).where(
            MVTenantStats.period == period
        )
    )
    return result.scalar_one()
```

### 1.3 Workflow Timeline
**Goal**: Transparency into agent processing

**Data Model**:
```python
# backend/models/evf.py
class EVFProject(Base):
    # Existing fields...
    status_history: Mapped[List[dict]] = mapped_column(JSONB)

    # Example history entry:
    # {
    #   "status": "compliance_check",
    #   "timestamp": "2025-11-09T10:30:00Z",
    #   "agent": "EVFComplianceAgent",
    #   "duration_ms": 1234,
    #   "result": "approved"
    # }
```

**UI Component**:
```typescript
// frontend/components/workflow-timeline.tsx
export function WorkflowTimeline({ evfId }: Props) {
  const { data } = useQuery(['evf-timeline', evfId], fetchTimeline)

  return (
    <Timeline>
      {data.history.map(step => (
        <TimelineStep
          key={step.timestamp}
          status={step.status}
          agent={step.agent}
          duration={step.duration_ms}
        />
      ))}
    </Timeline>
  )
}
```

---

## 🏗️ 2. Backend Domain Architecture

### 2.1 Service Layer Split

**Structure**:
```
backend/
├── api/
│   └── routers/          # Thin HTTP layer
│       ├── auth.py
│       ├── evf.py
│       └── files.py
├── services/             # Business logic (NEW)
│   ├── __init__.py
│   ├── tenant_service.py
│   ├── auth_service.py
│   ├── evf_service.py
│   └── file_service.py
├── domain/               # Domain models (NEW)
│   ├── __init__.py
│   ├── tenant.py
│   └── evf.py
└── infrastructure/       # External integrations (NEW)
    ├── __init__.py
    ├── claude_client.py
    └── qdrant_client.py
```

**Example Service**:
```python
# backend/services/evf_service.py
from backend.domain.evf import EVF, EVFStatus
from backend.infrastructure.claude_client import claude

class EVFService:
    """Business logic for EVF operations."""

    async def create_evf(
        self,
        db: AsyncSession,
        tenant_id: str,
        data: CreateEVFRequest
    ) -> EVF:
        """Create new EVF project."""
        # Validate
        if await self._evf_exists(db, data.name, tenant_id):
            raise ValueError("EVF already exists")

        # Create
        evf = EVF(tenant_id=tenant_id, **data.dict())
        db.add(evf)
        await db.commit()

        # Emit event
        await self._emit_event("evf.created", evf)

        # Trigger background processing
        await self._enqueue_processing(evf.id)

        return evf

    async def process_evf(
        self,
        db: AsyncSession,
        evf_id: str
    ) -> EVFResult:
        """Process EVF through agent pipeline."""
        async with rls_enforced_session(db, evf.tenant_id, "process_evf"):
            # Run LangGraph pipeline
            result = await self._run_agent_graph(evf_id)

            # Update status
            evf.status = EVFStatus.COMPLETED
            evf.status_history.append({
                "status": "completed",
                "timestamp": datetime.utcnow().isoformat(),
                "result": result
            })
            await db.commit()

            return result
```

### 2.2 Async Background Jobs

**Queue Setup**:
```python
# backend/worker/__init__.py
from dramatiq import actor
from dramatiq.brokers.redis import RedisBroker

redis_broker = RedisBroker(url=settings.redis_url)
dramatiq.set_broker(redis_broker)

@actor(max_retries=3, time_limit=300000)  # 5 minutes
def process_evf_task(evf_id: str):
    """Background task: Process EVF through agent pipeline."""
    asyncio.run(_process_evf(evf_id))

async def _process_evf(evf_id: str):
    async with db_manager.get_db_context() as db:
        service = EVFService()
        result = await service.process_evf(db, evf_id)
        logger.info("EVF processed", evf_id=evf_id, result=result)
```

**Enqueueing**:
```python
# In EVFService.create_evf()
from backend.worker import process_evf_task

await self._enqueue_processing(evf.id):
    process_evf_task.send(evf.id)
```

### 2.3 Event Sourcing Lite

**Event Emitter**:
```python
# backend/core/events.py
from typing import Protocol, Any
import structlog

logger = structlog.get_logger()

class EventBus(Protocol):
    async def emit(self, event_type: str, payload: dict) -> None:
        """Emit domain event."""

class InMemoryEventBus:
    """Simple in-memory event bus."""

    def __init__(self):
        self._handlers = {}

    def subscribe(self, event_type: str, handler: Callable):
        self._handlers.setdefault(event_type, []).append(handler)

    async def emit(self, event_type: str, payload: dict):
        logger.info("Event emitted", event_type=event_type, payload=payload)

        for handler in self._handlers.get(event_type, []):
            await handler(payload)

# Global event bus
event_bus = InMemoryEventBus()

# Handlers
@event_bus.subscribe("evf.created")
async def update_analytics(payload: dict):
    """Update analytics materialized view."""
    evf_id = payload["evf_id"]
    # Refresh mv_tenant_stats...

@event_bus.subscribe("evf.completed")
async def send_notification(payload: dict):
    """Send completion notification."""
    evf_id = payload["evf_id"]
    # Send email/Slack...
```

---

## 📊 3. Data Platform & Analytics

### 3.1 PostgreSQL Enhancements

**Materialized Views**:
```sql
-- migrations/versions/xxx_add_materialized_views.py
CREATE MATERIALIZED VIEW mv_tenant_stats AS
SELECT
    tenant_id,
    COUNT(*) AS total_evfs,
    AVG(processing_time_seconds) AS avg_processing_time,
    SUM(cost_euros) AS total_cost,
    COUNT(CASE WHEN status = 'completed' THEN 1 END) AS completed_evfs,
    MAX(updated_at) AS last_activity
FROM evf_projects
GROUP BY tenant_id;

-- Refresh schedule (pg_cron)
SELECT cron.schedule(
    'refresh-tenant-stats',
    '*/15 * * * *',  -- Every 15 minutes
    $$ REFRESH MATERIALIZED VIEW CONCURRENTLY mv_tenant_stats; $$
);
```

**Partitioning**:
```sql
-- migrations/versions/xxx_partition_audit_logs.py
-- Convert audit_logs to partitioned table
CREATE TABLE audit_logs_partitioned (
    LIKE audit_logs INCLUDING ALL
) PARTITION BY RANGE (created_at);

-- Create monthly partitions
CREATE TABLE audit_logs_2025_11 PARTITION OF audit_logs_partitioned
    FOR VALUES FROM ('2025-11-01') TO ('2025-12-01');

CREATE TABLE audit_logs_2025_12 PARTITION OF audit_logs_partitioned
    FOR VALUES FROM ('2025-12-01') TO ('2026-01-01');

-- Auto-create future partitions (pg_partman)
```

**Read Replica**:
```python
# backend/core/database.py
# Add read-only replica for analytics
analytics_engine = create_async_engine(
    settings.analytics_database_url,  # Read replica URL
    **engine_kwargs
)

async def get_analytics_db() -> AsyncGenerator[AsyncSession, None]:
    """Get read-only database session for analytics."""
    async_session_maker = async_sessionmaker(
        analytics_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    async with async_session_maker() as session:
        yield session
```

### 3.2 Warehouse Bridge

**nightly ETL Job**:
```python
# backend/worker/etl.py
from dramatiq.cron import cron

@cron("0 2 * * *")  # 2 AM daily
async def export_to_warehouse():
    """Export daily metrics to DuckDB/BigQuery."""
    async with db_manager.get_db_context() as db:
        # Extract
        evfs = await db.execute(
            select(EVFProject).where(
                EVFProject.updated_at >= yesterday()
            )
        )

        # Transform
        df = pd.DataFrame([evf.to_dict() for evf in evfs])

        # Load to DuckDB
        import duckdb
        conn = duckdb.connect('warehouse.db')
        conn.execute("INSERT INTO evf_facts SELECT * FROM df")

        # Or load to BigQuery
        from google.cloud import bigquery
        client = bigquery.Client()
        client.load_table_from_dataframe(df, 'evf_portugal.evf_facts')
```

---

## 🤖 4. AI & LangGraph Layer

### 4.1 Formalize Multi-Agent Graph

**Graph Structure**:
```python
# backend/agents/graph.py
from langgraph.graph import StateGraph, END
from backend.agents.input import InputAgent
from backend.agents.compliance import EVFComplianceAgent
from backend.agents.financial import FinancialModelAgent
from backend.agents.narrative import NarrativeAgent
from backend.agents.audit import AuditAgent

class EVFProcessingState(TypedDict):
    evf_id: str
    tenant_id: str
    saft_data: dict
    compliance_result: dict
    financial_model: dict
    narrative: str
    audit_trail: list[dict]

def create_evf_graph() -> StateGraph:
    """Create LangGraph for EVF processing."""
    graph = StateGraph(EVFProcessingState)

    # Add nodes
    graph.add_node("input", InputAgent().process)
    graph.add_node("compliance", EVFComplianceAgent().check)
    graph.add_node("financial", FinancialModelAgent().calculate)
    graph.add_node("narrative", NarrativeAgent().generate)
    graph.add_node("audit", AuditAgent().log)

    # Define edges
    graph.add_edge("input", "compliance")
    graph.add_edge("compliance", "financial")
    graph.add_edge("financial", "narrative")
    graph.add_edge("narrative", "audit")
    graph.add_edge("audit", END)

    # Set entry point
    graph.set_entry_point("input")

    return graph.compile()

# Usage with RLS
async def process_evf_with_graph(evf_id: str, tenant_id: str):
    """Process EVF through LangGraph with RLS enforcement."""
    async with db_manager.get_db_context() as db:
        async with rls_enforced_session(db, tenant_id, "langgraph_processing"):
            graph = create_evf_graph()
            result = await graph.ainvoke({
                "evf_id": evf_id,
                "tenant_id": tenant_id
            })
            return result
```

### 4.2 Safety Rails

**Guardrails Integration**:
```python
# backend/agents/safety.py
from guardrails import Guard
from guardrails.hub import ToxicLanguage, PIIDetector

# Define safety guard
safety_guard = Guard().use_many(
    ToxicLanguage(on_fail="exception"),
    PIIDetector(on_fail="fix")
)

class SafeNarrativeAgent:
    """Narrative agent with safety rails."""

    async def generate(self, state: EVFProcessingState) -> str:
        """Generate narrative with safety checks."""
        # Call Claude
        raw_narrative = await claude.generate(
            prompt=self._build_prompt(state),
            max_tokens=2000
        )

        # Validate output
        validated = safety_guard.validate(raw_narrative)

        # Log with OpenTelemetry
        with tracer.start_as_current_span("narrative_generation") as span:
            span.set_attribute("tenant_id", state["tenant_id"])
            span.set_attribute("agent", "NarrativeAgent")
            span.set_attribute("safety_checks_passed", validated.success)

        return validated.validated_output
```

### 4.3 Knowledge Base Hygiene

**TTL Policies**:
```python
# backend/infrastructure/qdrant_client.py
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, OptimizersConfigDiff

client = QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key)

# Create collection with TTL
client.create_collection(
    collection_name=f"tenant_{tenant_id}_knowledge",
    vectors_config=VectorParams(size=768, distance=Distance.COSINE),
    optimizers_config=OptimizersConfigDiff(
        indexing_threshold=10000
    ),
    # TTL: 90 days
    on_disk_payload=True
)

# Scheduled cleanup
@cron("0 3 * * 0")  # Weekly Sunday 3 AM
async def cleanup_expired_embeddings():
    """Delete embeddings older than 90 days."""
    cutoff = datetime.utcnow() - timedelta(days=90)

    for tenant_id in await get_all_tenant_ids():
        collection = f"tenant_{tenant_id}_knowledge"

        # Delete old points
        client.delete(
            collection_name=collection,
            points_selector={
                "filter": {
                    "must": [
                        {
                            "key": "created_at",
                            "range": {
                                "lt": cutoff.timestamp()
                            }
                        }
                    ]
                }
            }
        )
```

---

## 🎨 5. Frontend (Next.js 15 Ready)

### 5.1 App Router Migration

**Gradual Migration Plan**:
```
Phase 1 (Week 1): Dashboard routes
  /dashboard/insights → app/dashboard/insights/page.tsx
  /dashboard/pipeline → app/dashboard/pipeline/page.tsx

Phase 2 (Week 2): EVF routes
  /evf → app/evf/page.tsx
  /evf/[id] → app/evf/[id]/page.tsx

Phase 3 (Week 3): Forms
  Keep as client components, move to app/ directory
```

**Server Component Example**:
```typescript
// app/dashboard/insights/page.tsx
import { getInsights } from '@/lib/api/analytics'
import { InsightsChart } from '@/components/insights-chart'

export default async function InsightsPage() {
  // Server-side data fetching
  const data = await getInsights({ period: '30d' })

  return (
    <div>
      <h1>Insights</h1>
      <InsightsChart data={data} />
    </div>
  )
}
```

### 5.2 Server Actions

**Mutation Example**:
```typescript
// app/actions/evf.ts
'use server'

import { revalidatePath } from 'next/cache'
import { uploadEVF } from '@/lib/api/evf'

export async function uploadEVFAction(formData: FormData) {
  const file = formData.get('file') as File

  try {
    const result = await uploadEVF(file)

    // Revalidate cache
    revalidatePath('/evf')

    return { success: true, evfId: result.id }
  } catch (error) {
    return { success: false, error: error.message }
  }
}
```

**Form Component**:
```typescript
// components/upload-evf-form.tsx
'use client'

import { uploadEVFAction } from '@/app/actions/evf'
import { useTransition } from 'react'

export function UploadEVFForm() {
  const [isPending, startTransition] = useTransition()

  async function handleSubmit(formData: FormData) {
    startTransition(async () => {
      const result = await uploadEVFAction(formData)
      if (result.success) {
        toast.success('EVF uploaded!')
      }
    })
  }

  return (
    <form action={handleSubmit}>
      <input type="file" name="file" />
      <button disabled={isPending}>Upload</button>
    </form>
  )
}
```

### 5.3 Form Persistence + Recovery

**Auto-save Hook**:
```typescript
// hooks/use-auto-save.ts
import { useEffect } from 'react'
import { useDebounce } from 'use-debounce'

export function useAutoSave<T>(data: T, key: string) {
  const [debouncedData] = useDebounce(data, 1000)

  useEffect(() => {
    localStorage.setItem(key, JSON.stringify(debouncedData))
  }, [debouncedData, key])

  // Recover on mount
  useEffect(() => {
    const saved = localStorage.getItem(key)
    if (saved) {
      // Restore form data
      const parsed = JSON.parse(saved)
      // ... restore logic
    }
  }, [])
}
```

**Draft API**:
```python
# backend/api/routers/evf.py
@router.post("/evf/drafts")
@require_rls
async def save_draft(
    data: EVFDraftRequest,
    db: AsyncSession = Depends(get_db_with_tenant)
):
    """Save EVF form draft."""
    draft = EVFDraft(
        tenant_id=data.tenant_id,
        form_data=data.data,
        expires_at=datetime.utcnow() + timedelta(days=7)
    )
    db.add(draft)
    await db.commit()
    return {"draft_id": draft.id}
```

---

## 👥 6. Customer-Facing Value

### 6.1 Collaboration

**Roles & Permissions**:
```python
# backend/models/tenant.py
class TenantRole(str, Enum):
    VIEWER = "viewer"      # Read-only
    ANALYST = "analyst"    # Create/edit EVFs
    ADMIN = "admin"        # Manage users, billing

class TenantUser(Base):
    __tablename__ = "tenant_users"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"))
    role: Mapped[TenantRole]
    invited_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    invited_at: Mapped[datetime]
```

**Activity Feed**:
```python
# backend/models/activity.py
class Activity(Base):
    __tablename__ = "activities"

    id: Mapped[str] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str]  # "created_evf", "updated_evf", "invited_user"
    resource_type: Mapped[str]  # "evf", "user", "tenant"
    resource_id: Mapped[str]
    metadata: Mapped[dict] = mapped_column(JSONB)
    created_at: Mapped[datetime]
```

### 6.2 Notifications

**Email + Slack Webhooks**:
```python
# backend/services/notification_service.py
from fastapi import BackgroundTasks

class NotificationService:
    async def notify_evf_completed(
        self,
        evf_id: str,
        tenant_id: str,
        background_tasks: BackgroundTasks
    ):
        """Send completion notification."""
        # Email
        background_tasks.add_task(
            self._send_email,
            to=user.email,
            subject="EVF Completed",
            template="evf_completed",
            context={"evf_id": evf_id}
        )

        # Slack webhook (if configured)
        if tenant.slack_webhook_url:
            background_tasks.add_task(
                self._send_slack,
                webhook_url=tenant.slack_webhook_url,
                message=f"EVF {evf_id} completed!"
            )
```

### 6.3 Self-Service Reports

**PDF Generation**:
```python
# backend/services/report_service.py
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

class ReportService:
    async def generate_compliance_report(
        self,
        evf_id: str,
        tenant_id: str
    ) -> bytes:
        """Generate PDF compliance report."""
        async with rls_enforced_session(db, tenant_id, "generate_report"):
            evf = await get_evf(db, evf_id)

            # Generate PDF
            buffer = io.BytesIO()
            pdf = canvas.Canvas(buffer, pagesize=A4)
            pdf.drawString(100, 800, f"EVF Compliance Report: {evf.name}")
            # ... add content
            pdf.save()

            # Upload to S3
            s3_url = await upload_to_s3(
                buffer.getvalue(),
                f"reports/{tenant_id}/{evf_id}.pdf"
            )

            return s3_url
```

---

## 📊 7. Observability & Ops

### 7.1 Full OpenTelemetry

**Instrumentation**:
```python
# backend/core/tracing.py
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

# Setup tracer
trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer(__name__)

# Export to Grafana Tempo / Jaeger
otlp_exporter = OTLPSpanExporter(endpoint="tempo.grafana.com:443")
span_processor = BatchSpanProcessor(otlp_exporter)
trace.get_tracer_provider().add_span_processor(span_processor)

# Auto-instrument
FastAPIInstrumentor.instrument_app(app)
SQLAlchemyInstrumentor().instrument(engine=engine)

# Custom spans
@tracer.start_as_current_span("process_evf")
async def process_evf(evf_id: str):
    span = trace.get_current_span()
    span.set_attribute("evf_id", evf_id)
    span.set_attribute("tenant_id", tenant_id)
    # ... processing
```

### 7.2 Metrics Suite

**Prometheus Instrumentation**:
```python
# backend/core/metrics.py
from prometheus_client import Counter, Histogram, Gauge

# Request metrics
request_count = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"]
)

request_duration = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration",
    ["method", "endpoint"]
)

# Agent metrics
agent_runtime = Histogram(
    "agent_runtime_seconds",
    "Agent processing time",
    ["agent_name", "tenant_id"]
)

token_spend = Counter(
    "claude_tokens_total",
    "Total Claude tokens consumed",
    ["agent_name", "tenant_id"]
)

# Business metrics
evf_processed = Counter(
    "evf_processed_total",
    "Total EVFs processed",
    ["tenant_id", "status"]
)

active_tenants = Gauge(
    "active_tenants",
    "Number of active tenants"
)
```

### 7.3 Runbooks & SLOs

**Runbooks**:
```markdown
# docs/runbooks/key-rotation-failure.md

## Key Rotation Failure

**Severity**: P1 (Critical)
**SLO Impact**: Authentication unavailable

### Detection
- Alert: `key_rotation_failed` fires
- Symptom: JWKS endpoint returns 500

### Investigation
1. Check KeyManager logs: `grep "Key rotation" logs/app.log`
2. Verify file permissions: `ls -la backend/.keys/`
3. Check disk space: `df -h`

### Resolution
1. **Immediate**: Extend grace period for old keys
   ```bash
   # Manually update key expiration
   python backend/scripts/extend_key_grace.py --hours 24
   ```

2. **Root cause fix**:
   - Disk full → Clear old logs
   - Permission issue → `chmod 600 backend/.keys/*.json`
   - Corruption → Regenerate keys with backup private key

3. **Verify**:
   ```bash
   curl http://localhost:8001/api/v1/auth/.well-known/jwks.json
   ```

### Post-Incident
- Update key backup procedure
- Add disk space monitoring
- Review key rotation schedule
```

**SLO Definitions**:
```yaml
# slos.yaml
slos:
  - name: auth-availability
    description: Authentication endpoint availability
    target: 99.9%
    window: 30d
    sli:
      success_rate:
        numerator: http_requests_total{endpoint="/auth/login", status="200"}
        denominator: http_requests_total{endpoint="/auth/login"}

  - name: evf-processing-latency
    description: EVF processing time
    target: p95 < 180s
    window: 30d
    sli:
      latency:
        metric: agent_runtime_seconds_bucket
        threshold: 180
```

### 7.4 Chaos & Load Testing

**k6 Load Test**:
```javascript
// tests/load/auth-flow.js
import http from 'k6/http'
import { check, sleep } from 'k6'

export const options = {
  stages: [
    { duration: '2m', target: 100 },   // Ramp up
    { duration: '5m', target: 100 },   // Sustained
    { duration: '2m', target: 1000 },  // Spike
    { duration: '5m', target: 1000 },  // Sustained spike
    { duration: '2m', target: 0 }      // Ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<100'], // 95% < 100ms
    http_req_failed: ['rate<0.01']    // Error rate < 1%
  }
}

export default function () {
  // Login
  const loginRes = http.post('http://localhost:8001/api/v1/auth/login', {
    username: 'test@example.com',
    password: 'password123'
  })

  check(loginRes, {
    'login successful': (r) => r.status === 200,
    'response time < 100ms': (r) => r.timings.duration < 100
  })

  const token = loginRes.json('access_token')

  // List EVFs
  const evfsRes = http.get('http://localhost:8001/api/v1/evf', {
    headers: { 'Authorization': `Bearer ${token}` }
  })

  check(evfsRes, {
    'evfs retrieved': (r) => r.status === 200
  })

  sleep(1)
}
```

**Run Load Test**:
```bash
k6 run tests/load/auth-flow.js --out json=results.json
```

---

## 🔧 8. DevEx & CI/CD

### 8.1 Monorepo Automation

**Workspace Structure**:
```json
// package.json (root)
{
  "workspaces": ["frontend", "backend"],
  "scripts": {
    "dev": "concurrently \"npm:dev:backend\" \"npm:dev:frontend\"",
    "dev:backend": "cd backend && uvicorn main:app --reload",
    "dev:frontend": "cd frontend && next dev",
    "test": "npm run test:backend && npm run test:frontend",
    "test:backend": "cd backend && pytest",
    "test:frontend": "cd frontend && vitest"
  }
}
```

**DevContainer**:
```json
// .devcontainer/devcontainer.json
{
  "name": "EVF Portugal 2030",
  "dockerComposeFile": "docker-compose.yml",
  "service": "app",
  "workspaceFolder": "/workspace",
  "features": {
    "ghcr.io/devcontainers/features/python:1": { "version": "3.11" },
    "ghcr.io/devcontainers/features/node:1": { "version": "20" },
    "ghcr.io/devcontainers/features/docker-in-docker:2": {}
  },
  "postCreateCommand": "pip install -r requirements.txt && npm install",
  "customizations": {
    "vscode": {
      "extensions": [
        "ms-python.python",
        "bradlc.vscode-tailwindcss",
        "esbenp.prettier-vscode"
      ]
    }
  }
}
```

### 8.2 GitHub Actions Pipeline

```yaml
# .github/workflows/ci.yml
name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  backend-tests:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_PASSWORD: test
        options: --health-cmd pg_isready

    steps:
      - uses: actions/checkout@v3

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r backend/requirements.txt
          pip install pytest pytest-cov black ruff mypy

      - name: Lint
        run: |
          black backend/ --check
          ruff check backend/
          mypy backend/

      - name: Test
        run: |
          pytest backend/tests/ \
            --cov=backend \
            --cov-report=xml \
            --cov-fail-under=90

      - name: Upload coverage
        uses: codecov/codecov-action@v3

  frontend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup Node
        uses: actions/setup-node@v3
        with:
          node-version: '20'

      - name: Install dependencies
        run: cd frontend && npm ci

      - name: Lint
        run: cd frontend && npm run lint

      - name: Type check
        run: cd frontend && npm run type-check

      - name: Test
        run: cd frontend && npm run test

  security-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Run Trivy scanner
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          scan-ref: '.'
          format: 'sarif'
          output: 'trivy-results.sarif'

      - name: Generate SBOM
        uses: anchore/sbom-action@v0
        with:
          path: .
          format: spdx-json

      - name: Sign with Cosign
        uses: sigstore/cosign-installer@v3
        with:
          cosign-release: 'v2.2.0'

  deploy-staging:
    needs: [backend-tests, frontend-tests, security-scan]
    if: github.ref == 'refs/heads/develop'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Deploy to Railway (Backend)
        run: |
          railway up --service backend --environment staging

      - name: Deploy to Vercel (Frontend)
        run: |
          vercel deploy --prebuilt --prod
```

### 8.3 GitOps Deployment

**Railway Configuration**:
```toml
# railway.toml
[build]
builder = "NIXPACKS"
buildCommand = "pip install -r requirements.txt"

[deploy]
startCommand = "uvicorn backend.main:app --host 0.0.0.0 --port $PORT"
healthcheckPath = "/api/health"
healthcheckTimeout = 30
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 10

[[services]]
name = "backend"
environment = "production"

[[services.envs]]
key = "DATABASE_URL"
value = "${{Postgres.DATABASE_URL}}"

[[services.envs]]
key = "REDIS_URL"
value = "${{Redis.REDIS_URL}}"
```

**Feature Flags**:
```python
# backend/core/feature_flags.py
from configcat import ConfigCatClient

client = ConfigCatClient.get(settings.configcat_key)

def is_feature_enabled(flag: str, user_id: str) -> bool:
    """Check if feature is enabled for user."""
    return client.get_value(flag, False, user={"identifier": user_id})

# Usage
if is_feature_enabled("rs256_jwt", user.id):
    # Use RS256
else:
    # Use HS256 (rollback)
```

---

## 🔒 9. Security & Compliance Add-ons

### 9.1 Field-Level Encryption

**Encryption Mixin**:
```python
# backend/models/encrypted.py
from cryptography.fernet import Fernet
from sqlalchemy import String, TypeDecorator

class EncryptedString(TypeDecorator):
    """SQLAlchemy column type for encrypted strings."""

    impl = String
    cache_ok = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._fernet = Fernet(settings.field_encryption_key)

    def process_bind_param(self, value, dialect):
        """Encrypt before storing."""
        if value is not None:
            return self._fernet.encrypt(value.encode()).decode()
        return value

    def process_result_value(self, value, dialect):
        """Decrypt after retrieval."""
        if value is not None:
            return self._fernet.decrypt(value.encode()).decode()
        return value

# Usage
class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(primary_key=True)
    email: Mapped[str]  # Not encrypted
    nif: Mapped[str] = mapped_column(EncryptedString)  # Encrypted PII
    phone: Mapped[str] = mapped_column(EncryptedString)  # Encrypted PII
```

### 9.2 GDPR Tooling

**Self-Service Export**:
```python
# backend/api/routers/gdpr.py
@router.get("/gdpr/export")
@require_rls
async def export_user_data(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_with_tenant)
):
    """Export all user data (GDPR Art. 20)."""
    # Collect all user data
    user_data = {
        "user": current_user.to_dict(),
        "evfs": [evf.to_dict() for evf in current_user.evfs],
        "activities": [act.to_dict() for act in current_user.activities]
    }

    # Generate JSON file
    buffer = io.BytesIO()
    buffer.write(json.dumps(user_data, indent=2).encode())

    return StreamingResponse(
        buffer,
        media_type="application/json",
        headers={
            "Content-Disposition": f"attachment; filename=user_data_{current_user.id}.json"
        }
    )

@router.delete("/gdpr/delete-account")
@require_rls
async def delete_account(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_with_tenant)
):
    """Delete user account (GDPR Art. 17 - Right to erasure)."""
    # Anonymize instead of hard delete (preserve business logic)
    current_user.email = f"deleted_{current_user.id}@anonymized.com"
    current_user.full_name = "Deleted User"
    current_user.is_active = False
    current_user.deleted_at = datetime.utcnow()

    await db.commit()

    return {"message": "Account deleted successfully"}
```

### 9.3 Secrets Rotation

**Vault Integration**:
```python
# backend/core/secrets.py
import hvac

vault_client = hvac.Client(
    url=settings.vault_url,
    token=settings.vault_token
)

def get_secret(path: str) -> dict:
    """Get secret from Vault."""
    secret = vault_client.secrets.kv.v2.read_secret_version(path=path)
    return secret['data']['data']

# Rotate database password
async def rotate_database_password():
    """Rotate PostgreSQL password (90-day cycle)."""
    # Generate new password
    new_password = generate_secure_password(32)

    # Update in database
    await execute_sql(f"ALTER USER evf_app WITH PASSWORD '{new_password}';")

    # Store in Vault
    vault_client.secrets.kv.v2.create_or_update_secret(
        path='database/evf_app',
        secret=dict(password=new_password)
    )

    # Update Railway/Vercel env variables via API
    await update_railway_env('DATABASE_PASSWORD', new_password)

    # Restart services
    await restart_backend_service()
```

---

## 💰 10. Cost & Scaling

### 10.1 Autoscaling Profiles

**Kubernetes HPA** (if using k8s):
```yaml
# k8s/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: backend-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: backend
  minReplicas: 2
  maxReplicas: 20
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
    - type: Pods
      pods:
        metric:
          name: request_duration_p95
        target:
          type: AverageValue
          averageValue: "100m"  # 100ms
```

**Railway Autoscaling** (native):
```json
// railway.json
{
  "deploy": {
    "autoScaling": {
      "enabled": true,
      "minReplicas": 2,
      "maxReplicas": 10,
      "targetCPUUtilization": 70,
      "targetMemoryUtilization": 80
    }
  }
}
```

### 10.2 Per-Tenant Quotas

**Quota Model**:
```python
# backend/models/quota.py
class TenantQuota(Base):
    __tablename__ = "tenant_quotas"

    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), primary_key=True)
    plan: Mapped[str]  # "free", "starter", "professional", "enterprise"

    # Limits
    max_evfs_per_month: Mapped[int]
    max_storage_gb: Mapped[int]
    max_users: Mapped[int]
    max_api_calls_per_day: Mapped[int]

    # Current usage
    evfs_this_month: Mapped[int] = mapped_column(default=0)
    storage_used_gb: Mapped[float] = mapped_column(default=0.0)
    users_count: Mapped[int] = mapped_column(default=0)
    api_calls_today: Mapped[int] = mapped_column(default=0)

    # Resets
    month_reset_at: Mapped[datetime]
    day_reset_at: Mapped[datetime]

# Quota check middleware
@app.middleware("http")
async def quota_check(request: Request, call_next):
    tenant_id = getattr(request.state, "tenant_id", None)

    if tenant_id:
        quota = await get_tenant_quota(tenant_id)

        # Check API rate limit
        if quota.api_calls_today >= quota.max_api_calls_per_day:
            return JSONResponse(
                status_code=429,
                content={"error": "API rate limit exceeded. Upgrade plan."}
            )

        # Increment counter
        quota.api_calls_today += 1
        await db.commit()

    response = await call_next(request)
    return response
```

**Budget Alerts**:
```python
# backend/services/billing_service.py
async def check_budget_alerts():
    """Check if tenants are approaching quota limits."""
    tenants = await db.execute(select(TenantQuota))

    for quota in tenants:
        # Check EVF usage
        evf_usage_pct = (quota.evfs_this_month / quota.max_evfs_per_month) * 100

        if evf_usage_pct >= 90:
            await send_alert(
                tenant_id=quota.tenant_id,
                type="quota_warning",
                message=f"You've used {evf_usage_pct}% of your monthly EVF quota."
            )

        # Check Claude token spend
        token_spend = await get_claude_token_spend(quota.tenant_id)
        if token_spend >= quota.max_token_budget * 0.9:
            await send_alert(
                tenant_id=quota.tenant_id,
                type="budget_warning",
                message=f"Claude API costs approaching limit: €{token_spend:.2f} / €{quota.max_token_budget}"
            )
```

---

## 🚀 Implementation Roadmap

### Sprint 2 (Days 16-30): Service Layer + Observability
**Goal**: Establish service layer architecture and full observability

**Tasks**:
1. ✅ Finish Sprint 1 blockers (observability, DPoP, runbooks, load tests)
2. Create service layer structure (`backend/services/`)
3. Implement OpenTelemetry instrumentation
4. Add Prometheus metrics
5. Set up Grafana dashboards
6. Write operational runbooks
7. Run k6 load tests and document results

**Deliverables**:
- Service layer with 4 modules (tenant, auth, evf, file)
- Full tracing to Grafana Tempo
- 10+ Prometheus metrics
- 3 Grafana dashboards (requests, agents, business)
- 5 runbooks (key rotation, RLS violation, queue backlog, JWKS downtime, incident response)
- k6 load test results (1000 rps sustained)

### Sprint 3 (Days 31-45): Background Workers + Analytics
**Goal**: Async processing and analytics infrastructure

**Tasks**:
1. Set up Dramatiq/Celery with Redis
2. Migrate long-running operations to background tasks
3. Implement materialized views (`mv_tenant_stats`)
4. Add partition strategy for `audit_logs`
5. Create analytics API endpoints
6. Build DuckDB/BigQuery ETL pipeline
7. Dashboard UI for insights

**Deliverables**:
- Background worker processing EVFs
- Analytics API with 5+ endpoints
- Materialized views refreshing every 15 minutes
- Monthly partitioned audit logs
- Nightly ETL to warehouse
- Dashboard page showing tenant insights

### Sprint 4 (Days 46-60): Frontend + AI Enhancements
**Goal**: Next.js 15 migration and AI safety rails

**Tasks**:
1. Migrate dashboard routes to App Router
2. Implement Server Actions for mutations
3. Add form persistence + auto-save
4. Formalize LangGraph multi-agent pipeline
5. Integrate Guardrails.ai safety rails
6. Implement TTL policies for Qdrant
7. Add workflow timeline UI

**Deliverables**:
- Dashboard routes using Server Components
- 3+ Server Actions (upload, update, delete)
- Auto-save for EVF forms
- LangGraph graph definition (`backend/agents/graph.py`)
- Safety rails on all Claude calls
- Qdrant cleanup job (90-day TTL)
- Timeline component showing agent progress

### Sprint 5 (Days 61-75): Collaboration + Notifications
**Goal**: Multi-user collaboration and notification system

**Tasks**:
1. Implement role-based access control
2. Build activity feed
3. Add email notifications (SendGrid/Resend)
4. Integrate Slack webhooks
5. Create team invite flow
6. Build self-service PDF reports
7. Add real-time updates (WebSockets/SSE)

**Deliverables**:
- 3 roles (viewer, analyst, admin)
- Activity feed showing last 30 days
- Email notifications for 5 events
- Slack webhook integration
- Team invite flow with onboarding
- PDF report generation
- Real-time EVF status updates

### Sprint 6 (Days 76-90): Security + Compliance
**Goal**: Field-level encryption, GDPR compliance, secrets rotation

**Tasks**:
1. Implement field-level encryption for PII
2. Add GDPR self-service export
3. Build account deletion flow (anonymization)
4. Integrate Vault for secrets management
5. Implement DPoP token binding
6. Add database password rotation
7. Update threat model (STRIDE)

**Deliverables**:
- Encrypted fields (NIF, phone, address)
- GDPR export endpoint
- GDPR account deletion
- Vault integration
- DPoP validator (finally!)
- 90-day password rotation script
- Updated threat model document

### Sprint 7 (Days 91-105): DevEx + CI/CD
**Goal**: Developer experience improvements and automation

**Tasks**:
1. Set up monorepo with Turborepo
2. Create DevContainer configuration
3. Build GitHub Actions pipeline (lint, test, security scan)
4. Implement feature flags (ConfigCat)
5. Add SBOM generation (Syft)
6. Set up Cosign signing
7. GitOps deployment with Railway + Vercel

**Deliverables**:
- Turborepo configuration
- DevContainer for VS Code
- CI/CD pipeline with 6 stages
- Feature flags for 3 features
- SBOM generation in CI
- Signed container images
- Automated staging deployments

### Sprint 8 (Days 106-120): Scaling + Cost Optimization
**Goal**: Autoscaling, quotas, budget management

**Tasks**:
1. Configure autoscaling (Railway/k8s HPA)
2. Implement per-tenant quotas
3. Add quota enforcement middleware
4. Build usage dashboard for tenants
5. Set up budget alerts
6. Optimize Claude token usage
7. Add cost attribution per tenant

**Deliverables**:
- Autoscaling configuration (2-20 replicas)
- Quota model with 4 plans
- Quota middleware enforcing limits
- Usage dashboard showing consumption
- Budget alerts at 90% threshold
- 30% reduction in Claude costs
- Cost attribution dashboard

---

## 📞 Quick Reference

### Architecture Principles
1. **Security First**: RLS at every entry point, encryption for PII, audit everything
2. **Observability Built-in**: Every operation traced, metrics on all critical paths
3. **Service-Oriented**: Thin routers, fat services, clear domain boundaries
4. **Async by Default**: Background workers for long operations, never block requests
5. **Multi-Tenant Always**: Tenant context propagated through entire stack
6. **Gradual Migration**: Support old + new patterns during transitions

### Key Technologies
- **Backend**: FastAPI, SQLAlchemy 2.0, Dramatiq, OpenTelemetry
- **Frontend**: Next.js 15, React Server Components, Server Actions, Zustand
- **AI**: LangGraph, Claude 4.5 Sonnet, Guardrails.ai, Qdrant
- **Data**: PostgreSQL 16, Redis, DuckDB/BigQuery, Materialized Views
- **Infra**: Railway, Vercel, Qdrant Cloud, Grafana Cloud, Vault
- **DevEx**: Turborepo, DevContainer, GitHub Actions, k6, Playwright

### Success Metrics
- **Performance**: <100ms auth, <3h EVF processing, <5ms RLS overhead
- **Reliability**: 99.9% uptime, <1% error rate, <10s p95 latency
- **Quality**: >90% test coverage, 0 critical vulnerabilities, <10 production bugs/month
- **Business**: <1h time-to-value, <€1 cost per EVF, 30% manual effort reduction

---

**Document Version**: 2.0
**Last Updated**: November 9, 2025
**Status**: Planning & Prioritization
**Next Review**: After Sprint 2 completion
**Owner**: Product & Engineering Team

---

## 🎯 Immediate Next Actions (This Week)

1. **Finish Sprint 1 Blockers**
   - [ ] Implement observability layer (OpenTelemetry + Prometheus)
   - [ ] Write operational runbooks (5 scenarios)
   - [ ] Run k6 load tests and document results
   - [ ] Implement DPoP proof validator

2. **Stand Up Service Layer Skeleton**
   - [ ] Create `backend/services/` directory structure
   - [ ] Implement `TenantService`, `AuthService`, `EVFService`, `FileService`
   - [ ] Refactor 2 routes to use service layer

3. **Kick Off Next.js 15 Migration**
   - [ ] Migrate `/dashboard/insights` to App Router
   - [ ] Add OpenTelemetry instrumentation to frontend
   - [ ] Implement first Server Action (upload EVF)

**Estimated Time**: 1-2 weeks
**Sprint**: Sprint 1 completion + Sprint 2 kickoff
