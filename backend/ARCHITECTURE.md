# EVF Portugal 2030 - Backend Architecture

## System Overview

Multi-tenant B2B SaaS platform for automating Portuguese funding (PT2030/PRR) applications. The system uses 5 specialized AI agents orchestrated through FastAPI to transform Financial Viability Studies (EVF) from 24h manual work to 3h automated processing.

## Technology Stack

- **Framework**: FastAPI 0.115+ (Python 3.11+)
- **Database**: PostgreSQL 16 with Row-Level Security (RLS)
- **ORM**: SQLAlchemy 2.0 (async)
- **Cache**: Redis (Upstash serverless)
- **AI**: Claude 4.5 Sonnet via Anthropic API
- **Vector DB**: Qdrant Cloud (multi-tenant)
- **Task Queue**: FastAPI BackgroundTasks (initial) → Celery (scale)

## Core Architecture Principles

### 1. Multi-Tenant Isolation
- Every database table includes `tenant_id` (UUID)
- PostgreSQL Row-Level Security (RLS) enforces tenant isolation
- JWT tokens carry tenant context
- Middleware automatically sets tenant context on each request

### 2. Deterministic Financial Calculations
- All financial calculations are pure mathematical functions
- NO LLM usage for generating numbers
- VALF (NPV) and TRF (IRR) calculations follow official PT2030 guidelines
- 100% auditable and reproducible results

### 3. Agent-Based Architecture
Five specialized sub-agents handle distinct responsibilities:

#### InputAgent
- Parse SAF-T XML files (Portuguese tax format)
- Validate Excel/CSV uploads
- Map accounting codes to SNC taxonomy
- Calculate data quality score (0-100%)
- NO AI - deterministic validation only

#### EVFComplianceAgent
- Validate PT2030/PRR/SITCE rules
- Check VALF < 0 (requirement)
- Verify TRF < 4%
- Generate compliance checklists
- 100% rule-based, NO hallucinations

#### FinancialModelAgent
- Calculate VALF (Valor Atualizado Líquido Financeiro)
- Calculate TRF (Taxa de Rentabilidade Financeira)
- Project 10-year cash flows
- Generate 30+ financial ratios
- Pure mathematical functions, NO LLM

#### NarrativeAgent
- Generate explanatory text for proposals
- ONLY agent using Claude LLM
- NEVER invents numbers (uses provided data only)
- Contextualizes results in PT2030 language
- Cites sources for all claims

#### AuditAgent
- Track all operations with hash chains
- Monitor token usage and costs
- Generate compliance audit trails
- Alert on budget overruns
- 10-year retention for legal compliance

## Database Schema

### Multi-Tenant Foundation

```sql
-- Core tenant table
CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    nif VARCHAR(9) UNIQUE NOT NULL,
    plan VARCHAR(50) DEFAULT 'starter',
    mrr DECIMAL(10,2) DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    settings JSONB DEFAULT '{}'::jsonb
);

-- All tables inherit tenant_id
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id) NOT NULL,
    email VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) DEFAULT 'member',
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(tenant_id, email)
);

CREATE TABLE evf_projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id) NOT NULL,
    company_nif VARCHAR(9) NOT NULL,
    fund_type VARCHAR(50) NOT NULL, -- PT2030, PRR, SITCE
    status VARCHAR(50) DEFAULT 'draft',

    -- Financial results
    valf DECIMAL(15,2),
    trf DECIMAL(5,2),
    payback DECIMAL(5,2),

    -- Data
    assumptions JSONB,
    projections JSONB,
    compliance_status JSONB,

    -- Files
    input_file_path VARCHAR(500),
    excel_output_path VARCHAR(500),
    pdf_output_path VARCHAR(500),

    -- Audit
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    INDEX idx_tenant_status (tenant_id, status),
    INDEX idx_tenant_created (tenant_id, created_at DESC)
);

-- Immutable audit log
CREATE TABLE audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    evf_id UUID REFERENCES evf_projects(id),
    user_id UUID REFERENCES users(id),

    agent_name VARCHAR(50),
    action VARCHAR(100) NOT NULL,

    -- Data integrity
    input_hash VARCHAR(64),
    output_hash VARCHAR(64),

    -- Cost tracking
    tokens_used INTEGER DEFAULT 0,
    cost_euros DECIMAL(6,4) DEFAULT 0,

    -- Metadata
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Row-Level Security
ALTER TABLE evf_projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_evf ON evf_projects
    FOR ALL
    USING (tenant_id = current_setting('app.current_tenant')::uuid);

CREATE POLICY tenant_isolation_audit ON audit_log
    FOR ALL
    USING (tenant_id = current_setting('app.current_tenant')::uuid);
```

