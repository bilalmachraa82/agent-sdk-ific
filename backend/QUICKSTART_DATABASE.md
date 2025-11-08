# Quick Start - Database Setup

Fast track guide to get the EVF Portugal 2030 database up and running in 5 minutes.

## TL;DR

```bash
# 1. Create database
createdb evf_portugal_2030

# 2. Run migrations
alembic upgrade head

# 3. Test connection
python backend/test_connection.py

# 4. Seed demo data
python backend/seed_data.py

# 5. Start API
uvicorn backend.main:app --reload --port 8000
```

## Step-by-Step (5 Minutes)

### ⏱️ Step 1: Create Database (30 seconds)

```bash
# Using createdb command
createdb evf_portugal_2030

# OR using psql
psql -U postgres -c "CREATE DATABASE evf_portugal_2030;"
```

### ⏱️ Step 2: Install Dependencies (1 minute)

```bash
cd backend
pip install -r requirements.txt
```

### ⏱️ Step 3: Configure Environment (30 seconds)

Create `backend/.env` file:

```env
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/evf_portugal_2030
SECRET_KEY=your-secret-key-here
ENVIRONMENT=development
DEBUG=True
```

Replace `postgres:password` with your PostgreSQL credentials.

### ⏱️ Step 4: Run Migrations (1 minute)

```bash
# From project root
alembic upgrade head
```

Expected output:
```
INFO  [alembic.runtime.migration] Running upgrade  -> xxxxx
```

### ⏱️ Step 5: Test Connection (30 seconds)

```bash
python backend/test_connection.py
```

Should show:
```
✅ All tests passed! Database is ready.
```

### ⏱️ Step 6: Seed Demo Data (30 seconds)

```bash
python backend/seed_data.py
```

Creates:
- Demo tenant: `demo`
- Admin user: `admin@demo.pt` / `Demo@2024`
- Sample company and EVF project

### ⏱️ Step 7: Start API (10 seconds)

```bash
cd backend
uvicorn main:app --reload --port 8000
```

Access API at: http://localhost:8000/docs

## Verify Setup

### Test Login

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@demo.pt", "password": "Demo@2024"}'
```

Should return JWT token.

### Test Health Check

```bash
curl http://localhost:8000/health
```

Should return:
```json
{"status": "healthy", "database": "connected"}
```

## Demo Credentials

```
Email:    admin@demo.pt
Password: Demo@2024
Tenant:   demo (Demo Consultoria Lda)
NIF:      123456789
```

## Troubleshooting

### Database Connection Error

```bash
# Check PostgreSQL is running
pg_ctl status

# Or
sudo systemctl status postgresql
```

### Migration Errors

```bash
# Check Alembic version table
psql evf_portugal_2030 -c "SELECT * FROM alembic_version;"

# Reset if needed
psql evf_portugal_2030 -c "DELETE FROM alembic_version;"
alembic upgrade head
```

### Import Errors

```bash
# Reinstall dependencies
pip install -r backend/requirements.txt

# Verify installation
python -c "import sqlalchemy; print(sqlalchemy.__version__)"
```

## Reset Everything

To start fresh:

```bash
# Drop database
dropdb evf_portugal_2030

# Recreate
createdb evf_portugal_2030

# Run migrations
alembic upgrade head

# Seed data
python backend/seed_data.py
```

## Next Steps

1. ✅ Database running
2. ✅ Demo data loaded
3. ▶️ Test API endpoints at http://localhost:8000/docs
4. ▶️ Build your first EVF project
5. ▶️ Integrate with frontend

## Scripts Reference

| Script | Purpose | Runtime |
|--------|---------|---------|
| `test_connection.py` | Verify database setup | ~5 sec |
| `seed_data.py` | Create demo data | ~3 sec |

## Common Commands

```bash
# Check database size
psql evf_portugal_2030 -c "\dt+"

# Count records
psql evf_portugal_2030 -c "SELECT 'tenants' as table, COUNT(*) FROM tenants UNION ALL SELECT 'users', COUNT(*) FROM users;"

# View logs
tail -f backend/logs/app.log

# Run tests
pytest backend/tests/ -v
```

## Production Setup

For production deployment, see [DATABASE_SETUP.md](DATABASE_SETUP.md) for:
- SSL configuration
- Connection pooling
- RLS policies
- Backup strategy
- Monitoring setup

---

**Need Help?** Check the full guide: [DATABASE_SETUP.md](DATABASE_SETUP.md)
