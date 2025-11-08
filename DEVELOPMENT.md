# EVF Portugal 2030 - Development Guide

Complete guide for developers working on the EVF Portugal 2030 platform.

---

## Table of Contents

1. [Development Environment Setup](#development-environment-setup)
2. [Project Structure](#project-structure)
3. [Development Workflow](#development-workflow)
4. [Coding Standards](#coding-standards)
5. [Testing Guidelines](#testing-guidelines)
6. [Database Management](#database-management)
7. [API Development](#api-development)
8. [Agent Development](#agent-development)
9. [Frontend Development](#frontend-development)
10. [Debugging](#debugging)
11. [Common Tasks](#common-tasks)

---

## Development Environment Setup

### Initial Setup

1. **Clone and Configure**
   ```bash
   git clone <repository-url>
   cd "Agent SDK - IFIC"
   chmod +x *.sh
   ```

2. **Backend Setup**
   ```bash
   cd backend
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   cp .env.example .env
   # Edit .env with your keys
   ```

3. **Frontend Setup**
   ```bash
   cd frontend
   npm install
   cp .env.example .env.local
   # Edit .env.local
   ```

4. **Database Setup**
   ```bash
   ./start_postgres.sh
   cd backend
   alembic upgrade head
   python seed_data.py
   ```

### IDE Configuration

#### VS Code (Recommended)

**Recommended Extensions:**
- Python (Microsoft)
- Pylance
- Black Formatter
- Ruff
- ESLint
- Prettier
- Tailwind CSS IntelliSense
- GitLens

**settings.json:**
```json
{
  "python.linting.enabled": true,
  "python.linting.ruffEnabled": true,
  "python.formatting.provider": "black",
  "editor.formatOnSave": true,
  "python.analysis.typeCheckingMode": "basic",
  "[python]": {
    "editor.defaultFormatter": "ms-python.black-formatter",
    "editor.codeActionsOnSave": {
      "source.organizeImports": true
    }
  },
  "[typescript]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode"
  },
  "[typescriptreact]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode"
  }
}
```

#### PyCharm

1. Configure Python interpreter to use `backend/venv`
2. Enable Black formatter
3. Enable Ruff linter
4. Set import optimization on save

---

## Project Structure

### Backend Structure

```
backend/
├── agents/                 # AI agent implementations
│   ├── __init__.py
│   ├── input_agent.py     # File parsing & normalization
│   ├── compliance_agent.py # PT2030 rule validation
│   ├── financial_agent.py  # VALF/TRF calculations
│   ├── narrative_agent.py  # AI narrative generation
│   └── audit_agent.py      # Audit logging
├── api/                    # FastAPI routes
│   ├── __init__.py
│   └── routers/
│       ├── auth.py         # Authentication endpoints
│       ├── evf.py          # EVF processing endpoints
│       ├── files.py        # File upload/download
│       ├── admin.py        # Admin endpoints
│       └── health.py       # Health checks
├── core/                   # Core functionality
│   ├── config.py           # Configuration settings
│   ├── database.py         # Database connection
│   ├── security.py         # JWT, password hashing
│   ├── middleware.py       # Custom middleware
│   ├── logging.py          # Structured logging
│   └── encryption.py       # File encryption
├── models/                 # SQLAlchemy models
│   ├── base.py             # Base model with tenant_id
│   ├── tenant.py           # Tenant model
│   ├── user.py             # User model
│   ├── evf.py              # EVF project model
│   ├── file.py             # File metadata model
│   └── audit.py            # Audit log model
├── schemas/                # Pydantic schemas
│   ├── tenant.py           # Tenant schemas
│   ├── auth.py             # Auth request/response
│   ├── evf.py              # EVF schemas
│   └── file.py             # File schemas
├── services/               # Business logic
│   ├── orchestrator.py     # Agent orchestration
│   ├── cache_service.py    # Redis caching
│   ├── file_storage.py     # File storage (S3/local)
│   ├── qdrant_service.py   # Vector store
│   └── excel_generator.py  # Excel report generation
├── tests/                  # Test suite
│   ├── test_agents.py
│   ├── test_api.py
│   └── test_services.py
├── alembic/                # Database migrations
│   ├── versions/
│   └── env.py
├── main.py                 # FastAPI application
├── requirements.txt        # Python dependencies
└── seed_data.py           # Database seeding
```

### Frontend Structure

```
frontend/
├── app/                    # Next.js App Router
│   ├── layout.tsx          # Root layout
│   ├── page.tsx            # Home page
│   ├── login/              # Login page
│   ├── dashboard/          # Dashboard
│   └── evf/                # EVF pages
├── components/             # React components
│   ├── ui/                 # Shadcn UI components
│   ├── layout/             # Layout components
│   ├── forms/              # Form components
│   └── charts/             # Chart components
├── lib/                    # Utilities
│   ├── api.ts              # API client
│   ├── auth.ts             # Auth utilities
│   └── utils.ts            # Helper functions
├── hooks/                  # Custom React hooks
├── stores/                 # Zustand stores
├── types/                  # TypeScript types
└── public/                 # Static assets
```

---

## Development Workflow

### Feature Development

1. **Create Feature Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Implement Feature**
   - Write code
   - Add tests
   - Update documentation

3. **Run Quality Checks**
   ```bash
   # Backend
   cd backend
   black .
   ruff check .
   pytest -v --cov=.

   # Frontend
   cd frontend
   npm run lint
   npm run type-check
   ```

4. **Commit Changes**
   ```bash
   git add .
   git commit -m "feat: add your feature description"
   ```

5. **Push and Create PR**
   ```bash
   git push origin feature/your-feature-name
   ```

### Commit Message Convention

Use conventional commits:
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `test:` - Test additions/changes
- `refactor:` - Code refactoring
- `chore:` - Maintenance tasks

---

## Coding Standards

### Python (Backend)

**Follow PEP 8 with Black formatting:**

```python
# Good
async def get_evf_by_id(
    evf_id: UUID,
    tenant_id: UUID,
    session: AsyncSession
) -> EVFProject:
    """
    Retrieve EVF project by ID with tenant isolation.

    Args:
        evf_id: EVF project UUID
        tenant_id: Tenant UUID
        session: Database session

    Returns:
        EVFProject instance

    Raises:
        HTTPException: If EVF not found
    """
    query = select(EVFProject).where(
        EVFProject.id == evf_id,
        EVFProject.tenant_id == tenant_id
    )
    result = await session.execute(query)
    evf = result.scalar_one_or_none()

    if not evf:
        raise HTTPException(status_code=404, detail="EVF not found")

    return evf
```

**Type hints are mandatory:**

```python
# Good
def calculate_valf(
    cash_flows: list[float],
    discount_rate: float
) -> float:
    pass

# Bad
def calculate_valf(cash_flows, discount_rate):
    pass
```

### TypeScript (Frontend)

**Use TypeScript strictly:**

```typescript
// Good
interface EVFProject {
  id: string;
  name: string;
  totalInvestment: number;
  status: EVFStatus;
}

async function fetchEVF(id: string): Promise<EVFProject> {
  const response = await api.get<EVFProject>(`/evf/${id}`);
  return response.data;
}

// Bad
async function fetchEVF(id) {
  const response = await api.get(`/evf/${id}`);
  return response.data;
}
```

---

## Testing Guidelines

### Backend Testing

**Unit Tests:**

```python
import pytest
from backend.agents.financial_agent import FinancialModelAgent

@pytest.mark.asyncio
async def test_calculate_valf():
    """Test VALF calculation with known cash flows."""
    agent = FinancialModelAgent()

    cash_flows = [-100000, 30000, 40000, 50000]
    discount_rate = 0.08

    valf = agent.calculate_valf(cash_flows, discount_rate)

    assert valf < 0, "VALF should be negative for approval"
    assert abs(valf - (-8532.45)) < 1, "VALF calculation incorrect"
```

**Integration Tests:**

```python
@pytest.mark.asyncio
async def test_evf_processing_workflow(client, auth_headers):
    """Test complete EVF processing workflow."""
    # Upload file
    with open("tests/fixtures/sample_saft.xml", "rb") as f:
        response = await client.post(
            "/api/v1/files/upload",
            files={"file": f},
            headers=auth_headers
        )
    assert response.status_code == 200
    file_id = response.json()["id"]

    # Create EVF
    response = await client.post(
        "/api/v1/evf/create",
        json={
            "name": "Test EVF",
            "file_id": file_id,
            "fund_type": "PT2030"
        },
        headers=auth_headers
    )
    assert response.status_code == 201
    evf_id = response.json()["id"]

    # Wait for processing
    # ... assert final status
```

### Frontend Testing

(To be implemented with Jest/React Testing Library)

---

## Database Management

### Creating Migrations

```bash
cd backend

# Auto-generate migration from model changes
alembic revision --autogenerate -m "add new field to evf table"

# Review generated migration in alembic/versions/
# Edit if necessary

# Apply migration
alembic upgrade head
```

### Manual Migrations

```python
# alembic/versions/xxx_manual_change.py
from alembic import op
import sqlalchemy as sa

def upgrade():
    op.add_column('evf_projects',
        sa.Column('new_field', sa.String(100), nullable=True)
    )

def downgrade():
    op.drop_column('evf_projects', 'new_field')
```

### Adding Row-Level Security

```python
def upgrade():
    # Enable RLS on table
    op.execute('ALTER TABLE evf_projects ENABLE ROW LEVEL SECURITY')

    # Create policy
    op.execute('''
        CREATE POLICY tenant_isolation ON evf_projects
        USING (tenant_id = current_setting('app.current_tenant')::uuid)
    ''')
```

---

## API Development

### Adding New Endpoint

1. **Define Schema** (`schemas/your_feature.py`):
   ```python
   from pydantic import BaseModel, Field

   class FeatureCreate(BaseModel):
       name: str = Field(..., min_length=1, max_length=100)
       value: float = Field(..., gt=0)

   class FeatureResponse(BaseModel):
       id: UUID
       name: str
       value: float
       created_at: datetime
   ```

2. **Create Route** (`api/routers/your_feature.py`):
   ```python
   from fastapi import APIRouter, Depends
   from backend.core.database import get_db

   router = APIRouter()

   @router.post("/", response_model=FeatureResponse)
   async def create_feature(
       data: FeatureCreate,
       db: AsyncSession = Depends(get_db),
       current_user: User = Depends(get_current_user)
   ):
       # Implementation
       pass
   ```

3. **Register Router** (`main.py`):
   ```python
   from backend.api.routers import your_feature

   app.include_router(
       your_feature.router,
       prefix="/api/v1/features",
       tags=["features"]
   )
   ```

---

## Agent Development

### Creating New Agent

```python
# agents/my_new_agent.py
from backend.agents.base import BaseAgent

class MyNewAgent(BaseAgent):
    """
    Description of what this agent does.
    """

    def __init__(self):
        super().__init__(name="MyNewAgent")

    async def process(self, input_data: dict) -> dict:
        """
        Process data and return results.

        Args:
            input_data: Input data dictionary

        Returns:
            Processing results
        """
        self.log_info("Starting processing", data=input_data)

        try:
            # Processing logic
            result = await self._do_processing(input_data)

            self.log_info("Processing completed", result=result)
            return result

        except Exception as e:
            self.log_error("Processing failed", error=str(e))
            raise

    async def _do_processing(self, data: dict) -> dict:
        # Implementation
        pass
```

---

## Frontend Development

### Creating New Page

```typescript
// app/my-page/page.tsx
'use client';

import { useState, useEffect } from 'react';
import { useApi } from '@/hooks/useApi';

export default function MyPage() {
  const { data, loading, error } = useApi('/api/v1/my-endpoint');

  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error.message}</div>;

  return (
    <div>
      <h1>My Page</h1>
      {/* Content */}
    </div>
  );
}
```

---

## Debugging

### Backend Debugging

**Enable debug logging:**
```bash
# In .env
LOG_LEVEL=DEBUG
DATABASE_ECHO=true
```

**VS Code launch.json:**
```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: FastAPI",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": [
        "backend.main:app",
        "--reload"
      ],
      "jinja": true,
      "justMyCode": false
    }
  ]
}
```

### Database Debugging

```bash
# Connect to PostgreSQL
docker exec -it evf-postgres psql -U evf_user -d evf_portugal_2030

# View tables
\dt

# Describe table
\d evf_projects

# Query data
SELECT * FROM tenants;
```

---

## Common Tasks

### Reset Database
```bash
cd backend
alembic downgrade base
alembic upgrade head
python seed_data.py
```

### Clear Redis Cache
```bash
docker exec -it evf-redis redis-cli FLUSHALL
```

### View Logs
```bash
# Backend logs
tail -f backend/logs/app.log

# Docker logs
docker logs evf-postgres
docker logs evf-redis
```

### Generate Test Data
```bash
cd backend
python -m backend.scripts.generate_test_data
```

---

**Happy coding!** 🚀
