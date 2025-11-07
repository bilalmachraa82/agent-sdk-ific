# EVF Portugal 2030 - Backend Implementation Guide

## Project Overview

This guide provides complete implementation instructions for the EVF Portugal 2030 backend platform. The system is designed as a multi-tenant B2B SaaS application using FastAPI with 5 specialized AI agents.

## Directory Structure Created

```
/Users/bilal/Programaçao/Agent SDK - IFIC/backend/
├── agents/                          # 5 Sub-agents (to be implemented)
│   ├── __init__.py
│   ├── base_agent.py               # Abstract base class
│   ├── input_agent.py              # SAF-T parser (deterministic)
│   ├── compliance_agent.py         # PT2030 validator (rule-based)
│   ├── financial_agent.py          # VALF/TRF calculator (pure math)
│   ├── narrative_agent.py          # Text generation (Claude LLM)
│   └── audit_agent.py              # Tracking & cost control
├── api/
│   ├── __init__.py
│   ├── main.py                     # FastAPI app
│   ├── deps.py                     # Dependencies
│   └── routers/
│       ├── __init__.py
│       ├── auth.py                 # Authentication
│       ├── evf.py                  # EVF operations
│       └── admin.py                # Admin endpoints
├── core/
│   ├── __init__.py
│   ├── config.py                   # ✅ CREATED - Pydantic settings
│   ├── database.py                 # ✅ CREATED - Async SQLAlchemy
│   ├── security.py                 # ✅ CREATED - JWT & passwords
│   ├── middleware.py               # ✅ CREATED - Tenant isolation
│   └── tenant.py                   # Tenant context manager
├── models/
│   ├── __init__.py
│   ├── base.py                     # Base model with tenant_id
│   ├── tenant.py                   # Tenant model
│   ├── user.py                     # User model
│   ├── evf.py                      # EVF project model
│   └── audit.py                    # Audit log model
├── schemas/
│   ├── __init__.py
│   ├── tenant.py                   # Tenant Pydantic schemas
│   ├── evf.py                      # EVF schemas
│   └── auth.py                     # Auth schemas
├── services/
│   ├── __init__.py
│   ├── saft_parser.py              # SAF-T XML parser
│   ├── claude_client.py            # Claude API wrapper
│   ├── qdrant_service.py           # Vector DB service
│   ├── orchestrator.py             # Agent orchestration
│   └── excel_generator.py          # Excel output generation
├── workers/
│   └── background.py               # Background task workers
├── tests/
│   ├── conftest.py                 # Pytest fixtures
│   ├── test_agents/
│   ├── test_compliance/
│   └── test_financial/
├── regulations/
│   ├── pt2030_rules.json           # PT2030 compliance rules
│   ├── prr_rules.json              # PRR rules
│   └── sitce_rules.json            # SITCE rules
├── alembic/                        # Database migrations
├── requirements.txt                # ✅ CREATED
├── pyproject.toml                  # ✅ CREATED
├── .env.example                    # ✅ CREATED
├── ARCHITECTURE.md                 # ✅ CREATED
└── IMPLEMENTATION_GUIDE.md         # This file
```

## Implementation Status

### ✅ Completed Files
1. `/backend/requirements.txt` - All Python dependencies
2. `/backend/pyproject.toml` - Poetry configuration
3. `/backend/.env.example` - Environment variables template
4. `/backend/core/config.py` - Configuration management
5. `/backend/core/database.py` - Async database with RLS
6. `/backend/core/security.py` - JWT authentication
7. `/backend/core/middleware.py` - Tenant isolation
8. `/backend/ARCHITECTURE.md` - Complete architecture documentation

### 🔨 Next Steps - Critical Files to Implement

#### 1. Base Models (`models/base.py`)
```python
"""
Base SQLAlchemy models with multi-tenant support.
All models inherit from TenantBaseModel which includes tenant_id.
"""
from datetime import datetime
from uuid import uuid4
from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class TenantBaseModel(Base):
    """Abstract base model with tenant isolation."""
    __abstract__ = True

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()
```

#### 2. Tenant Model (`models/tenant.py`)
```python
"""Tenant model for multi-tenant architecture."""
from sqlalchemy import Column, String, Numeric, JSON
from backend.models.base import Base

class Tenant(Base):
    """Represents a tenant (company/organization)."""
    __tablename__ = "tenants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    slug = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    nif = Column(String(9), unique=True, nullable=False)
    plan = Column(String(50), default="starter")
    mrr = Column(Numeric(10, 2), default=0)
    settings = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
```

