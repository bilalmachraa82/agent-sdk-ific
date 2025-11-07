"""
Tenant and user models for multi-tenant authentication and organization.
"""

from datetime import datetime
from uuid import uuid4
from sqlalchemy import (
    Column, String, VARCHAR, Integer, Numeric, DateTime, func,
    Index, UniqueConstraint, JSON, Boolean, UUID, Enum, ForeignKey, Text
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
import enum

from .base import Base, BaseTenantModel


class TenantPlan(str, enum.Enum):
    """Available subscription plans."""
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"
    CUSTOM = "custom"


class Tenant(Base):
    """
    Root tenant organization.
    Every other entity is scoped to a tenant via tenant_id.
    """
    __tablename__ = "tenants"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        comment="Unique tenant identifier"
    )
    slug = Column(
        VARCHAR(50),
        unique=True,
        nullable=False,
        index=True,
        comment="URL-friendly tenant identifier"
    )
    name = Column(
        String(255),
        nullable=False,
        comment="Tenant organization name"
    )
    nif = Column(
        VARCHAR(9),
        unique=True,
        nullable=False,
        index=True,
        comment="Portuguese NIF (tax ID)"
    )
    plan = Column(
        Enum(TenantPlan),
        default=TenantPlan.STARTER,
        nullable=False,
        comment="Subscription plan"
    )
    mrr = Column(
        Numeric(10, 2),
        default=0,
        comment="Monthly recurring revenue in EUR"
    )

    # Contact information
    email = Column(
        String(255),
        nullable=True,
        comment="Primary contact email"
    )
    phone = Column(
        VARCHAR(20),
        nullable=True,
        comment="Primary contact phone"
    )
    website = Column(
        String(255),
        nullable=True,
        comment="Tenant website"
    )

    # Address information
    address = Column(
        Text,
        nullable=True,
        comment="Business address"
    )
    city = Column(
        String(100),
        nullable=True,
        comment="City"
    )
    postal_code = Column(
        VARCHAR(10),
        nullable=True,
        comment="Postal code"
    )

    # Settings and metadata
    settings = Column(
        JSONB,
        default=lambda: {},
        comment="Tenant-specific configuration settings"
    )
    custom_metadata = Column(
        "metadata",  # Column name in database
        JSONB,
        default=lambda: {},
        comment="Custom metadata"
    )

    # Status tracking
    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
        comment="Whether tenant is active"
    )
    is_verified = Column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether tenant email is verified"
    )

    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
        comment="Tenant creation timestamp"
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="Last update timestamp"
    )
    deleted_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Soft delete timestamp"
    )

    # Relationships
    users = relationship("User", back_populates="tenant", cascade="all, delete-orphan")
    companies = relationship("Company", secondary="tenant_companies", back_populates="tenants")
    projects = relationship("EVFProject", back_populates="tenant", cascade="all, delete-orphan")
    usage = relationship("TenantUsage", back_populates="tenant", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Tenant(id={self.id}, slug={self.slug}, name={self.name})>"


class UserRole(str, enum.Enum):
    """User roles within a tenant."""
    ADMIN = "admin"
    ANALYST = "analyst"
    REVIEWER = "reviewer"
    VIEWER = "viewer"


class User(Base, BaseTenantModel):
    """
    Users belong to exactly one tenant.
    Tenant isolation is enforced at the database level via RLS.
    """
    __tablename__ = "users"

    email = Column(
        String(255),
        nullable=False,
        comment="User email address"
    )
    password_hash = Column(
        String(255),
        nullable=False,
        comment="Hashed password (bcrypt)"
    )
    full_name = Column(
        String(255),
        nullable=True,
        comment="User full name"
    )
    role = Column(
        Enum(UserRole),
        default=UserRole.VIEWER,
        nullable=False,
        comment="Role within tenant"
    )

    # Contact information
    phone = Column(
        VARCHAR(20),
        nullable=True,
        comment="User phone number"
    )
    department = Column(
        String(100),
        nullable=True,
        comment="Department or team"
    )

    # Status
    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
        comment="Whether user account is active"
    )
    is_verified = Column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether email is verified"
    )

    # Last activity
    last_login = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Last login timestamp"
    )

    # Foreign keys
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="User's tenant"
    )

    # Relationships
    tenant = relationship("Tenant", back_populates="users")

    # Constraints
    __table_args__ = (
        UniqueConstraint("tenant_id", "email", name="uq_tenant_email"),
        Index("idx_user_tenant_active", "tenant_id", "is_active"),
    )

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, tenant_id={self.tenant_id})>"


