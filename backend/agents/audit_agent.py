"""
AuditAgent - Comprehensive Logging and Cost Tracking
Manages immutable audit logs for compliance, cost tracking, and traceability.

CRITICAL: All operations must be logged for PT2030 compliance (10-year retention).
Tracks Claude API costs, storage costs, and compute time per EVF project.
"""

from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import UUID
import hashlib
import json
import logging
from enum import Enum

from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select, func, and_, or_, desc, cast, String
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.evf import AuditLog, EVFProject
from ..core.config import settings

logger = logging.getLogger(__name__)


class AgentType(str, Enum):
    """Types of agents in the system."""
    INPUT_AGENT = "input_agent"
    COMPLIANCE_AGENT = "compliance_agent"
    FINANCIAL_AGENT = "financial_agent"
    NARRATIVE_AGENT = "narrative_agent"
    AUDIT_AGENT = "audit_agent"
    ORCHESTRATOR = "orchestrator"


class OperationStatus(str, Enum):
    """Status of logged operations."""
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    IN_PROGRESS = "in_progress"


class ResourceType(str, Enum):
    """Types of resources in the system."""
    EVF_PROJECT = "evf_project"
    FINANCIAL_MODEL = "financial_model"
    FILE_UPLOAD = "file_upload"
    COMPLIANCE_CHECK = "compliance_check"
    NARRATIVE_GENERATION = "narrative_generation"
    USER = "user"
    TENANT = "tenant"


# Pydantic Models for Request/Response

class AuditLogCreate(BaseModel):
    """Request model for creating audit log entries."""
    action: str = Field(..., max_length=100, description="Operation performed")
    resource_type: str = Field(..., max_length=50, description="Type of resource")
    resource_id: Optional[UUID] = Field(None, description="ID of affected resource")
    tenant_id: UUID = Field(..., description="Tenant ID for multi-tenant isolation")
    user_id: Optional[UUID] = Field(None, description="User who triggered action")
    agent_name: Optional[str] = Field(None, max_length=50, description="Agent that performed action")

    # Request/Response metadata
    input_hash: Optional[str] = Field(None, max_length=64, description="SHA-256 hash of input")
    output_hash: Optional[str] = Field(None, max_length=64, description="SHA-256 hash of output")
    input_size_bytes: Optional[int] = Field(None, ge=0, description="Size of input data")
    output_size_bytes: Optional[int] = Field(None, ge=0, description="Size of output data")

    # Cost tracking
    tokens_used: int = Field(default=0, ge=0, description="Claude tokens consumed")
    cost_euros: Decimal = Field(default=Decimal("0"), ge=0, description="Cost in EUR")

    # Client information
    ip_address: Optional[str] = Field(None, max_length=45, description="Client IP")
    user_agent: Optional[str] = Field(None, max_length=500, description="Client user agent")

    # Request details
    request_method: Optional[str] = Field(None, max_length=10, description="HTTP method")
    request_path: Optional[str] = Field(None, max_length=500, description="API endpoint")
    request_duration_ms: Optional[int] = Field(None, ge=0, description="Processing time in ms")

    # Project association
    project_id: Optional[UUID] = Field(None, description="Related EVF project")

    # Status and errors
    status: str = Field(default="success", description="Operation status")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    error_stacktrace: Optional[str] = Field(None, description="Stack trace if failed")

    # Additional metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Custom metadata")


class AuditLogResponse(BaseModel):
    """Response model for audit log entries."""
    id: UUID
    action: str
    resource_type: str
    resource_id: Optional[UUID]
    tenant_id: UUID
    user_id: Optional[UUID]
    agent_name: Optional[str]

    input_hash: Optional[str]
    output_hash: Optional[str]
    tokens_used: int
    cost_euros: Decimal

    status: str
    error_message: Optional[str]

    request_method: Optional[str]
    request_path: Optional[str]
    request_duration_ms: Optional[int]

    project_id: Optional[UUID]
    metadata: Dict[str, Any]
    created_at: datetime

    class Config:
        from_attributes = True


