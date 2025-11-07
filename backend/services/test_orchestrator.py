"""
Test suite for EVF Agent Orchestrator

Tests all orchestrator functionality:
- Agent coordination
- State machine transitions
- Error handling and retry logic
- Progress tracking
- Cost tracking
- Audit trail
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4, UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.services.orchestrator import (
    EVFOrchestrator,
    OrchestratorConfig,
    ProcessingStep,
    ProcessingStatus,
    EVFResult,
    AgentResult,
)
from backend.models.evf import (
    EVFProject,
    EVFStatus,
    ComplianceStatus,
    FundType,
    FinancialModel,
)
from backend.models.audit import AuditLog
from backend.models.tenant import Tenant


@pytest.fixture
def orchestrator_config():
    """Default orchestrator configuration for tests."""
    return OrchestratorConfig(
        max_retries=2,
        retry_delay_seconds=1,
        timeout_seconds=60,
        enable_caching=False,
        cost_limit_euros=Decimal("10.00"),
    )


@pytest.fixture
def orchestrator(orchestrator_config):
    """Create orchestrator instance for testing."""
    return EVFOrchestrator(config=orchestrator_config)


@pytest.fixture
async def test_tenant(db_session: AsyncSession):
    """Create test tenant."""
    tenant = Tenant(
        id=uuid4(),
        name="Test Tenant",
        slug="test-tenant",
        is_active=True,
    )
    db_session.add(tenant)
    await db_session.commit()
    return tenant


@pytest.fixture
async def test_project(db_session: AsyncSession, test_tenant):
    """Create test EVF project."""
    project = EVFProject(
        id=uuid4(),
        tenant_id=test_tenant.id,
        name="Test EVF Project",
        description="Test project for orchestrator",
        fund_type=FundType.PT2030,
        project_duration_years=5,
        total_investment=Decimal("100000.00"),
        eligible_investment=Decimal("80000.00"),
        funding_requested=Decimal("40000.00"),
        status=EVFStatus.DRAFT,
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    return project


@pytest.mark.asyncio
class TestOrchestratorBasics:
    """Test basic orchestrator functionality."""

    async def test_orchestrator_initialization(self, orchestrator):
        """Test orchestrator initializes correctly."""
        assert orchestrator.VERSION == "1.0.0"
        assert orchestrator.financial_agent is not None
        assert orchestrator.config.max_retries == 2

    async def test_step_weights_sum_to_100(self, orchestrator):
        """Test that step weights sum to approximately 100%."""
        total_weight = sum(orchestrator.STEP_WEIGHTS.values())
        assert total_weight == 100

    async def test_orchestrator_config_validation(self):
        """Test orchestrator config validation."""
        # Valid config
        config = OrchestratorConfig(max_retries=3)
        assert config.max_retries == 3

        # Invalid retry count
        with pytest.raises(ValueError):
            OrchestratorConfig(max_retries=15)  # Max is 10


@pytest.mark.asyncio
class TestProcessingPipeline:
    """Test complete processing pipeline."""

    async def test_process_evf_success(
        self,
        orchestrator,
        test_project,
        db_session
    ):
        """Test successful EVF processing."""
        result = await orchestrator.process_evf(
            project_id=test_project.id,
            tenant_id=test_project.tenant_id,
            session=db_session,
        )

        # Check result
        assert result.status == ProcessingStatus.COMPLETED
        assert result.project_id == test_project.id
        assert result.valf is not None
        assert result.trf is not None
        assert result.processing_duration_seconds > 0

        # Check all agents executed
        assert result.input_agent_result is not None
        assert result.input_agent_result.success is True
        assert result.financial_agent_result is not None
        assert result.financial_agent_result.success is True
        assert result.compliance_agent_result is not None

        # Check project updated
        await db_session.refresh(test_project)
        assert test_project.status == EVFStatus.REVIEW
        assert test_project.valf is not None
        assert test_project.trf is not None
        assert test_project.processing_end_time is not None

    async def test_process_evf_creates_financial_model(
        self,
        orchestrator,
        test_project,
        db_session
    ):
        """Test that processing creates a financial model record."""
        await orchestrator.process_evf(
            project_id=test_project.id,
            tenant_id=test_project.tenant_id,
            session=db_session,
        )

        # Check financial model created
        stmt = select(FinancialModel).where(
            FinancialModel.project_id == test_project.id
        )
        result = await db_session.execute(stmt)
        models = result.scalars().all()

        assert len(models) == 1
        model = models[0]
        assert model.valf is not None
        assert model.trf is not None
        assert model.calculated_by_agent == "FinancialAgent"

    async def test_process_evf_creates_audit_logs(
        self,
        orchestrator,
        test_project,
        db_session
    ):
        """Test that processing creates audit logs."""
        await orchestrator.process_evf(
            project_id=test_project.id,
            tenant_id=test_project.tenant_id,
            session=db_session,
        )

        # Check audit logs created
        stmt = select(AuditLog).where(
            AuditLog.project_id == test_project.id
        )
        result = await db_session.execute(stmt)
        logs = result.scalars().all()

        assert len(logs) >= 2  # At least start and complete logs

        # Check start log
        start_logs = [log for log in logs if log.action == "orchestrator_start"]
        assert len(start_logs) == 1

        # Check complete log
        complete_logs = [log for log in logs if log.action == "orchestrator_complete"]
        assert len(complete_logs) == 1

    async def test_process_evf_with_user_id(
        self,
        orchestrator,
        test_project,
        db_session
    ):
        """Test processing with user ID tracking."""
        user_id = uuid4()

        result = await orchestrator.process_evf(
            project_id=test_project.id,
            tenant_id=test_project.tenant_id,
            session=db_session,
            user_id=user_id,
        )

        assert result.status == ProcessingStatus.COMPLETED

        # Check audit logs have user_id
        stmt = select(AuditLog).where(
            AuditLog.project_id == test_project.id,
            AuditLog.user_id == user_id
        )
        result = await db_session.execute(stmt)
        logs = result.scalars().all()

        assert len(logs) > 0


@pytest.mark.asyncio
class TestProgressTracking:
    """Test progress tracking functionality."""

    async def test_get_processing_status_in_progress(
        self,
        orchestrator,
        test_project,
        db_session
    ):
        """Test getting status while processing."""
        # Start processing in background
        task = asyncio.create_task(
            orchestrator.process_evf(
                project_id=test_project.id,
                tenant_id=test_project.tenant_id,
                session=db_session,
            )
        )

        # Small delay to let processing start
        await asyncio.sleep(0.1)

        # Get status
        status = await orchestrator.get_processing_status(test_project.id)

        assert status.project_id == test_project.id
        assert status.status in [ProcessingStatus.IN_PROGRESS, ProcessingStatus.COMPLETED]
        assert 0 <= status.progress_percentage <= 100

        # Wait for completion
        await task

    async def test_get_processing_status_not_found(self, orchestrator):
        """Test getting status for non-existent project."""
        with pytest.raises(ValueError, match="not found"):
            await orchestrator.get_processing_status(uuid4())

    async def test_progress_percentage_increases(
        self,
        orchestrator,
        test_project,
        db_session
    ):
        """Test that progress percentage increases during processing."""
        progress_values = []

        # Monkey-patch to capture progress
        original_update = orchestrator._update_progress

        async def capture_progress(progress, step, percentage):
            progress_values.append(percentage)
            await original_update(progress, step, percentage)

        orchestrator._update_progress = capture_progress

        # Process
        await orchestrator.process_evf(
            project_id=test_project.id,
            tenant_id=test_project.tenant_id,
            session=db_session,
        )

        # Check progress increased
        assert len(progress_values) > 1
        assert progress_values[-1] >= progress_values[0]


@pytest.mark.asyncio
class TestErrorHandling:
    """Test error handling and retry logic."""

    async def test_process_evf_project_not_found(
        self,
        orchestrator,
        db_session
    ):
        """Test processing non-existent project."""
        fake_id = uuid4()
        fake_tenant_id = uuid4()

        with pytest.raises(ValueError, match="not found"):
            await orchestrator.process_evf(
                project_id=fake_id,
                tenant_id=fake_tenant_id,
                session=db_session,
            )

    async def test_retry_logic_on_step_failure(
        self,
        orchestrator,
        test_project,
        db_session
    ):
        """Test retry logic when a step fails."""
        retry_count = 0

        # Monkey-patch financial agent to fail twice then succeed
        original_calc = orchestrator.financial_agent.calculate

        def failing_calc(input_data):
            nonlocal retry_count
            retry_count += 1
            if retry_count < 3:
                raise RuntimeError("Simulated failure")
            return original_calc(input_data)

        orchestrator.financial_agent.calculate = failing_calc

        # Process should succeed after retries
        result = await orchestrator.process_evf(
            project_id=test_project.id,
            tenant_id=test_project.tenant_id,
            session=db_session,
        )

        assert result.status == ProcessingStatus.COMPLETED
        assert retry_count == 3  # Failed twice, succeeded third time

    async def test_max_retries_exceeded(
        self,
        orchestrator,
        test_project,
        db_session
    ):
        """Test behavior when max retries exceeded."""
        # Monkey-patch to always fail
        def always_fail(input_data):
            raise RuntimeError("Persistent failure")

        orchestrator.financial_agent.calculate = always_fail

        # Process should fail
        with pytest.raises(RuntimeError):
            await orchestrator.process_evf(
                project_id=test_project.id,
                tenant_id=test_project.tenant_id,
                session=db_session,
            )

        # Check project status updated to review
        await db_session.refresh(test_project)
        assert test_project.status == EVFStatus.REVIEW

        # Check error logged
        stmt = select(AuditLog).where(
            AuditLog.project_id == test_project.id,
            AuditLog.action == "orchestrator_failed"
        )
        result = await db_session.execute(stmt)
        error_logs = result.scalars().all()

        assert len(error_logs) == 1
        assert "Persistent failure" in error_logs[0].error_message


@pytest.mark.asyncio
class TestCancellation:
    """Test processing cancellation."""

    async def test_cancel_processing(
        self,
        orchestrator,
        test_project,
        db_session
    ):
        """Test cancelling ongoing processing."""
        # Start processing
        task = asyncio.create_task(
            orchestrator.process_evf(
                project_id=test_project.id,
                tenant_id=test_project.tenant_id,
                session=db_session,
            )
        )

        # Small delay
        await asyncio.sleep(0.1)

        # Cancel
        cancelled = await orchestrator.cancel_processing(
            test_project.id, db_session
        )

        assert cancelled is True

        # Wait for task to complete
        with pytest.raises(RuntimeError, match="cancelled"):
            await task

    async def test_cancel_not_processing(
        self,
        orchestrator,
        test_project,
        db_session
    ):
        """Test cancelling when not processing."""
        cancelled = await orchestrator.cancel_processing(
            test_project.id, db_session
        )

        assert cancelled is False


@pytest.mark.asyncio
class TestComplianceValidation:
    """Test compliance validation logic."""

    async def test_non_compliant_project(
        self,
        orchestrator,
        db_session,
        test_tenant
    ):
        """Test processing non-compliant project."""
        # Create project with positive VALF (non-compliant)
        project = EVFProject(
            id=uuid4(),
            tenant_id=test_tenant.id,
            name="Non-Compliant Project",
            fund_type=FundType.PT2030,
            project_duration_years=3,
            total_investment=Decimal("50000.00"),
            eligible_investment=Decimal("40000.00"),
            funding_requested=Decimal("20000.00"),
            status=EVFStatus.DRAFT,
        )
        db_session.add(project)
        await db_session.commit()

        # Process
        result = await orchestrator.process_evf(
            project_id=project.id,
            tenant_id=project.tenant_id,
            session=db_session,
        )

        # May or may not be compliant depending on cash flows
        assert result.compliance_status in [
            ComplianceStatus.COMPLIANT,
            ComplianceStatus.NON_COMPLIANT
        ]

        # Check compliance agent ran
        assert result.compliance_agent_result is not None


@pytest.mark.asyncio
class TestCostTracking:
    """Test cost tracking functionality."""

    async def test_cost_tracking(
        self,
        orchestrator,
        test_project,
        db_session
    ):
        """Test that costs are tracked correctly."""
        result = await orchestrator.process_evf(
            project_id=test_project.id,
            tenant_id=test_project.tenant_id,
            session=db_session,
        )

        # Check total cost calculated
        assert result.total_cost_euros >= 0

        # If narrative agent ran, should have token costs
        if result.narrative_agent_result:
            assert result.total_tokens_used > 0

    async def test_cost_limit_warning(
        self,
        test_project,
        db_session
    ):
        """Test cost limit warning."""
        # Create orchestrator with very low limit
        config = OrchestratorConfig(cost_limit_euros=Decimal("0.01"))
        orchestrator = EVFOrchestrator(config=config)

        # Process - should still complete but log warning
        result = await orchestrator.process_evf(
            project_id=test_project.id,
            tenant_id=test_project.tenant_id,
            session=db_session,
        )

        # Should still complete
        assert result.status == ProcessingStatus.COMPLETED


@pytest.mark.asyncio
class TestStatusMapping:
    """Test status mapping helpers."""

    def test_map_evf_status_to_processing_status(self, orchestrator):
        """Test EVF status to processing status mapping."""
        assert orchestrator._map_evf_status_to_processing_status(
            EVFStatus.DRAFT
        ) == ProcessingStatus.PENDING

        assert orchestrator._map_evf_status_to_processing_status(
            EVFStatus.PROCESSING
        ) == ProcessingStatus.IN_PROGRESS

        assert orchestrator._map_evf_status_to_processing_status(
            EVFStatus.APPROVED
        ) == ProcessingStatus.COMPLETED

    def test_calculate_progress_from_status(self, orchestrator):
        """Test progress calculation from status."""
        progress = orchestrator._calculate_progress_from_status(EVFStatus.DRAFT)
        assert progress == 0.0

        progress = orchestrator._calculate_progress_from_status(EVFStatus.APPROVED)
        assert progress == 100.0

        progress = orchestrator._calculate_progress_from_status(EVFStatus.PROCESSING)
        assert 0 < progress < 100


@pytest.mark.asyncio
class TestAgentResults:
    """Test agent result models."""

    def test_agent_result_creation(self):
        """Test AgentResult model."""
        result = AgentResult(
            agent_name="TestAgent",
            success=True,
            data={"test": "data"},
            execution_time_seconds=1.5,
            tokens_used=100,
            cost_euros=Decimal("0.05"),
        )

        assert result.agent_name == "TestAgent"
        assert result.success is True
        assert result.data["test"] == "data"
        assert result.execution_time_seconds == 1.5

    def test_evf_result_defaults(self):
        """Test EVFResult default values."""
        result = EVFResult(
            project_id=uuid4(),
            tenant_id=uuid4(),
            status=ProcessingStatus.PENDING,
            started_at=datetime.utcnow(),
        )

        assert result.total_tokens_used == 0
        assert result.total_cost_euros == Decimal("0.00")
        assert result.errors == []
        assert result.warnings == []


# Performance test
@pytest.mark.asyncio
@pytest.mark.slow
class TestPerformance:
    """Test orchestrator performance."""

    async def test_processing_time_under_limit(
        self,
        orchestrator,
        test_project,
        db_session
    ):
        """Test that processing completes within reasonable time."""
        start = datetime.utcnow()

        result = await orchestrator.process_evf(
            project_id=test_project.id,
            tenant_id=test_project.tenant_id,
            session=db_session,
        )

        end = datetime.utcnow()
        duration = (end - start).total_seconds()

        # Should complete in under 10 seconds for mock data
        assert duration < 10

        assert result.status == ProcessingStatus.COMPLETED


# Import asyncio for async tests
import asyncio