## API Structure

```
backend/
├── api/
│   ├── main.py                 # FastAPI app initialization
│   ├── deps.py                 # Dependency injection
│   └── routers/
│       ├── auth.py             # Authentication endpoints
│       ├── evf.py              # EVF processing endpoints
│       ├── tenants.py          # Tenant management
│       └── admin.py            # Admin operations
├── agents/                     # 5 specialized sub-agents
│   ├── base_agent.py           # Base agent interface
│   ├── input_agent.py          # SAF-T/Excel parser
│   ├── compliance_agent.py     # PT2030 rule validator
│   ├── financial_agent.py      # VALF/TRF calculator
│   ├── narrative_agent.py      # Text generation (LLM)
│   └── audit_agent.py          # Tracking & compliance
├── core/
│   ├── config.py               # Pydantic settings
│   ├── database.py             # Async SQLAlchemy + RLS
│   ├── security.py             # JWT + password hashing
│   ├── middleware.py           # Tenant isolation middleware
│   └── tenant.py               # Tenant context management
├── models/                     # SQLAlchemy ORM models
│   ├── base.py                 # Base model with tenant_id
│   ├── tenant.py               # Tenant model
│   ├── evf.py                  # EVF project models
│   └── audit.py                # Audit log models
├── schemas/                    # Pydantic schemas
│   ├── tenant.py               # Tenant schemas
│   ├── evf.py                  # EVF schemas
│   └── auth.py                 # Auth schemas
├── services/                   # Business logic
│   ├── saft_parser.py          # SAF-T XML parser
│   ├── claude_client.py        # Claude API wrapper
│   ├── qdrant_service.py       # Vector DB operations
│   └── orchestrator.py         # Agent orchestration
└── regulations/                # Compliance rules (JSON)
    ├── pt2030_rules.json
    ├── prr_rules.json
    └── sitce_rules.json
```

## Request Flow

```
1. Request arrives → TenantMiddleware
   ├─ Extract tenant from subdomain/header
   ├─ Validate JWT token
   ├─ Set PostgreSQL RLS context: SET app.current_tenant = '<tenant_id>'
   └─ Attach tenant_id to request.state

2. Upload SAF-T file → EVF Router
   ├─ Validate file size & type
   ├─ Store encrypted file (tenant_id in path)
   └─ Queue processing job

3. Background Worker → Orchestrator
   ├─ InputAgent: Parse & validate SAF-T
   ├─ FinancialModelAgent: Calculate VALF/TRF (parallel)
   ├─ ComplianceAgent: Validate PT2030 rules (parallel)
   ├─ NarrativeAgent: Generate text (uses LLM)
   └─ AuditAgent: Log everything

4. Return Results
   ├─ Generate Excel output (PT2030 template)
   ├─ Generate PDF report
   ├─ Update EVF project status
   └─ Notify user (email/webhook)
```

## Security Architecture

### Authentication
- JWT tokens with tenant context in payload
- Access tokens: 30 minutes expiry
- Refresh tokens: 7 days expiry
- bcrypt password hashing (cost factor 12)

### Authorization
- Role-Based Access Control (RBAC)
- Roles: admin, manager, member
- Tenant admin can only manage their tenant

### Data Protection
- All file uploads encrypted at rest (AES-256)
- TLS 1.3 for all connections
- PostgreSQL RLS enforces tenant isolation
- Audit logs are immutable (append-only)

### Rate Limiting
- 100 requests/minute per tenant
- Redis-based distributed rate limiting
- Separate limits for expensive operations (LLM calls)

## Agent Orchestration

### Parallel Execution
```python
async def process_evf(evf_id: str, tenant_id: str):
    # Initialize agents
    input_agent = InputAgent(tenant_id)
    financial_agent = FinancialModelAgent(tenant_id)
    compliance_agent = EVFComplianceAgent(tenant_id)
    narrative_agent = NarrativeAgent(tenant_id)
    audit_agent = AuditAgent(tenant_id)

    # Step 1: Parse input (sequential)
    saft_data = await input_agent.process(evf_id)

    # Step 2: Parallel calculations & validation
    financial_task = financial_agent.calculate(saft_data)
    compliance_task = compliance_agent.validate(saft_data)

    financial_results, compliance_results = await asyncio.gather(
        financial_task,
        compliance_task
    )

    # Step 3: Generate narrative (sequential - uses LLM)
    narrative = await narrative_agent.generate(financial_results)

    # Step 4: Audit everything
    await audit_agent.log_execution({
        "evf_id": evf_id,
        "agents_used": ["input", "financial", "compliance", "narrative"],
        "tokens_consumed": narrative.tokens_used,
        "cost_euros": narrative.cost_euros
    })
```

