# EVF Portugal 2030 - Startup Instructions

**Quick reference guide for starting the application**

---

## 🚀 Quick Start (5 Minutes)

### Step 1: Prerequisites Check

Ensure you have installed:
- ✅ Python 3.11+ (`python --version`)
- ✅ Node.js 18+ (`node --version`)
- ✅ Docker Desktop (running: `docker ps`)

### Step 2: Configure Environment

```bash
# Backend configuration
cd backend
cp .env.example .env

# REQUIRED: Edit backend/.env and set:
# 1. CLAUDE_API_KEY=sk-ant-api03-your-actual-key
# 2. SECRET_KEY=<generate with command below>
# 3. ENCRYPTION_KEY=<generate with command below>

# Generate keys:
python -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(32))"
python -c "import secrets, base64; print('ENCRYPTION_KEY=' + base64.b64encode(secrets.token_bytes(32)).decode())"

# Frontend configuration
cd ../frontend
cp .env.example .env.local
# No changes needed for local development
```

### Step 3: Start Application

```bash
# From project root
./start_all.sh
```

**That's it!** 🎉

Access the application at:
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/api/docs

**Login with:**
- Email: `admin@demo.pt`
- Password: `Demo@2024`

---

## 📋 Detailed Startup Methods

### Method 1: All-in-One Script (Recommended)

**Best for:** First-time setup, development

```bash
./start_all.sh
```

**What it does:**
1. Starts PostgreSQL in Docker
2. Creates Python virtual environment
3. Installs backend dependencies
4. Runs database migrations
5. Seeds demo data
6. Starts backend API
7. Installs frontend dependencies
8. Starts frontend dev server

**Output:**
```
🚀 Starting EVF Portugal 2030 - Complete Stack
================================================

Step 1/3: Starting PostgreSQL...
✅ PostgreSQL is ready!

Step 2/3: Starting Backend...
✅ Backend is ready!

Step 3/3: Starting Frontend...
✅ Frontend is ready!

================================================
✨ EVF Portugal 2030 is now running!
================================================

📍 Services:
   Frontend:  http://localhost:3000
   Backend:   http://localhost:8000
   API Docs:  http://localhost:8000/api/docs
```

**Stop:** Press `Ctrl+C`

---

### Method 2: Individual Services

**Best for:** Debugging specific components

#### Terminal 1: PostgreSQL

```bash
./start_postgres.sh
```

**Output:**
```
🐘 Starting PostgreSQL for EVF Portugal 2030...
✅ PostgreSQL is ready!

📍 Connection details:
   Host: localhost
   Port: 5432
   Database: evf_portugal_2030
   User: evf_user
   Password: evf_password
```

#### Terminal 2: Backend

```bash
./start_backend.sh
```

**Output:**
```
🚀 Starting EVF Portugal 2030 Backend...
✅ Database connection successful
🔄 Running database migrations...
🌱 Seeding initial data...
✨ Starting FastAPI server...

📍 API will be available at: http://localhost:8000
📖 API docs will be at: http://localhost:8000/api/docs
```

#### Terminal 3: Frontend

```bash
./start_frontend.sh
```

**Output:**
```
🚀 Starting EVF Portugal 2030 Frontend...
✨ Starting Next.js development server...

📍 Frontend will be available at: http://localhost:3000
```

---

### Method 3: Docker Compose

**Best for:** Production-like environment, full isolation

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

**Services included:**
- PostgreSQL database
- Redis cache
- Backend API
- Frontend app
- Qdrant (optional, use `--profile full`)

---

## 🔧 Configuration Reference

### Backend Environment Variables (.env)

**Required:**
```env
CLAUDE_API_KEY=sk-ant-api03-your-key-here
SECRET_KEY=<generated-secret-key>
ENCRYPTION_KEY=<generated-encryption-key>
```

**Optional (defaults work for local dev):**
```env
DATABASE_URL=postgresql+asyncpg://evf_user:evf_password@localhost:5432/evf_portugal_2030
REDIS_URL=redis://localhost:6379/0
ENVIRONMENT=development
API_PORT=8000
```

### Frontend Environment Variables (.env.local)

