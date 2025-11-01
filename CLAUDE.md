# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**FundAI** is an AI-powered SaaS platform that automates Portuguese IFIC funding applications (PT2030 - IA nas PME). It uses a multi-agent architecture powered by Claude Sonnet 4.5 to research companies, analyze tech stacks, generate proposals, calculate merit scores, and validate compliance.

**Key Differentiator:** Stack Intelligence Engine that prevents redundant tool recommendations (e.g., never suggests Monday.com to PHC users, or Slack to Microsoft 365 users).

## Common Development Commands

### Setup & Installation
```bash
# Complete project setup
make setup                    # Install dependencies + pre-commit hooks

# Alternative: Manual Poetry setup
poetry install --with dev
poetry run pre-commit install
```

### Development
```bash
# Start development server (FastAPI with hot reload)
make dev                      # Runs on http://localhost:8000
# API documentation: http://localhost:8000/docs

# Run with Docker Compose (full stack: API + PostgreSQL + Redis)
make docker-up                # Start all services
make docker-down              # Stop all services
make docker-logs              # View logs
```

### Testing
```bash
# Run all tests
make test                     # Standard test run
make test-verbose             # Verbose output
make test-cov                 # With coverage report (opens htmlcov/index.html)

# Run specific test categories
make test-unit                # Unit tests only (fast)
make test-integration         # Integration tests only (slower)

# Test individual agents
pytest tests/test_agents.py::TestStackIntelligenceAgent -v
```

### Code Quality
```bash
# Format code
make format                   # Black formatter (100 char line length)

# Lint code
make lint                     # Ruff linter
make lint-fix                 # Auto-fix linting issues

# Type checking
make typecheck                # mypy with strict mode

# Run all quality checks
make quality                  # format + lint + typecheck
```

### Database
```bash
# Run migrations
make db-migrate               # Apply all pending migrations

# Rollback migration
make db-rollback              # Rollback one migration

# Reset database (WARNING: destroys data)
make db-reset                 # Drop all data and restart
```

### Pre-deployment
```bash
# Full validation before deploying
make deploy-check             # Runs quality + test
```

## High-Level Architecture

### Multi-Agent Orchestration System

The application uses a **coordinator pattern** where `IFICOrchestrator` (orchestrator.py:30) manages an 8-phase pipeline:

```
┌────────────────────────────────────────────────────────┐
│              IFICOrchestrator                          │
│         (agents/orchestrator.py:30)                    │
└────────────────────────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┬──────────────┐
        ▼                ▼                ▼              ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ RESEARCHER   │ │ STACK INTEL  │ │ FINANCIAL    │ │ SCORER       │
│ (Phase 1)    │ │ (Phase 2)    │ │ (Phase 4)    │ │ (Phase 6)    │
└──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘
                         │                │              │
                         └────────────────┼──────────────┘
                                          ▼
                              ┌──────────────────────┐
                              │  WRITER + VALIDATOR  │
                              │  (Phases 5,7,8)      │
                              └──────────────────────┘
```

**Phase Breakdown:**
1. **Company Research** (researcher.py:27) - eInforma → Racius → Website scraping
2. **Stack Intelligence** (stack_intel.py:15) - Redundancy detection + recommendations
3. **Budget Gate** (orchestrator.py:317) - Validates IFIC minimum requirements
4. **Financial Analysis** (agents/financial.py) - IES parsing, ratios, ROI projections
5. **Use Case Generation** (agents/writer.py) - Claude-powered use case generation
6. **Merit Scoring** (agents/scorer.py) - MP = 0.5A + 0.5B calculation
7. **Compliance Validation** (agents/validator.py) - RGPD/DNSH/eligibility checks
8. **Proposal Generation** (agents/writer.py) - HTML + CSV artifacts

### Critical Business Logic

#### Stack Intelligence Redundancy Rules (stack_intel.py:27)
**NEVER modify these without understanding business impact:**

```python
REDUNDANCY_RULES = {
    "PHC": ["Monday.com", "HubSpot CRM", "Salesforce", "NetSuite"],
    "Microsoft 365": ["Slack", "Notion", "Trello", "Asana"],
    "SAP": ["NetSuite", "Odoo", "PHC"],
    # ... (see stack_intel.py:27-63)
}
```

