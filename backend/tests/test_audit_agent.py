"""
Comprehensive tests for AuditAgent.
Tests audit logging, cost tracking, and report generation.
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from backend.models.base import Base
from backend.models.evf import AuditLog, EVFProject, EVFStatus, FundType
from backend.models.tenant import Tenant
from backend.models.user import User
from backend.agents.audit_agent import (
    AuditAgent,
    AgentType,
    OperationStatus,
    ResourceType,
    AuditLogCreate,
    ProjectCost,
    AuditReport,
)


# Test database setup

@pytest.fixture
async def db_engine():
    """Create in-memory test database engine."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session."""
    async_session_maker = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_maker() as session:
        yield session


@pytest.fixture
async def test_tenant(db_session: AsyncSession) -> Tenant:
    """Create test tenant."""
    tenant = Tenant(
        id=uuid4(),
        name="Test Company Ltd",
        slug="test-company",
        contact_email="test@example.com",
        is_active=True,
    )
    db_session.add(tenant)
    await db_session.commit()
    await db_session.refresh(tenant)
    return tenant


@pytest.fixture
async def test_user(db_session: AsyncSession, test_tenant: Tenant) -> User:
    """Create test user."""
    user = User(
        id=uuid4(),
        email="user@example.com",
        hashed_password="hashed_password_here",
        full_name="Test User",
        tenant_id=test_tenant.id,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def test_project(db_session: AsyncSession, test_tenant: Tenant, test_user: User) -> EVFProject:
    """Create test EVF project."""
    project = EVFProject(
        id=uuid4(),
        tenant_id=test_tenant.id,
        name="Test EVF Project",
        description="Test project for audit",
        fund_type=FundType.PT2030,
        status=EVFStatus.DRAFT,
        created_by=test_user.id,
        project_duration_years=5,
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    return project


@pytest.fixture
def audit_agent(db_session: AsyncSession) -> AuditAgent:
    """Create AuditAgent instance."""
    return AuditAgent(db=db_session)


# Test Cases

class TestAuditAgentBasicLogging:
    """Test basic audit logging functionality."""

    @pytest.mark.asyncio
    async def test_log_simple_operation(
        self,
        audit_agent: AuditAgent,
        test_tenant: Tenant,
        test_user: User,
    ):
        """Test logging a simple operation."""
        log = await audit_agent.log_operation(
            action="test_action",
            resource_type=ResourceType.EVF_PROJECT.value,
            resource_id=uuid4(),
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            agent_name=AgentType.INPUT_AGENT.value,
        )

        assert log.id is not None
        assert log.action == "test_action"
        assert log.resource_type == ResourceType.EVF_PROJECT.value
        assert log.tenant_id == test_tenant.id
        assert log.user_id == test_user.id
        assert log.agent_name == AgentType.INPUT_AGENT.value
        assert log.status == OperationStatus.SUCCESS.value
        assert log.tokens_used == 0
        assert log.cost_euros == Decimal("0")
        assert log.created_at is not None

    @pytest.mark.asyncio
    async def test_log_operation_with_data_hashing(
        self,
        audit_agent: AuditAgent,
        test_tenant: Tenant,
        test_project: EVFProject,
    ):
        """Test logging with input/output data hashing."""
        input_data = {"company_name": "Test Company", "revenue": 100000}
        output_data = {"valf": -50000, "trf": 3.5}

        log = await audit_agent.log_operation(
            action="calculate_financial_model",
            resource_type=ResourceType.FINANCIAL_MODEL.value,
            resource_id=uuid4(),
            tenant_id=test_tenant.id,
            agent_name=AgentType.FINANCIAL_AGENT.value,
            project_id=test_project.id,
            input_data=input_data,
            output_data=output_data,
        )

        assert log.input_hash is not None
        assert len(log.input_hash) == 64  # SHA-256 hex digest
        assert log.output_hash is not None
        assert len(log.output_hash) == 64
        assert log.input_size_bytes > 0
        assert log.output_size_bytes > 0

        # Verify hash consistency
        hash1, _ = audit_agent._hash_data(input_data)
        hash2, _ = audit_agent._hash_data(input_data)
        assert hash1 == hash2  # Hashing should be deterministic

    @pytest.mark.asyncio
    async def test_log_operation_with_tokens_and_cost(
        self,
        audit_agent: AuditAgent,
        test_tenant: Tenant,
    ):
        """Test logging with token usage and cost calculation."""
        tokens_used = 10000  # 10k tokens

        log = await audit_agent.log_operation(
            action="generate_narrative",
            resource_type=ResourceType.NARRATIVE_GENERATION.value,
            resource_id=uuid4(),
            tenant_id=test_tenant.id,
            agent_name=AgentType.NARRATIVE_AGENT.value,
            tokens_used=tokens_used,
        )

        assert log.tokens_used == tokens_used
        # Cost should be auto-calculated: 10k tokens = 0.01M tokens * €9 = €0.09
        expected_cost = Decimal("0.09")
        assert log.cost_euros == expected_cost

    @pytest.mark.asyncio
    async def test_log_operation_with_custom_cost(
        self,
        audit_agent: AuditAgent,
        test_tenant: Tenant,
    ):
        """Test logging with custom cost override."""
        custom_cost = Decimal("1.50")

        log = await audit_agent.log_operation(
            action="custom_operation",
            resource_type=ResourceType.EVF_PROJECT.value,
            resource_id=uuid4(),
            tenant_id=test_tenant.id,
            cost_euros=custom_cost,
        )

        assert log.cost_euros == custom_cost

    @pytest.mark.asyncio
    async def test_log_error_operation(
        self,
        audit_agent: AuditAgent,
        test_tenant: Tenant,
    ):
        """Test logging an error operation."""
        error_message = "Database connection failed"
        error_stacktrace = "Traceback (most recent call last):\n  File..."

        log = await audit_agent.log_operation(
            action="upload_file",
            resource_type=ResourceType.FILE_UPLOAD.value,
            resource_id=uuid4(),
            tenant_id=test_tenant.id,
            status=OperationStatus.ERROR.value,
            error_message=error_message,
            error_stacktrace=error_stacktrace,
        )

        assert log.status == OperationStatus.ERROR.value
        assert log.error_message == error_message
        assert log.error_stacktrace == error_stacktrace

    @pytest.mark.asyncio
    async def test_log_operation_with_metadata(
        self,
        audit_agent: AuditAgent,
        test_tenant: Tenant,
    ):
        """Test logging with custom metadata."""
        metadata = {
            "file_type": "SAF-T",
            "file_size_mb": 25,
            "processing_version": "1.0.0",
            "custom_fields": {"department": "finance"},
        }

        log = await audit_agent.log_operation(
            action="parse_saft",
            resource_type=ResourceType.FILE_UPLOAD.value,
            resource_id=uuid4(),
            tenant_id=test_tenant.id,
            metadata=metadata,
        )

        assert log.custom_metadata == metadata
        assert log.custom_metadata["file_type"] == "SAF-T"
        assert log.custom_metadata["custom_fields"]["department"] == "finance"

    @pytest.mark.asyncio
    async def test_log_operation_with_request_details(
        self,
        audit_agent: AuditAgent,
        test_tenant: Tenant,
        test_user: User,
    ):
        """Test logging with HTTP request details."""
        log = await audit_agent.log_operation(
            action="create_project",
            resource_type=ResourceType.EVF_PROJECT.value,
            resource_id=uuid4(),
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            request_method="POST",
            request_path="/api/v1/projects",
            request_duration_ms=1234,
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
        )

        assert log.request_method == "POST"
        assert log.request_path == "/api/v1/projects"
        assert log.request_duration_ms == 1234
        assert log.ip_address == "192.168.1.1"
        assert log.user_agent == "Mozilla/5.0"


class TestAuditAgentQueries:
    """Test audit log query functionality."""

    @pytest.mark.asyncio
    async def test_get_project_audit_trail(
        self,
        audit_agent: AuditAgent,
        test_tenant: Tenant,
        test_project: EVFProject,
    ):
        """Test retrieving complete audit trail for a project."""
        # Create multiple audit logs for the project
        for i in range(5):
            await audit_agent.log_operation(
                action=f"action_{i}",
                resource_type=ResourceType.EVF_PROJECT.value,
                resource_id=test_project.id,
                tenant_id=test_tenant.id,
                project_id=test_project.id,
                agent_name=AgentType.INPUT_AGENT.value,
            )

        # Create logs for a different project (should not be included)
        other_project_id = uuid4()
        await audit_agent.log_operation(
            action="other_action",
            resource_type=ResourceType.EVF_PROJECT.value,
            resource_id=other_project_id,
            tenant_id=test_tenant.id,
            project_id=other_project_id,
        )

        # Get audit trail
        logs = await audit_agent.get_project_audit_trail(
            project_id=test_project.id,
            tenant_id=test_tenant.id,
        )

        assert len(logs) == 5
        assert all(log.project_id == test_project.id for log in logs)
        # Should be ordered by creation time descending
        assert logs[0].action == "action_4"
        assert logs[-1].action == "action_0"

    @pytest.mark.asyncio
    async def test_get_project_audit_trail_with_pagination(
        self,
        audit_agent: AuditAgent,
        test_tenant: Tenant,
        test_project: EVFProject,
    ):
        """Test audit trail retrieval with pagination."""
        # Create 10 audit logs
        for i in range(10):
            await audit_agent.log_operation(
                action=f"action_{i}",
                resource_type=ResourceType.EVF_PROJECT.value,
                resource_id=test_project.id,
                tenant_id=test_tenant.id,
                project_id=test_project.id,
            )

        # Get first page (3 items)
        page1 = await audit_agent.get_project_audit_trail(
            project_id=test_project.id,
            tenant_id=test_tenant.id,
            limit=3,
            offset=0,
        )

        # Get second page (3 items)
        page2 = await audit_agent.get_project_audit_trail(
            project_id=test_project.id,
            tenant_id=test_tenant.id,
            limit=3,
            offset=3,
        )

        assert len(page1) == 3
        assert len(page2) == 3
        # Pages should not overlap
        assert page1[0].id != page2[0].id

    @pytest.mark.asyncio
    async def test_get_logs_by_criteria_date_range(
        self,
        audit_agent: AuditAgent,
        test_tenant: Tenant,
    ):
        """Test querying logs by date range."""
        now = datetime.utcnow()
        yesterday = now - timedelta(days=1)
        tomorrow = now + timedelta(days=1)

        # Create log from "yesterday"
        await audit_agent.log_operation(
            action="old_action",
            resource_type=ResourceType.EVF_PROJECT.value,
            resource_id=uuid4(),
            tenant_id=test_tenant.id,
        )

        # Manually update created_at to yesterday (SQLite doesn't support server_default well)
        await audit_agent.db.execute(
            f"UPDATE audit_log SET created_at = '{yesterday.isoformat()}' WHERE action = 'old_action'"
        )
        await audit_agent.db.commit()

        # Create log from "today"
        await audit_agent.log_operation(
            action="new_action",
            resource_type=ResourceType.EVF_PROJECT.value,
            resource_id=uuid4(),
            tenant_id=test_tenant.id,
        )

        # Query logs from today only
        logs = await audit_agent.get_logs_by_criteria(
            tenant_id=test_tenant.id,
            start_date=now - timedelta(hours=1),
            end_date=tomorrow,
        )

        assert len(logs) == 1
        assert logs[0].action == "new_action"

    @pytest.mark.asyncio
    async def test_get_logs_by_criteria_action_filter(
        self,
        audit_agent: AuditAgent,
        test_tenant: Tenant,
    ):
        """Test querying logs by action."""
        # Create logs with different actions
        await audit_agent.log_operation(
            action="upload_file",
            resource_type=ResourceType.FILE_UPLOAD.value,
            resource_id=uuid4(),
            tenant_id=test_tenant.id,
        )
        await audit_agent.log_operation(
            action="calculate_valf",
            resource_type=ResourceType.FINANCIAL_MODEL.value,
            resource_id=uuid4(),
            tenant_id=test_tenant.id,
        )
        await audit_agent.log_operation(
            action="upload_file",
            resource_type=ResourceType.FILE_UPLOAD.value,
            resource_id=uuid4(),
            tenant_id=test_tenant.id,
        )

        # Query only upload_file actions
        logs = await audit_agent.get_logs_by_criteria(
            tenant_id=test_tenant.id,
            action="upload_file",
        )

        assert len(logs) == 2
        assert all(log.action == "upload_file" for log in logs)

    @pytest.mark.asyncio
    async def test_get_logs_by_criteria_agent_filter(
        self,
        audit_agent: AuditAgent,
        test_tenant: Tenant,
    ):
        """Test querying logs by agent name."""
        # Create logs from different agents
        await audit_agent.log_operation(
            action="action1",
            resource_type=ResourceType.EVF_PROJECT.value,
            resource_id=uuid4(),
            tenant_id=test_tenant.id,
            agent_name=AgentType.INPUT_AGENT.value,
        )
        await audit_agent.log_operation(
            action="action2",
            resource_type=ResourceType.FINANCIAL_MODEL.value,
            resource_id=uuid4(),
            tenant_id=test_tenant.id,
            agent_name=AgentType.FINANCIAL_AGENT.value,
        )
        await audit_agent.log_operation(
            action="action3",
            resource_type=ResourceType.EVF_PROJECT.value,
            resource_id=uuid4(),
            tenant_id=test_tenant.id,
            agent_name=AgentType.INPUT_AGENT.value,
        )

        # Query only input_agent logs
        logs = await audit_agent.get_logs_by_criteria(
            tenant_id=test_tenant.id,
            agent_name=AgentType.INPUT_AGENT.value,
        )

        assert len(logs) == 2
        assert all(log.agent_name == AgentType.INPUT_AGENT.value for log in logs)

    @pytest.mark.asyncio
    async def test_get_logs_by_criteria_status_filter(
        self,
        audit_agent: AuditAgent,
        test_tenant: Tenant,
    ):
        """Test querying logs by status."""
        # Create logs with different statuses
        await audit_agent.log_operation(
            action="success_action",
            resource_type=ResourceType.EVF_PROJECT.value,
            resource_id=uuid4(),
            tenant_id=test_tenant.id,
            status=OperationStatus.SUCCESS.value,
        )
        await audit_agent.log_operation(
            action="error_action",
            resource_type=ResourceType.EVF_PROJECT.value,
            resource_id=uuid4(),
            tenant_id=test_tenant.id,
            status=OperationStatus.ERROR.value,
        )

        # Query only error logs
        logs = await audit_agent.get_logs_by_criteria(
            tenant_id=test_tenant.id,
            status=OperationStatus.ERROR.value,
        )

        assert len(logs) == 1
        assert logs[0].action == "error_action"

    @pytest.mark.asyncio
    async def test_get_logs_multi_tenant_isolation(
        self,
        audit_agent: AuditAgent,
        test_tenant: Tenant,
        db_session: AsyncSession,
    ):
        """Test that audit logs respect multi-tenant isolation."""
        # Create another tenant
        other_tenant = Tenant(
            id=uuid4(),
            name="Other Company",
            slug="other-company",
            contact_email="other@example.com",
            is_active=True,
        )
        db_session.add(other_tenant)
        await db_session.commit()

        # Create logs for both tenants
        await audit_agent.log_operation(
            action="tenant1_action",
            resource_type=ResourceType.EVF_PROJECT.value,
            resource_id=uuid4(),
            tenant_id=test_tenant.id,
        )
        await audit_agent.log_operation(
            action="tenant2_action",
            resource_type=ResourceType.EVF_PROJECT.value,
            resource_id=uuid4(),
            tenant_id=other_tenant.id,
        )

        # Query logs for test_tenant
        logs = await audit_agent.get_logs_by_criteria(
            tenant_id=test_tenant.id,
        )

        assert len(logs) == 1
        assert logs[0].action == "tenant1_action"
        assert logs[0].tenant_id == test_tenant.id


class TestAuditAgentCostCalculation:
    """Test cost calculation and tracking functionality."""

    @pytest.mark.asyncio
    async def test_calculate_project_cost_simple(
        self,
        audit_agent: AuditAgent,
        test_tenant: Tenant,
        test_project: EVFProject,
    ):
        """Test basic project cost calculation."""
        # Create audit logs with costs
        await audit_agent.log_operation(
            action="parse_saft",
            resource_type=ResourceType.FILE_UPLOAD.value,
            resource_id=uuid4(),
            tenant_id=test_tenant.id,
            project_id=test_project.id,
            tokens_used=5000,
        )
        await audit_agent.log_operation(
            action="calculate_valf",
            resource_type=ResourceType.FINANCIAL_MODEL.value,
            resource_id=uuid4(),
            tenant_id=test_tenant.id,
            project_id=test_project.id,
            tokens_used=0,
        )
        await audit_agent.log_operation(
            action="generate_narrative",
            resource_type=ResourceType.NARRATIVE_GENERATION.value,
            resource_id=uuid4(),
            tenant_id=test_tenant.id,
            project_id=test_project.id,
            tokens_used=15000,
        )

        # Calculate cost
        cost = await audit_agent.calculate_project_cost(
            project_id=test_project.id,
            tenant_id=test_tenant.id,
        )

        assert cost.project_id == test_project.id
        assert cost.project_name == test_project.name
        assert cost.operation_count == 3
        assert cost.successful_operations == 3
        assert cost.failed_operations == 0
        assert cost.total_tokens_used == 20000  # 5k + 0 + 15k
        # Cost: 0.02M tokens * €9 = €0.18
        assert cost.total_api_cost_euros == Decimal("0.18")

    @pytest.mark.asyncio
    async def test_calculate_project_cost_with_agent_breakdown(
        self,
        audit_agent: AuditAgent,
        test_tenant: Tenant,
        test_project: EVFProject,
    ):
        """Test project cost calculation with agent-level breakdown."""
        # Create logs from different agents
        await audit_agent.log_operation(
            action="parse_input",
            resource_type=ResourceType.FILE_UPLOAD.value,
            resource_id=uuid4(),
            tenant_id=test_tenant.id,
            project_id=test_project.id,
            agent_name=AgentType.INPUT_AGENT.value,
            tokens_used=10000,
        )
        await audit_agent.log_operation(
            action="generate_narrative",
            resource_type=ResourceType.NARRATIVE_GENERATION.value,
            resource_id=uuid4(),
            tenant_id=test_tenant.id,
            project_id=test_project.id,
            agent_name=AgentType.NARRATIVE_AGENT.value,
            tokens_used=20000,
        )

        # Calculate cost
        cost = await audit_agent.calculate_project_cost(
            project_id=test_project.id,
            tenant_id=test_tenant.id,
        )

        assert AgentType.INPUT_AGENT.value in cost.agent_tokens
        assert cost.agent_tokens[AgentType.INPUT_AGENT.value] == 10000
        assert AgentType.NARRATIVE_AGENT.value in cost.agent_tokens
        assert cost.agent_tokens[AgentType.NARRATIVE_AGENT.value] == 20000

        assert AgentType.INPUT_AGENT.value in cost.agent_costs
        assert cost.agent_costs[AgentType.INPUT_AGENT.value] == Decimal("0.09")
        assert AgentType.NARRATIVE_AGENT.value in cost.agent_costs
        assert cost.agent_costs[AgentType.NARRATIVE_AGENT.value] == Decimal("0.18")

    @pytest.mark.asyncio
    async def test_calculate_project_cost_with_failures(
        self,
        audit_agent: AuditAgent,
        test_tenant: Tenant,
        test_project: EVFProject,
    ):
        """Test cost calculation includes failed operations."""
        # Create successful and failed operations
        await audit_agent.log_operation(
            action="success_op",
            resource_type=ResourceType.EVF_PROJECT.value,
            resource_id=test_project.id,
            tenant_id=test_tenant.id,
            project_id=test_project.id,
            status=OperationStatus.SUCCESS.value,
        )
        await audit_agent.log_operation(
            action="failed_op",
            resource_type=ResourceType.EVF_PROJECT.value,
            resource_id=test_project.id,
            tenant_id=test_tenant.id,
            project_id=test_project.id,
            status=OperationStatus.ERROR.value,
            tokens_used=5000,  # Tokens consumed before error
        )

        # Calculate cost
        cost = await audit_agent.calculate_project_cost(
            project_id=test_project.id,
            tenant_id=test_tenant.id,
        )

        assert cost.operation_count == 2
        assert cost.successful_operations == 1
        assert cost.failed_operations == 1
        assert cost.total_tokens_used == 5000  # Failed operation still counts

    @pytest.mark.asyncio
    async def test_calculate_project_cost_with_processing_time(
        self,
        audit_agent: AuditAgent,
        test_tenant: Tenant,
        test_project: EVFProject,
    ):
        """Test cost calculation includes processing time metrics."""
        # Create operations with processing times
        await audit_agent.log_operation(
            action="op1",
            resource_type=ResourceType.EVF_PROJECT.value,
            resource_id=test_project.id,
            tenant_id=test_tenant.id,
            project_id=test_project.id,
            request_duration_ms=1000,
        )
        await audit_agent.log_operation(
            action="op2",
            resource_type=ResourceType.EVF_PROJECT.value,
            resource_id=test_project.id,
            tenant_id=test_tenant.id,
            project_id=test_project.id,
            request_duration_ms=2000,
        )

        # Calculate cost
        cost = await audit_agent.calculate_project_cost(
            project_id=test_project.id,
            tenant_id=test_tenant.id,
        )

        assert cost.total_processing_time_ms == 3000
        assert cost.average_operation_time_ms == 1500.0

    @pytest.mark.asyncio
    async def test_calculate_token_cost(self, audit_agent: AuditAgent):
        """Test token cost calculation method."""
        # 10,000 tokens
        cost1 = audit_agent._calculate_token_cost(10000)
        assert cost1 == Decimal("0.09")  # 0.01M * €9

        # 100,000 tokens
        cost2 = audit_agent._calculate_token_cost(100000)
        assert cost2 == Decimal("0.9")  # 0.1M * €9

        # 1,000,000 tokens
        cost3 = audit_agent._calculate_token_cost(1000000)
        assert cost3 == Decimal("9.0")  # 1M * €9

    @pytest.mark.asyncio
    async def test_project_cost_storage_estimation(
        self,
        audit_agent: AuditAgent,
        test_tenant: Tenant,
        test_project: EVFProject,
    ):
        """Test storage cost estimation in project cost."""
        # Create operation with large data
        large_input = "x" * 1024 * 1024 * 10  # 10 MB
        large_output = "y" * 1024 * 1024 * 5  # 5 MB

        await audit_agent.log_operation(
            action="process_large_file",
            resource_type=ResourceType.FILE_UPLOAD.value,
            resource_id=test_project.id,
            tenant_id=test_tenant.id,
            project_id=test_project.id,
            input_data=large_input,
            output_data=large_output,
        )

        # Calculate cost
        cost = await audit_agent.calculate_project_cost(
            project_id=test_project.id,
            tenant_id=test_tenant.id,
        )

        assert cost.input_data_size_bytes > 0
        assert cost.output_data_size_bytes > 0
        assert cost.estimated_storage_cost_euros > Decimal("0")


class TestAuditAgentReporting:
    """Test audit report generation functionality."""

    @pytest.mark.asyncio
    async def test_generate_audit_report_basic(
        self,
        audit_agent: AuditAgent,
        test_tenant: Tenant,
    ):
        """Test basic audit report generation."""
        start_date = datetime.utcnow() - timedelta(days=7)
        end_date = datetime.utcnow() + timedelta(days=1)

        # Create some audit logs
        for i in range(5):
            await audit_agent.log_operation(
                action=f"action_{i}",
                resource_type=ResourceType.EVF_PROJECT.value,
                resource_id=uuid4(),
                tenant_id=test_tenant.id,
                tokens_used=1000,
            )

        # Generate report
        report = await audit_agent.generate_audit_report(
            tenant_id=test_tenant.id,
            start_date=start_date,
            end_date=end_date,
        )

        assert report.tenant_id == test_tenant.id
        assert report.start_date == start_date
        assert report.end_date == end_date
        assert report.total_operations == 5
        assert report.total_tokens_used == 5000
        assert report.generated_at is not None

    @pytest.mark.asyncio
    async def test_generate_audit_report_operation_breakdown(
        self,
        audit_agent: AuditAgent,
        test_tenant: Tenant,
    ):
        """Test report includes operation breakdown by action and agent."""
        start_date = datetime.utcnow() - timedelta(days=1)
        end_date = datetime.utcnow() + timedelta(days=1)

        # Create logs with different actions
        await audit_agent.log_operation(
            action="upload_file",
            resource_type=ResourceType.FILE_UPLOAD.value,
            resource_id=uuid4(),
            tenant_id=test_tenant.id,
            agent_name=AgentType.INPUT_AGENT.value,
        )
        await audit_agent.log_operation(
            action="upload_file",
            resource_type=ResourceType.FILE_UPLOAD.value,
            resource_id=uuid4(),
            tenant_id=test_tenant.id,
            agent_name=AgentType.INPUT_AGENT.value,
        )
        await audit_agent.log_operation(
            action="calculate_valf",
            resource_type=ResourceType.FINANCIAL_MODEL.value,
            resource_id=uuid4(),
            tenant_id=test_tenant.id,
            agent_name=AgentType.FINANCIAL_AGENT.value,
        )

        # Generate report
        report = await audit_agent.generate_audit_report(
            tenant_id=test_tenant.id,
            start_date=start_date,
            end_date=end_date,
        )

        assert report.operations_by_action["upload_file"] == 2
        assert report.operations_by_action["calculate_valf"] == 1
        assert report.operations_by_agent[AgentType.INPUT_AGENT.value] == 2
        assert report.operations_by_agent[AgentType.FINANCIAL_AGENT.value] == 1

    @pytest.mark.asyncio
    async def test_generate_audit_report_cost_breakdown(
        self,
        audit_agent: AuditAgent,
        test_tenant: Tenant,
        test_project: EVFProject,
    ):
        """Test report includes cost breakdown by agent and project."""
        start_date = datetime.utcnow() - timedelta(days=1)
        end_date = datetime.utcnow() + timedelta(days=1)

        # Create logs with costs
        await audit_agent.log_operation(
            action="action1",
            resource_type=ResourceType.EVF_PROJECT.value,
            resource_id=test_project.id,
            tenant_id=test_tenant.id,
            project_id=test_project.id,
            agent_name=AgentType.INPUT_AGENT.value,
            tokens_used=10000,
        )
        await audit_agent.log_operation(
            action="action2",
            resource_type=ResourceType.FINANCIAL_MODEL.value,
            resource_id=uuid4(),
            tenant_id=test_tenant.id,
            project_id=test_project.id,
            agent_name=AgentType.NARRATIVE_AGENT.value,
            tokens_used=20000,
        )

        # Generate report
        report = await audit_agent.generate_audit_report(
            tenant_id=test_tenant.id,
            start_date=start_date,
            end_date=end_date,
        )

        assert AgentType.INPUT_AGENT.value in report.cost_by_agent
        assert report.cost_by_agent[AgentType.INPUT_AGENT.value] == Decimal("0.09")
        assert AgentType.NARRATIVE_AGENT.value in report.cost_by_agent
        assert report.cost_by_agent[AgentType.NARRATIVE_AGENT.value] == Decimal("0.18")

        assert str(test_project.id) in report.cost_by_project

    @pytest.mark.asyncio
    async def test_generate_audit_report_error_tracking(
        self,
        audit_agent: AuditAgent,
        test_tenant: Tenant,
    ):
        """Test report includes error tracking."""
        start_date = datetime.utcnow() - timedelta(days=1)
        end_date = datetime.utcnow() + timedelta(days=1)

        # Create successful and failed operations
        await audit_agent.log_operation(
            action="success",
            resource_type=ResourceType.EVF_PROJECT.value,
            resource_id=uuid4(),
            tenant_id=test_tenant.id,
            status=OperationStatus.SUCCESS.value,
        )
        await audit_agent.log_operation(
            action="error1",
            resource_type=ResourceType.EVF_PROJECT.value,
            resource_id=uuid4(),
            tenant_id=test_tenant.id,
            status=OperationStatus.ERROR.value,
            error_message="Database connection failed",
        )
        await audit_agent.log_operation(
            action="error2",
            resource_type=ResourceType.EVF_PROJECT.value,
            resource_id=uuid4(),
            tenant_id=test_tenant.id,
            status=OperationStatus.ERROR.value,
            error_message="File not found",
        )

        # Generate report
        report = await audit_agent.generate_audit_report(
            tenant_id=test_tenant.id,
            start_date=start_date,
            end_date=end_date,
        )

        assert report.total_errors == 2
        assert report.operations_by_status[OperationStatus.SUCCESS.value] == 1
        assert report.operations_by_status[OperationStatus.ERROR.value] == 2
        assert len(report.errors_by_type) == 2

    @pytest.mark.asyncio
    async def test_generate_audit_report_compliance_metrics(
        self,
        audit_agent: AuditAgent,
        test_tenant: Tenant,
    ):
        """Test report includes compliance metrics."""
        start_date = datetime.utcnow() - timedelta(days=1)
        end_date = datetime.utcnow() + timedelta(days=1)

        # Create logs with complete audit trail (input/output hashes)
        await audit_agent.log_operation(
            action="complete_audit",
            resource_type=ResourceType.EVF_PROJECT.value,
            resource_id=uuid4(),
            tenant_id=test_tenant.id,
            input_data={"test": "data"},
            output_data={"result": "ok"},
        )
        await audit_agent.log_operation(
            action="incomplete_audit",
            resource_type=ResourceType.EVF_PROJECT.value,
            resource_id=uuid4(),
            tenant_id=test_tenant.id,
            # No input/output data
        )

        # Generate report
        report = await audit_agent.generate_audit_report(
            tenant_id=test_tenant.id,
            start_date=start_date,
            end_date=end_date,
        )

        assert report.total_operations == 2
        assert report.operations_with_audit_trail == 1
        assert report.compliance_percentage == Decimal("50.00")

    @pytest.mark.asyncio
    async def test_generate_audit_report_empty_period(
        self,
        audit_agent: AuditAgent,
        test_tenant: Tenant,
    ):
        """Test report generation for period with no operations."""
        # Far future dates
        start_date = datetime.utcnow() + timedelta(days=100)
        end_date = datetime.utcnow() + timedelta(days=110)

        # Generate report
        report = await audit_agent.generate_audit_report(
            tenant_id=test_tenant.id,
            start_date=start_date,
            end_date=end_date,
        )

        assert report.total_operations == 0
        assert report.total_cost_euros == Decimal("0")
        assert report.compliance_percentage == Decimal("100")  # No ops = 100% compliant


class TestAuditAgentDailyCost:
    """Test daily cost tracking and limits."""

    @pytest.mark.asyncio
    async def test_get_daily_cost_summary(
        self,
        audit_agent: AuditAgent,
        test_tenant: Tenant,
    ):
        """Test daily cost summary calculation."""
        # Create some operations today
        await audit_agent.log_operation(
            action="action1",
            resource_type=ResourceType.EVF_PROJECT.value,
            resource_id=uuid4(),
            tenant_id=test_tenant.id,
            tokens_used=10000,
        )
        await audit_agent.log_operation(
            action="action2",
            resource_type=ResourceType.EVF_PROJECT.value,
            resource_id=uuid4(),
            tenant_id=test_tenant.id,
            tokens_used=5000,
        )

        # Get summary
        summary = await audit_agent.get_daily_cost_summary(
            tenant_id=test_tenant.id,
        )

        assert summary["total_cost_euros"] == float(Decimal("0.135"))  # 15k tokens
        assert summary["total_tokens"] == 15000
        assert summary["operation_count"] == 2
        assert "daily_limit_euros" in summary
        assert "limit_percentage" in summary
        assert "limit_exceeded" in summary

    @pytest.mark.asyncio
    async def test_daily_cost_limit_not_exceeded(
        self,
        audit_agent: AuditAgent,
        test_tenant: Tenant,
    ):
        """Test daily cost summary when limit not exceeded."""
        # Create small operation
        await audit_agent.log_operation(
            action="small_op",
            resource_type=ResourceType.EVF_PROJECT.value,
            resource_id=uuid4(),
            tenant_id=test_tenant.id,
            tokens_used=100,  # Very small
        )

        summary = await audit_agent.get_daily_cost_summary(
            tenant_id=test_tenant.id,
        )

        assert summary["limit_exceeded"] is False
        assert summary["limit_percentage"] < 1.0  # Less than 1% of limit


class TestAuditAgentHelpers:
    """Test helper methods."""

    @pytest.mark.asyncio
    async def test_hash_data_string(self, audit_agent: AuditAgent):
        """Test hashing string data."""
        data = "test string data"
        hash1, size1 = audit_agent._hash_data(data)

        assert len(hash1) == 64  # SHA-256 hex digest
        assert size1 == len(data.encode("utf-8"))

        # Same data should produce same hash
        hash2, size2 = audit_agent._hash_data(data)
        assert hash1 == hash2
        assert size1 == size2

    @pytest.mark.asyncio
    async def test_hash_data_bytes(self, audit_agent: AuditAgent):
        """Test hashing bytes data."""
        data = b"test bytes data"
        hash_val, size = audit_agent._hash_data(data)

        assert len(hash_val) == 64
        assert size == len(data)

    @pytest.mark.asyncio
    async def test_hash_data_dict(self, audit_agent: AuditAgent):
        """Test hashing dictionary data."""
        data = {"key1": "value1", "key2": 123, "key3": [1, 2, 3]}
        hash_val, size = audit_agent._hash_data(data)

        assert len(hash_val) == 64
        assert size > 0

        # Same dict with different key order should produce same hash
        data_reordered = {"key3": [1, 2, 3], "key1": "value1", "key2": 123}
        hash_reordered, _ = audit_agent._hash_data(data_reordered)
        assert hash_val == hash_reordered  # keys are sorted in JSON

    @pytest.mark.asyncio
    async def test_hash_data_deterministic(self, audit_agent: AuditAgent):
        """Test that hashing is deterministic."""
        data = {"complex": {"nested": {"data": [1, 2, 3]}}}

        # Hash multiple times
        hashes = [audit_agent._hash_data(data)[0] for _ in range(10)]

        # All hashes should be identical
        assert len(set(hashes)) == 1
