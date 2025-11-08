# Database Setup and Seed Data Guide

This guide explains how to set up the database, run migrations, seed demo data, and test the connection for the EVF Portugal 2030 backend.

## Prerequisites

1. **PostgreSQL 16** installed and running
2. **Python dependencies** installed:
   ```bash
   pip install -r backend/requirements.txt
   ```
3. **Environment variables** configured in `backend/.env`

## Step-by-Step Setup

### 1. Create Database

First, create the PostgreSQL database:

```bash
# Connect to PostgreSQL
psql -U postgres

# Create database
CREATE DATABASE evf_portugal_2030;

# Create user (if needed)
CREATE USER evf_user WITH PASSWORD 'evf_password';

# Grant privileges
GRANT ALL PRIVILEGES ON DATABASE evf_portugal_2030 TO evf_user;

# Exit psql
\q
```

### 2. Configure Environment

Edit `backend/.env` to match your database configuration:

```env
DATABASE_URL=postgresql+asyncpg://evf_user:evf_password@localhost:5432/evf_portugal_2030
ENVIRONMENT=development
DEBUG=True
SECRET_KEY=your-secret-key-change-in-production
```

### 3. Run Migrations

Initialize the database schema using Alembic:

```bash
# From the project root directory
cd /Users/bilal/Programaçao/Agent\ SDK\ -\ IFIC

# Run migrations
alembic upgrade head
```

Expected output:
```
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> xxxxx, Initial migration
```

### 4. Test Database Connection

Verify that the database is properly set up:

```bash
python backend/test_connection.py
```

This script will:
- ✓ Test database connectivity
- ✓ Verify all tables exist
- ✓ Inspect table structures
- ✓ Check for existing data
- ✓ Verify indexes
- ✓ Test Row-Level Security (RLS) configuration

### 5. Seed Demo Data

Create demo tenant, users, and sample project:

```bash
python backend/seed_data.py
```

This will create:
- **Demo Tenant**: "Demo Consultoria Lda"
  - Slug: `demo`
  - NIF: `123456789`
  - Plan: PROFESSIONAL

- **Admin User**:
  - Email: `admin@demo.pt`
  - Password: `Demo@2024`
  - Role: ADMIN

- **Demo Company**: "Empresa Exemplo Lda"
  - NIF: `987654321`

- **Sample EVF Project**: "Projeto Indústria 4.0"
  - Status: DRAFT
  - Fund Type: PT2030

## Using the Seed Data

### Starting the API

```bash
cd backend
uvicorn main:app --reload --port 8000
```

### Login with Demo Credentials

Use the following credentials to access the API:

```
Email: admin@demo.pt
Password: Demo@2024
```

### Example API Requests

#### 1. Login (Get JWT Token)

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@demo.pt",
    "password": "Demo@2024"
  }'
```

Response:
```json
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer",
  "tenant_id": "uuid-here"
}
```

#### 2. Get Tenant Info

```bash
curl http://localhost:8000/api/v1/tenants/demo \
  -H "Authorization: Bearer YOUR_TOKEN"
```

#### 3. List EVF Projects

```bash
curl http://localhost:8000/api/v1/projects \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "X-Tenant-ID: YOUR_TENANT_ID"
```

## Scripts Reference

### test_connection.py

**Purpose**: Comprehensive database connectivity and structure verification

**Features**:
- Tests PostgreSQL connection
- Lists all database tables
- Displays table structures
- Shows data statistics
- Checks RLS policies
- Verifies indexes
- Displays current configuration

**Usage**:
```bash
python backend/test_connection.py
```

**Output Example**:
```
============================================================
EVF Portugal 2030 - Database Connection Test
============================================================

🔌 Testing database connection...
   ✓ Connected successfully!
   ℹ  PostgreSQL version: PostgreSQL 16.0

📋 Checking database tables...
   ✓ Found 10 tables:
      • tenants
      • users
      • companies
      ...

📊 Test Summary
============================================================
Test            Result
--------------  --------
Connection      ✓ PASS
Configuration   ✓ PASS
Tables          ✓ PASS
...
```

### seed_data.py

**Purpose**: Create demo tenant and sample data for testing

**Features**:
- Idempotent (safe to run multiple times)
- Creates complete tenant hierarchy
- Generates realistic demo data
- Links all entities correctly

**Usage**:
```bash
python backend/seed_data.py
```

**Output Example**:
```
============================================================
EVF Portugal 2030 - Database Seed Script
============================================================

