# Database Scripts - Usage Instructions

Complete guide for using the database setup, seeding, and testing scripts.

## Available Scripts

| Script | Purpose | Runtime |
|--------|---------|---------|
| `setup_database.sh` | Automated full setup | ~2 min |
| `seed_data.py` | Create demo data | ~3 sec |
| `test_connection.py` | Verify database | ~5 sec |

## Quick Start (Automated)

### Option 1: One Command Setup

```bash
./backend/setup_database.sh
```

This will automatically:
1. ✓ Check PostgreSQL is running
2. ✓ Create database
3. ✓ Install Python dependencies
4. ✓ Run Alembic migrations
5. ✓ Test database connection
6. ✓ Seed demo data

**Output**:
```
============================================================
EVF Portugal 2030 - Database Setup
============================================================

ℹ Checking prerequisites...
✓ PostgreSQL client found
✓ Python 3 found (Python 3.11.5)

============================================================
Step 1: Database Creation
============================================================

ℹ Creating database: evf_portugal_2030
✓ Database created

============================================================
Step 2: Install Dependencies
============================================================

ℹ Installing Python dependencies
✓ Dependencies installed

============================================================
Step 3: Run Migrations
============================================================

ℹ Running database migrations
INFO  [alembic.runtime.migration] Running upgrade  -> xxxxx
✓ Migrations completed

============================================================
Step 4: Test Connection
============================================================

ℹ Running connection tests
[test output...]
✓ Connection tests completed

============================================================
Step 5: Seed Demo Data
============================================================

ℹ Seeding demo data
[seed output...]
✓ Seed data completed

============================================================
Setup Complete!
============================================================

✓ Database is ready for use!

ℹ Demo credentials:
   Email:    admin@demo.pt
   Password: Demo@2024

ℹ Start the API with:
   cd backend
   uvicorn main:app --reload --port 8000

ℹ API documentation:
   http://localhost:8000/docs
```

### Option 2: Manual Step-by-Step

If you prefer manual control:

```bash
# 1. Create database
createdb evf_portugal_2030

# 2. Install dependencies
pip install -r backend/requirements.txt

# 3. Run migrations
alembic upgrade head

# 4. Test connection
python backend/test_connection.py

# 5. Seed demo data
python backend/seed_data.py
```

## Script Options

### setup_database.sh Options

```bash
# Full setup (default)
./backend/setup_database.sh

# Reset everything (drop and recreate)
./backend/setup_database.sh --reset

# Run only connection tests
./backend/setup_database.sh --test-only

# Run only seed script
./backend/setup_database.sh --seed-only
```

### Individual Script Usage

#### Test Connection

```bash
# Test database connectivity and structure
python backend/test_connection.py
```

**What it tests**:
- Database connection
- Configuration display
- Table existence
- Table structures
- Data statistics
- Indexes
- RLS policies

**When to use**:
- After migrations
- Before starting development
- To verify multi-tenant setup
- Troubleshooting database issues

#### Seed Demo Data

```bash
# Create demo tenant and data
python backend/seed_data.py
```

**What it creates**:
- Demo tenant organization
- Admin user account
- Sample company
- Sample EVF project
- Usage tracking record

**When to use**:
- First-time setup
- After database reset
- Creating test environment
- Demo presentations

## Common Workflows

### First-Time Setup

```bash
# Automated approach (recommended)
./backend/setup_database.sh

# OR Manual approach
createdb evf_portugal_2030
pip install -r backend/requirements.txt
alembic upgrade head
python backend/test_connection.py
python backend/seed_data.py
```

### Daily Development

```bash
# Quick health check
python backend/test_connection.py

# Start API
cd backend
uvicorn main:app --reload
```

### After Schema Changes

```bash
# Create migration
alembic revision --autogenerate -m "description"

# Review migration file
cat alembic/versions/xxxxx_description.py

# Apply migration
alembic upgrade head

# Verify
python backend/test_connection.py
```

### Reset Everything

```bash
# Option 1: Using setup script
./backend/setup_database.sh --reset

# Option 2: Manual
dropdb evf_portugal_2030
createdb evf_portugal_2030
alembic upgrade head
python backend/seed_data.py
```

### Testing Multi-Tenant Isolation

```bash
# Test connection (includes RLS checks)
python backend/test_connection.py

# Manual SQL testing
psql evf_portugal_2030

# Set tenant context
SET app.current_tenant = 'tenant-uuid-here';

# Query should only return tenant's data
SELECT * FROM evf_projects;
```

## Demo Data Details

### Tenant: Demo Consultoria Lda

```json
{
  "slug": "demo",
  "name": "Demo Consultoria Lda",
  "nif": "123456789",
  "plan": "professional",
  "mrr": 299.00,
  "email": "contato@demo.pt",
  "phone": "+351 211 234 567",
  "address": "Av. da Liberdade 123, 3º Andar",
  "city": "Lisboa",
  "postal_code": "1250-140"
}
```

### Admin User

```json
{
  "email": "admin@demo.pt",
  "password": "Demo@2024",
  "full_name": "Admin Demo",
  "role": "admin",
  "phone": "+351 911 234 567",
  "department": "Gestão"
}
```

### Company: Empresa Exemplo Lda

```json
{
  "nif": "987654321",
  "name": "Empresa Exemplo Lda",
  "cae_code": "62010",
  "email": "info@empresaexemplo.pt",
  "phone": "+351 211 987 654",
  "sector": "Technology",
  "employees": 25,
  "founded_year": 2018
}
```

