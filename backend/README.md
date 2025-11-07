# EVF Portugal 2030 - Backend

AI-powered B2B SaaS platform for automating Portuguese funding (PT2030/PRR) application processing. Transform Financial Viability Studies (EVF) from 24h manual work to 3h automated processing using 5 specialized AI agents.

## Quick Links

- **[Architecture Documentation](ARCHITECTURE.md)** - Complete system design
- **[Implementation Guide](IMPLEMENTATION_GUIDE.md)** - Detailed code examples
- **[Quick Start Guide](QUICKSTART.md)** - Get started in minutes
- **[API Documentation](http://localhost:8000/docs)** - Interactive API docs (when running)

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     EVF Portugal 2030 Platform                   │
│                   Multi-Tenant B2B SaaS Backend                  │
└─────────────────────────────────────────────────────────────────┘
                                 │
        ┌────────────────────────┼────────────────────────┐
        │                        │                        │
┌───────▼────────┐    ┌─────────▼────────┐    ┌─────────▼────────┐
│   FastAPI      │    │   PostgreSQL 16  │    │   Redis Cache    │
│  (Async API)   │◄───│  (Multi-tenant)  │◄───│  (Rate Limit)    │
│                │    │   + RLS          │    │                  │
└───────┬────────┘    └──────────────────┘    └──────────────────┘
        │
        │ Orchestrates
        │
┌───────▼─────────────────────────────────────────────────────────┐
│                     5 Specialized Agents                         │
├──────────────┬──────────────┬──────────────┬──────────────┬─────┤
│ InputAgent   │ Financial    │ Compliance   │ Narrative    │Audit│
│ (SAF-T)      │ (VALF/TRF)   │ (PT2030)     │ (Claude AI)  │(Log)│
│ NO AI        │ NO AI        │ NO AI        │ LLM ONLY     │NO AI│
└──────────────┴──────────────┴──────────────┴──────────────┴─────┘
        │                │               │              │        │
        └────────────────┴───────────────┴──────────────┴────────┘
                                 │
                    ┌────────────▼────────────┐
                    │   Excel + PDF Output    │
                    │   (PT2030 Template)     │
                    └─────────────────────────┘
```

## Features

### ✅ Implemented (Core Infrastructure)
- **Multi-Tenant Architecture**: Complete tenant isolation with PostgreSQL RLS
- **Async Database Layer**: SQLAlchemy 2.0 with asyncpg for high performance
- **JWT Authentication**: Secure authentication with tenant context
- **Rate Limiting**: 100 requests/minute per tenant
- **Configuration Management**: Type-safe Pydantic settings
- **Middleware System**: Automatic tenant extraction and validation

### 🔨 In Progress (Agent Implementation)
- **5 Specialized Agents**: InputAgent, FinancialAgent, ComplianceAgent, NarrativeAgent, AuditAgent
- **API Endpoints**: Authentication, EVF processing, admin operations
- **Service Layer**: Orchestrator, SAF-T parser, Claude client
- **Database Models**: Tenant, User, EVF Project, Audit Log
- **Test Suite**: 90%+ coverage target

## Technology Stack

- **Framework**: FastAPI 0.115+ (Python 3.11+)
- **Database**: PostgreSQL 16 with Row-Level Security
- **ORM**: SQLAlchemy 2.0 (async)
- **Cache**: Redis 7
- **AI**: Claude 4.5 Sonnet (Anthropic)
- **Vector DB**: Qdrant Cloud
- **Testing**: pytest + pytest-cov
- **Code Quality**: black, ruff, mypy

## Installation

### Prerequisites
- Python 3.11+
- PostgreSQL 16+
- Redis 7+
- Docker (optional)

### Setup

```bash
# Clone repository
cd /Users/bilal/Programaçao/Agent\ SDK\ -\ IFIC/backend

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your credentials

# Start services (Docker)
docker-compose up -d

# Run migrations
alembic upgrade head

# Start development server
uvicorn backend.api.main:app --reload
```

Visit:
- API: http://localhost:8000
- Docs: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Project Structure

```
backend/
├── agents/              # 5 specialized AI agents
│   ├── input_agent.py          # SAF-T parser (deterministic)
│   ├── financial_agent.py      # VALF/TRF calculator (pure math)
│   ├── compliance_agent.py     # PT2030 validator (rule-based)
│   ├── narrative_agent.py      # Text generation (Claude LLM)
│   └── audit_agent.py          # Tracking & compliance
│
├── api/                 # FastAPI endpoints
│   ├── main.py                 # Application entry point
│   └── routers/
│       ├── auth.py             # Authentication
│       ├── evf.py              # EVF operations
│       └── admin.py            # Admin endpoints
│
├── core/                # Core infrastructure (✅ COMPLETE)
│   ├── config.py               # Configuration management
│   ├── database.py             # Async SQLAlchemy + RLS
│   ├── security.py             # JWT & password hashing
│   └── middleware.py           # Tenant isolation
│
├── models/              # Database models
│   ├── base.py                 # Base model with tenant_id
│   ├── tenant.py               # Tenant model
│   ├── evf.py                  # EVF project model
│   └── audit.py                # Audit log model
│
├── services/            # Business logic
│   ├── orchestrator.py         # Agent orchestration
│   ├── saft_parser.py          # SAF-T XML parser
│   ├── claude_client.py        # Claude API wrapper
│   └── qdrant_service.py       # Vector DB operations
│
├── schemas/             # Pydantic schemas
├── tests/               # Test suite
└── regulations/         # PT2030 compliance rules
```

## Core Concepts

### Multi-Tenant Isolation

Every database query is automatically filtered by tenant:

```python
# PostgreSQL RLS automatically enforces
SET app.current_tenant = '<tenant_uuid>';

# All queries now filtered by tenant_id
SELECT * FROM evf_projects;  # Only returns current tenant's data
```

### Agent Architecture

```python
# 1. Parse SAF-T file (deterministic)
saft_data = await input_agent.process(file_path)

# 2. Calculate financials (pure math)
financial = await financial_agent.calculate(saft_data)

# 3. Validate compliance (rule-based)
compliance = await compliance_agent.validate(financial)

# 4. Generate text (LLM - only agent using AI)
narrative = await narrative_agent.generate(financial)

# 5. Audit everything (tracking)
await audit_agent.log_execution(...)
```

### Critical Rules

1. **Multi-Tenant**: ALWAYS include `tenant_id` in queries
2. **Financial Calculations**: NEVER use LLM for numbers
3. **Compliance**: 100% rule-based validation
4. **Audit**: ALL operations must be logged
5. **Security**: ALL data encrypted at rest

## API Examples

### Authentication
```bash
# Register tenant
POST /api/v1/auth/register
{
  "company_name": "ACME Ltd",
  "nif": "123456789",
  "email": "admin@acme.pt",
  "password": "secure_password"
}

# Login
POST /api/v1/auth/login
{
  "email": "admin@acme.pt",
  "password": "secure_password"
}
```

### EVF Processing
```bash
# Upload SAF-T file
POST /api/v1/evf/upload
Headers: Authorization: Bearer <token>
Body: multipart/form-data
  file: <saft_file.xml>
  fund_type: PT2030

# Check status
GET /api/v1/evf/{evf_id}/status
Headers: Authorization: Bearer <token>

# Download results
GET /api/v1/evf/{evf_id}/download
Headers: Authorization: Bearer <token>
```

## Development

### Running Tests
```bash
# All tests
pytest

# With coverage
pytest --cov=backend --cov-report=html

# Specific test
pytest tests/test_agents/test_financial_agent.py -v
```

### Code Quality
```bash
# Format code
black backend/

# Lint
ruff backend/

# Type checking
mypy backend/
```

### Database Migrations
```bash
# Create migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

## Performance

### Targets
- API Response: < 3 seconds (p95)
- EVF Processing: < 3 hours end-to-end
- Cost per EVF: < €1
- Concurrent Tenants: 100+
- Uptime: 99.9%

### Optimization Strategies
- Async everywhere (FastAPI + SQLAlchemy)
- Parallel agent execution with `asyncio.gather()`
- Redis caching for expensive operations
- Connection pooling (asyncpg)
- Index optimization for tenant queries

## Security

### Authentication
- JWT tokens with 30-minute expiry
- Refresh tokens with 7-day expiry
- bcrypt password hashing (cost factor 12)
- Tenant context in token payload

### Data Protection
- PostgreSQL Row-Level Security (RLS)
- AES-256 encryption at rest
- TLS 1.3 in transit
- Rate limiting (100 req/min per tenant)
- Input validation with Pydantic

### Compliance
- GDPR compliant (EU-West hosting)
- 10-year audit log retention
- Immutable audit trails
- PT2030 regulation compliance

## Monitoring

### Health Check
```bash
curl http://localhost:8000/health
```

### Metrics (Coming Soon)
- Request latency (p50, p95, p99)
- Error rates by endpoint
- Token usage per tenant
- Daily/monthly costs
- Database performance

## Deployment

### Railway (Production)
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login and init
railway login
railway init

# Add services
railway add postgres
railway add redis

# Deploy
railway up
```

### Environment Variables
```env
ENVIRONMENT=production
DATABASE_URL=<railway-postgres-url>
REDIS_URL=<railway-redis-url>
SECRET_KEY=<generate-secure-key>
CLAUDE_API_KEY=<your-api-key>
```

## Cost Analysis

### Infrastructure (Monthly)
- Railway: €50
- Qdrant Cloud: €100
- Total: €150/month

### Per EVF
- Claude API: €0.50
- Storage: €0.05
- Total: ~€1/EVF

### Pricing
- Starter: €15/EVF
- Pro: €10/EVF
- Enterprise: €7/EVF
- Margin: 85-90%

## Documentation

- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Complete system architecture
- **[IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md)** - Step-by-step implementation
- **[QUICKSTART.md](QUICKSTART.md)** - Quick start guide
- **[API Docs](http://localhost:8000/docs)** - Interactive API documentation

## Roadmap

### Phase 1: Foundation (✅ Complete)
- [x] Core infrastructure
- [x] Multi-tenant database
- [x] Security & authentication
- [x] Middleware system

### Phase 2: Agents (In Progress)
- [ ] InputAgent implementation
- [ ] FinancialModelAgent
- [ ] ComplianceAgent
- [ ] NarrativeAgent
- [ ] AuditAgent

### Phase 3: API & Integration
- [ ] FastAPI endpoints
- [ ] Orchestrator service
- [ ] Claude integration
- [ ] Qdrant integration

### Phase 4: Testing & Deploy
- [ ] Test suite (90%+ coverage)
- [ ] Performance testing
- [ ] Production deployment
- [ ] Pilot testing

### Phase 5: Production
- [ ] Monitoring & alerting
- [ ] Customer onboarding
- [ ] Launch & scaling

## Contributing

This is a solo developer project optimized for Claude Code assistance.

Development workflow:
1. Review documentation
2. Implement features with Claude Code
3. Write tests
4. Submit for review
5. Deploy

## Support

For questions or issues:
1. Check documentation in this directory
2. Review API docs at `/docs`
3. Check logs for errors
4. Consult implementation guide

## License

Proprietary - All rights reserved

---

**Status**: Foundation Complete - Ready for Agent Implementation
**Version**: 1.0.0
**Last Updated**: 2025-11-07