📦 Creating demo tenant...
   ✓ Created tenant 'Demo Consultoria Lda' (ID: ...)

👤 Creating demo admin user...
   ✓ Created user 'admin@demo.pt' (ID: ...)

✅ Database seeding completed successfully!
============================================================

📌 Summary:
   Tenant ID:  xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
   Tenant Slug: demo
   Admin Email: admin@demo.pt
   Admin Password: Demo@2024
```

## Troubleshooting

### Issue: Connection Refused

**Problem**: `connection refused` error when running scripts

**Solution**:
1. Ensure PostgreSQL is running: `pg_ctl status`
2. Check port in `.env` matches PostgreSQL port
3. Verify firewall settings

### Issue: Migrations Fail

**Problem**: Alembic migrations fail with error

**Solution**:
1. Check database exists: `psql -l`
2. Verify user permissions: `GRANT ALL PRIVILEGES...`
3. Clear alembic_version if stuck: `DELETE FROM alembic_version;`

### Issue: Tables Not Found

**Problem**: `test_connection.py` reports missing tables

**Solution**:
1. Run migrations: `alembic upgrade head`
2. Check for migration errors in output
3. Verify DATABASE_URL in `.env`

### Issue: Seed Script Fails

**Problem**: `seed_data.py` throws integrity errors

**Solution**:
1. Script is idempotent - check if data already exists
2. Verify migrations ran successfully
3. Check unique constraints (NIF, email, etc.)

## Database Maintenance

### Reset Database

To completely reset the database:

```bash
# Drop and recreate database
psql -U postgres -c "DROP DATABASE evf_portugal_2030;"
psql -U postgres -c "CREATE DATABASE evf_portugal_2030;"

# Run migrations
alembic upgrade head

# Seed demo data
python backend/seed_data.py
```

### View Migration History

```bash
# Show current revision
alembic current

# Show migration history
alembic history

# Show pending migrations
alembic history --verbose
```

### Create New Migration

After modifying models:

```bash
# Auto-generate migration
alembic revision --autogenerate -m "Description of changes"

# Review the generated migration in alembic/versions/

# Apply migration
alembic upgrade head
```

## Multi-Tenant Isolation

The database uses Row-Level Security (RLS) for tenant isolation:

1. **Every query** must include `tenant_id`
2. **RLS policies** enforce isolation at database level
3. **Set tenant context** before queries:
   ```sql
   SET app.current_tenant = 'tenant-uuid';
   ```

### Testing Isolation

```bash
# In psql, test RLS
psql -U evf_user -d evf_portugal_2030

# Set tenant context
SET app.current_tenant = 'your-tenant-uuid';

# Query should only return data for this tenant
SELECT * FROM users;
```

## Performance Tips

1. **Connection Pooling**: Configured via DATABASE_MIN_POOL_SIZE and DATABASE_MAX_POOL_SIZE
2. **Indexes**: Automatically created for tenant_id, created_at, and common query patterns
3. **EXPLAIN ANALYZE**: Use to debug slow queries
4. **Monitoring**: Enable DATABASE_ECHO=True to log all SQL queries (dev only)

## Security Checklist

- [ ] Change default SECRET_KEY in production
- [ ] Use strong passwords (not "Demo@2024")
- [ ] Enable SSL for database connections
- [ ] Rotate encryption keys every 90 days
- [ ] Regular backups configured
- [ ] RLS policies verified and tested
- [ ] Audit logging enabled

## Next Steps

1. ✅ Database setup complete
2. ✅ Demo data seeded
3. ✅ Connection verified
4. ▶️ Start the API: `uvicorn main:app --reload`
5. ▶️ Test endpoints with Postman or curl
6. ▶️ Build frontend integration

## Support

For issues or questions:
- Check logs in `backend/logs/`
- Review Alembic migration files
- Consult `backend/ARCHITECTURE.md`
- Check PostgreSQL logs: `tail -f /var/log/postgresql/postgresql-16-main.log`