**Why this matters:** Portuguese ERPs (PHC, Primavera) have broad functionality. Suggesting redundant tools destroys proposal credibility with IFIC evaluators.

**Testing redundancy rules:**
```bash
pytest tests/test_agents.py::test_phc_blocks_mondaycom -v
pytest tests/test_agents.py::test_m365_blocks_slack -v
```

#### Budget Gate Validation (orchestrator.py:317)
Enforces IFIC constraints:
- Minimum eligible investment: €5,000 (settings.ific_min_eligible)
- Cofinancing rate: 75% (25% company contribution required)
- Budget tiers: Essencial/Recomendado/Completo with realistic allocations (60-70% RH, not 47%!)

#### Merit Score Calculation (agents/scorer.py)
Formula: `MP = 0.50 × A + 0.50 × min(B1, B2)`
- Job creation = 25% of B score (critical for approval)
- Target: MP ≥ 4.0 for competitive applications
- Generates what-if scenarios for proposal interactivity

### Data Flow

1. **Input:** User submits `ApplicationRequest` via API (main.py:110)
2. **Research:** CompanyResearchAgent fetches data from 3 sources (researcher.py:33)
3. **Analysis:** StackIntelligenceAgent + FinancialAnalysisAgent process data
4. **Scoring:** MeritScoringAgent calculates MP with job creation impact
5. **Validation:** ComplianceValidatorAgent checks RGPD/DNSH/eligibility
6. **Output:** FundingApplication with HTML proposal + CSVs + audit trail

### Key Files & Their Responsibilities

**Core Application:**
- `main.py` - FastAPI application with 8 REST endpoints
- `orchestrator.py` - Main coordinator for 8-phase pipeline
- `config.py` - Centralized settings (50+ env vars) with Pydantic validation
- `schemas.py` - 15+ validated data models (CompanyData, BudgetInput, MeritScore, etc.)

**Agents (All in root directory):**
- `researcher.py` - Company data fetching (eInforma/Racius/website)
- `stack_intel.py` - **CRITICAL** - Redundancy detection engine
- `__init__.py` - Placeholder for FinancialAnalysisAgent, ProposalWriterAgent, MeritScoringAgent, ComplianceValidatorAgent

**Infrastructure:**
- `Dockerfile` - Multi-stage build for production
- `docker-compose.yml` - Development stack (API + PostgreSQL + Redis + Celery)
- `Makefile` - 30+ common commands
- `pyproject.toml` - Poetry dependencies (25+ packages)

**Testing:**
- `test_agents.py` - Unit tests for all agents
- `pytest.ini` - Test configuration (asyncio mode)

## Development Patterns

### Adding a New Agent

1. Create agent class in root directory (e.g., `new_agent.py`)
2. Initialize in orchestrator: `self.new_agent = NewAgent(self.client)`
3. Add phase to `process_application()` method in orchestrator.py
4. Create unit tests in `test_agents.py`
5. Add feature flag to config.py if needed

### Adding a New API Endpoint

1. Define request/response models in `schemas.py`
2. Add endpoint in `main.py` following existing pattern
3. Use dependency injection: `orchestrator: IFICOrchestrator = Depends(get_orchestrator)`
4. Add integration test in `tests/integration/`
5. Test via Swagger UI: http://localhost:8000/docs

### Working with Claude API

All agents use Claude via the Anthropic SDK:
```python
response = self.client.messages.create(
    model=settings.claude_model,  # claude-sonnet-4-20250514
    max_tokens=4000,
    temperature=0.3,
    messages=[{"role": "user", "content": prompt}]
)
```

**Best practices:**
- Use temperature=0.3 for consistent outputs
- Extract structured data via JSON formatting in prompts
- Handle API errors gracefully (see researcher.py:241)
- Log all Claude calls for debugging: `logger.info(f"Claude call | prompt_length={len(prompt)}")`

### Configuration Management

All settings in `config.py` use Pydantic for validation:
```python
from core.config import settings

# Access settings
api_key = settings.anthropic_api_key
min_investment = settings.ific_min_eligible
```

**Environment variables:**
- Required: `ANTHROPIC_API_KEY`, `SECRET_KEY`, `POSTGRES_PASSWORD`
- Optional: `EINFORMA_API_KEY`, `RACIUS_API_KEY`, `SENTRY_DSN`
- See `.env.example` for full list

### Testing Strategy