**Default (no changes needed):**
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_API_PREFIX=/api/v1
```

---

## ✅ Verification Checklist

After starting, verify everything works:

### 1. PostgreSQL
```bash
docker ps | grep evf-postgres
# Should show running container
```

### 2. Backend
```bash
curl http://localhost:8000/api/health
# Should return: {"status":"healthy"}
```

### 3. Frontend
```bash
curl -I http://localhost:3000
# Should return: HTTP/1.1 200 OK
```

### 4. Login
1. Open http://localhost:3000
2. Click "Login"
3. Enter:
   - Email: `admin@demo.pt`
   - Password: `Demo@2024`
4. Should see dashboard

---

## 🆘 Troubleshooting

### PostgreSQL won't start

**Error:** `Docker is not running`

**Solution:**
```bash
# Start Docker Desktop, then:
./start_postgres.sh
```

---

### Backend connection error

**Error:** `Database connection failed`

**Solution:**
```bash
# Ensure PostgreSQL is running
docker ps | grep evf-postgres

# If not running:
./start_postgres.sh

# Then retry backend:
./start_backend.sh
```

---

### Backend import errors

**Error:** `ModuleNotFoundError`

**Solution:**
```bash
cd backend
source venv/bin/activate
pip install -r requirements.txt --upgrade
```

---

### Frontend won't start

**Error:** `Module not found` or port in use

**Solution:**
```bash
cd frontend

# Clear and reinstall
rm -rf node_modules .next
npm install

# If port 3000 is in use, kill process:
lsof -ti:3000 | xargs kill -9

# Then restart:
npm run dev
```

---

### Migration errors

**Error:** `Can't locate revision`

**Solution:**
```bash
cd backend
source venv/bin/activate

# Reset database
alembic downgrade base
alembic upgrade head
python seed_data.py
```

---

### Claude API errors

**Error:** `401 Unauthorized` when generating narratives

**Solution:**
```bash
# Verify API key is set
cat backend/.env | grep CLAUDE_API_KEY

# Should show: CLAUDE_API_KEY=sk-ant-api03-...

# If empty, edit backend/.env and add your key
```

---

## 🔄 Common Commands

### Restart Everything
```bash
# Stop all
docker stop evf-postgres
pkill -f "uvicorn main:app"
pkill -f "next dev"

# Start all
./start_all.sh
```

### Reset Database
```bash
cd backend
source venv/bin/activate
alembic downgrade base
alembic upgrade head
python seed_data.py
```

### View Logs
```bash
# Backend
tail -f backend/logs/app.log

# PostgreSQL
docker logs evf-postgres

# Frontend
# Check terminal where you ran ./start_frontend.sh
```

### Clean Start
```bash
# Remove all Docker data
docker compose down -v
docker stop evf-postgres evf-redis
docker rm evf-postgres evf-redis
docker volume prune -f

# Remove Python venv
rm -rf backend/venv

# Remove Node modules
rm -rf frontend/node_modules frontend/.next

# Start fresh
./start_all.sh
```

---

## 📚 Next Steps

1. **Read the Quick Start Guide**: [QUICKSTART.md](QUICKSTART.md)
2. **Explore API Documentation**: http://localhost:8000/api/docs
3. **Review Architecture**: [arquitetura_mvp_v4_final.md](arquitetura_mvp_v4_final.md)
4. **Development Guide**: [DEVELOPMENT.md](DEVELOPMENT.md)

---

## 🎯 Summary of Files Created

### Startup Scripts
- `start_all.sh` - Start everything (PostgreSQL + Backend + Frontend)
- `start_postgres.sh` - Start PostgreSQL in Docker
- `start_backend.sh` - Start FastAPI backend
- `start_frontend.sh` - Start Next.js frontend

### Configuration
- `docker-compose.yml` - Docker Compose for full stack
- `backend/.env.example` - Backend environment template
- `frontend/.env.example` - Frontend environment template
- `backend/Dockerfile` - Backend Docker image
- `frontend/Dockerfile` - Frontend Docker image
- `backend/init_db.sql` - PostgreSQL initialization
- `backend/seed_data.py` - Database seeding script

### Documentation
- `README.md` - Main project documentation
- `QUICKSTART.md` - Quick start guide
- `DEVELOPMENT.md` - Development guide
- `STARTUP_INSTRUCTIONS.md` - This file

---

**All scripts are executable and ready to use!** ✅

**Questions?** Check [QUICKSTART.md](QUICKSTART.md) for detailed troubleshooting.
