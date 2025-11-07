"""
EVF Agent Orchestrator - Coordinates all 5 specialized agents

Orchestrates the complete EVF processing pipeline:
1. InputAgent - Parse and validate SAF-T/Excel/CSV files
2. FinancialAgent - Calculate VALF/TRF (deterministic)
3. ComplianceAgent - Validate PT2030/PRR/SITCE rules
4. NarrativeAgent - Generate proposal text using Claude
5. AuditAgent - Log all operations and costs

State machine with progress tracking, error handling, and full audit trail.
"""

import asyncio
import hashlib
import json
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
from uuid import UUID, uuid4

import structlog
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings
from backend.core.database import db_manager
from backend.models.evf import (
    EVFProject,
    EVFStatus,
    FinancialModel,
    ComplianceStatus,
)
from backend.models.audit import AuditLog
from backend.agents.financial_agent import FinancialAgent, FinancialInput
from backend.services.cache_service import CacheService

# Setup logger
logger = structlog.get_logger(__name__)


class ProcessingStep(str, Enum):
    """Processing steps in the EVF pipeline."""
    INITIALIZING = "initializing"
    PARSING_INPUT = "parsing_input"
    CALCULATING_FINANCIALS = "calculating_financials"
    VALIDATING_COMPLIANCE = "validating_compliance"
    GENERATING_NARRATIVE = "generating_narrative"
    AUDITING_RESULTS = "auditing_results"
    FINALIZING = "finalizing"
    COMPLETED = "completed"
    FAILED = "failed"


