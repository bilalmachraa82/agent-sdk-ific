"""
EVF (Economic Viability Study) project models.
Core business entities for the PT2030 funding application system.
"""

from datetime import datetime
from uuid import uuid4
from sqlalchemy import (
    Column, String, VARCHAR, Integer, Numeric, DateTime, func,
    Index, ForeignKey, Text, Boolean, UUID, Enum, JSON, Computed
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
import enum

from backend.models.base import Base, BaseTenantModel


class EVFStatus(str, enum.Enum):
    """Status of an EVF project."""
    DRAFT = "draft"
    UPLOADING = "uploading"
    VALIDATING = "validating"
    PROCESSING = "processing"
    REVIEW = "review"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUBMITTED = "submitted"
    ARCHIVED = "archived"


class FundType(str, enum.Enum):
    """Types of Portuguese funding programs."""
    PT2030 = "pt2030"
    PRR = "prr"  # Recovery and Resilience Plan
    SITCE = "sitce"
    OTHER = "other"


class ComplianceStatus(str, enum.Enum):
    """Compliance validation status."""
    NOT_VALIDATED = "not_validated"
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    REVIEW_REQUIRED = "review_required"


class EVFProject(Base, BaseTenantModel):
    """
    Main EVF project entity.
    Represents a funding application being processed.
    """
    __tablename__ = "evf_projects"

    # Basic information
    name = Column(
        String(255),
        nullable=False,
        comment="Project name"
    )
    description = Column(
        Text,
        nullable=True,
        comment="Project description"
    )
    fund_type = Column(
        Enum(FundType),
        nullable=False,
        default=FundType.PT2030,
        comment="Type of funding (PT2030, PRR, SITCE)"
    )

    # Project scope
    company_id = Column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="SET NULL"),
        nullable=True,
        comment="Company applying for funding"
    )
    project_start_year = Column(
        Integer,
        nullable=True,
        comment="Year project starts"
    )
    project_end_year = Column(
        Integer,
        nullable=True,
        comment="Year project ends"
    )
    project_duration_years = Column(
        Integer,
        nullable=True,
        comment="Project duration in years"
    )

    # File references
    saft_file_path = Column(
        String(500),
        nullable=True,
        comment="Path to uploaded SAF-T XML file"
    )
    saft_file_hash = Column(
        VARCHAR(64),
        nullable=True,
        comment="SHA-256 hash of SAF-T file for integrity"
    )
    excel_file_path = Column(
        String(500),
        nullable=True,
        comment="Path to generated Excel model"
    )
    pdf_report_path = Column(
        String(500),
        nullable=True,
        comment="Path to generated PDF report"
    )

    # Financial metrics (from FinancialModelAgent)
    valf = Column(
        Numeric(15, 2),
        nullable=True,
        comment="Net Present Value (VALF) at 4% discount rate"
    )
    trf = Column(
        Numeric(5, 2),
        nullable=True,
        comment="Internal Rate of Return (TRF) in percentage"
    )
    payback_period = Column(
        Numeric(5, 2),
        nullable=True,
        comment="Payback period in years"
    )
    total_investment = Column(
        Numeric(15, 2),
        nullable=True,
        comment="Total project investment"
    )
    eligible_investment = Column(
        Numeric(15, 2),
        nullable=True,
        comment="Eligible investment amount"
    )
    funding_requested = Column(
        Numeric(15, 2),
        nullable=True,
        comment="Funding amount requested"
    )

    # Compliance status
    compliance_status = Column(
        Enum(ComplianceStatus),
        default=ComplianceStatus.NOT_VALIDATED,
        comment="PT2030 compliance validation status"
    )
    compliance_errors = Column(
        ARRAY(String),
        default=list,
        comment="List of compliance validation errors"
    )
    compliance_suggestions = Column(
        JSONB,
        default=lambda: {},
        comment="Suggestions to achieve compliance"
    )

    # Processing status
    status = Column(
        Enum(EVFStatus),
        default=EVFStatus.DRAFT,
        nullable=False,
        index=True,
        comment="Current project status"
    )
    processing_start_time = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="When processing started"
    )
    processing_end_time = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="When processing completed"
    )
    processing_duration_seconds = Column(
        Integer,
        nullable=True,
        comment="Total processing time in seconds"
    )

    # Audit information
    created_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="User who created this project"
    )
    approved_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="User who approved this project"
    )
    approved_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="When project was approved"
    )

    # Metadata and notes
    metadata = Column(
        JSONB,
        default=lambda: {},
        comment="Custom metadata and processing details"
    )
    notes = Column(
        Text,
        nullable=True,
        comment="Internal notes about the project"
    )

    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    tenant = relationship("Tenant", back_populates="projects")
    company = relationship("Company")
    financial_models = relationship("FinancialModel", back_populates="project", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="project", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index("idx_evf_tenant_status", "tenant_id", "status"),
        Index("idx_evf_tenant_created", "tenant_id", "created_at", postgresql_using="btree"),
        Index("idx_evf_company", "company_id"),
        Index("idx_evf_fund_type", "fund_type"),
    )

    def __repr__(self):
        return f"<EVFProject(id={self.id}, name={self.name}, status={self.status})>"


