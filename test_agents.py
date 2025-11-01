"""
FundAI Test Suite
Basic tests for orchestrator and agents
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from core.schemas import (
    CompanyInput,
    ProjectInput,
    BudgetInput,
    ImpactMetrics,
    CompanySize,
    NUTSII,
)
from agents.orchestrator import IFICOrchestrator


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def sample_company_input():
    """Sample company input for testing"""
    return CompanyInput(
        nome="TechStartup Lda",
        url="https://techstartup.pt",
        nif="123456789",
        cae="62010",
        nuts_ii=NUTSII.PT17,
        certificacao_pme=True,
        dimensao=CompanySize.PEQUENA,
    )


@pytest.fixture
def sample_project_input():
    """Sample project input for testing"""
    return ProjectInput(
        objetivos="Deploy ML forecasting system for sales prediction",
        processos_alvo=["Sales", "Operations", "Analytics"],
        dados_disponiveis="3 years historical sales data, CRM records",
        inicio_previsto="2026-01",
        fim_previsto="2027-12",
        departamentos=["Sales", "IT"],
    )


@pytest.fixture
def sample_budget_input():
    """Sample budget input for testing"""
    return BudgetInput(
        teto_max_investimento=180_000,
        cofinanciamento_disponivel=45_000,
        preferencias=["SaaS", "RH", "Consultoria"],
    )


@pytest.fixture
def sample_impact_metrics():
    """Sample impact metrics for testing"""
    return ImpactMetrics(
        postos_trabalho_liquidos=2,
        crescimento_vab_percent=8.0,
        exportacoes_aumento_percent=5.0,
        inovacao_score=4.0,
    )


# ============================================================================
# ORCHESTRATOR TESTS
# ============================================================================

class TestIFICOrchestrator:
    """Test suite for main orchestrator"""

    def test_orchestrator_initialization(self):
        """Test orchestrator initializes with all subagents"""
        orchestrator = IFICOrchestrator()
        
        assert orchestrator.session_id is not None
        assert orchestrator.researcher is not None
        assert orchestrator.stack_intel is not None
        assert orchestrator.financial is not None
        assert orchestrator.writer is not None
        assert orchestrator.scorer is not None
        assert orchestrator.validator is not None

    def test_budget_gate_validation_pass(self, sample_budget_input):
        """Test budget gate validation with valid input"""
        orchestrator = IFICOrchestrator()
        
        # Should not raise exception
        orchestrator._validate_budget_gate(sample_budget_input)

    def test_budget_gate_validation_fail_too_low(self):
        """Test budget gate fails with investment < €5k"""
        orchestrator = IFICOrchestrator()
        
        budget = BudgetInput(
            teto_max_investimento=4_000,  # Below minimum
            cofinanciamento_disponivel=1_000,
            preferencias=[],
        )
        
        with pytest.raises(ValueError, match="inviável"):
            orchestrator._validate_budget_gate(budget)

    def test_budget_gate_validation_fail_cofinancing(self):
        """Test budget gate fails with insufficient cofinancing"""
        orchestrator = IFICOrchestrator()
        
        budget = BudgetInput(
            teto_max_investimento=100_000,
            cofinanciamento_disponivel=10_000,  # Less than 25%
            preferencias=[],
        )
        
        with pytest.raises(ValueError, match="Cofinanciamento insuficiente"):
            orchestrator._validate_budget_gate(budget)


# ============================================================================
# STACK INTELLIGENCE TESTS
# ============================================================================

class TestStackIntelligenceAgent:
    """Test suite for stack intelligence agent"""

    @pytest.mark.asyncio
    async def test_redundancy_detection_phc(self):
        """Test that PHC blocks redundant CRM tools"""
        from agents.stack_intel import StackIntelligenceAgent
        from anthropic import Anthropic
        
        agent = StackIntelligenceAgent(Mock(spec=Anthropic))
        
        analysis = await agent.analyze_stack(
            existing_stack=["PHC", "Microsoft 365"],
            industry_cae="70220",
            company_size=CompanySize.PEQUENA,
        )
        
        # PHC should block Monday.com, HubSpot CRM, Salesforce
        blocked = analysis["tools_blocked"]
        assert "Monday.com" in blocked
        assert "HubSpot CRM" in blocked
        assert "Salesforce" in blocked

    @pytest.mark.asyncio
    async def test_m365_blocks_collaboration_tools(self):
        """Test that Microsoft 365 blocks Slack, Notion, etc."""
        from agents.stack_intel import StackIntelligenceAgent
        from anthropic import Anthropic
        
        agent = StackIntelligenceAgent(Mock(spec=Anthropic))
        
        analysis = await agent.analyze_stack(
            existing_stack=["Microsoft 365"],
            industry_cae="62010",
            company_size=CompanySize.MEDIA,
        )
        
        blocked = analysis["tools_blocked"]
        assert "Slack" in blocked
        assert "Notion" in blocked
        assert "Trello" in blocked


# ============================================================================
# MERIT SCORING TESTS
# ============================================================================

class TestMeritScoringAgent:
    """Test suite for merit scoring agent"""

    @pytest.mark.asyncio
    async def test_merit_score_calculation(self, sample_impact_metrics):
        """Test MP = 0.5*A + 0.5*min(B1,B2) formula"""
        from agents import MeritScoringAgent
        from anthropic import Anthropic
        
        agent = MeritScoringAgent(Mock(spec=Anthropic))
        
        quality_indicators = {
            "financial_health": 4.0,
            "innovation_capacity": 4.0,
            "implementation_readiness": 4.0,
        }
        
        score = await agent.calculate_merit_score(
            project_quality_indicators=quality_indicators,
            impact_metrics=sample_impact_metrics,
        )
        
        # Check formula
        assert score.criterio_a_qualidade == 4.0  # Average of indicators
        assert score.merit_point_final >= 3.0  # Minimum eligible
        assert score.merit_point_final <= 5.0  # Maximum possible
        assert score.elegivel is True

    @pytest.mark.asyncio
    async def test_job_creation_bonus(self):
        """Test that job creation increases B1 score"""
        from agents import MeritScoringAgent
        from anthropic import Anthropic
        
        agent = MeritScoringAgent(Mock(spec=Anthropic))
        
        # Scenario 1: No jobs
        impact_no_jobs = ImpactMetrics(
            postos_trabalho_liquidos=0,
            crescimento_vab_percent=5.0,
        )
        
        score_no_jobs = await agent.calculate_merit_score(
            {"quality": 4.0},
            impact_no_jobs,
        )
        
        # Scenario 2: 2 jobs
        impact_with_jobs = ImpactMetrics(
            postos_trabalho_liquidos=2,
            crescimento_vab_percent=5.0,
        )
        
        score_with_jobs = await agent.calculate_merit_score(
            {"quality": 4.0},
            impact_with_jobs,
        )
        
        # MP should increase with job creation
        assert score_with_jobs.merit_point_final > score_no_jobs.merit_point_final
        assert score_with_jobs.criterio_b1_competitividade > score_no_jobs.criterio_b1_competitividade


# ============================================================================
# COMPLIANCE VALIDATION TESTS
# ============================================================================

class TestComplianceValidatorAgent:
    """Test suite for compliance validator"""

    @pytest.mark.asyncio
    async def test_compliance_check_all_pass(
        self,
        sample_company_input,
        sample_project_input,
        sample_budget_input,
    ):
        """Test compliance with all checks passing"""
        from agents import ComplianceValidatorAgent
        from anthropic import Anthropic
        from core.schemas import CompanyData
        
        agent = ComplianceValidatorAgent(Mock(spec=Anthropic))
        
        # Mock company data with all compliance OK
        company_data = CompanyData(
            nome="TechStartup",
            nif="123456789",
            cae="62010",
            nuts_ii=NUTSII.PT17,
            certificacao_pme=True,
            dimensao=CompanySize.PEQUENA,
            situacao_fiscal_regular=True,
            situacao_ss_regular=True,
            situacao_rcbe_regular=True,
        )
        
        report = await agent.validate_compliance(
            company_data=company_data,
            project_input=sample_project_input,
            budget_scenarios=[],
            use_cases=[],
        )
        
        assert report.overall_status == "pass"
        assert report.elegibilidade_ok is True
        assert report.rgpd_compliant is True
        assert report.dnsh_compliant is True


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

@pytest.mark.skip(reason="Integration test - requires API keys")
@pytest.mark.asyncio
async def test_full_application_processing(
    sample_company_input,
    sample_project_input,
    sample_budget_input,
    sample_impact_metrics,
):
    """End-to-end test of full application processing"""
    orchestrator = IFICOrchestrator()
    
    application = await orchestrator.process_application(
        company_input=sample_company_input,
        project_input=sample_project_input,
        budget_input=sample_budget_input,
        impact_metrics=sample_impact_metrics,
        user_id="test_user",
    )
    
    # Verify application structure
    assert application.application_id is not None
    assert application.status == "ready"
    assert application.company is not None
    assert len(application.budget_scenarios) == 3  # 3 tiers
    assert len(application.use_cases) > 0
    assert application.merit_scoring.merit_point_final >= 3.0
    assert application.compliance.overall_status in ["pass", "conditional"]
    assert len(application.artifacts) > 0


# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
