# EVF Portugal 2030 - Quick Start Guide

Welcome to EVF Portugal 2030! This guide will help you set up and run the application in minutes.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Running the Application](#running-the-application)
5. [Testing the Workflow](#testing-the-workflow)
6. [Troubleshooting](#troubleshooting)
7. [API Documentation](#api-documentation)
8. [Demo Credentials](#demo-credentials)

---

## Prerequisites

Before you begin, ensure you have the following installed:

### Required Software

- **Python 3.11+** - [Download](https://www.python.org/downloads/)
  ```bash
  python --version  # Should show 3.11 or higher
  ```

- **Node.js 18+** and **npm** - [Download](https://nodejs.org/)
  ```bash
  node --version  # Should show 18.0 or higher
  npm --version
  ```

- **Docker Desktop** - [Download](https://www.docker.com/products/docker-desktop/)
  ```bash
  docker --version
  docker compose version
  ```

- **Git** - [Download](https://git-scm.com/downloads)
  ```bash
  git --version
  ```

### Optional but Recommended

- **PostgreSQL Client (psql)** - For database inspection
- **Redis CLI** - For cache inspection
- **Postman or Insomnia** - For API testing

---

## Installation

### Option 1: Quick Start (Recommended for Development)

1. **Clone the repository**
   ```bash
   cd "/Users/bilal/Programaçao/Agent SDK - IFIC"
   ```

2. **Make scripts executable**
   ```bash
   chmod +x start_postgres.sh start_backend.sh start_frontend.sh start_all.sh
   ```

3. **Configure environment variables** (see [Configuration](#configuration))

4. **Run everything with one command**
   ```bash
   ./start_all.sh
   ```

### Option 2: Docker Compose (Recommended for Production-like Setup)

1. **Create environment file**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

2. **Start all services**
   ```bash
   # Start core services (PostgreSQL, Redis, Backend, Frontend)
   docker compose up -d

   # Or start with Qdrant for full RAG capabilities
   docker compose --profile full up -d
   ```

3. **View logs**
   ```bash
   docker compose logs -f
   ```

### Option 3: Manual Setup (For Advanced Users)

1. **Start PostgreSQL**
   ```bash
   ./start_postgres.sh
   ```

2. **Start Backend** (in a new terminal)
   ```bash
   ./start_backend.sh
   ```

3. **Start Frontend** (in a new terminal)
   ```bash
   ./start_frontend.sh
   ```

---

## Configuration

### Backend Configuration (`.env`)

Create a `.env` file in the `backend/` directory:

```bash
cd backend
cp .env.example .env
```

**Minimum required configuration:**

```env
# Environment
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO

# Database (if using Docker script, these are the defaults)
DATABASE_URL=postgresql+asyncpg://evf_user:evf_password@localhost:5432/evf_portugal_2030

# Redis
REDIS_URL=redis://localhost:6379/0

# Security
SECRET_KEY=your-super-secret-key-change-this-in-production-min-32-chars
ENCRYPTION_KEY=base64-encoded-32-byte-key-for-aes-256-encryption

# Claude AI (REQUIRED for narrative generation)
CLAUDE_API_KEY=sk-ant-api03-...your-key-here

# Qdrant Vector Store (Optional - use Qdrant Cloud or local)
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=  # Leave empty for local Qdrant

# File Storage (use 'local' for development, 's3' for production)
STORAGE_BACKEND=local
LOCAL_STORAGE_PATH=storage/uploads

# For S3 (production)
# S3_BUCKET_NAME=evf-portugal-2030
# S3_REGION=eu-west-1
# S3_ACCESS_KEY=your-access-key
# S3_SECRET_KEY=your-secret-key

# CORS (for frontend)
CORS_ORIGINS=["http://localhost:3000","http://127.0.0.1:3000"]
```

**Generate secure keys:**

```bash
# Generate SECRET_KEY (min 32 characters)
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Generate ENCRYPTION_KEY (base64-encoded 32 bytes for AES-256)
python -c "import secrets, base64; print(base64.b64encode(secrets.token_bytes(32)).decode())"
```

### Frontend Configuration (`.env.local`)

Create a `.env.local` file in the `frontend/` directory:

```bash
cd frontend
cp .env.example .env.local
```

**Configuration:**

```env
# API Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_API_PREFIX=/api/v1

# App Configuration
NEXT_PUBLIC_APP_NAME=EVF Portugal 2030
NEXT_PUBLIC_APP_VERSION=1.0.0
NEXT_PUBLIC_ENVIRONMENT=development
```

---

## Running the Application

### Quick Start (All-in-One)

```bash
./start_all.sh
```

This will:
1. Start PostgreSQL in Docker
2. Start the Backend API (FastAPI)
3. Start the Frontend (Next.js)

**Access the application:**
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/api/docs
- **Health Check**: http://localhost:8000/api/health

### Individual Services

**Start PostgreSQL only:**
```bash
./start_postgres.sh
```

**Start Backend only:**
```bash
./start_backend.sh
```

**Start Frontend only:**
```bash
./start_frontend.sh
```

### Using Docker Compose

**Start all services:**
```bash
docker compose up
```

**Start in background:**
```bash
docker compose up -d
```

**Stop all services:**
```bash
docker compose down
```

**Stop and remove volumes (clean slate):**
```bash
docker compose down -v
```

**View logs:**
```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f backend
docker compose logs -f frontend
```

---

## Testing the Workflow

### 1. Access the Frontend

Open your browser and navigate to http://localhost:3000

### 2. Register/Login

Use the demo credentials (if database was seeded) or register a new account:

**Demo credentials:**
- Email: `demo@evfportugal2030.pt`
- Password: `Demo123!@#`

### 3. Upload a Financial File

1. Go to the dashboard
2. Click "New EVF Processing"
3. Upload a SAF-T XML, Excel, or CSV file with financial data
4. The system will:
   - Parse the file (InputAgent)
   - Validate compliance (ComplianceAgent)
   - Calculate VALF/TRF (FinancialModelAgent)
   - Generate narrative (NarrativeAgent)
   - Create audit trail (AuditAgent)

### 4. View Results

- Check the EVF status
- Download generated reports
- Review audit logs
- Export to Excel/PDF

### 5. API Testing (Optional)

Use the interactive API documentation at http://localhost:8000/api/docs

**Example API calls:**

```bash
# Health check
curl http://localhost:8000/api/health

# Register a new user
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "Test123!@#",
    "full_name": "Test User",
    "company_name": "Test Company"
  }'

# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "test@example.com",
    "password": "Test123!@#"
  }'

# Upload file (requires authentication token)
curl -X POST http://localhost:8000/api/v1/files/upload \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -F "file=@path/to/your/file.xml"
```

---

## Troubleshooting

### Common Issues

#### 1. PostgreSQL Connection Failed

**Error:** `Database connection failed: could not connect to server`

**Solution:**
```bash
# Check if Docker is running
docker ps

# Start PostgreSQL
./start_postgres.sh

# Or check if it's already running
docker ps | grep evf-postgres

# If stuck, restart it
docker restart evf-postgres
```

#### 2. Backend Won't Start

**Error:** `ModuleNotFoundError` or import errors

**Solution:**
```bash
cd backend
source venv/bin/activate
pip install -r requirements.txt --upgrade
```

#### 3. Frontend Won't Start

**Error:** `Module not found` or dependency errors

**Solution:**
```bash
cd frontend
rm -rf node_modules .next
npm install
npm run dev
```

#### 4. Port Already in Use

**Error:** `Address already in use: 8000` or `3000`

**Solution:**
```bash
# Find process using the port
lsof -i :8000  # or :3000 for frontend

# Kill the process
kill -9 <PID>

# Or use different ports
API_PORT=8001 ./start_backend.sh
```

#### 5. Alembic Migration Errors

**Error:** `Can't locate revision identified by 'xyz'`

**Solution:**
```bash
cd backend

# Reset migrations (CAUTION: This will drop all tables)
alembic downgrade base
alembic upgrade head

# Or create new migration
alembic revision --autogenerate -m "Fix migration"
alembic upgrade head
```

#### 6. Claude API Key Invalid

**Error:** `401 Unauthorized` when generating narratives

**Solution:**
```bash
# Verify your Claude API key
echo $CLAUDE_API_KEY

# Or check .env file
cat backend/.env | grep CLAUDE_API_KEY

# Get a new key from: https://console.anthropic.com/
```

#### 7. File Upload Fails

**Error:** `413 Request Entity Too Large` or encryption errors

**Solution:**
```bash
# Check max file size in backend/.env
echo "MAX_FILE_SIZE_MB=500" >> backend/.env

# Ensure encryption key is set
python -c "import secrets, base64; print(base64.b64encode(secrets.token_bytes(32)).decode())"
# Copy output to ENCRYPTION_KEY in .env
```

### View Logs

**Backend logs:**
```bash
# If running with script
tail -f backend/logs/app.log

# If running with Docker
docker compose logs -f backend
```

**Frontend logs:**
```bash
# Check console in the terminal where you ran ./start_frontend.sh

# Or with Docker
docker compose logs -f frontend
```

**Database logs:**
```bash
docker logs evf-postgres

# Or connect to database
docker exec -it evf-postgres psql -U evf_user -d evf_portugal_2030
```

### Reset Everything

If all else fails, start fresh:

```bash
# Stop all services
docker compose down -v
docker stop evf-postgres evf-redis
docker rm evf-postgres evf-redis

# Remove data
docker volume prune -f

# Restart
./start_all.sh
```

---

## API Documentation

### Interactive Documentation

- **Swagger UI**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc
- **OpenAPI JSON**: http://localhost:8000/api/openapi.json

### Key Endpoints

#### Authentication
- `POST /api/v1/auth/register` - Register new user/tenant
- `POST /api/v1/auth/login` - Login and get JWT token
- `POST /api/v1/auth/refresh` - Refresh access token
- `GET /api/v1/auth/me` - Get current user info

#### EVF Processing
- `POST /api/v1/evf/create` - Create new EVF processing request
- `GET /api/v1/evf/{id}` - Get EVF status and results
- `GET /api/v1/evf/` - List all EVFs (tenant-scoped)
- `DELETE /api/v1/evf/{id}` - Delete EVF

#### File Management
- `POST /api/v1/files/upload` - Upload financial files
- `GET /api/v1/files/{id}` - Get file metadata
- `GET /api/v1/files/{id}/download` - Download file
- `DELETE /api/v1/files/{id}` - Delete file

#### Admin
- `GET /api/v1/admin/tenants` - List all tenants (admin only)
- `GET /api/v1/admin/stats` - System statistics
- `GET /api/v1/admin/audit-logs` - View audit logs

### Authentication

All protected endpoints require a JWT token in the Authorization header:

```bash
Authorization: Bearer <your-jwt-token>
```

---

## Demo Credentials

After seeding the database (automatic on first run), you can use these credentials:

### Demo User Account
- **Email**: `demo@evfportugal2030.pt`
- **Password**: `Demo123!@#`
- **Tenant**: Demo Company Lda
- **Role**: Admin

### Test User Account
- **Email**: `test@evfportugal2030.pt`
- **Password**: `Test123!@#`
- **Tenant**: Test Tenant Lda
- **Role**: User

### Admin Account
- **Email**: `admin@evfportugal2030.pt`
- **Password**: `Admin123!@#`
- **Role**: Super Admin

**Note:** Change these credentials in production!

---

## Next Steps

1. **Explore the Dashboard** - Upload sample financial files
2. **Review Generated EVFs** - Check VALF/TRF calculations
3. **Test Compliance Rules** - Try files that violate PT2030 rules
4. **Customize Agents** - Modify agent behavior in `backend/agents/`
5. **Add Custom Rules** - Extend compliance checking in `backend/agents/compliance_agent.py`

---

## Additional Resources

- **Architecture Documentation**: `arquitetura_mvp_v4_final.md`
- **Implementation Guide**: `claude_code_implementation_v4.md`
- **60-Day Roadmap**: `implementacao_60dias_v4.md`
- **Cost Analysis**: `custos_roi_realista_v4.md`
- **Project Instructions**: `CLAUDE.md`

---

## Support

For issues or questions:
1. Check the [Troubleshooting](#troubleshooting) section
2. Review the API documentation at http://localhost:8000/api/docs
3. Check application logs
4. Review the architecture documentation

---

## License

Copyright © 2024 EVF Portugal 2030. All rights reserved.
