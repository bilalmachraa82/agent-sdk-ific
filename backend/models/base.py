"""
Base SQLAlchemy models with common fields and multi-tenant support.
All models inherit from these base classes to ensure consistent structure.
"""

from datetime import datetime
from uuid import uuid4
from typing import Optional
from sqlalchemy import Column, UUID, DateTime, String, func, Index
from sqlalchemy.orm import declarative_base, declared_attr
from sqlalchemy.ext.hybrid import hybrid_property

# Create declarative base for all models
Base = declarative_base()


class BaseTenantModel:
    """
    Base model for all tenant-scoped tables.
    Ensures tenant_id is present on every model.
    """

    @declared_attr
    def tenant_id(cls):
        """UUID reference to the tenant owning this record."""
        from sqlalchemy import ForeignKey
        return Column(
            UUID(as_uuid=True),
            ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
            comment="Tenant ID for multi-tenant isolation"
        )

    @declared_attr
    def id(cls):
        """Primary key UUID."""
        return Column(
            UUID(as_uuid=True),
            primary_key=True,
            default=uuid4,
            comment="Unique identifier"
        )

    @declared_attr
    def created_at(cls):
        """Timestamp when record was created."""
        return Column(
            DateTime(timezone=True),
            server_default=func.now(),
            nullable=False,
            index=True,
            comment="Creation timestamp"
        )

    @declared_attr
    def updated_at(cls):
        """Timestamp when record was last updated."""
        return Column(
            DateTime(timezone=True),
            server_default=func.now(),
            onupdate=func.now(),
            nullable=False,
            comment="Last update timestamp"
        )

    @declared_attr
    def __table_args__(cls):
        """Add indexes for common queries on tenant tables."""
        return (
            Index(
                f"idx_{cls.__tablename__}_tenant_created",
                cls.tenant_id,
                "created_at",
                postgresql_using="btree"
            ),
        )


class BaseAuditModel(BaseTenantModel):
    """
    Base model for audit and immutable log tables.
    Extends BaseTenantModel with audit-specific fields.
    """

    @declared_attr
    def created_by_user_id(cls):
        """User ID who created this record."""
        return Column(
            UUID(as_uuid=True),
            nullable=True,
            comment="User who created this record"
        )

    @declared_attr
    def ip_address(cls):
        """IP address of the request that created this record."""
        return Column(
            String(45),  # Supports IPv6
            nullable=True,
            comment="Client IP address"
        )

    @declared_attr
    def user_agent(cls):
        """User agent string from the request."""
        return Column(
            String(500),
            nullable=True,
            comment="Client user agent"
        )

    @declared_attr
    def __table_args__(cls):
        """Add audit-specific indexes."""
        return (
            Index(
                f"idx_{cls.__tablename__}_tenant_created",
                cls.tenant_id,
                "created_at",
                postgresql_using="btree"
            ),
            Index(
                f"idx_{cls.__tablename__}_user",
                cls.created_by_user_id,
                postgresql_using="btree"
            ),
        )


class TimeStampMixin:
    """Mixin for adding timestamp fields to models."""

    @declared_attr
    def created_at(cls):
        """Timestamp when record was created."""
        return Column(
            DateTime(timezone=True),
            server_default=func.now(),
            nullable=False,
            index=True
        )

    @declared_attr
    def updated_at(cls):
        """Timestamp when record was last updated."""
        return Column(
            DateTime(timezone=True),
            server_default=func.now(),
            onupdate=func.now(),
            nullable=False,
            index=True
        )
