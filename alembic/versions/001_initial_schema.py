"""
Initial database schema with multi-tenant support and RLS.
Creates core tables: tenants, users, companies, evf_projects, financial_models, audit_logs.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# Revision identifiers
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create initial schema."""

    # Create tenants table (root entity)
    op.create_table(
        'tenants',
        sa.Column('id', sa.UUID(), nullable=False, comment='Unique tenant identifier'),
        sa.Column('slug', sa.VARCHAR(length=50), nullable=False, comment='URL-friendly tenant identifier'),
        sa.Column('name', sa.String(length=255), nullable=False, comment='Tenant organization name'),
        sa.Column('nif', sa.VARCHAR(length=9), nullable=False, comment='Portuguese NIF (tax ID)'),
        sa.Column('plan', sa.Enum('starter', 'professional', 'enterprise', 'custom', name='tenantplan'), nullable=False),
        sa.Column('mrr', sa.Numeric(precision=10, scale=2), nullable=True, comment='Monthly recurring revenue in EUR'),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('phone', sa.VARCHAR(length=20), nullable=True),
        sa.Column('website', sa.String(length=255), nullable=True),
        sa.Column('address', sa.Text(), nullable=True),
        sa.Column('city', sa.String(length=100), nullable=True),
        sa.Column('postal_code', sa.VARCHAR(length=10), nullable=True),
        sa.Column('settings', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='{}'),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='{}'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug', name='uq_tenant_slug'),
        sa.UniqueConstraint('nif', name='uq_tenant_nif'),
    )
    op.create_index('ix_tenants_created_at', 'tenants', ['created_at'], unique=False)

    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=True),
        sa.Column('role', sa.Enum('admin', 'analyst', 'reviewer', 'viewer', name='userrole'), nullable=False),
        sa.Column('phone', sa.VARCHAR(length=20), nullable=True),
        sa.Column('department', sa.String(length=100), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('last_login', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'email', name='uq_tenant_email'),
    )
    op.create_index('ix_users_tenant_id', 'users', ['tenant_id'], unique=False)
    op.create_index('ix_user_tenant_active', 'users', ['tenant_id', 'is_active'], unique=False)
    op.create_index('ix_users_created_at', 'users', ['created_at'], unique=False)

    # Create companies table (not tenant-specific, shared across consultants)
    op.create_table(
        'companies',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('nif', sa.VARCHAR(length=9), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('cae_code', sa.VARCHAR(length=5), nullable=True),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('phone', sa.VARCHAR(length=20), nullable=True),
        sa.Column('website', sa.String(length=255), nullable=True),
        sa.Column('address', sa.Text(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('nif', name='uq_company_nif'),
    )
    op.create_index('ix_companies_nif', 'companies', ['nif'], unique=False)

    # Create tenant_companies (many-to-many)
    op.create_table(
        'tenant_companies',
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('company_id', sa.UUID(), nullable=False),
        sa.Column('added_by', sa.UUID(), nullable=True),
        sa.Column('added_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['added_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('tenant_id', 'company_id'),
    )

    # Create tenant_usage table
    op.create_table(
        'tenant_usage',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('month', sa.DateTime(timezone=True), nullable=False),
        sa.Column('evfs_processed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('tokens_consumed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('storage_mb', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0'),
        sa.Column('cost_euros', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0'),
        sa.Column('storage_cost_euros', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0'),
        sa.Column('ai_cost_euros', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'month', name='uq_tenant_month_usage'),
    )
    op.create_index('idx_usage_tenant_month', 'tenant_usage', ['tenant_id', 'month'], unique=False)

    # Create evf_projects table
    op.create_table(
        'evf_projects',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('fund_type', sa.Enum('pt2030', 'prr', 'sitce', 'other', name='fundtype'), nullable=False),
        sa.Column('company_id', sa.UUID(), nullable=True),
        sa.Column('project_start_year', sa.Integer(), nullable=True),
        sa.Column('project_end_year', sa.Integer(), nullable=True),
        sa.Column('project_duration_years', sa.Integer(), nullable=True),
        sa.Column('saft_file_path', sa.String(length=500), nullable=True),
        sa.Column('saft_file_hash', sa.VARCHAR(length=64), nullable=True),
        sa.Column('excel_file_path', sa.String(length=500), nullable=True),
        sa.Column('pdf_report_path', sa.String(length=500), nullable=True),
        sa.Column('valf', sa.Numeric(precision=15, scale=2), nullable=True, comment='Net Present Value at 4%'),
        sa.Column('trf', sa.Numeric(precision=5, scale=2), nullable=True, comment='Internal Rate of Return (%)'),
        sa.Column('payback_period', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('total_investment', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('eligible_investment', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('funding_requested', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('compliance_status', sa.Enum('not_validated', 'compliant', 'non_compliant', 'review_required', name='compliancestatus'), nullable=False),
        sa.Column('compliance_errors', postgresql.ARRAY(sa.String()), nullable=False, server_default='{}'),
        sa.Column('compliance_suggestions', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='{}'),
        sa.Column('status', sa.Enum('draft', 'uploading', 'validating', 'processing', 'review', 'approved', 'rejected', 'submitted', 'archived', name='evfstatus'), nullable=False),
        sa.Column('processing_start_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('processing_end_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('processing_duration_seconds', sa.Integer(), nullable=True),
        sa.Column('created_by', sa.UUID(), nullable=True),
        sa.Column('approved_by', sa.UUID(), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='{}'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['approved_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_evf_tenant_id', 'evf_projects', ['tenant_id'], unique=False)
    op.create_index('ix_evf_status', 'evf_projects', ['status'], unique=False)
    op.create_index('idx_evf_tenant_status', 'evf_projects', ['tenant_id', 'status'], unique=False)
    op.create_index('idx_evf_tenant_created', 'evf_projects', ['tenant_id', 'created_at'], unique=False)
    op.create_index('idx_evf_company', 'evf_projects', ['company_id'], unique=False)
    op.create_index('idx_evf_fund_type', 'evf_projects', ['fund_type'], unique=False)

    # Create financial_models table
    op.create_table(
        'financial_models',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('project_id', sa.UUID(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('input_data', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('input_hash', sa.VARCHAR(length=64), nullable=False),
        sa.Column('calculations', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('valf', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('trf', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column('payback_period', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('roi', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('cash_flows', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('financial_ratios', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('is_valid', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('validation_errors', postgresql.ARRAY(sa.String()), nullable=False, server_default='{}'),
        sa.Column('model_type', sa.String(length=50), nullable=False, server_default='deterministic'),
        sa.Column('assumptions', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('sources', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('calculated_by_agent', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['evf_projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_financial_model_project_id', 'financial_models', ['project_id'], unique=False)
    op.create_index('idx_financial_model_project', 'financial_models', ['project_id'], unique=False)
    op.create_index('idx_financial_model_tenant_created', 'financial_models', ['tenant_id', 'created_at'], unique=False)

    # Create audit_log table (immutable)
    op.create_table(
        'audit_log',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('resource_type', sa.String(length=50), nullable=False),
        sa.Column('resource_id', sa.UUID(), nullable=True),
        sa.Column('agent_name', sa.String(length=50), nullable=True),
        sa.Column('input_hash', sa.VARCHAR(length=64), nullable=True),
        sa.Column('output_hash', sa.VARCHAR(length=64), nullable=True),
        sa.Column('input_size_bytes', sa.Integer(), nullable=True),
        sa.Column('output_size_bytes', sa.Integer(), nullable=True),
        sa.Column('tokens_used', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('cost_euros', sa.Numeric(precision=6, scale=4), nullable=False, server_default='0'),
        sa.Column('user_id', sa.UUID(), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=500), nullable=True),
        sa.Column('request_method', sa.String(length=10), nullable=True),
        sa.Column('request_path', sa.String(length=500), nullable=True),
        sa.Column('request_duration_ms', sa.Integer(), nullable=True),
        sa.Column('project_id', sa.UUID(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='success'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('error_stacktrace', sa.Text(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['evf_projects.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_audit_tenant_created', 'audit_log', ['tenant_id', 'created_at'], unique=False)
    op.create_index('idx_audit_resource', 'audit_log', ['resource_type', 'resource_id'], unique=False)
    op.create_index('idx_audit_user', 'audit_log', ['user_id'], unique=False)
    op.create_index('idx_audit_action', 'audit_log', ['action'], unique=False)
    op.create_index('idx_audit_cost', 'audit_log', ['cost_euros'], unique=False)

    # Create Row-Level Security policies
    op.execute("""
    ALTER TABLE users ENABLE ROW LEVEL SECURITY;
    CREATE POLICY tenant_isolation_users ON users
        USING (tenant_id = CAST(current_setting('app.current_tenant', true) AS UUID));
    """)

    op.execute("""
    ALTER TABLE evf_projects ENABLE ROW LEVEL SECURITY;
    CREATE POLICY tenant_isolation_evf ON evf_projects
        USING (tenant_id = CAST(current_setting('app.current_tenant', true) AS UUID));
    """)

    op.execute("""
    ALTER TABLE financial_models ENABLE ROW LEVEL SECURITY;
    CREATE POLICY tenant_isolation_financial ON financial_models
        USING (tenant_id = CAST(current_setting('app.current_tenant', true) AS UUID));
    """)

    op.execute("""
    ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;
    CREATE POLICY tenant_isolation_audit ON audit_log
        USING (tenant_id = CAST(current_setting('app.current_tenant', true) AS UUID));
    """)

    op.execute("""
    ALTER TABLE tenant_usage ENABLE ROW LEVEL SECURITY;
    CREATE POLICY tenant_isolation_usage ON tenant_usage
        USING (tenant_id = CAST(current_setting('app.current_tenant', true) AS UUID));
    """)


def downgrade() -> None:
    """Drop all tables and policies."""
    op.execute("DROP POLICY IF EXISTS tenant_isolation_usage ON tenant_usage")
    op.execute("DROP POLICY IF EXISTS tenant_isolation_audit ON audit_log")
    op.execute("DROP POLICY IF EXISTS tenant_isolation_financial ON financial_models")
    op.execute("DROP POLICY IF EXISTS tenant_isolation_evf ON evf_projects")
    op.execute("DROP POLICY IF EXISTS tenant_isolation_users ON users")

    op.drop_table('audit_log')
    op.drop_table('financial_models')
    op.drop_table('evf_projects')
    op.drop_table('tenant_usage')
    op.drop_table('tenant_companies')
    op.drop_table('companies')
    op.drop_table('users')
    op.drop_table('tenants')

    # Drop enums
    op.execute("DROP TYPE IF EXISTS tenantplan")
    op.execute("DROP TYPE IF EXISTS userrole")
    op.execute("DROP TYPE IF EXISTS fundtype")
    op.execute("DROP TYPE IF EXISTS evfstatus")
    op.execute("DROP TYPE IF EXISTS compliancestatus")