#### 3. EVF Project Model (`models/evf.py`)
```python
"""EVF project model with all financial data."""
from sqlalchemy import Column, String, Numeric, JSON, ForeignKey, Index
from sqlalchemy.orm import relationship
from backend.models.base import TenantBaseModel

class EVFProject(TenantBaseModel):
    """EVF (Financial Viability Study) project."""
    __tablename__ = "evf_projects"

    company_nif = Column(String(9), nullable=False)
    company_name = Column(String(255), nullable=False)
    fund_type = Column(String(50), nullable=False)  # PT2030, PRR, SITCE
    status = Column(String(50), default="draft")

    # Financial results (calculated by FinancialModelAgent)
    valf = Column(Numeric(15, 2))  # Must be < 0
    trf = Column(Numeric(5, 2))    # Must be < 4%
    payback = Column(Numeric(5, 2))

    # Data structures
    assumptions = Column(JSON)
    projections = Column(JSON)
    compliance_status = Column(JSON)

    # File paths
    input_file_path = Column(String(500))
    excel_output_path = Column(String(500))
    pdf_output_path = Column(String(500))

    # Relationships
    audit_logs = relationship("AuditLog", back_populates="evf_project")

    __table_args__ = (
        Index('idx_tenant_status', 'tenant_id', 'status'),
        Index('idx_tenant_created', 'tenant_id', 'created_at'),
    )
```

#### 4. Agent Orchestrator (`services/orchestrator.py`)
```python
"""
Orchestrates the 5 sub-agents to process EVF projects.
Handles parallel execution where possible.
"""
import asyncio
from typing import Dict, Any
from backend.agents.input_agent import InputAgent
from backend.agents.financial_agent import FinancialModelAgent
from backend.agents.compliance_agent import EVFComplianceAgent
from backend.agents.narrative_agent import NarrativeAgent
from backend.agents.audit_agent import AuditAgent

class EVFOrchestrator:
    """Coordinates all agents to process EVF."""

    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self.input_agent = InputAgent(tenant_id)
        self.financial_agent = FinancialModelAgent(tenant_id)
        self.compliance_agent = EVFComplianceAgent(tenant_id)
        self.narrative_agent = NarrativeAgent(tenant_id)
        self.audit_agent = AuditAgent(tenant_id)

    async def process_evf(self, evf_id: str, file_path: str) -> Dict[str, Any]:
        """
        Complete EVF processing pipeline.

        Workflow:
        1. Parse SAF-T file (InputAgent)
        2. Calculate VALF/TRF + Validate compliance (parallel)
        3. Generate narrative text (NarrativeAgent)
        4. Audit everything (AuditAgent)
        """

        # Step 1: Parse and validate input
        saft_data = await self.input_agent.process(file_path, "xml")

        if saft_data.quality_score < 70:
            raise ValueError(f"Data quality too low: {saft_data.quality_score}%")

        # Step 2: Parallel calculations
        financial_task = self.financial_agent.calculate({
            "last_year_revenue": saft_data.accounts.get("71", 0),
            "last_year_costs": saft_data.accounts.get("62", 0),
            "investment": 500000,  # From form input
            "project_years": 10
        })

        compliance_task = self.compliance_agent.validate({
            "company_name": saft_data.company_name,
            "valf": None,  # Will be set after calculation
            "trf": None,
            "project_years": 10
        }, fund_type="PT2030")

        financial_results, compliance_results = await asyncio.gather(
            financial_task,
            compliance_task
        )

        # Step 3: Generate narrative
        narrative = await self.narrative_agent.generate({
            "company_name": saft_data.company_name,
            "investment": 500000,
            "valf": financial_results["valf"],
            "trf": financial_results["trf"],
            "fiscal_year": saft_data.fiscal_year
        })

        # Step 4: Audit
        await self.audit_agent.log_execution({
            "evf_id": evf_id,
            "agent_name": "orchestrator",
            "action": "process_evf",
            "tokens_used": narrative["tokens_used"],
            "cost_euros": narrative["cost_euros"]
        })

        return {
            "saft_data": saft_data,
            "financial_results": financial_results,
            "compliance_results": compliance_results,
            "narrative": narrative
        }
```

