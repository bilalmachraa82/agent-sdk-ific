# EVF Portugal 2030 - AI-Powered Funding Application Platform

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Node.js 18+](https://img.shields.io/badge/node-18+-green.svg)](https://nodejs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-teal.svg)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-14-black.svg)](https://nextjs.org/)

An AI-powered B2B SaaS platform for automating Portuguese funding (IFIC/PT2030/PRR) application processing. Transform Financial Viability Studies (EVF) from 24-hour manual work to 3-hour automated processing using specialized AI agents.

---

## 🚀 Quick Start

Get the application running in **less than 5 minutes**:

```bash
# 1. Make scripts executable
chmod +x start_all.sh start_postgres.sh start_backend.sh start_frontend.sh

# 2. Configure environment (first time only)
cd backend && cp .env.example .env
cd ../frontend && cp .env.example .env.local
cd ..

# 3. Edit backend/.env with your CLAUDE_API_KEY and security keys
# See Configuration section below for generating keys

# 4. Start everything
./start_all.sh
```

**Access the application:**
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/api/docs

**Demo Credentials:**
- Email: `admin@demo.pt`
- Password: `Demo@2024`

📖 **For detailed instructions, see [QUICKSTART.md](QUICKSTART.md)**

---

## 📋 Table of Contents

- [Features](#-features)
- [Architecture](#-architecture)
- [Tech Stack](#-tech-stack)
- [Prerequisites](#-prerequisites)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Running the Application](#-running-the-application)
- [Development](#-development)
- [Testing](#-testing)
- [Deployment](#-deployment)
- [Documentation](#-documentation)
- [Contributing](#-contributing)
- [License](#-license)

---

## ✨ Features

### Core Capabilities

- **🤖 Multi-Agent AI System** - 5 specialized sub-agents (Input, Compliance, Financial, Narrative, Audit)
- **📊 Financial Calculations** - Deterministic VALF/TRF calculations with 100% accuracy
- **✅ PT2030 Compliance** - Automated validation against Portuguese funding rules
- **📝 Narrative Generation** - AI-powered proposal text using Claude 4.5 Sonnet
- **📁 File Processing** - SAF-T XML, Excel, CSV parsing with encryption
- **🏢 Multi-Tenancy** - Full tenant isolation with PostgreSQL Row-Level Security
- **🔍 Audit Trail** - Complete tracking of all operations and decisions
- **📈 Dashboard & Reports** - Real-time processing status and Excel/PDF exports

### Business Benefits

- **⏱️ 87.5% Time Reduction** - From 24h to 3h per EVF
- **💰 Cost Efficiency** - < €1 per EVF processing
- **🎯 100% Compliance** - Deterministic rule validation
- **📊 Scalability** - Handle 100+ concurrent tenants
- **🔒 Security** - AES-256 encryption, JWT auth, rate limiting

---

## 🏗️ Architecture

### Multi-Agent System

```
┌─────────────────────────────────────────────────────────────┐
│                    Orchestrator Service                      │
│         (Coordinates all agents, manages workflow)           │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ InputAgent   │    │ Compliance   │    │ Financial    │
│              │───▶│   Agent      │───▶│  Agent       │
│ Parse files  │    │ Validate     │    │ Calculate    │
│ Normalize    │    │ PT2030 rules │    │ VALF/TRF     │
└──────────────┘    └──────────────┘    └──────────────┘
                                                │
                    ┌───────────────────────────┘
                    │
                    ▼
        ┌──────────────────────┐
        │   NarrativeAgent     │
        │                      │
        │ Generate proposal    │
        │ using Claude AI      │
        └──────────────────────┘
                    │
                    ▼
        ┌──────────────────────┐
        │    AuditAgent        │
        │                      │
        │ Track all operations │
        │ Log costs & events   │
        └──────────────────────┘
```

### Data Flow

1. **Upload** → User uploads SAF-T/Excel/CSV file
2. **Parse** → InputAgent extracts financial data
3. **Validate** → ComplianceAgent checks PT2030 rules
4. **Calculate** → FinancialModelAgent computes VALF/TRF
5. **Generate** → NarrativeAgent creates proposal text
6. **Audit** → AuditAgent logs all operations
7. **Export** → User downloads Excel/PDF report

---

## 🛠️ Tech Stack

### Backend
- **Framework**: FastAPI 0.115+ (Python 3.11+)
- **Database**: PostgreSQL 16 with Row-Level Security
- **Cache**: Redis (Upstash serverless)
- **AI**: Claude 4.5 Sonnet (Anthropic)
- **Vector DB**: Qdrant Cloud
- **ORM**: SQLAlchemy 2.0 (async)
- **Migrations**: Alembic

### Frontend
- **Framework**: Next.js 14 (App Router)
- **Language**: TypeScript
- **UI**: Shadcn/ui + Tailwind CSS
- **State**: Zustand
- **Forms**: React Hook Form + Zod
- **Tables**: TanStack Table
- **Charts**: Recharts
- **HTTP**: Axios + TanStack Query

### Infrastructure
- **Backend Hosting**: Railway
- **Frontend Hosting**: Vercel
- **Database**: Railway PostgreSQL
- **Cache**: Upstash Redis
- **Storage**: Cloudflare R2 / AWS S3
- **Monitoring**: Sentry
- **CI/CD**: GitHub Actions

---

## 📦 Prerequisites

### Required Software

- **Python 3.11+** - [Download](https://www.python.org/downloads/)
- **Node.js 18+** - [Download](https://nodejs.org/)
- **Docker Desktop** - [Download](https://www.docker.com/products/docker-desktop/)
- **Git** - [Download](https://git-scm.com/downloads)

### API Keys (Required)

- **Claude API Key** - Get from [Anthropic Console](https://console.anthropic.com/)
- **Qdrant API Key** (Optional) - Get from [Qdrant Cloud](https://cloud.qdrant.io/)

---

## 📥 Installation

### Clone Repository

```bash
git clone <repository-url>
cd "Agent SDK - IFIC"
```

### Make Scripts Executable

```bash
chmod +x start_all.sh start_postgres.sh start_backend.sh start_frontend.sh
```

---

## ⚙️ Configuration

### 1. Backend Configuration

```bash
cd backend
cp .env.example .env
```

**Edit `backend/.env`:**

```env
# Required: Claude API Key
CLAUDE_API_KEY=sk-ant-api03-your-key-here

# Required: Generate secure keys
SECRET_KEY=<generate-with-command-below>
ENCRYPTION_KEY=<generate-with-command-below>

# Optional: Use local PostgreSQL (Docker)
DATABASE_URL=postgresql+asyncpg://evf_user:evf_password@localhost:5432/evf_portugal_2030
```

**Generate secure keys:**

```bash
# SECRET_KEY (min 32 characters)
python -c "import secrets; print(secrets.token_urlsafe(32))"

# ENCRYPTION_KEY (base64-encoded 32 bytes)
python -c "import secrets, base64; print(base64.b64encode(secrets.token_bytes(32)).decode())"
```

### 2. Frontend Configuration

```bash
cd frontend
cp .env.example .env.local
```

**Edit `frontend/.env.local`:**

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_API_PREFIX=/api/v1
```

---

## 🏃 Running the Application

### Option 1: All-in-One (Recommended)

```bash
./start_all.sh
```

This starts PostgreSQL, Backend, and Frontend in the correct order.

### Option 2: Individual Services

```bash
# Terminal 1: PostgreSQL
./start_postgres.sh

# Terminal 2: Backend
./start_backend.sh

# Terminal 3: Frontend
./start_frontend.sh
```

### Option 3: Docker Compose

```bash
# Start all services
docker compose up

# Or start in background
docker compose up -d

# View logs
docker compose logs -f

# Stop services
docker compose down
```

---

## 🔧 Development

### Project Structure

```
evf-portugal-2030/
├── backend/
│   ├── agents/              # 5 AI sub-agents
│   │   ├── input_agent.py
│   │   ├── compliance_agent.py
│   │   ├── financial_agent.py
│   │   ├── narrative_agent.py
│   │   └── audit_agent.py
│   ├── api/                # FastAPI endpoints
│   │   └── routers/
│   ├── core/               # Config, database, security
│   ├── models/             # SQLAlchemy models
│   ├── schemas/            # Pydantic schemas
│   ├── services/           # Business logic
│   └── tests/              # Pytest tests
├── frontend/
│   ├── app/                # Next.js App Router
│   ├── components/         # React components
│   └── lib/                # Utilities
├── mcp_servers/            # Custom MCP servers (future)
├── alembic/                # Database migrations
└── scripts/                # Startup scripts
```

### Key Files

- `backend/main.py` - FastAPI application entry point
- `backend/core/config.py` - Configuration settings
- `backend/services/orchestrator.py` - Agent orchestration
- `frontend/app/page.tsx` - Frontend home page

### Running Tests

```bash
# Backend tests
cd backend
pytest -v --cov=. --cov-report=html

# Frontend tests (when implemented)
cd frontend
npm test
```

### Database Migrations

```bash
cd backend

# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1

# View migration history
alembic history
```

### Code Quality

```bash
# Backend: Format with Black
cd backend
black .

# Backend: Lint with Ruff
ruff check .

# Frontend: Lint
cd frontend
npm run lint
```

---

## 🧪 Testing

### Backend Tests

```bash
cd backend
pytest -v --cov=. --cov-report=html
```

**Test Coverage Target**: > 90%

### Integration Testing

Test the complete EVF workflow:

1. Upload SAF-T file
2. Parse financial data
3. Validate compliance
4. Calculate VALF/TRF
5. Generate narrative
6. Export to Excel/PDF

---

## 🚀 Deployment

### Backend (Railway)

```bash
# Install Railway CLI
npm i -g @railway/cli

# Login to Railway
railway login

# Create new project
railway init

# Add PostgreSQL
railway add

# Set environment variables
railway variables set CLAUDE_API_KEY=your-key

# Deploy
railway up
```

### Frontend (Vercel)

```bash
# Install Vercel CLI
npm i -g vercel

# Login to Vercel
vercel login

# Deploy
vercel --prod
```

### Environment Variables

See `.env.example` files for required variables.

---

## 📚 Documentation

- **[QUICKSTART.md](QUICKSTART.md)** - Quick start guide
- **[arquitetura_mvp_v4_final.md](arquitetura_mvp_v4_final.md)** - Technical architecture
- **[claude_code_implementation_v4.md](claude_code_implementation_v4.md)** - Implementation guide
- **[implementacao_60dias_v4.md](implementacao_60dias_v4.md)** - 60-day roadmap
- **[custos_roi_realista_v4.md](custos_roi_realista_v4.md)** - Cost analysis
- **[CLAUDE.md](CLAUDE.md)** - Claude Code instructions

### API Documentation

Interactive API docs available at:
- **Swagger UI**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc

---

## 🤝 Contributing

This is currently a solo developer project optimized for Claude Code assistance.

### Development Workflow

1. Create feature branch
2. Implement changes
3. Add tests (>90% coverage)
4. Run linters and formatters
5. Submit pull request

---

## 📄 License

Copyright © 2024 EVF Portugal 2030. All rights reserved.

---

## 🆘 Support

### Troubleshooting

See [QUICKSTART.md - Troubleshooting](QUICKSTART.md#troubleshooting) for common issues.

### Common Commands

```bash
# View backend logs
tail -f backend/logs/app.log

# View PostgreSQL logs
docker logs evf-postgres

# Reset database
cd backend
alembic downgrade base
alembic upgrade head
python seed_data.py

# Check service health
curl http://localhost:8000/api/health
```

---

## 🎯 Roadmap

- [x] Multi-tenant architecture
- [x] JWT authentication
- [x] File upload & encryption
- [x] InputAgent (SAF-T parsing)
- [x] ComplianceAgent (PT2030 rules)
- [x] FinancialModelAgent (VALF/TRF)
- [x] NarrativeAgent (Claude integration)
- [x] AuditAgent (tracking)
- [x] Next.js frontend
- [ ] MCP servers (SAF-T, Compliance, Qdrant)
- [ ] PDF report generation
- [ ] Email notifications
- [ ] Advanced analytics dashboard
- [ ] Mobile app

---

**Built with ❤️ for Portuguese consultants and entrepreneurs**
