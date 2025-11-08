-- EVF Portugal 2030 - Database Initialization Script
-- This script is executed when PostgreSQL container is first created

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create database if not exists (this is handled by POSTGRES_DB env var)
-- But we can set up permissions and schemas here

-- Set default search path
ALTER DATABASE evf_portugal_2030 SET search_path TO public;

-- Create schema for audit logs (optional - for future use)
CREATE SCHEMA IF NOT EXISTS audit;

-- Grant permissions
GRANT ALL PRIVILEGES ON SCHEMA public TO evf_user;
GRANT ALL PRIVILEGES ON SCHEMA audit TO evf_user;

-- Enable Row-Level Security by default for all new tables
-- (Individual tables will define their own RLS policies via Alembic migrations)
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO evf_user;

-- Create a function for updated_at timestamps (will be used by Alembic models)
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Success message
DO $$
BEGIN
    RAISE NOTICE '✅ EVF Portugal 2030 database initialized successfully';
    RAISE NOTICE '   Extensions: uuid-ossp, pgcrypto';
    RAISE NOTICE '   Schemas: public, audit';
    RAISE NOTICE '   User: evf_user';
END $$;