## Agent Implementation Details

### 1. InputAgent (Deterministic Parser)
**File**: `agents/input_agent.py`
**Purpose**: Parse SAF-T XML files, validate structure, map to SNC taxonomy
**AI Usage**: NONE - Pure XML parsing with lxml
**Key Functions**:
- `process(file_path, file_type)` - Main entry point
- `_process_saft(file_path)` - Parse SAF-T XML
- `_validate_xsd(doc)` - Validate against XSD schema
- `_map_to_snc(account_id)` - Map to Portuguese SNC codes
- `_calculate_quality_score()` - Data quality 0-100%

### 2. FinancialModelAgent (Pure Mathematics)
**File**: `agents/financial_agent.py`
**Purpose**: Calculate VALF, TRF, cash flows - 100% deterministic
**AI Usage**: NONE - Pure financial formulas
**Key Functions**:
- `calculate(financial_data)` - Main calculation
- `_project_cash_flows()` - 10-year projections
- `_calculate_valf()` - Net Present Value at 4%
- `_calculate_trf()` - Internal Rate of Return
- `_calculate_payback()` - Payback period
**Critical**: Never use LLM for numbers!

### 3. EVFComplianceAgent (Rule-Based Validation)
**File**: `agents/compliance_agent.py`
**Purpose**: Validate PT2030/PRR rules, no hallucinations
**AI Usage**: NONE - Rule engine only
**Key Functions**:
- `validate(evf_data, fund_type)` - Main validation
- `_load_rules()` - Load from regulations/pt2030_rules.json
- `_check_valf()` - VALF < 0 check
- `_check_trf()` - TRF < 4% check
- `_generate_suggestions()` - Actionable fixes

### 4. NarrativeAgent (LLM Text Generation)
**File**: `agents/narrative_agent.py`
**Purpose**: Generate explanatory text using Claude
**AI Usage**: Claude 4.5 Sonnet - ONLY agent using LLM
**Key Functions**:
- `generate(evf_data)` - Generate all text sections
- `_generate_section(section_type)` - Specific section
- System prompt enforces: NEVER invent numbers
**Critical**: All numbers come from provided data!

### 5. AuditAgent (Tracking & Compliance)
**File**: `agents/audit_agent.py`
**Purpose**: Track all operations, costs, ensure compliance
**AI Usage**: NONE - Pure logging
**Key Functions**:
- `log_execution(data)` - Create audit entry
- `get_daily_stats()` - Usage tracking
- `_check_limits()` - Cost control
- `_hash_data()` - SHA-256 for integrity

## FastAPI Application Structure

### Main Application (`api/main.py`)
```python
"""FastAPI application with multi-tenant middleware."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.core.config import settings
from backend.core.middleware import TenantMiddleware
from backend.core.database import initialize_database, close_database
from backend.api.routers import auth, evf, admin

app = FastAPI(
    title=settings.api_title,
    description=settings.api_description,
    version=settings.api_version
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.api_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Tenant isolation middleware
app.add_middleware(TenantMiddleware)

# Startup/shutdown events
@app.on_event("startup")
async def startup():
    await initialize_database()

@app.on_event("shutdown")
async def shutdown():
    await close_database()

# Include routers
app.include_router(auth.router, prefix=f"{settings.api_prefix}/auth", tags=["auth"])
app.include_router(evf.router, prefix=f"{settings.api_prefix}/evf", tags=["evf"])
app.include_router(admin.router, prefix=f"{settings.api_prefix}/admin", tags=["admin"])

@app.get("/health")
async def health():
    return {"status": "healthy", "version": settings.api_version}
```

## Database Migration Setup

### Initialize Alembic
```bash
cd backend
alembic init alembic
```

### Configure `alembic/env.py`
```python
from backend.core.config import settings
from backend.models.base import Base

target_metadata = Base.metadata
config.set_main_option("sqlalchemy.url", settings.database_url)
```

### Create Initial Migration
```bash
alembic revision --autogenerate -m "Initial schema with multi-tenant"
alembic upgrade head
```

## Testing Structure

