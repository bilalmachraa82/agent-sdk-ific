# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**EVF Portugal 2030** - An AI-powered B2B SaaS platform for automating Portuguese funding (IFIC/PT2030/PRR) application processing. The system orchestrates multiple specialized AI agents to transform Financial Viability Studies (EVF) from 24h manual work to 3h automated processing.

**Current Status**: Architecture and documentation phase - ready for implementation via Claude Code following the 60-day solo developer roadmap.

## Core Architecture

### Multi-Agent System (5 Specialized Sub-Agents)
1. **InputAgent** - Parse and validate SAF-T/Excel/CSV files, normalize data
2. **EVFComplianceAgent** - Validate PT2030/PRR/SITCE rules (100% deterministic)
3. **FinancialModelAgent** - VALF/TRF calculations (pure mathematical functions)
4. **NarrativeAgent** - Generate proposal text (only agent using LLM)
5. **AuditAgent** - Track all operations, costs, and compliance

### Tech Stack
- **Backend**: FastAPI 0.115+ (Python 3.11+) with async SQLAlchemy 2.0
- **Database**: PostgreSQL 16 with Row-Level Security (multi-tenant)
- **AI Integration**: Claude 4.5 Sonnet via Tool Use API
- **Vector Store**: Qdrant Cloud (multi-tenant via payload filters)
- **Cache**: Redis (Upstash serverless)
- **Frontend**: Next.js 14 App Router + TypeScript + Shadcn/ui
- **MCP Servers**: Custom servers for SAF-T parsing, compliance checking, and vector search

## Development Commands

### Initial Setup
```bash
# Install dependencies (when pyproject.toml is created)
pip install -r requirements.txt  # or poetry install

# Database setup
alembic init alembic
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head

# Start development server
uvicorn main:app --reload --port 8000

# Run tests
pytest -v --cov=. --cov-report=html
```

### MCP Server Management
```bash
# The project uses MCP servers defined in .mcp.json
# Current servers: context7, playwright, browser-use, github
# Custom servers to be implemented: saft-parser, compliance-checker, qdrant-search
```

## Critical Business Rules

1. **Financial Calculations**: All financial calculations MUST be deterministic functions. Never use LLM to generate numbers.
2. **Multi-tenancy**: Every database query MUST include tenant_id. Use PostgreSQL RLS for enforcement.
3. **Data Privacy**: Never send full SAF-T files to external APIs. Process locally via MCP servers.
4. **Audit Trail**: Every calculation and decision must have traceable source and timestamp.
5. **PT2030 Compliance**: VALF must be < 0 and TRF < 4% for approval. These are hard requirements.

## Project Structure

```
evf-portugal-2030/
├── backend/
│   ├── agents/          # 5 sub-agents implementation
│   ├── api/            # FastAPI endpoints
│   ├── core/           # Config, database, security
│   ├── models/         # SQLAlchemy models with tenant_id
│   ├── schemas/        # Pydantic schemas for validation
│   └── services/       # Business logic layer
├── frontend/
│   ├── app/            # Next.js 14 App Router
│   ├── components/     # React components with Shadcn/ui
│   └── lib/            # Utilities and API clients
├── mcp_servers/        # Custom MCP servers
│   ├── saft_parser.py
│   ├── compliance_checker.py
│   └── qdrant_search.py
├── tests/              # Pytest with 90%+ coverage target
└── .mcp.json          # MCP configuration
```

## Implementation Roadmap (60 Days)

### Week 1: Foundation
- Multi-tenant database with RLS
- JWT authentication with tenant context
- MCP server setup
- File upload system with encryption

### Week 2-3: Core Agents
- InputAgent: SAF-T/Excel parsing
- ComplianceAgent: PT2030 rules validation
- FinancialModelAgent: VALF/TRF calculations

### Week 4: AI Integration
- NarrativeAgent: Claude integration
- AuditAgent: Tracking and logging
- Qdrant vector store setup

### Week 5-6: Frontend & Testing
- Next.js dashboard with multi-tenant isolation
- Integration testing
- Performance optimization

### Week 7-8: Production & Scaling
- Deployment (Railway backend, Vercel frontend)
- Monitoring and alerts
- Customer onboarding flow

## Performance Targets
- API response time: < 3 seconds
- EVF processing: < 3 hours
- Cost per EVF: < €1
- Test coverage: > 90%
- Uptime SLA: 99.9%

## Security Requirements
- All data encrypted at rest (AES-256)
- TLS 1.3 for all connections
- JWT with tenant claims and refresh tokens
- Rate limiting per tenant (100 req/min)
- Input sanitization via Pydantic schemas
- Regular security audits for PT2030 compliance

## Testing Strategy
- Unit tests for all financial calculations
- Integration tests for multi-tenant isolation
- E2E tests for complete EVF workflow
- Load tests for 100+ concurrent tenants
- Compliance tests for PT2030 rules

## Deployment Configuration
- **Backend**: Railway (PostgreSQL + Redis included)
- **Frontend**: Vercel Pro
- **Vector DB**: Qdrant Cloud
- **Monitoring**: Sentry + Datadog
- **CI/CD**: GitHub Actions with environments (dev, staging, prod)

## Key Documentation References
- `arquitetura_mvp_v4_final.md`: Complete technical architecture
- `claude_code_implementation_v4.md`: Claude Code-specific implementation guide
- `implementacao_60dias_v4.md`: Detailed 60-day implementation plan
- `custos_roi_realista_v4.md`: Financial projections and costs

## Available Claude Code Commands
- `/scaffold-module [name]`: Create new module with tests
- `/generate-tests [module]`: Generate comprehensive test suite
- `/check-compliance`: Validate against PT2030 requirements
- `/evf-audit`: Audit financial calculations
- `/implement-agent [name]`: Create new agent with MCP integration

## Important Notes
- This is a solo developer project optimized for Claude Code assistance
- Follow the 70/30 rule: 70% AI-generated code, 30% human validation
- All financial numbers must be calculated, never estimated by LLM
- Multi-tenant isolation is critical - test thoroughly
- PT2030 compliance rules are non-negotiable