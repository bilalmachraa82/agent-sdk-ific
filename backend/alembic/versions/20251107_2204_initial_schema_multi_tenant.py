"""initial_schema_multi_tenant

Revision ID: 05d3decaaf4a
Revises:
Create Date: 2025-11-07 22:04:52.418998

Creates all initial tables for EVF Portugal 2030 with multi-tenant support and Row-Level Security (RLS).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '05d3decaaf4a'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create UUID extension if not exists
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')

    # ========== TENANTS TABLE ==========
    op.create_table(
        'tenants',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()'), comment='Unique tenant identifier'),
        sa.Column('slug', sa.VARCHAR(length=50), nullable=False, unique=True, index=True, comment='URL-friendly tenant identifier'),
        sa.Column('name', sa.String(length=255), nullable=False, comment='Tenant organization name'),
        sa.Column('nif', sa.VARCHAR(length=9), nullable=False, unique=True, index=True, comment='Portuguese NIF (tax ID)'),
        sa.Column('plan', sa.Enum('STARTER', 'PROFESSIONAL', 'ENTERPRISE', 'CUSTOM', name='tenantplan'), nullable=False, server_default='STARTER', comment='Subscription plan'),
        sa.Column('mrr', sa.Numeric(precision=10, scale=2), server_default='0', comment='Monthly recurring revenue in EUR'),
        sa.Column('email', sa.String(length=255), comment='Primary contact email'),
        sa.Column('phone', sa.VARCHAR(length=20), comment='Primary contact phone'),
        sa.Column('website', sa.String(length=255), comment='Tenant website'),
        sa.Column('address', sa.Text, comment='Business address'),
        sa.Column('city', sa.String(length=100), comment='City'),
        sa.Column('postal_code', sa.VARCHAR(length=10), comment='Postal code'),
        sa.Column('settings', postgresql.JSONB, server_default='{}', comment='Tenant-specific configuration settings'),
        sa.Column('metadata', postgresql.JSONB, server_default='{}', comment='Custom metadata'),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default='true', comment='Whether tenant is active'),
        sa.Column('is_verified', sa.Boolean, nullable=False, server_default='false', comment='Whether tenant email is verified'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, index=True, comment='Tenant creation timestamp'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=False, comment='Last update timestamp'),
        sa.Column('deleted_at', sa.DateTime(timezone=True), comment='Soft delete timestamp'),
    )

    # ========== COMPANIES TABLE ==========
    op.create_table(
        'companies',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('nif', sa.VARCHAR(length=9), nullable=False, unique=True, index=True, comment='Portuguese NIF (tax ID)'),
        sa.Column('name', sa.String(length=255), nullable=False, comment='Company name'),
        sa.Column('cae_code', sa.VARCHAR(length=5), comment='Portuguese CAE code (sector classification)'),
        sa.Column('email', sa.String(length=255)),
        sa.Column('phone', sa.VARCHAR(length=20)),
        sa.Column('website', sa.String(length=255)),
        sa.Column('address', sa.Text),
        sa.Column('metadata', postgresql.JSONB, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, index=True),
    )

    # ========== USERS TABLE (Multi-tenant) ==========
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()'), comment='Unique identifier'),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True, comment='Tenant ID for multi-tenant isolation'),
        sa.Column('email', sa.String(length=255), nullable=False, comment='User email address'),
        sa.Column('password_hash', sa.String(length=255), nullable=False, comment='Hashed password (bcrypt)'),
        sa.Column('full_name', sa.String(length=255), comment='User full name'),
        sa.Column('role', sa.Enum('ADMIN', 'ANALYST', 'REVIEWER', 'VIEWER', name='userrole'), nullable=False, server_default='VIEWER', comment='Role within tenant'),
        sa.Column('phone', sa.VARCHAR(length=20), comment='User phone number'),
        sa.Column('department', sa.String(length=100), comment='Department or team'),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default='true', comment='Whether user account is active'),
        sa.Column('is_verified', sa.Boolean, nullable=False, server_default='false', comment='Whether email is verified'),
        sa.Column('last_login', sa.DateTime(timezone=True), comment='Last login timestamp'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, index=True, comment='Creation timestamp'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=False, comment='Last update timestamp'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('tenant_id', 'email', name='uq_tenant_email'),
    )
    op.create_index('idx_user_tenant_active', 'users', ['tenant_id', 'is_active'])
    op.create_index('idx_users_tenant_created', 'users', ['tenant_id', 'created_at'], postgresql_using='btree')

    # ========== TENANT_COMPANIES (Many-to-many) ==========
    op.create_table(
        'tenant_companies',
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), primary_key=True, comment='Tenant (consultant)'),
        sa.Column('company_id', postgresql.UUID(as_uuid=True), primary_key=True, comment='Company being accessed'),
        sa.Column('added_by', postgresql.UUID(as_uuid=True), comment='User who granted access'),
        sa.Column('added_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='When access was granted'),
        sa.Column('notes', sa.Text, comment='Notes about this access'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['added_by'], ['users.id'], ondelete='SET NULL'),
    )

    # ========== TENANT_USAGE (Multi-tenant) ==========
    op.create_table(
        'tenant_usage',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()'), comment='Unique identifier'),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True, comment='Tenant ID for multi-tenant isolation'),
        sa.Column('month', sa.DateTime(timezone=True), nullable=False, comment='Month (first day of month)'),
        sa.Column('evfs_processed', sa.Integer, server_default='0', comment='Number of EVFs processed this month'),
        sa.Column('tokens_consumed', sa.Integer, server_default='0', comment='Claude tokens consumed (thousands)'),
        sa.Column('storage_mb', sa.Numeric(precision=10, scale=2), server_default='0', comment='Storage used in MB'),
        sa.Column('cost_euros', sa.Numeric(precision=10, scale=2), server_default='0', comment='Total cost in EUR for this month'),
        sa.Column('storage_cost_euros', sa.Numeric(precision=10, scale=2), server_default='0', comment='Storage cost in EUR'),
        sa.Column('ai_cost_euros', sa.Numeric(precision=10, scale=2), server_default='0', comment='AI/Claude cost in EUR'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, index=True, comment='Creation timestamp'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=False, comment='Last update timestamp'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('tenant_id', 'month', name='uq_tenant_month_usage'),
    )
    op.create_index('idx_usage_tenant_month', 'tenant_usage', ['tenant_id', 'month'])
    op.create_index('idx_tenant_usage_tenant_created', 'tenant_usage', ['tenant_id', 'created_at'], postgresql_using='btree')

    # ========== EVF_PROJECTS (Multi-tenant) ==========
    op.create_table(
        'evf_projects',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()'), comment='Unique identifier'),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True, comment='Tenant ID for multi-tenant isolation'),
        sa.Column('name', sa.String(length=255), nullable=False, comment='Project name'),
        sa.Column('description', sa.Text, comment='Project description'),
        sa.Column('fund_type', sa.Enum('PT2030', 'PRR', 'SITCE', 'OTHER', name='fundtype'), nullable=False, server_default='PT2030', comment='Type of funding (PT2030, PRR, SITCE)'),
        sa.Column('company_id', postgresql.UUID(as_uuid=True), comment='Company applying for funding'),
        sa.Column('project_start_year', sa.Integer, comment='Year project starts'),
        sa.Column('project_end_year', sa.Integer, comment='Year project ends'),
        sa.Column('project_duration_years', sa.Integer, comment='Project duration in years'),
        sa.Column('saft_file_path', sa.String(length=500), comment='Path to uploaded SAF-T XML file'),
        sa.Column('saft_file_hash', sa.VARCHAR(length=64), comment='SHA-256 hash of SAF-T file for integrity'),
        sa.Column('excel_file_path', sa.String(length=500), comment='Path to generated Excel model'),
        sa.Column('pdf_report_path', sa.String(length=500), comment='Path to generated PDF report'),
        sa.Column('valf', sa.Numeric(precision=15, scale=2), comment='Net Present Value (VALF) at 4% discount rate'),
        sa.Column('trf', sa.Numeric(precision=5, scale=2), comment='Internal Rate of Return (TRF) in percentage'),
        sa.Column('payback_period', sa.Numeric(precision=5, scale=2), comment='Payback period in years'),
        sa.Column('total_investment', sa.Numeric(precision=15, scale=2), comment='Total project investment'),
        sa.Column('eligible_investment', sa.Numeric(precision=15, scale=2), comment='Eligible investment amount'),
        sa.Column('funding_requested', sa.Numeric(precision=15, scale=2), comment='Funding amount requested'),
        sa.Column('compliance_status', sa.Enum('NOT_VALIDATED', 'COMPLIANT', 'NON_COMPLIANT', 'REVIEW_REQUIRED', name='compliancestatus'), server_default='NOT_VALIDATED', comment='PT2030 compliance validation status'),
        sa.Column('compliance_errors', postgresql.ARRAY(sa.String), server_default='{}', comment='List of compliance validation errors'),
        sa.Column('compliance_suggestions', postgresql.JSONB, server_default='{}', comment='Suggestions to achieve compliance'),
        sa.Column('status', sa.Enum('DRAFT', 'UPLOADING', 'VALIDATING', 'PROCESSING', 'REVIEW', 'APPROVED', 'REJECTED', 'SUBMITTED', 'ARCHIVED', name='evfstatus'), nullable=False, server_default='DRAFT', index=True, comment='Current project status'),
        sa.Column('processing_start_time', sa.DateTime(timezone=True), comment='When processing started'),
        sa.Column('processing_end_time', sa.DateTime(timezone=True), comment='When processing completed'),
        sa.Column('processing_duration_seconds', sa.Integer, comment='Total processing time in seconds'),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), comment='User who created this project'),
        sa.Column('approved_by', postgresql.UUID(as_uuid=True), comment='User who approved this project'),
        sa.Column('approved_at', sa.DateTime(timezone=True), comment='When project was approved'),
        sa.Column('metadata', postgresql.JSONB, server_default='{}', comment='Custom metadata and processing details'),
        sa.Column('notes', sa.Text, comment='Internal notes about the project'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, index=True, comment='Creation timestamp'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=False, comment='Last update timestamp'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['approved_by'], ['users.id'], ondelete='SET NULL'),
    )
    op.create_index('idx_evf_tenant_status', 'evf_projects', ['tenant_id', 'status'])
    op.create_index('idx_evf_tenant_created', 'evf_projects', ['tenant_id', 'created_at'], postgresql_using='btree')
    op.create_index('idx_evf_company', 'evf_projects', ['company_id'])
    op.create_index('idx_evf_fund_type', 'evf_projects', ['fund_type'])

    # ========== FINANCIAL_MODELS (Multi-tenant) ==========
    op.create_table(
        'financial_models',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()'), comment='Unique identifier'),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True, comment='Tenant ID for multi-tenant isolation'),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=False, index=True, comment='Related EVF project'),
        sa.Column('version', sa.Integer, server_default='1', comment='Version number of this model'),
        sa.Column('input_data', postgresql.JSONB, nullable=False, comment='Complete input data used for calculations'),
        sa.Column('input_hash', sa.VARCHAR(length=64), nullable=False, comment='SHA-256 hash of input data'),
        sa.Column('calculations', postgresql.JSONB, nullable=False, comment='All financial calculations and formulas used'),
        sa.Column('valf', sa.Numeric(precision=15, scale=2), nullable=False, comment='Net Present Value'),
        sa.Column('trf', sa.Numeric(precision=5, scale=2), nullable=False, comment='Internal Rate of Return (%)'),
        sa.Column('payback_period', sa.Numeric(precision=5, scale=2)),
        sa.Column('roi', sa.Numeric(precision=5, scale=2), comment='Return on Investment (%)'),
        sa.Column('cash_flows', postgresql.JSONB, nullable=False, comment='10-year cash flow projection'),
        sa.Column('financial_ratios', postgresql.JSONB, nullable=False, comment='30+ financial ratios (debt ratio, liquidity, etc.)'),
        sa.Column('is_valid', sa.Boolean, server_default='true', comment='Whether calculations are valid'),
        sa.Column('validation_errors', postgresql.ARRAY(sa.String), server_default='{}', comment='Any validation errors'),
        sa.Column('model_type', sa.String(length=50), server_default='deterministic', comment='Type of model (deterministic, probabilistic)'),
        sa.Column('assumptions', postgresql.JSONB, nullable=False, comment='Key assumptions used in model'),
        sa.Column('sources', postgresql.JSONB, nullable=False, comment='Data sources for inputs'),
        sa.Column('calculated_by_agent', sa.String(length=50), nullable=False, comment='Name of agent that performed calculation'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, index=True, comment='Creation timestamp'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=False, comment='Last update timestamp'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['evf_projects.id'], ondelete='CASCADE'),
    )
    op.create_index('idx_financial_model_project', 'financial_models', ['project_id'])
    op.create_index('idx_financial_model_tenant_created', 'financial_models', ['tenant_id', 'created_at'])
    op.create_index('idx_financial_models_tenant_created', 'financial_models', ['tenant_id', 'created_at'], postgresql_using='btree')

    # ========== FILES (Multi-tenant) ==========
    op.create_table(
        'files',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()'), comment='Unique identifier'),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True, comment='Tenant ID for multi-tenant isolation'),
        sa.Column('file_name', sa.String(length=255), nullable=False, index=True, comment='Original file name'),
        sa.Column('file_type', sa.String(length=50), nullable=False, index=True, comment='File type (saft, excel, pdf, csv, json)'),
        sa.Column('file_extension', sa.String(length=10), nullable=False, comment='File extension (.xml, .xlsx, .pdf, etc.)'),
        sa.Column('mime_type', sa.String(length=100), nullable=False, comment='MIME type'),
        sa.Column('file_size_bytes', sa.Integer, nullable=False, comment='Original file size in bytes'),
        sa.Column('encrypted_size_bytes', sa.Integer, nullable=False, comment='Encrypted file size in bytes'),
        sa.Column('sha256_hash', sa.String(length=64), nullable=False, index=True, comment='SHA-256 hash for integrity validation'),
        sa.Column('storage_path', sa.String(length=500), nullable=False, unique=True, comment='Path/key in storage backend'),
        sa.Column('storage_backend', sa.String(length=20), nullable=False, comment='Storage backend (local or s3)'),
        sa.Column('is_encrypted', sa.Boolean, nullable=False, server_default='true', comment='Whether file is encrypted at rest'),
        sa.Column('upload_timestamp', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()'), index=True, comment='When file was uploaded'),
        sa.Column('uploaded_by_user_id', postgresql.UUID(as_uuid=True), index=True, comment='User who uploaded the file'),
        sa.Column('metadata', postgresql.JSON, comment='Additional metadata (project_id, description, etc.)'),
        sa.Column('is_deleted', sa.Boolean, nullable=False, server_default='false', index=True, comment='Soft delete flag'),
        sa.Column('deleted_at', sa.DateTime(timezone=True), comment='When file was deleted'),
        sa.Column('deleted_by_user_id', postgresql.UUID(as_uuid=True), comment='User who deleted the file'),
        sa.Column('last_accessed_at', sa.DateTime(timezone=True), comment='Last time file was accessed'),
        sa.Column('access_count', sa.Integer, nullable=False, server_default='0', comment='Number of times file was accessed'),
        sa.Column('retention_until', sa.DateTime(timezone=True), comment='Retention period end date'),
        sa.Column('compliance_tags', postgresql.JSON, comment='Compliance tags (PT2030, PRR, etc.)'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, index=True, comment='Creation timestamp'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=False, comment='Last update timestamp'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
    )
    op.create_index('idx_files_tenant_created', 'files', ['tenant_id', 'created_at'], postgresql_using='btree')

    # ========== FILE_ACCESS_LOGS (Multi-tenant) ==========
    op.create_table(
        'file_access_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()'), comment='Unique identifier'),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True, comment='Tenant ID for multi-tenant isolation'),
        sa.Column('file_id', postgresql.UUID(as_uuid=True), nullable=False, index=True, comment='File that was accessed'),
        sa.Column('access_type', sa.String(length=50), nullable=False, index=True, comment='Type of access (download, view, delete)'),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), index=True, comment='User who accessed the file'),
        sa.Column('ip_address', sa.String(length=45), comment='IP address of the request'),
        sa.Column('user_agent', sa.String(length=500), comment='User agent string'),
        sa.Column('success', sa.Boolean, nullable=False, server_default='true', comment='Whether access was successful'),
        sa.Column('error_message', sa.Text, comment='Error message if access failed'),
        sa.Column('access_timestamp', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()'), index=True, comment='When access occurred'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, index=True, comment='Creation timestamp'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=False, comment='Last update timestamp'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
    )
    op.create_index('idx_file_access_logs_tenant_created', 'file_access_logs', ['tenant_id', 'created_at'], postgresql_using='btree')

    # ========== AUDIT_LOG (Multi-tenant) ==========
    op.create_table(
        'audit_log',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()'), comment='Unique identifier'),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True, comment='Tenant ID for multi-tenant isolation'),
        sa.Column('action', sa.String(length=100), nullable=False, comment="Operation performed (e.g., 'upload_file', 'calculate_valf')"),
        sa.Column('resource_type', sa.String(length=50), nullable=False, comment="Type of resource (e.g., 'evf_project', 'financial_model')"),
        sa.Column('resource_id', postgresql.UUID(as_uuid=True), comment='ID of affected resource'),
        sa.Column('agent_name', sa.String(length=50), comment='Name of agent that performed action'),
        sa.Column('input_hash', sa.VARCHAR(length=64), comment='SHA-256 hash of input data'),
        sa.Column('output_hash', sa.VARCHAR(length=64), comment='SHA-256 hash of output data'),
        sa.Column('input_size_bytes', sa.Integer, comment='Size of input data'),
        sa.Column('output_size_bytes', sa.Integer, comment='Size of output data'),
        sa.Column('tokens_used', sa.Integer, server_default='0', comment='Claude tokens consumed (if applicable)'),
        sa.Column('cost_euros', sa.Numeric(precision=6, scale=4), server_default='0', comment='Cost of operation in EUR'),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), comment='User who triggered action'),
        sa.Column('ip_address', sa.String(length=45), comment='Client IP address'),
        sa.Column('user_agent', sa.String(length=500), comment='Client user agent'),
        sa.Column('request_method', sa.String(length=10), comment='HTTP method (GET, POST, etc.)'),
        sa.Column('request_path', sa.String(length=500), comment='API endpoint path'),
        sa.Column('request_duration_ms', sa.Integer, comment='Request processing time in milliseconds'),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), comment='Related EVF project if applicable'),
        sa.Column('status', sa.String(length=20), server_default='success', comment='Operation status (success, error, warning)'),
        sa.Column('error_message', sa.Text, comment='Error message if operation failed'),
        sa.Column('error_stacktrace', sa.Text, comment='Stack trace if operation failed'),
        sa.Column('metadata', postgresql.JSONB, server_default='{}', comment='Additional contextual data'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, index=True, comment='Creation timestamp'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=False, comment='Last update timestamp'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['project_id'], ['evf_projects.id'], ondelete='SET NULL'),
    )
    op.create_index('idx_audit_tenant_created', 'audit_log', ['tenant_id', 'created_at'], postgresql_using='btree')
    op.create_index('idx_audit_resource', 'audit_log', ['resource_type', 'resource_id'])
    op.create_index('idx_audit_user', 'audit_log', ['user_id'])
    op.create_index('idx_audit_action', 'audit_log', ['action'])
    op.create_index('idx_audit_cost', 'audit_log', ['cost_euros'])
    op.create_index('idx_audit_log_tenant_created', 'audit_log', ['tenant_id', 'created_at'], postgresql_using='btree')

    # ========== ROW-LEVEL SECURITY (RLS) SETUP ==========
    # Enable RLS on all multi-tenant tables
    for table in ['users', 'tenant_usage', 'evf_projects', 'financial_models', 'files', 'file_access_logs', 'audit_log']:
        op.execute(f'ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;')

        # Create RLS policy: tenants can only see their own data
        op.execute(f'''
            CREATE POLICY tenant_isolation_policy ON {table}
            USING (tenant_id::text = current_setting('app.current_tenant', TRUE)::text);
        ''')

        # Create RLS policy for bypass (admin operations)
        op.execute(f'''
            CREATE POLICY bypass_rls_policy ON {table}
            USING (current_setting('app.bypass_rls', TRUE)::text = 'true');
        ''')


def downgrade() -> None:
    # Drop all tables (CASCADE will handle dependencies)
    op.drop_table('audit_log')
    op.drop_table('file_access_logs')
    op.drop_table('files')
    op.drop_table('financial_models')
    op.drop_table('evf_projects')
    op.drop_table('tenant_usage')
    op.drop_table('tenant_companies')
    op.drop_table('users')
    op.drop_table('companies')
    op.drop_table('tenants')

    # Drop enums
    op.execute('DROP TYPE IF EXISTS evfstatus CASCADE;')
    op.execute('DROP TYPE IF EXISTS compliancestatus CASCADE;')
    op.execute('DROP TYPE IF EXISTS fundtype CASCADE;')
    op.execute('DROP TYPE IF EXISTS userrole CASCADE;')
    op.execute('DROP TYPE IF EXISTS tenantplan CASCADE;')