class ProcessingStatus(str, Enum):
    """Overall processing status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentResult(BaseModel):
    """Result from an individual agent execution."""
    agent_name: str
    success: bool
    data: Dict[str, Any] = Field(default_factory=dict)
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    execution_time_seconds: float = 0.0
    tokens_used: int = 0
    cost_euros: Decimal = Decimal("0.00")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ProcessingProgress(BaseModel):
    """Real-time processing progress information."""
    project_id: UUID
    tenant_id: UUID
    status: ProcessingStatus
    current_step: ProcessingStep
    progress_percentage: float = Field(ge=0, le=100)
    steps_completed: List[str] = Field(default_factory=list)
    steps_remaining: List[str] = Field(default_factory=list)
    started_at: Optional[datetime] = None
    estimated_completion_at: Optional[datetime] = None
    current_agent: Optional[str] = None
    error_message: Optional[str] = None
    total_tokens_used: int = 0
    total_cost_euros: Decimal = Decimal("0.00")


class EVFResult(BaseModel):
    """Final result of EVF processing."""
    project_id: UUID
    tenant_id: UUID
    status: ProcessingStatus

    # Agent results
    input_agent_result: Optional[AgentResult] = None
    financial_agent_result: Optional[AgentResult] = None
    compliance_agent_result: Optional[AgentResult] = None
    narrative_agent_result: Optional[AgentResult] = None
    audit_agent_result: Optional[AgentResult] = None

    # Summary
    valf: Optional[Decimal] = None
    trf: Optional[Decimal] = None
    pt2030_compliant: bool = False
    compliance_status: ComplianceStatus = ComplianceStatus.NOT_VALIDATED

    # Processing metadata
    processing_duration_seconds: float = 0.0
    total_tokens_used: int = 0
    total_cost_euros: Decimal = Decimal("0.00")
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)

    # Paths to generated files
    excel_file_path: Optional[str] = None
    pdf_report_path: Optional[str] = None

    # Timestamps
    started_at: datetime
    completed_at: Optional[datetime] = None


class OrchestratorConfig(BaseModel):
    """Configuration for the orchestrator."""
    max_retries: int = Field(default=3, ge=0, le=10)
    retry_delay_seconds: int = Field(default=5, ge=1, le=60)
    timeout_seconds: int = Field(default=300, ge=60, le=3600)
    enable_caching: bool = True
    enable_parallel_execution: bool = False  # Future: parallel non-dependent agents
    cost_limit_euros: Decimal = Field(default=Decimal("5.00"), ge=0)


class EVFOrchestrator:
    """
    Orchestrator for coordinating all 5 EVF processing agents.

    Manages the complete pipeline:
    1. InputAgent - Parse SAF-T/Excel
    2. FinancialAgent - Calculate VALF/TRF
    3. ComplianceAgent - Validate PT2030
    4. NarrativeAgent - Generate text
    5. AuditAgent - Log everything

    Features:
    - State machine with progress tracking
    - Error handling with retry logic
    - Full audit trail
    - Cost tracking and limits
    - Async processing
    """

    VERSION = "1.0.0"

    # Step weights for progress calculation (total = 100%)
    STEP_WEIGHTS = {
        ProcessingStep.INITIALIZING: 5,
        ProcessingStep.PARSING_INPUT: 15,
        ProcessingStep.CALCULATING_FINANCIALS: 20,
        ProcessingStep.VALIDATING_COMPLIANCE: 20,
        ProcessingStep.GENERATING_NARRATIVE: 25,
        ProcessingStep.AUDITING_RESULTS: 10,
        ProcessingStep.FINALIZING: 5,
    }

    def __init__(
        self,
        config: Optional[OrchestratorConfig] = None,
        cache_service: Optional[CacheService] = None
    ):
        """
        Initialize the orchestrator.

        Args:
            config: Orchestrator configuration
            cache_service: Cache service for intermediate results
        """
        self.config = config or OrchestratorConfig()
        self.cache_service = cache_service

        # Initialize agents
        self.financial_agent = FinancialAgent()

        # Processing state
        self._processing_state: Dict[UUID, ProcessingProgress] = {}
        self._cancel_flags: Dict[UUID, bool] = {}

    async def process_evf(
        self,
        project_id: UUID,
        tenant_id: UUID,
        session: AsyncSession,
        user_id: Optional[UUID] = None
    ) -> EVFResult:
        """
        Process an EVF project through all agents.

        Args:
            project_id: ID of the EVF project
            tenant_id: Tenant ID for isolation
            session: Database session
            user_id: User initiating the processing

        Returns:
            EVFResult with complete processing results

        Raises:
            ValueError: If project not found or invalid
            RuntimeError: If processing fails
        """
        start_time = datetime.utcnow()

        # Initialize progress tracking
        progress = ProcessingProgress(
            project_id=project_id,
            tenant_id=tenant_id,
            status=ProcessingStatus.IN_PROGRESS,
            current_step=ProcessingStep.INITIALIZING,
            progress_percentage=0.0,
            started_at=start_time,
            steps_remaining=list(ProcessingStep),
        )
        self._processing_state[project_id] = progress

        # Initialize result
        result = EVFResult(
            project_id=project_id,
            tenant_id=tenant_id,
            status=ProcessingStatus.IN_PROGRESS,
            started_at=start_time,
        )

        try:
            # Load project
            project = await self._load_project(project_id, tenant_id, session)

            # Update project status
            await self._update_project_status(
                project, EVFStatus.PROCESSING, session
            )

            # Log start
            await self._create_audit_log(
                session=session,
                tenant_id=tenant_id,
                project_id=project_id,
                action="orchestrator_start",
                resource_type="evf_project",
                resource_id=project_id,
                user_id=user_id,
                metadata={"orchestrator_version": self.VERSION}
            )

            # Execute pipeline
            logger.info(
                "Starting EVF processing",
                project_id=str(project_id),
                tenant_id=str(tenant_id)
            )

            # Step 1: Input Agent
            result.input_agent_result = await self._execute_step(
                step=ProcessingStep.PARSING_INPUT,
                agent_func=self._run_input_agent,
                project=project,
                session=session,
                progress=progress,
            )

            if not result.input_agent_result.success:
                raise RuntimeError(f"Input agent failed: {result.input_agent_result.errors}")

            # Step 2: Financial Agent
            result.financial_agent_result = await self._execute_step(
                step=ProcessingStep.CALCULATING_FINANCIALS,
                agent_func=self._run_financial_agent,
                project=project,
                session=session,
                progress=progress,
                input_data=result.input_agent_result.data,
            )

            if not result.financial_agent_result.success:
                raise RuntimeError(f"Financial agent failed: {result.financial_agent_result.errors}")

            # Extract financial results
            result.valf = result.financial_agent_result.data.get("valf")
            result.trf = result.financial_agent_result.data.get("trf")

            # Step 3: Compliance Agent
            result.compliance_agent_result = await self._execute_step(
                step=ProcessingStep.VALIDATING_COMPLIANCE,
                agent_func=self._run_compliance_agent,
                project=project,
                session=session,
                progress=progress,
                financial_data=result.financial_agent_result.data,
            )

            if not result.compliance_agent_result.success:
                logger.warning(
                    "Compliance agent detected issues",
                    project_id=str(project_id),
                    errors=result.compliance_agent_result.errors
                )

            result.pt2030_compliant = result.compliance_agent_result.data.get(
                "pt2030_compliant", False
            )
            result.compliance_status = (
                ComplianceStatus.COMPLIANT if result.pt2030_compliant
                else ComplianceStatus.NON_COMPLIANT
            )

            # Step 4: Narrative Agent (only if enabled)
            if settings.enable_ai_narrative:
                result.narrative_agent_result = await self._execute_step(
                    step=ProcessingStep.GENERATING_NARRATIVE,
                    agent_func=self._run_narrative_agent,
                    project=project,
                    session=session,
                    progress=progress,
                    financial_data=result.financial_agent_result.data,
                    compliance_data=result.compliance_agent_result.data,
                )

                # Accumulate AI costs
                result.total_tokens_used += result.narrative_agent_result.tokens_used
                result.total_cost_euros += result.narrative_agent_result.cost_euros

                # Check cost limit
                if result.total_cost_euros > self.config.cost_limit_euros:
                    logger.warning(
                        "Cost limit exceeded",
                        total_cost=float(result.total_cost_euros),
                        limit=float(self.config.cost_limit_euros)
                    )

            # Step 5: Audit Agent
            result.audit_agent_result = await self._execute_step(
                step=ProcessingStep.AUDITING_RESULTS,
                agent_func=self._run_audit_agent,
                project=project,
                session=session,
                progress=progress,
                all_results=result.model_dump(),
            )

            # Finalize
            await self._update_progress(
                progress, ProcessingStep.FINALIZING, 95.0
            )

            # Update project with final results
            await self._finalize_project(project, result, session)

            # Mark as completed
            result.status = ProcessingStatus.COMPLETED
            result.completed_at = datetime.utcnow()
            result.processing_duration_seconds = (
                result.completed_at - start_time
            ).total_seconds()

            progress.status = ProcessingStatus.COMPLETED
            progress.current_step = ProcessingStep.COMPLETED
            progress.progress_percentage = 100.0

            # Log completion
            await self._create_audit_log(
                session=session,
                tenant_id=tenant_id,
                project_id=project_id,
                action="orchestrator_complete",
                resource_type="evf_project",
                resource_id=project_id,
                user_id=user_id,
                metadata={
                    "duration_seconds": result.processing_duration_seconds,
                    "total_cost_euros": float(result.total_cost_euros),
                    "valf": float(result.valf) if result.valf else None,
                    "trf": float(result.trf) if result.trf else None,
                    "compliant": result.pt2030_compliant,
                }
            )

            logger.info(
                "EVF processing completed",
                project_id=str(project_id),
                duration_seconds=result.processing_duration_seconds,
                cost_euros=float(result.total_cost_euros),
                compliant=result.pt2030_compliant
            )

            return result

        except Exception as e:
            # Mark as failed
            result.status = ProcessingStatus.FAILED
            result.completed_at = datetime.utcnow()
            result.processing_duration_seconds = (
                result.completed_at - start_time
            ).total_seconds()
            result.errors.append(str(e))

            progress.status = ProcessingStatus.FAILED
            progress.current_step = ProcessingStep.FAILED
            progress.error_message = str(e)

            # Update project status
            await self._update_project_status(
                project, EVFStatus.REVIEW, session, error_message=str(e)
            )

            # Log failure
            await self._create_audit_log(
                session=session,
                tenant_id=tenant_id,
                project_id=project_id,
                action="orchestrator_failed",
                resource_type="evf_project",
                resource_id=project_id,
                user_id=user_id,
                status="error",
                error_message=str(e),
                metadata={"duration_seconds": result.processing_duration_seconds}
            )

            logger.error(
                "EVF processing failed",
                project_id=str(project_id),
                error=str(e),
                duration_seconds=result.processing_duration_seconds
            )

            raise

        finally:
            # Cleanup
            if project_id in self._processing_state:
                del self._processing_state[project_id]
            if project_id in self._cancel_flags:
                del self._cancel_flags[project_id]

    async def get_processing_status(
        self,
        project_id: UUID,
        session: Optional[AsyncSession] = None
    ) -> ProcessingProgress:
        """
        Get current processing status for a project.

        Args:
            project_id: ID of the EVF project
            session: Optional database session for persistent status

        Returns:
            ProcessingProgress with current status
        """
        # Check in-memory state first
        if project_id in self._processing_state:
            return self._processing_state[project_id]

        # If not in memory and session provided, check database
        if session:
            project = await session.get(EVFProject, project_id)
            if project:
                # Reconstruct progress from project status
                return ProcessingProgress(
                    project_id=project_id,
                    tenant_id=project.tenant_id,
                    status=self._map_evf_status_to_processing_status(project.status),
                    current_step=self._infer_current_step(project),
                    progress_percentage=self._calculate_progress_from_status(project.status),
                    started_at=project.processing_start_time,
                    steps_completed=[],
                    steps_remaining=[],
                )

        # Not found
        raise ValueError(f"Project {project_id} not found or not processing")

    async def cancel_processing(
        self,
        project_id: UUID,
        session: AsyncSession
    ) -> bool:
        """
        Cancel ongoing processing for a project.

        Args:
            project_id: ID of the EVF project
            session: Database session

        Returns:
            True if cancelled successfully, False if not processing
        """
        if project_id not in self._processing_state:
            return False

        # Set cancel flag
        self._cancel_flags[project_id] = True

        # Update progress
        progress = self._processing_state[project_id]
        progress.status = ProcessingStatus.CANCELLED

        # Update project
        project = await session.get(EVFProject, project_id)
        if project:
            await self._update_project_status(
                project, EVFStatus.DRAFT, session
            )

        logger.info("Processing cancelled", project_id=str(project_id))

        return True

    # ===== Private Helper Methods =====

    async def _load_project(
        self,
        project_id: UUID,
        tenant_id: UUID,
        session: AsyncSession
    ) -> EVFProject:
        """Load and validate EVF project."""
        stmt = select(EVFProject).where(
            EVFProject.id == project_id,
            EVFProject.tenant_id == tenant_id
        )
        result = await session.execute(stmt)
        project = result.scalar_one_or_none()

        if not project:
            raise ValueError(
                f"Project {project_id} not found for tenant {tenant_id}"
            )

        return project

    async def _update_project_status(
        self,
        project: EVFProject,
        status: EVFStatus,
        session: AsyncSession,
        error_message: Optional[str] = None
    ):
        """Update project status in database."""
        project.status = status

        if status == EVFStatus.PROCESSING and not project.processing_start_time:
            project.processing_start_time = datetime.utcnow()

        if status in [EVFStatus.APPROVED, EVFStatus.REJECTED, EVFStatus.REVIEW]:
            if not project.processing_end_time:
                project.processing_end_time = datetime.utcnow()

                if project.processing_start_time:
                    duration = (
                        project.processing_end_time - project.processing_start_time
                    )
                    project.processing_duration_seconds = int(duration.total_seconds())

        if error_message:
            project.notes = (
                f"{project.notes or ''}\n\nError: {error_message}"
            ).strip()

        session.add(project)
        await session.commit()

    async def _execute_step(
        self,
        step: ProcessingStep,
        agent_func,
        project: EVFProject,
        session: AsyncSession,
        progress: ProcessingProgress,
        **kwargs
    ) -> AgentResult:
        """
        Execute a single agent step with retry logic.

        Args:
            step: Processing step being executed
            agent_func: Agent function to execute
            project: EVF project
            session: Database session
            progress: Progress tracker
            **kwargs: Additional arguments for agent function

        Returns:
            AgentResult from the agent
        """
        # Check for cancellation
        if self._cancel_flags.get(project.id, False):
            raise RuntimeError("Processing cancelled by user")

        # Update progress
        step_start_weight = sum(
            self.STEP_WEIGHTS.get(s, 0)
            for s in list(ProcessingStep)
            if list(ProcessingStep).index(s) < list(ProcessingStep).index(step)
        )
        await self._update_progress(progress, step, step_start_weight)

        # Execute with retry
        last_error = None
        for attempt in range(self.config.max_retries + 1):
            try:
                logger.info(
                    "Executing step",
                    step=step,
                    attempt=attempt + 1,
                    project_id=str(project.id)
                )

                result = await agent_func(project, session, **kwargs)

                # Update progress
                progress.steps_completed.append(step)
                if step in progress.steps_remaining:
                    progress.steps_remaining.remove(step)

                return result

            except Exception as e:
                last_error = e
                logger.warning(
                    "Step execution failed",
                    step=step,
                    attempt=attempt + 1,
                    error=str(e),
                    project_id=str(project.id)
                )

                if attempt < self.config.max_retries:
                    await asyncio.sleep(self.config.retry_delay_seconds)

        # All retries failed
        return AgentResult(
            agent_name=step,
            success=False,
            errors=[f"Failed after {self.config.max_retries + 1} attempts: {last_error}"]
        )

    async def _update_progress(
        self,
        progress: ProcessingProgress,
        step: ProcessingStep,
        percentage: float
    ):
        """Update progress tracking."""
        progress.current_step = step
        progress.progress_percentage = min(percentage, 100.0)

        # Estimate completion time
        if progress.started_at:
            elapsed = (datetime.utcnow() - progress.started_at).total_seconds()
            if percentage > 0:
                total_estimated = elapsed * (100.0 / percentage)
                remaining = total_estimated - elapsed
                progress.estimated_completion_at = (
                    datetime.utcnow() + timedelta(seconds=remaining)
                )

    # ===== Agent Execution Methods =====

    async def _run_input_agent(
        self,
        project: EVFProject,
        session: AsyncSession,
        **kwargs
    ) -> AgentResult:
        """
        Execute InputAgent - Parse SAF-T/Excel files.

        TODO: Implement full InputAgent with MCP server integration
        For now, returns mock data for testing.
        """
        start_time = datetime.utcnow()

        try:
            # TODO: Implement actual SAF-T parsing via MCP server
            # For now, return mock parsed data

            parsed_data = {
                "company_name": "Example Corp",
                "tax_id": "123456789",
                "project_name": project.name,
                "project_duration_years": project.project_duration_years or 5,
                "total_investment": float(project.total_investment or 100000),
                "eligible_investment": float(project.eligible_investment or 80000),
                "funding_requested": float(project.funding_requested or 40000),
                "cash_flows": [
                    # Year 0: Initial investment
                    {
                        "year": 0,
                        "revenue": 0,
                        "operating_costs": 0,
                        "capex": 0,
                        "depreciation": 0,
                        "working_capital_change": 0,
                    }
                ] + [
                    # Years 1-5: Operations
                    {
                        "year": i,
                        "revenue": 50000 * i,
                        "operating_costs": 30000 * i,
                        "capex": 5000 if i == 1 else 0,
                        "depreciation": 20000,
                        "working_capital_change": 0,
                    }
                    for i in range(1, (project.project_duration_years or 5) + 1)
                ]
            }

            duration = (datetime.utcnow() - start_time).total_seconds()

            return AgentResult(
                agent_name="InputAgent",
                success=True,
                data=parsed_data,
                execution_time_seconds=duration,
                metadata={"source": "mock_data"}
            )

        except Exception as e:
            duration = (datetime.utcnow() - start_time).total_seconds()
            return AgentResult(
                agent_name="InputAgent",
                success=False,
                errors=[str(e)],
                execution_time_seconds=duration
            )

    async def _run_financial_agent(
        self,
        project: EVFProject,
        session: AsyncSession,
        input_data: Dict[str, Any],
        **kwargs
    ) -> AgentResult:
        """Execute FinancialAgent - Calculate VALF/TRF."""
        start_time = datetime.utcnow()

        try:
            # Convert input data to FinancialInput
            from backend.agents.financial_agent import CashFlow

            financial_input = FinancialInput(
                project_name=input_data["project_name"],
                project_duration_years=input_data["project_duration_years"],
                total_investment=Decimal(str(input_data["total_investment"])),
                eligible_investment=Decimal(str(input_data["eligible_investment"])),
                funding_requested=Decimal(str(input_data["funding_requested"])),
                cash_flows=[
                    CashFlow(**cf) for cf in input_data["cash_flows"]
                ]
            )

            # Execute financial calculations
            output = self.financial_agent.calculate(financial_input)

            # Store financial model in database
            financial_model = FinancialModel(
                id=uuid4(),
                tenant_id=project.tenant_id,
                project_id=project.id,
                version=1,
                input_data=input_data,
                input_hash=output.input_hash,
                calculations=output.assumptions,
                valf=output.valf,
                trf=output.trf,
                payback_period=output.payback_period,
                roi=output.financial_ratios.roi,
                cash_flows={"annual": input_data["cash_flows"]},
                financial_ratios=output.financial_ratios.model_dump(),
                is_valid=output.pt2030_compliant,
                validation_errors=output.compliance_notes if not output.pt2030_compliant else [],
                assumptions=output.assumptions,
                sources={"input_agent": "parsed_saft"},
                calculated_by_agent="FinancialAgent",
            )

            session.add(financial_model)
            await session.commit()

            # Update project
            project.valf = output.valf
            project.trf = output.trf
            project.payback_period = output.payback_period
            session.add(project)
            await session.commit()

            duration = (datetime.utcnow() - start_time).total_seconds()

            return AgentResult(
                agent_name="FinancialAgent",
                success=True,
                data={
                    "valf": output.valf,
                    "trf": output.trf,
                    "payback_period": output.payback_period,
                    "total_fcf": output.total_fcf,
                    "average_annual_fcf": output.average_annual_fcf,
                    "financial_ratios": output.financial_ratios.model_dump(),
                    "pt2030_compliant": output.pt2030_compliant,
                    "compliance_notes": output.compliance_notes,
                },
                execution_time_seconds=duration,
                metadata={
                    "model_version": financial_model.version,
                    "input_hash": output.input_hash,
                }
            )

        except Exception as e:
            duration = (datetime.utcnow() - start_time).total_seconds()
            return AgentResult(
                agent_name="FinancialAgent",
                success=False,
                errors=[str(e)],
                execution_time_seconds=duration
            )

    async def _run_compliance_agent(
        self,
        project: EVFProject,
        session: AsyncSession,
        financial_data: Dict[str, Any],
        **kwargs
    ) -> AgentResult:
        """
        Execute ComplianceAgent - Validate PT2030 rules.

        TODO: Implement full ComplianceAgent with comprehensive rules
        For now, uses basic VALF/TRF checks from FinancialAgent.
        """
        start_time = datetime.utcnow()

        try:
            # Extract financial metrics
            valf = financial_data.get("valf")
            trf = financial_data.get("trf")

            # PT2030 compliance checks
            errors = []
            warnings = []
            compliant = True

            # Rule 1: VALF must be negative
            if valf is not None and float(valf) >= 0:
                errors.append("VALF must be negative (< 0) for PT2030 eligibility")
                compliant = False

            # Rule 2: TRF must be less than 4%
            if trf is not None and float(trf) >= 4.0:
                errors.append("TRF must be less than 4% for PT2030 eligibility")
                compliant = False

            # Rule 3: Check funding limits
            if project.funding_requested and project.eligible_investment:
                funding_ratio = float(project.funding_requested) / float(project.eligible_investment)
                if funding_ratio > 0.5:  # Max 50% funding for most programs
                    warnings.append(
                        f"Funding requested is {funding_ratio*100:.1f}% of eligible investment. "
                        "Most PT2030 programs have 50% limit."
                    )

            # Update project compliance status
            project.compliance_status = (
                ComplianceStatus.COMPLIANT if compliant
                else ComplianceStatus.NON_COMPLIANT
            )
            project.compliance_errors = errors if errors else []

            session.add(project)
            await session.commit()

            duration = (datetime.utcnow() - start_time).total_seconds()

            return AgentResult(
                agent_name="ComplianceAgent",
                success=True,
                data={
                    "pt2030_compliant": compliant,
                    "compliance_status": project.compliance_status,
                    "checks_passed": [] if errors else ["valf_negative", "trf_below_threshold"],
                    "checks_failed": errors,
                },
                errors=errors,
                warnings=warnings,
                execution_time_seconds=duration,
            )

        except Exception as e:
            duration = (datetime.utcnow() - start_time).total_seconds()
            return AgentResult(
                agent_name="ComplianceAgent",
                success=False,
                errors=[str(e)],
                execution_time_seconds=duration
            )

    async def _run_narrative_agent(
        self,
        project: EVFProject,
        session: AsyncSession,
        financial_data: Dict[str, Any],
        compliance_data: Dict[str, Any],
        **kwargs
    ) -> AgentResult:
        """
        Execute NarrativeAgent - Generate proposal text using Claude.

        TODO: Implement full NarrativeAgent with Claude integration
        For now, returns placeholder.
        """
        start_time = datetime.utcnow()

        try:
            # TODO: Implement Claude API integration
            # For now, return placeholder

            narrative = {
                "executive_summary": f"Financial viability analysis for {project.name}",
                "financial_analysis": f"VALF: {financial_data.get('valf')}, TRF: {financial_data.get('trf')}%",
                "compliance_summary": "Compliant" if compliance_data.get("pt2030_compliant") else "Non-compliant",
            }

            duration = (datetime.utcnow() - start_time).total_seconds()

            # Mock token usage (will be real when Claude is integrated)
            tokens_used = 500
            cost_euros = Decimal("0.15")  # Approximate cost

            return AgentResult(
                agent_name="NarrativeAgent",
                success=True,
                data=narrative,
                execution_time_seconds=duration,
                tokens_used=tokens_used,
                cost_euros=cost_euros,
                metadata={"model": "claude-3-5-sonnet (mock)"}
            )

        except Exception as e:
            duration = (datetime.utcnow() - start_time).total_seconds()
            return AgentResult(
                agent_name="NarrativeAgent",
                success=False,
                errors=[str(e)],
                execution_time_seconds=duration
            )

    async def _run_audit_agent(
        self,
        project: EVFProject,
        session: AsyncSession,
        all_results: Dict[str, Any],
        **kwargs
    ) -> AgentResult:
        """Execute AuditAgent - Log all operations."""
        start_time = datetime.utcnow()

        try:
            # Create comprehensive audit trail
            audit_summary = {
                "project_id": str(project.id),
                "total_processing_time": all_results.get("processing_duration_seconds", 0),
                "total_cost_euros": float(all_results.get("total_cost_euros", 0)),
                "agents_executed": [
                    "InputAgent",
                    "FinancialAgent",
                    "ComplianceAgent",
                    "NarrativeAgent",
                ],
                "final_status": all_results.get("status"),
                "compliant": all_results.get("pt2030_compliant"),
            }

            # Store in audit log
            await self._create_audit_log(
                session=session,
                tenant_id=project.tenant_id,
                project_id=project.id,
                action="evf_processing_summary",
                resource_type="evf_project",
                resource_id=project.id,
                metadata=audit_summary
            )

            duration = (datetime.utcnow() - start_time).total_seconds()

            return AgentResult(
                agent_name="AuditAgent",
                success=True,
                data=audit_summary,
                execution_time_seconds=duration,
            )

        except Exception as e:
            duration = (datetime.utcnow() - start_time).total_seconds()
            return AgentResult(
                agent_name="AuditAgent",
                success=False,
                errors=[str(e)],
                execution_time_seconds=duration
            )

    async def _finalize_project(
        self,
        project: EVFProject,
        result: EVFResult,
        session: AsyncSession
    ):
        """Update project with final results."""
        # Update status based on compliance
        if result.pt2030_compliant:
            project.status = EVFStatus.REVIEW  # Ready for human review
        else:
            project.status = EVFStatus.REVIEW  # Needs review due to non-compliance

        # Store final metadata
        project.metadata = {
            "orchestrator_version": self.VERSION,
            "processing_summary": {
                "duration_seconds": result.processing_duration_seconds,
                "total_cost_euros": float(result.total_cost_euros),
                "total_tokens_used": result.total_tokens_used,
            },
            "agent_results": {
                "input_agent": result.input_agent_result.success if result.input_agent_result else False,
                "financial_agent": result.financial_agent_result.success if result.financial_agent_result else False,
                "compliance_agent": result.compliance_agent_result.success if result.compliance_agent_result else False,
                "narrative_agent": result.narrative_agent_result.success if result.narrative_agent_result else False,
                "audit_agent": result.audit_agent_result.success if result.audit_agent_result else False,
            }
        }

        session.add(project)
        await session.commit()

    async def _create_audit_log(
        self,
        session: AsyncSession,
        tenant_id: UUID,
        project_id: UUID,
        action: str,
        resource_type: str,
        resource_id: UUID,
        user_id: Optional[UUID] = None,
        status: str = "success",
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Create an audit log entry."""
        audit_log = AuditLog(
            id=uuid4(),
            tenant_id=tenant_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            project_id=project_id,
            user_id=user_id,
            status=status,
            error_message=error_message,
            metadata=metadata or {},
            agent_name="Orchestrator",
        )

        session.add(audit_log)
        await session.commit()

    # ===== Status Mapping Helpers =====

    def _map_evf_status_to_processing_status(
        self,
        evf_status: EVFStatus
    ) -> ProcessingStatus:
        """Map EVF status to processing status."""
        mapping = {
            EVFStatus.DRAFT: ProcessingStatus.PENDING,
            EVFStatus.UPLOADING: ProcessingStatus.IN_PROGRESS,
            EVFStatus.VALIDATING: ProcessingStatus.IN_PROGRESS,
            EVFStatus.PROCESSING: ProcessingStatus.IN_PROGRESS,
            EVFStatus.REVIEW: ProcessingStatus.COMPLETED,
            EVFStatus.APPROVED: ProcessingStatus.COMPLETED,
            EVFStatus.REJECTED: ProcessingStatus.FAILED,
            EVFStatus.SUBMITTED: ProcessingStatus.COMPLETED,
            EVFStatus.ARCHIVED: ProcessingStatus.COMPLETED,
        }
        return mapping.get(evf_status, ProcessingStatus.PENDING)

    def _infer_current_step(self, project: EVFProject) -> ProcessingStep:
        """Infer current processing step from project state."""
        if not project.processing_start_time:
            return ProcessingStep.INITIALIZING

        if project.valf is None:
            return ProcessingStep.CALCULATING_FINANCIALS

        if project.compliance_status == ComplianceStatus.NOT_VALIDATED:
            return ProcessingStep.VALIDATING_COMPLIANCE

        if project.processing_end_time:
            return ProcessingStep.COMPLETED

        return ProcessingStep.GENERATING_NARRATIVE

    def _calculate_progress_from_status(self, status: EVFStatus) -> float:
        """Calculate approximate progress percentage from status."""
        mapping = {
            EVFStatus.DRAFT: 0.0,
            EVFStatus.UPLOADING: 10.0,
            EVFStatus.VALIDATING: 20.0,
            EVFStatus.PROCESSING: 50.0,
            EVFStatus.REVIEW: 90.0,
            EVFStatus.APPROVED: 100.0,
            EVFStatus.REJECTED: 100.0,
            EVFStatus.SUBMITTED: 100.0,
            EVFStatus.ARCHIVED: 100.0,
        }
        return mapping.get(status, 0.0)