class TenantUsage(Base, BaseTenantModel):
    """
    Track monthly usage metrics per tenant for billing and cost control.
    """
    __tablename__ = "tenant_usage"

    month = Column(
        DateTime(timezone=True),
        nullable=False,
        comment="Month (first day of month)"
    )

    # Usage metrics
    evfs_processed = Column(
        Integer,
        default=0,
        comment="Number of EVFs processed this month"
    )
    tokens_consumed = Column(
        Integer,
        default=0,
        comment="Claude tokens consumed (thousands)"
    )
    storage_mb = Column(
        Numeric(10, 2),
        default=0,
        comment="Storage used in MB"
    )

    # Cost tracking
    cost_euros = Column(
        Numeric(10, 2),
        default=0,
        comment="Total cost in EUR for this month"
    )
    storage_cost_euros = Column(
        Numeric(10, 2),
        default=0,
        comment="Storage cost in EUR"
    )
    ai_cost_euros = Column(
        Numeric(10, 2),
        default=0,
        comment="AI/Claude cost in EUR"
    )

    # Foreign keys
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Relationships
    tenant = relationship("Tenant", back_populates="usage")

    # Constraints
    __table_args__ = (
        UniqueConstraint("tenant_id", "month", name="uq_tenant_month_usage"),
        Index("idx_usage_tenant_month", "tenant_id", "month"),
    )

    def __repr__(self):
        return f"<TenantUsage(tenant_id={self.tenant_id}, month={self.month})>"


class Company(Base):
    """
    Companies that can be referenced across multiple tenants.
    Typically used when consultants work with multiple companies.
    """
    __tablename__ = "companies"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    nif = Column(
        VARCHAR(9),
        unique=True,
        nullable=False,
        index=True,
        comment="Portuguese NIF (tax ID)"
    )
    name = Column(
        String(255),
        nullable=False,
        comment="Company name"
    )
    cae_code = Column(
        VARCHAR(5),
        nullable=True,
        comment="Portuguese CAE code (sector classification)"
    )

    # Company details
    email = Column(
        String(255),
        nullable=True,
    )
    phone = Column(
        VARCHAR(20),
        nullable=True,
    )
    website = Column(
        String(255),
        nullable=True,
    )
    address = Column(
        Text,
        nullable=True,
    )

    # Metadata
    custom_metadata = Column(
        "metadata",  # Column name in database
        JSONB,
        default=lambda: {},
    )

    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    # Relationships
    tenants = relationship("Tenant", secondary="tenant_companies", back_populates="companies")

    def __repr__(self):
        return f"<Company(id={self.id}, nif={self.nif}, name={self.name})>"


class TenantCompanyAccess(Base):
    """
    Many-to-many relationship allowing tenants (consultants) to access companies.
    """
    __tablename__ = "tenant_companies"

    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        primary_key=True,
        comment="Tenant (consultant)"
    )
    company_id = Column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        primary_key=True,
        comment="Company being accessed"
    )

    # Track who added the access
    added_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="User who granted access"
    )
    added_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="When access was granted"
    )

    # Access notes
    notes = Column(
        Text,
        nullable=True,
        comment="Notes about this access"
    )

    def __repr__(self):
        return f"<TenantCompanyAccess(tenant_id={self.tenant_id}, company_id={self.company_id})>"