### EVF Project: Projeto Indústria 4.0

```json
{
  "name": "Projeto Indústria 4.0",
  "description": "Implementação de sistema MES para automação...",
  "fund_type": "pt2030",
  "status": "draft",
  "project_start_year": 2025,
  "project_end_year": 2027,
  "total_investment": 500000.00,
  "eligible_investment": 450000.00,
  "funding_requested": 225000.00
}
```

## API Integration Examples

### 1. Login

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@demo.pt",
    "password": "Demo@2024"
  }'
```

**Response**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "tenant_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
}
```

### 2. Get Current User

```bash
curl http://localhost:8000/api/v1/users/me \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 3. List EVF Projects

```bash
curl http://localhost:8000/api/v1/projects \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "X-Tenant-ID: YOUR_TENANT_ID"
```

### 4. Get Project Details

```bash
curl http://localhost:8000/api/v1/projects/{project_id} \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "X-Tenant-ID: YOUR_TENANT_ID"
```

## Troubleshooting

### PostgreSQL Not Running

**Error**: `connection refused` or `could not connect to server`

**Solution**:
```bash
# Check status
pg_ctl status

# Start PostgreSQL (macOS with Homebrew)
brew services start postgresql

# OR Linux
sudo systemctl start postgresql

# Verify it's running
psql -U postgres -c "SELECT version();"
```

### Database Already Exists

**Error**: `database "evf_portugal_2030" already exists`

**Solution**:
```bash
# Option 1: Use reset flag
./backend/setup_database.sh --reset

# Option 2: Manual drop and recreate
dropdb evf_portugal_2030
createdb evf_portugal_2030
```

### Migration Errors

**Error**: Alembic migration fails

**Solution**:
```bash
# Check current version
alembic current

# Check migration history
alembic history

# If stuck, reset alembic
psql evf_portugal_2030 -c "DELETE FROM alembic_version;"

# Re-run migrations
alembic upgrade head
```

### Import Errors

**Error**: `ModuleNotFoundError: No module named 'xxx'`

**Solution**:
```bash
# Ensure you're in the right directory
cd /Users/bilal/Programaçao/Agent\ SDK\ -\ IFIC

# Reinstall dependencies
pip install -r backend/requirements.txt

# Verify installation
pip list | grep sqlalchemy
```

### Seed Script Reports Existing Data

**Message**: `✓ Tenant already exists`

**This is normal!** The seed script is idempotent and won't create duplicates.

**If you want fresh data**:
```bash
# Reset database
./backend/setup_database.sh --reset
```

### RLS Policies Not Found

**Warning**: `No RLS policies found`

**Solution**:
```bash
# RLS policies need to be created via migration
# Create a new migration:
alembic revision -m "add_rls_policies"

# Edit the migration file to add policies
# Then apply:
alembic upgrade head
```

## Environment Variables

Key variables in `backend/.env`:

```env
# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/evf_portugal_2030
DATABASE_MIN_POOL_SIZE=5
DATABASE_MAX_POOL_SIZE=20

# Security
SECRET_KEY=your-secret-key-change-in-production
JWT_EXPIRATION_MINUTES=30

# Environment
ENVIRONMENT=development
DEBUG=True
LOG_LEVEL=INFO
```

## Performance Tips

### Connection Pooling

```env
# Adjust pool size based on load
DATABASE_MIN_POOL_SIZE=5
DATABASE_MAX_POOL_SIZE=20
DATABASE_POOL_TIMEOUT=30
```

### Query Optimization

```bash
# Enable SQL logging (dev only)
DATABASE_ECHO=True

# Test query performance
psql evf_portugal_2030

# Use EXPLAIN ANALYZE
EXPLAIN ANALYZE SELECT * FROM evf_projects WHERE tenant_id = 'xxx';
```

### Index Verification

```bash
# Run test script to see indexes
python backend/test_connection.py

# Or check manually
psql evf_portugal_2030 -c "\di"
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Database Setup

jobs:
  setup:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_DB: evf_portugal_2030
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v3

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install -r backend/requirements.txt

      - name: Run migrations
        run: alembic upgrade head
        env:
          DATABASE_URL: postgresql+asyncpg://postgres:postgres@localhost:5432/evf_portugal_2030

      - name: Test connection
        run: python backend/test_connection.py

      - name: Seed demo data
        run: python backend/seed_data.py
```

## Next Steps

After successful setup:

1. ✅ **Start API**
   ```bash
   cd backend
   uvicorn main:app --reload --port 8000
   ```

2. ✅ **Test API**
   - Open http://localhost:8000/docs
   - Login with demo credentials
   - Explore interactive API documentation

3. ✅ **Frontend Integration**
   - Use demo tenant ID in frontend
   - Test authentication flow
   - Build UI components

4. ✅ **Development**
   - Create new migrations as needed
   - Run tests regularly
   - Monitor database performance

## Additional Resources

- **Full Setup Guide**: [DATABASE_SETUP.md](DATABASE_SETUP.md)
- **Quick Start**: [QUICKSTART_DATABASE.md](QUICKSTART_DATABASE.md)
- **Implementation Summary**: [SEED_DATA_SUMMARY.md](SEED_DATA_SUMMARY.md)
- **Architecture**: [ARCHITECTURE.md](ARCHITECTURE.md)

## Support

For issues:
1. Check this guide first
2. Review error messages carefully
3. Test connection with `test_connection.py`
4. Check PostgreSQL logs
5. Review migration history

---

**Last Updated**: 2025-11-07
**Version**: 1.0.0