**Unit tests** - Fast, isolated, mock external dependencies:
```python
@pytest.mark.unit
def test_budget_gate_validation():
    orchestrator = IFICOrchestrator()
    orchestrator._validate_budget_gate(valid_budget)  # Should not raise
```

**Integration tests** - Slower, test full pipeline:
```python
@pytest.mark.integration
async def test_full_application_processing():
    application = await orchestrator.process_application(...)
    assert application.status == ApplicationStatus.READY
    assert application.merit_scoring.merit_point_final >= 3.0
```

**Critical test scenarios:**
- Stack Intelligence: PHC blocks Monday.com, M365 blocks Slack
- Budget Gate: Validates €5k minimum, 25% cofinancing
- Merit Scoring: Job creation bonus = 25% of B score
- ROI Caps: Never exceeds 60% (realistic projections)

## Important Constraints

### IFIC Regulatory Requirements
- Minimum eligible investment: €5,000
- Maximum incentive: €300,000
- Cofinancing rate: 75% (company pays 25%)
- Duration: Max 24 months
- RH allocation: 60-70% (NOT 47%!)
- Training allocation: 4-10% (realistic)

### Data Compliance
- **RGPD:** All AI services must use EU data centers (Azure OpenAI, not OpenAI.com)
- **DNSH:** Proposals must validate "Do No Significant Harm" environmental principles
- **Double Funding:** Check against other EU funds (Compete 2030, etc.)

### Performance Targets
- End-to-end processing: <3 minutes (see orchestrator.py:303)
- API response time: <5 seconds for application creation
- Approval rate target: >70% (vs 30-40% DIY)
- Merit score target: ≥4.0 average

## Common Gotchas

1. **Portuguese ERP Context:** PHC and Primavera are NOT just accounting software - they include CRM, project management, and workflow. Always check REDUNDANCY_RULES before suggesting tools.

2. **Merit Score Formula:** Job creation is 25% of B1 score, NOT total merit score. Creating +2 FTE can swing MP from 3.5 to 4.2.

3. **Budget Allocations:** IFIC expects 60-70% RH, 4-10% training. Proposals with 47% training get flagged as unrealistic.

4. **ROI Caps:** Never project >60% ROI. Conservative (30-50%) projections build credibility.

5. **NUTS II Inference:** Lisboa (PT17) is default if city unknown (see researcher.py:105). Always verify for non-Lisbon companies.

6. **Async/Await:** All agent methods are async. Use `await` when calling them:
   ```python
   # WRONG
   company_data = orchestrator.researcher.fetch_company_data(...)

   # CORRECT
   company_data = await orchestrator.researcher.fetch_company_data(...)
   ```

7. **Type Hints:** This project uses strict mypy. Always add type hints:
   ```python
   # WRONG
   def calculate_score(metrics):

   # CORRECT
   def calculate_score(metrics: ImpactMetrics) -> float:
   ```

## Roadmap Context

**Current Status:** Production-ready skeleton with core agents implemented

**Pending Implementation:**
- Database layer (SQLAlchemy models + Alembic migrations)
- Real eInforma API integration (currently placeholder at researcher.py:137)
- Proposal HTML template generation (6-module structure with glassmorphism CSS)
- File storage (S3/GCS for artifacts)
- Authentication (JWT for multi-user)
- Rate limiting (Redis-based)

**Critical Path for MVP:**
1. eInforma API integration (highest priority - main data source)
2. Proposal HTML template generation (core deliverable)
3. Database persistence (required for production)

**Business Model:**
- Pricing tiers: €1.5k (DIY) / €5k (Standard) / €8k (Premium)
- Target: €150k ARR by Q4 2026
- Success metrics: >70% approval rate, <3 day turnaround

## Code Style

- **Line length:** 100 characters (Black + Ruff)
- **Docstrings:** Google style with type hints in signature
- **Logging:** Use loguru, not print()
- **Error handling:** Log errors with context, raise specific exceptions
- **Naming:** snake_case for functions/variables, PascalCase for classes

## References

For detailed specifications, see:
- `IFIC_SAAS_CLAUDE_CONFIG.md` - Master technical specification (62 KB)
- `QUICKSTART_CLAUDE_CODE.md` - Implementation roadmap (12 phases)
- `DEPLOYMENT.md` - Production deployment guide
- `PROJECT_SUMMARY.md` - Session summary with implementation notes