## Performance Targets

- API response time: < 3 seconds (p95)
- EVF processing: < 3 hours end-to-end
- Cost per EVF: < €1
- Database query time: < 100ms (p95)
- Concurrent tenants: 100+
- Uptime SLA: 99.9%

## Monitoring & Observability

### Metrics
- Request latency (p50, p95, p99)
- Error rates by endpoint
- Token usage per tenant
- Cost tracking (Claude API, Qdrant)
- Database connection pool utilization

### Logging
- Structured JSON logs
- Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
- Correlation IDs for request tracing
- Sensitive data redaction (NIFs, emails)

### Alerting
- Daily cost exceeds €50 per tenant
- Error rate > 5% for 5 minutes
- EVF processing time > 4 hours
- Database connection pool exhausted
- Disk space < 10%

## Cost Control

### Claude API Costs
- Input: $3/M tokens
- Output: $15/M tokens
- Average EVF: ~50k tokens = ~€0.50
- Daily limit: €50/tenant
- Monthly limit: €1000/tenant

### Infrastructure Costs
- Railway backend: €50/month
- Qdrant Cloud: €100/month
- Redis (Upstash): €20/month
- Total: €170/month base

### Break-even Analysis
- Cost per EVF: €1
- Pricing: €15/EVF (Starter), €10/EVF (Pro), €7/EVF (Enterprise)
- Break-even: 40-60 clients @ 10 EVFs/month

## Deployment

### Environments
- **Development**: Local Docker Compose
- **Staging**: Railway with test data
- **Production**: Railway with auto-scaling

### CI/CD Pipeline
```yaml
1. Push to GitHub
2. Run tests (pytest with 90%+ coverage)
3. Lint (ruff, black, mypy)
4. Build Docker image
5. Push to Railway
6. Run migrations
7. Health check
8. Smoke tests
```

### Database Migrations
- Alembic for schema versioning
- Zero-downtime migrations
- Automatic backup before migration
- Rollback capability

## Testing Strategy

### Unit Tests
- All financial calculations
- Agent logic
- Utility functions
- 90% code coverage target

### Integration Tests
- Multi-tenant isolation
- API endpoints
- Database operations
- External service mocks

### E2E Tests
- Complete EVF workflow
- File upload → processing → download
- Multi-user scenarios

### Performance Tests
- Load testing with Locust
- 100 concurrent users
- Stress test multi-tenant isolation

## Compliance & Audit

### PT2030 Compliance
- VALF < 0 (validated deterministically)
- TRF < 4% (validated deterministically)
- All rules in JSON (regulations/pt2030_rules.json)
- Zero tolerance for errors

### Data Retention
- Audit logs: 10 years (legal requirement)
- EVF projects: Indefinite (until tenant deletion)
- Uploaded files: 30 days (configurable)
- Backups: 90 days

### GDPR Compliance
- Data minimization
- Right to deletion
- Data portability
- Consent management
- EU-West hosting only

## Future Enhancements

### Phase 2 (Months 3-6)
- Celery for heavy workloads
- Batch processing
- API webhooks
- Multi-language support

### Phase 3 (Months 6-12)
- Mobile app
- Advanced analytics dashboard
- Benchmarking across tenants
- AI-powered recommendations

## Key Files Reference

| File | Purpose |
|------|---------|
| `/backend/core/config.py` | All configuration settings |
| `/backend/core/database.py` | Async SQLAlchemy + RLS |
| `/backend/core/security.py` | JWT + password hashing |
| `/backend/core/middleware.py` | Tenant isolation |
| `/backend/agents/orchestrator.py` | Agent coordination |
| `/backend/models/base.py` | Base model with tenant_id |
| `/backend/api/main.py` | FastAPI app entry point |
| `/backend/regulations/pt2030_rules.json` | PT2030 compliance rules |

---

**Version**: 1.0.0
**Last Updated**: 2025-11-07
**Status**: Production-Ready Architecture