### Pytest Configuration (`conftest.py`)
```python
"""Pytest fixtures for multi-tenant testing."""
import pytest
import asyncio
from httpx import AsyncClient
from backend.api.main import app
from backend.core.database import db_manager

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def client():
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

@pytest.fixture
def test_tenant():
    return {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "slug": "test-tenant",
        "name": "Test Company"
    }
```

## Deployment Commands

### Local Development
```bash
# Install dependencies
cd backend
pip install -r requirements.txt

# Setup environment
cp .env.example .env
# Edit .env with your credentials

# Run database
docker-compose up -d postgres redis

# Run migrations
alembic upgrade head

# Start server
uvicorn backend.api.main:app --reload --host 0.0.0.0 --port 8000
```

### Production Deployment (Railway)
```bash
# Push to GitHub
git add .
git commit -m "Backend implementation complete"
git push origin main

# Railway will auto-deploy
# Ensure environment variables are set in Railway dashboard
```

## Critical Implementation Rules

### 1. Multi-Tenant Isolation
- ✅ ALWAYS include `tenant_id` in database queries
- ✅ ALWAYS set PostgreSQL RLS context
- ✅ ALWAYS validate tenant access in middleware
- ❌ NEVER mix data between tenants

### 2. Financial Calculations
- ✅ ALWAYS use deterministic mathematical functions
- ✅ ALWAYS validate inputs before calculations
- ✅ ALWAYS round to 2 decimal places
- ❌ NEVER use LLM to generate numbers

### 3. Security
- ✅ ALWAYS hash passwords with bcrypt
- ✅ ALWAYS validate JWT tokens
- ✅ ALWAYS use HTTPS in production
- ❌ NEVER log sensitive data

### 4. Error Handling
- ✅ ALWAYS catch and log exceptions
- ✅ ALWAYS return meaningful error messages
- ✅ ALWAYS rollback database transactions on error
- ❌ NEVER expose internal errors to users

## Performance Optimization

### Database
- Index on (tenant_id, created_at) for EVF projects
- Connection pooling with asyncpg
- Query result caching with Redis

### API
- Async endpoints with FastAPI
- Parallel agent execution with asyncio.gather()
- Response compression for large payloads

### Caching Strategy
```python
# Cache benchmarks for 1 hour
@cached(ttl=3600, key="benchmarks:{sector}:{tenant_id}")
async def get_sector_benchmarks(sector: str, tenant_id: str):
    return await qdrant_service.search(...)
```

## Cost Control

### Daily Monitoring
```python
async def check_daily_costs(tenant_id: str):
    stats = await audit_agent.get_daily_stats()
    if stats["cost_euros"] > 50:
        await send_alert(f"Tenant {tenant_id} exceeded daily limit")
```

### Monthly Reporting
- Aggregate token usage per tenant
- Calculate actual cost vs MRR
- Identify optimization opportunities

## Next Implementation Steps

1. **Complete Model Files** (2-3 hours)
   - `models/base.py`, `models/tenant.py`, `models/evf.py`

2. **Implement 5 Agents** (8-10 hours)
   - Start with `InputAgent` (SAF-T parser)
   - Then `FinancialModelAgent` (calculations)
   - Then `ComplianceAgent` (validation)
   - Then `NarrativeAgent` (text generation)
   - Finally `AuditAgent` (tracking)

3. **Create API Endpoints** (4-5 hours)
   - `routers/auth.py` - Login/register
   - `routers/evf.py` - Upload/process/download
   - `routers/admin.py` - Tenant management

4. **Write Tests** (6-8 hours)
   - Unit tests for each agent
   - Integration tests for orchestrator
   - E2E tests for complete workflow

5. **Setup Deployment** (2-3 hours)
   - Railway configuration
   - Environment variables
   - CI/CD pipeline

## Total Estimated Time
- **Solo developer**: 60 days @ 6 hours/day = 240 hours
- **With Claude Code assistance**: 30-40 days @ 6 hours/day = 120-160 hours

## Resources

- **PT2030 Official Documentation**: https://www.portugal2030.pt
- **SAF-T Specification**: https://info.portaldasfinancas.gov.pt/pt/apoio_contribuinte/
- **FastAPI Documentation**: https://fastapi.tiangolo.com
- **SQLAlchemy Async**: https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html
- **Claude API**: https://docs.anthropic.com

---

**Version**: 1.0.0
**Last Updated**: 2025-11-07
**Status**: Implementation Ready