class ProjectCost(BaseModel):
    """Cost breakdown for an EVF project."""
    project_id: UUID
    project_name: str
    tenant_id: UUID

    # Token and API costs
    total_tokens_used: int = Field(default=0, description="Total Claude tokens")
    total_api_cost_euros: Decimal = Field(default=Decimal("0"), description="Total Claude API cost")

    # Operation breakdown
    operation_count: int = Field(default=0, description="Total operations")
    successful_operations: int = Field(default=0, description="Successful operations")
    failed_operations: int = Field(default=0, description="Failed operations")

    # Agent breakdown
    agent_costs: Dict[str, Decimal] = Field(default_factory=dict, description="Cost per agent")
    agent_tokens: Dict[str, int] = Field(default_factory=dict, description="Tokens per agent")

    # Time breakdown
    total_processing_time_ms: int = Field(default=0, description="Total processing time")
    average_operation_time_ms: float = Field(default=0, description="Average operation time")

    # Storage costs (estimated)
    input_data_size_bytes: int = Field(default=0, description="Total input data size")
    output_data_size_bytes: int = Field(default=0, description="Total output data size")
    estimated_storage_cost_euros: Decimal = Field(default=Decimal("0"), description="Estimated storage cost")

    # Total cost
    total_cost_euros: Decimal = Field(default=Decimal("0"), description="Total cost for project")

    # Timestamps
    first_operation: Optional[datetime] = None
    last_operation: Optional[datetime] = None


class AuditReport(BaseModel):
    """Comprehensive audit report for a tenant."""
    tenant_id: UUID
    start_date: datetime
    end_date: datetime
    generated_at: datetime = Field(default_factory=datetime.utcnow)

    # Overall statistics
    total_operations: int = Field(default=0, description="Total operations in period")
    total_projects: int = Field(default=0, description="Unique projects in period")
    total_users: int = Field(default=0, description="Unique users in period")

    # Cost summary
    total_api_cost_euros: Decimal = Field(default=Decimal("0"))
    total_storage_cost_euros: Decimal = Field(default=Decimal("0"))
    total_cost_euros: Decimal = Field(default=Decimal("0"))
    total_tokens_used: int = Field(default=0)

    # Operation breakdown
    operations_by_action: Dict[str, int] = Field(default_factory=dict)
    operations_by_agent: Dict[str, int] = Field(default_factory=dict)
    operations_by_status: Dict[str, int] = Field(default_factory=dict)

    # Cost breakdown
    cost_by_agent: Dict[str, Decimal] = Field(default_factory=dict)
    cost_by_project: Dict[str, Decimal] = Field(default_factory=dict)

    # Performance metrics
    average_operation_time_ms: float = Field(default=0)
    p95_operation_time_ms: Optional[float] = None
    p99_operation_time_ms: Optional[float] = None

    # Error summary
    total_errors: int = Field(default=0)
    errors_by_type: Dict[str, int] = Field(default_factory=dict)

    # Compliance metrics
    operations_with_audit_trail: int = Field(default=0, description="Operations with complete audit trail")
    compliance_percentage: Decimal = Field(default=Decimal("100"), description="% operations with audit trail")