class FinancialModel(Base, BaseTenantModel):
    """
    Stores financial model calculations and snapshots.
    Immutable records for audit trail of all calculations.
    """
    __tablename__ = "financial_models"

    # Reference to project
    project_id = Column(
        UUID(as_uuid=True),
        ForeignKey("evf_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Related EVF project"
    )
    version = Column(
        Integer,
        default=1,
        comment="Version number of this model"
    )

    # Input data snapshot
    input_data = Column(
        JSONB,
        nullable=False,
        comment="Complete input data used for calculations"
    )
    input_hash = Column(
        VARCHAR(64),
        nullable=False,
        comment="SHA-256 hash of input data"
    )

    # Financial calculations
    calculations = Column(
        JSONB,
        nullable=False,
        comment="All financial calculations and formulas used"
    )

    # Output results
    valf = Column(Numeric(15, 2), nullable=False, comment="Net Present Value")
    trf = Column(Numeric(5, 2), nullable=False, comment="Internal Rate of Return (%)")
    payback_period = Column(Numeric(5, 2), nullable=True)
    roi = Column(Numeric(5, 2), nullable=True, comment="Return on Investment (%)")

    # Cash flow projection
    cash_flows = Column(
        JSONB,
        nullable=False,
        comment="10-year cash flow projection"
    )

    # Financial ratios
    financial_ratios = Column(
        JSONB,
        nullable=False,
        comment="30+ financial ratios (debt ratio, liquidity, etc.)"
    )

    # Validation
    is_valid = Column(
        Boolean,
        default=True,
        comment="Whether calculations are valid"
    )
    validation_errors = Column(
        ARRAY(String),
        default=list,
        comment="Any validation errors"
    )

    # Metadata
    model_type = Column(
        String(50),
        default="deterministic",
        comment="Type of model (deterministic, probabilistic)"
    )
    assumptions = Column(
        JSONB,
        nullable=False,
        comment="Key assumptions used in model"
    )
    sources = Column(
        JSONB,
        nullable=False,
        comment="Data sources for inputs"
    )

    # Audit
    calculated_by_agent = Column(
        String(50),
        nullable=False,
        comment="Name of agent that performed calculation"
    )

    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    # Relationships
    project = relationship("EVFProject", back_populates="financial_models")

    # Indexes
    __table_args__ = (
        Index("idx_financial_model_project", "project_id"),
        Index("idx_financial_model_tenant_created", "tenant_id", "created_at"),
    )

    def __repr__(self):
        return f"<FinancialModel(project_id={self.project_id}, version={self.version})>"


class AuditLog(Base, BaseTenantModel):
    """
    Immutable audit log for compliance and traceability.
    Every operation is logged with full details for PT2030 compliance.
    """
    __tablename__ = "audit_log"

    # Operation details
    action = Column(
        String(100),
        nullable=False,
        comment="Operation performed (e.g., 'upload_file', 'calculate_valf')"
    )
    resource_type = Column(
        String(50),
        nullable=False,
        comment="Type of resource (e.g., 'evf_project', 'financial_model')"
    )
    resource_id = Column(
        UUID(as_uuid=True),
        nullable=True,
        comment="ID of affected resource"
    )

    # Agent information
    agent_name = Column(
        String(50),
        nullable=True,
        comment="Name of agent that performed action"
    )

    # Request/Response data
    input_hash = Column(
        VARCHAR(64),
        nullable=True,
        comment="SHA-256 hash of input data"
    )
    output_hash = Column(
        VARCHAR(64),
        nullable=True,
        comment="SHA-256 hash of output data"
    )
    input_size_bytes = Column(
        Integer,
        nullable=True,
        comment="Size of input data"
    )
    output_size_bytes = Column(
        Integer,
        nullable=True,
        comment="Size of output data"
    )

    # Cost tracking
    tokens_used = Column(
        Integer,
        default=0,
        comment="Claude tokens consumed (if applicable)"
    )
    cost_euros = Column(
        Numeric(6, 4),
        default=0,
        comment="Cost of operation in EUR"
    )

    # Client information
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="User who triggered action"
    )
    ip_address = Column(
        String(45),
        nullable=True,
        comment="Client IP address"
    )
    user_agent = Column(
        String(500),
        nullable=True,
        comment="Client user agent"
    )

    # Request details
    request_method = Column(
        String(10),
        nullable=True,
        comment="HTTP method (GET, POST, etc.)"
    )
    request_path = Column(
        String(500),
        nullable=True,
        comment="API endpoint path"
    )
    request_duration_ms = Column(
        Integer,
        nullable=True,
        comment="Request processing time in milliseconds"
    )

    # Related project
    project_id = Column(
        UUID(as_uuid=True),
        ForeignKey("evf_projects.id", ondelete="SET NULL"),
        nullable=True,
        comment="Related EVF project if applicable"
    )

    # Status and errors
    status = Column(
        String(20),
        default="success",
        comment="Operation status (success, error, warning)"
    )
    error_message = Column(
        Text,
        nullable=True,
        comment="Error message if operation failed"
    )
    error_stacktrace = Column(
        Text,
        nullable=True,
        comment="Stack trace if operation failed"
    )

    # Metadata
    metadata = Column(
        JSONB,
        default=lambda: {},
        comment="Additional contextual data"
    )

    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    # Relationships
    project = relationship("EVFProject", back_populates="audit_logs")

    # Indexes (critical for audit queries)
    __table_args__ = (
        Index("idx_audit_tenant_created", "tenant_id", "created_at", postgresql_using="btree"),
        Index("idx_audit_resource", "resource_type", "resource_id"),
        Index("idx_audit_user", "user_id"),
        Index("idx_audit_action", "action"),
        Index("idx_audit_cost", "cost_euros"),
    )

    def __repr__(self):
        return f"<AuditLog(id={self.id}, action={self.action}, status={self.status})>"