class AuditAgent:
    """
    Agent responsible for comprehensive logging and cost tracking.

    Features:
    - Log every operation to database with full context
    - Track Claude API costs (tokens and EUR)
    - Track storage and compute costs
    - Calculate total EVF processing cost
    - Generate audit reports for compliance
    - Support 10-year retention requirement

    All operations are immutable and stored permanently for compliance.
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize AuditAgent with database session.

        Args:
            db: Async SQLAlchemy database session
        """
        self.db = db
        self.agent_name = AgentType.AUDIT_AGENT.value

        # Claude API pricing (EUR per 1M tokens) - Sonnet 4.5 pricing
        self.claude_input_token_cost = Decimal("0.003")  # €3 per 1M input tokens
        self.claude_output_token_cost = Decimal("0.015")  # €15 per 1M output tokens
        # Use average for simplicity when input/output split not available
        self.claude_avg_token_cost = Decimal("0.009")  # €9 per 1M tokens average

        # Storage costs (S3-like pricing: €0.023 per GB-month)
        self.storage_cost_per_gb_month = Decimal("0.023")

    async def log_operation(
        self,
        action: str,
        resource_type: str,
        resource_id: Optional[UUID],
        tenant_id: UUID,
        user_id: Optional[UUID] = None,
        agent_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        tokens_used: int = 0,
        cost_euros: Optional[Decimal] = None,
        input_data: Optional[Union[str, bytes, Dict]] = None,
        output_data: Optional[Union[str, bytes, Dict]] = None,
        project_id: Optional[UUID] = None,
        status: str = OperationStatus.SUCCESS.value,
        error_message: Optional[str] = None,
        error_stacktrace: Optional[str] = None,
        request_method: Optional[str] = None,
        request_path: Optional[str] = None,
        request_duration_ms: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditLog:
        """
        Log an operation to the audit trail.

        Args:
            action: Operation performed (e.g., 'upload_file', 'calculate_valf')
            resource_type: Type of resource (e.g., 'evf_project', 'financial_model')
            resource_id: ID of affected resource
            tenant_id: Tenant ID for multi-tenant isolation
            user_id: User who triggered the action
            agent_name: Name of agent that performed action
            metadata: Additional contextual data
            tokens_used: Claude tokens consumed (if applicable)
            cost_euros: Cost in EUR (auto-calculated if None)
            input_data: Input data for hashing
            output_data: Output data for hashing
            project_id: Related EVF project ID
            status: Operation status (success, error, warning)
            error_message: Error message if operation failed
            error_stacktrace: Stack trace if operation failed
            request_method: HTTP method
            request_path: API endpoint path
            request_duration_ms: Request processing time
            ip_address: Client IP address
            user_agent: Client user agent

        Returns:
            Created AuditLog entry
        """
        try:
            # Calculate hashes if data provided
            input_hash = None
            input_size_bytes = None
            if input_data is not None:
                input_hash, input_size_bytes = self._hash_data(input_data)

            output_hash = None
            output_size_bytes = None
            if output_data is not None:
                output_hash, output_size_bytes = self._hash_data(output_data)

            # Calculate cost if not provided
            if cost_euros is None and tokens_used > 0:
                cost_euros = self._calculate_token_cost(tokens_used)
            elif cost_euros is None:
                cost_euros = Decimal("0")

            # Create audit log entry
            audit_log = AuditLog(
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                tenant_id=tenant_id,
                user_id=user_id,
                agent_name=agent_name or self.agent_name,
                input_hash=input_hash,
                output_hash=output_hash,
                input_size_bytes=input_size_bytes,
                output_size_bytes=output_size_bytes,
                tokens_used=tokens_used,
                cost_euros=cost_euros,
                ip_address=ip_address,
                user_agent=user_agent,
                request_method=request_method,
                request_path=request_path,
                request_duration_ms=request_duration_ms,
                project_id=project_id,
                status=status,
                error_message=error_message,
                error_stacktrace=error_stacktrace,
                custom_metadata=metadata or {},
            )

            self.db.add(audit_log)
            await self.db.commit()
            await self.db.refresh(audit_log)

            logger.info(
                f"Logged operation: {action} for {resource_type}:{resource_id} "
                f"by {agent_name or 'system'} (status: {status}, cost: €{cost_euros})"
            )

            return audit_log

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to log operation: {e}", exc_info=True)
            raise

    async def get_project_audit_trail(
        self,
        project_id: UUID,
        tenant_id: UUID,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> List[AuditLog]:
        """
        Get complete audit trail for a project.

        Args:
            project_id: EVF project ID
            tenant_id: Tenant ID for security
            limit: Maximum number of records to return
            offset: Offset for pagination

        Returns:
            List of audit log entries ordered by creation time
        """
        try:
            query = (
                select(AuditLog)
                .where(
                    and_(
                        AuditLog.project_id == project_id,
                        AuditLog.tenant_id == tenant_id,
                    )
                )
                .order_by(desc(AuditLog.created_at))
            )

            if limit:
                query = query.limit(limit).offset(offset)

            result = await self.db.execute(query)
            logs = result.scalars().all()

            logger.info(f"Retrieved {len(logs)} audit logs for project {project_id}")
            return list(logs)

        except Exception as e:
            logger.error(f"Failed to get project audit trail: {e}", exc_info=True)
            raise

    async def get_logs_by_criteria(
        self,
        tenant_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        action: Optional[str] = None,
        agent_name: Optional[str] = None,
        resource_type: Optional[str] = None,
        status: Optional[str] = None,
        user_id: Optional[UUID] = None,
        limit: Optional[int] = 1000,
        offset: int = 0,
    ) -> List[AuditLog]:
        """
        Query audit logs by various criteria.

        Args:
            tenant_id: Tenant ID for security
            start_date: Filter logs after this date
            end_date: Filter logs before this date
            action: Filter by action
            agent_name: Filter by agent
            resource_type: Filter by resource type
            status: Filter by status
            user_id: Filter by user
            limit: Maximum records to return
            offset: Offset for pagination

        Returns:
            List of matching audit log entries
        """
        try:
            # Build query with filters
            conditions = [AuditLog.tenant_id == tenant_id]

            if start_date:
                conditions.append(AuditLog.created_at >= start_date)
            if end_date:
                conditions.append(AuditLog.created_at <= end_date)
            if action:
                conditions.append(AuditLog.action == action)
            if agent_name:
                conditions.append(AuditLog.agent_name == agent_name)
            if resource_type:
                conditions.append(AuditLog.resource_type == resource_type)
            if status:
                conditions.append(AuditLog.status == status)
            if user_id:
                conditions.append(AuditLog.user_id == user_id)

            query = (
                select(AuditLog)
                .where(and_(*conditions))
                .order_by(desc(AuditLog.created_at))
                .limit(limit)
                .offset(offset)
            )

            result = await self.db.execute(query)
            logs = result.scalars().all()

            logger.info(f"Retrieved {len(logs)} audit logs matching criteria")
            return list(logs)

        except Exception as e:
            logger.error(f"Failed to get logs by criteria: {e}", exc_info=True)
            raise

    async def calculate_project_cost(
        self,
        project_id: UUID,
        tenant_id: UUID,
    ) -> ProjectCost:
        """
        Calculate comprehensive cost breakdown for an EVF project.

        Args:
            project_id: EVF project ID
            tenant_id: Tenant ID for security

        Returns:
            ProjectCost with detailed breakdown
        """
        try:
            # Get project details
            project_result = await self.db.execute(
                select(EVFProject).where(
                    and_(
                        EVFProject.id == project_id,
                        EVFProject.tenant_id == tenant_id,
                    )
                )
            )
            project = project_result.scalar_one_or_none()

            if not project:
                raise ValueError(f"Project {project_id} not found for tenant {tenant_id}")

            # Get all audit logs for this project
            logs = await self.get_project_audit_trail(project_id, tenant_id)

            # Initialize cost breakdown
            cost = ProjectCost(
                project_id=project_id,
                project_name=project.name,
                tenant_id=tenant_id,
            )

            # Aggregate metrics
            agent_costs = {}
            agent_tokens = {}

            for log in logs:
                # Count operations
                cost.operation_count += 1
                if log.status == OperationStatus.SUCCESS.value:
                    cost.successful_operations += 1
                elif log.status == OperationStatus.ERROR.value:
                    cost.failed_operations += 1

                # Aggregate costs
                cost.total_tokens_used += log.tokens_used
                cost.total_api_cost_euros += log.cost_euros

                # Agent breakdown
                if log.agent_name:
                    agent_costs[log.agent_name] = (
                        agent_costs.get(log.agent_name, Decimal("0")) + log.cost_euros
                    )
                    agent_tokens[log.agent_name] = (
                        agent_tokens.get(log.agent_name, 0) + log.tokens_used
                    )

                # Time tracking
                if log.request_duration_ms:
                    cost.total_processing_time_ms += log.request_duration_ms

                # Data size tracking
                if log.input_size_bytes:
                    cost.input_data_size_bytes += log.input_size_bytes
                if log.output_size_bytes:
                    cost.output_data_size_bytes += log.output_size_bytes

                # Track time range
                if cost.first_operation is None or log.created_at < cost.first_operation:
                    cost.first_operation = log.created_at
                if cost.last_operation is None or log.created_at > cost.last_operation:
                    cost.last_operation = log.created_at

            # Calculate averages
            if cost.operation_count > 0:
                cost.average_operation_time_ms = (
                    cost.total_processing_time_ms / cost.operation_count
                )

            # Estimate storage costs
            total_data_gb = (
                cost.input_data_size_bytes + cost.output_data_size_bytes
            ) / (1024 ** 3)

            # Estimate for 1 month retention (actual is 10 years, but calculated monthly)
            cost.estimated_storage_cost_euros = (
                Decimal(str(total_data_gb)) * self.storage_cost_per_gb_month
            )

            # Total cost
            cost.total_cost_euros = (
                cost.total_api_cost_euros + cost.estimated_storage_cost_euros
            )

            # Set agent breakdowns
            cost.agent_costs = agent_costs
            cost.agent_tokens = agent_tokens

            logger.info(
                f"Calculated cost for project {project_id}: "
                f"€{cost.total_cost_euros} ({cost.operation_count} operations)"
            )

            return cost

        except Exception as e:
            logger.error(f"Failed to calculate project cost: {e}", exc_info=True)
            raise

    async def generate_audit_report(
        self,
        tenant_id: UUID,
        start_date: datetime,
        end_date: datetime,
    ) -> AuditReport:
        """
        Generate comprehensive audit report for a tenant.

        Args:
            tenant_id: Tenant ID
            start_date: Report start date
            end_date: Report end date

        Returns:
            AuditReport with comprehensive statistics
        """
        try:
            # Get all logs in date range
            logs = await self.get_logs_by_criteria(
                tenant_id=tenant_id,
                start_date=start_date,
                end_date=end_date,
                limit=None,  # Get all logs
            )

            # Initialize report
            report = AuditReport(
                tenant_id=tenant_id,
                start_date=start_date,
                end_date=end_date,
            )

            # Track unique entities
            unique_projects = set()
            unique_users = set()
            operation_times = []

            # Aggregate metrics
            for log in logs:
                # Count operations
                report.total_operations += 1

                # Track unique entities
                if log.project_id:
                    unique_projects.add(log.project_id)
                if log.user_id:
                    unique_users.add(log.user_id)

                # Cost aggregation
                report.total_tokens_used += log.tokens_used
                report.total_api_cost_euros += log.cost_euros

                # Operation breakdown by action
                report.operations_by_action[log.action] = (
                    report.operations_by_action.get(log.action, 0) + 1
                )

                # Operation breakdown by agent
                if log.agent_name:
                    report.operations_by_agent[log.agent_name] = (
                        report.operations_by_agent.get(log.agent_name, 0) + 1
                    )

                    # Cost by agent
                    report.cost_by_agent[log.agent_name] = (
                        report.cost_by_agent.get(log.agent_name, Decimal("0")) + log.cost_euros
                    )

                # Operation breakdown by status
                report.operations_by_status[log.status] = (
                    report.operations_by_status.get(log.status, 0) + 1
                )

                # Cost by project
                if log.project_id:
                    project_id_str = str(log.project_id)
                    report.cost_by_project[project_id_str] = (
                        report.cost_by_project.get(project_id_str, Decimal("0")) + log.cost_euros
                    )

                # Error tracking
                if log.status == OperationStatus.ERROR.value:
                    report.total_errors += 1
                    error_type = log.error_message or "unknown_error"
                    # Use first 50 chars of error message as type
                    error_type = error_type[:50]
                    report.errors_by_type[error_type] = (
                        report.errors_by_type.get(error_type, 0) + 1
                    )

                # Performance tracking
                if log.request_duration_ms:
                    operation_times.append(log.request_duration_ms)

                # Compliance tracking (logs with complete audit trail)
                if log.input_hash and log.output_hash:
                    report.operations_with_audit_trail += 1

            # Set unique counts
            report.total_projects = len(unique_projects)
            report.total_users = len(unique_users)

            # Calculate performance percentiles
            if operation_times:
                operation_times.sort()
                report.average_operation_time_ms = sum(operation_times) / len(operation_times)

                p95_idx = int(len(operation_times) * 0.95)
                p99_idx = int(len(operation_times) * 0.99)
                report.p95_operation_time_ms = float(operation_times[min(p95_idx, len(operation_times) - 1)])
                report.p99_operation_time_ms = float(operation_times[min(p99_idx, len(operation_times) - 1)])

            # Calculate compliance percentage
            if report.total_operations > 0:
                report.compliance_percentage = Decimal(
                    str(report.operations_with_audit_trail / report.total_operations * 100)
                ).quantize(Decimal("0.01"))

            # Estimate storage costs
            total_storage_query = await self.db.execute(
                select(
                    func.sum(AuditLog.input_size_bytes),
                    func.sum(AuditLog.output_size_bytes)
                ).where(
                    and_(
                        AuditLog.tenant_id == tenant_id,
                        AuditLog.created_at >= start_date,
                        AuditLog.created_at <= end_date,
                    )
                )
            )
            input_bytes, output_bytes = total_storage_query.one()
            input_bytes = input_bytes or 0
            output_bytes = output_bytes or 0

            total_gb = (input_bytes + output_bytes) / (1024 ** 3)
            report.total_storage_cost_euros = (
                Decimal(str(total_gb)) * self.storage_cost_per_gb_month
            )

            # Total cost
            report.total_cost_euros = (
                report.total_api_cost_euros + report.total_storage_cost_euros
            )

            logger.info(
                f"Generated audit report for tenant {tenant_id}: "
                f"{report.total_operations} operations, €{report.total_cost_euros} total cost"
            )

            return report

        except Exception as e:
            logger.error(f"Failed to generate audit report: {e}", exc_info=True)
            raise

    async def get_daily_cost_summary(
        self,
        tenant_id: UUID,
        date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Get daily cost summary for rate limiting and alerts.

        Args:
            tenant_id: Tenant ID
            date: Date to check (defaults to today)

        Returns:
            Dictionary with daily costs and usage
        """
        try:
            if date is None:
                date = datetime.utcnow()

            start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = start_of_day + timedelta(days=1)

            # Query daily aggregates
            result = await self.db.execute(
                select(
                    func.sum(AuditLog.cost_euros).label("total_cost"),
                    func.sum(AuditLog.tokens_used).label("total_tokens"),
                    func.count(AuditLog.id).label("operation_count"),
                ).where(
                    and_(
                        AuditLog.tenant_id == tenant_id,
                        AuditLog.created_at >= start_of_day,
                        AuditLog.created_at < end_of_day,
                    )
                )
            )
            row = result.one()

            total_cost = row.total_cost or Decimal("0")
            total_tokens = row.total_tokens or 0
            operation_count = row.operation_count or 0

            # Check against limits
            daily_limit_euros = settings.claude_daily_limit_euros
            limit_percentage = float(total_cost / Decimal(str(daily_limit_euros)) * 100) if daily_limit_euros > 0 else 0

            summary = {
                "date": date.date(),
                "tenant_id": str(tenant_id),
                "total_cost_euros": float(total_cost),
                "total_tokens": total_tokens,
                "operation_count": operation_count,
                "daily_limit_euros": daily_limit_euros,
                "limit_percentage": limit_percentage,
                "limit_exceeded": total_cost >= Decimal(str(daily_limit_euros)),
            }

            logger.info(f"Daily cost summary for tenant {tenant_id}: €{total_cost} ({limit_percentage:.1f}% of limit)")

            return summary

        except Exception as e:
            logger.error(f"Failed to get daily cost summary: {e}", exc_info=True)
            raise

    def _hash_data(self, data: Union[str, bytes, Dict]) -> tuple[str, int]:
        """
        Generate SHA-256 hash and size of data.

        Args:
            data: Data to hash (string, bytes, or dict)

        Returns:
            Tuple of (hash_string, size_in_bytes)
        """
        if isinstance(data, dict):
            # Sort keys for consistent hashing
            data_str = json.dumps(data, sort_keys=True)
            data_bytes = data_str.encode("utf-8")
        elif isinstance(data, str):
            data_bytes = data.encode("utf-8")
        else:
            data_bytes = data

        hash_value = hashlib.sha256(data_bytes).hexdigest()
        size_bytes = len(data_bytes)

        return hash_value, size_bytes

    def _calculate_token_cost(self, tokens: int) -> Decimal:
        """
        Calculate cost in EUR for Claude tokens.

        Args:
            tokens: Number of tokens used

        Returns:
            Cost in EUR
        """
        # Convert to millions of tokens
        tokens_millions = Decimal(str(tokens)) / Decimal("1000000")

        # Calculate cost using average price
        cost = tokens_millions * self.claude_avg_token_cost

        # Round to 4 decimal places
        return cost.quantize(Decimal("0.0001"))
