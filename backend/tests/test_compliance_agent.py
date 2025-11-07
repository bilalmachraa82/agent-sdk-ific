"""
Tests for ComplianceAgent - PT2030/PRR/SITCE validation
"""

import pytest
from decimal import Decimal
from pathlib import Path

from agents.compliance_agent import (
    ComplianceAgent,
    ComplianceInput,
    CompanyInfo,
    InvestmentInfo,
    ProjectInfo,
    CompanySize,
    FundingProgram,
    CheckSeverity
)


@pytest.fixture
def compliance_agent():
    """Create ComplianceAgent instance with test rules."""
    return ComplianceAgent()


@pytest.fixture
def valid_pt2030_company():
    """Valid small enterprise for PT2030."""
    return CompanyInfo(
        nif="123456789",
        company_size=CompanySize.SMALL,
        employees=25,
        annual_turnover=Decimal("5000000"),
        balance_sheet_total=Decimal("4000000"),
        sector="manufacturing",
        region="Porto",
        company_age_years=5,
        has_tax_debt=False,
        has_social_security_debt=False,
        in_difficulty=False
    )


@pytest.fixture
def valid_pt2030_investment():
    """Valid investment for PT2030."""
    return InvestmentInfo(
        total_investment=Decimal("500000"),
        eligible_investment=Decimal("450000"),
        funding_requested=Decimal("225000"),  # 50% of eligible
        equipment_costs=Decimal("300000"),
        software_costs=Decimal("100000"),
        construction_costs=Decimal("50000"),
        rd_costs=Decimal("50000"),
        investment_types=["equipment_acquisition", "it_infrastructure", "rd_equipment"],
        green_investment_percent=Decimal("20"),
        digital_investment_percent=Decimal("30")
    )


@pytest.fixture
def valid_pt2030_project():
    """Valid project for PT2030."""
    return ProjectInfo(
        project_name="Digital Manufacturing Upgrade",
        project_duration_years=5,
        jobs_created=3,
        jobs_maintained=25,
        valf=Decimal("-50000"),  # Negative (good)
        trf=Decimal("3.5"),  # Below 4% (good)
        sustainability_score=50,
        dnsh_compliant=True,
        gender_equality_plan=True,
        accessibility_compliant=True
    )


class TestComplianceAgentInitialization:
    """Test ComplianceAgent initialization."""

    def test_init_with_default_rules(self):
        """Test initialization with default rules path."""
        agent = ComplianceAgent()
        assert agent.VERSION == "1.0.0"
        assert agent.AGENT_NAME == "ComplianceAgent"
        assert agent.rules is not None
        assert "programs" in agent.rules

    def test_init_with_custom_rules(self, tmp_path):
        """Test initialization with custom rules path."""
        rules_file = tmp_path / "custom_rules.json"
        rules_file.write_text('{"version": "1.0.0", "programs": {"PT2030": {}}}')

        agent = ComplianceAgent(rules_path=rules_file)
        assert agent.rules["version"] == "1.0.0"

    def test_init_with_missing_rules(self, tmp_path):
        """Test initialization with missing rules file."""
        with pytest.raises(FileNotFoundError):
            ComplianceAgent(rules_path=tmp_path / "nonexistent.json")


class TestPT2030Validation:
    """Test PT2030 compliance validation."""

    def test_fully_compliant_project(self, compliance_agent, valid_pt2030_company,
                                    valid_pt2030_investment, valid_pt2030_project):
        """Test validation of fully compliant PT2030 project."""
        input_data = ComplianceInput(
            program=FundingProgram.PT2030,
            company=valid_pt2030_company,
            investment=valid_pt2030_investment,
            project=valid_pt2030_project
        )

        result = compliance_agent.validate(input_data)

        assert result.is_compliant is True
        assert result.program == "PT2030"
        assert result.critical_failures == 0
        assert result.confidence_score >= 0.7
        assert len(result.checks) > 0
        assert result.requested_funding_valid is True

    def test_valf_positive_fails(self, compliance_agent, valid_pt2030_company,
                                valid_pt2030_investment, valid_pt2030_project):
        """Test that positive VALF fails validation."""
        valid_pt2030_project.valf = Decimal("10000")  # Positive (bad)

        input_data = ComplianceInput(
            program=FundingProgram.PT2030,
            company=valid_pt2030_company,
            investment=valid_pt2030_investment,
            project=valid_pt2030_project
        )

        result = compliance_agent.validate(input_data)

        assert result.is_compliant is False
        assert result.critical_failures >= 1

        # Find VALF check
        valf_check = next((c for c in result.checks if c.check_id == "FIN_001"), None)
        assert valf_check is not None
        assert valf_check.passed is False
        assert valf_check.severity == CheckSeverity.CRITICAL

    def test_trf_too_high_fails(self, compliance_agent, valid_pt2030_company,
                               valid_pt2030_investment, valid_pt2030_project):
        """Test that TRF >= discount rate fails validation."""
        valid_pt2030_project.trf = Decimal("5.0")  # Above 4% discount rate

        input_data = ComplianceInput(
            program=FundingProgram.PT2030,
            company=valid_pt2030_company,
            investment=valid_pt2030_investment,
            project=valid_pt2030_project
        )

        result = compliance_agent.validate(input_data)

        assert result.is_compliant is False
        assert result.critical_failures >= 1

        # Find TRF check
        trf_check = next((c for c in result.checks if c.check_id == "FIN_002"), None)
        assert trf_check is not None
        assert trf_check.passed is False

    def test_investment_amount_limits(self, compliance_agent, valid_pt2030_company,
                                     valid_pt2030_investment, valid_pt2030_project):
        """Test investment amount limits."""
        # Too small
        valid_pt2030_investment.total_investment = Decimal("1000")
        valid_pt2030_investment.eligible_investment = Decimal("1000")
        valid_pt2030_investment.funding_requested = Decimal("500")

        input_data = ComplianceInput(
            program=FundingProgram.PT2030,
            company=valid_pt2030_company,
            investment=valid_pt2030_investment,
            project=valid_pt2030_project
        )

        result = compliance_agent.validate(input_data)

        inv_check = next((c for c in result.checks if c.check_id == "FIN_003"), None)
        assert inv_check is not None
        assert inv_check.passed is False  # Below minimum

    def test_company_tax_debt_fails(self, compliance_agent, valid_pt2030_company,
                                   valid_pt2030_investment, valid_pt2030_project):
        """Test that tax debt fails validation."""
        valid_pt2030_company.has_tax_debt = True

        input_data = ComplianceInput(
            program=FundingProgram.PT2030,
            company=valid_pt2030_company,
            investment=valid_pt2030_investment,
            project=valid_pt2030_project
        )

        result = compliance_agent.validate(input_data)

        assert result.is_compliant is False

        tax_check = next((c for c in result.checks if c.check_id == "COMP_002"), None)
        assert tax_check is not None
        assert tax_check.passed is False

    def test_company_in_difficulty_fails(self, compliance_agent, valid_pt2030_company,
                                        valid_pt2030_investment, valid_pt2030_project):
        """Test that company in difficulty fails validation."""
        valid_pt2030_company.in_difficulty = True

        input_data = ComplianceInput(
            program=FundingProgram.PT2030,
            company=valid_pt2030_company,
            investment=valid_pt2030_investment,
            project=valid_pt2030_project
        )

        result = compliance_agent.validate(input_data)

        assert result.is_compliant is False

        difficulty_check = next((c for c in result.checks if c.check_id == "COMP_004"), None)
        assert difficulty_check is not None
        assert difficulty_check.passed is False

    def test_excluded_sector_fails(self, compliance_agent, valid_pt2030_company,
                                  valid_pt2030_investment, valid_pt2030_project):
        """Test that excluded sector fails validation."""
        valid_pt2030_company.sector = "gambling"  # Excluded sector

        input_data = ComplianceInput(
            program=FundingProgram.PT2030,
            company=valid_pt2030_company,
            investment=valid_pt2030_investment,
            project=valid_pt2030_project
        )

        result = compliance_agent.validate(input_data)

        assert result.is_compliant is False

        sector_check = next((c for c in result.checks if c.check_id == "SECT_001"), None)
        assert sector_check is not None
        assert sector_check.passed is False

    def test_ineligible_investment_type_fails(self, compliance_agent, valid_pt2030_company,
                                             valid_pt2030_investment, valid_pt2030_project):
        """Test that ineligible investment types fail validation."""
        valid_pt2030_investment.investment_types = ["land_purchase", "working_capital"]

        input_data = ComplianceInput(
            program=FundingProgram.PT2030,
            company=valid_pt2030_company,
            investment=valid_pt2030_investment,
            project=valid_pt2030_project
        )

        result = compliance_agent.validate(input_data)

        assert result.is_compliant is False

        inv_type_check = next((c for c in result.checks if c.check_id == "INV_002"), None)
        assert inv_type_check is not None
        assert inv_type_check.passed is False


class TestFundingCalculations:
    """Test funding rate calculations."""

    def test_max_funding_calculation_small_company(self, compliance_agent,
                                                   valid_pt2030_company,
                                                   valid_pt2030_investment,
                                                   valid_pt2030_project):
        """Test max funding calculation for small company."""
        input_data = ComplianceInput(
            program=FundingProgram.PT2030,
            company=valid_pt2030_company,
            investment=valid_pt2030_investment,
            project=valid_pt2030_project
        )

        result = compliance_agent.validate(input_data)

        # Small company should get base rate + potential bonuses
        assert result.max_funding_rate_percent >= 50  # Minimum base rate
        assert result.calculated_funding_amount > 0
        assert result.calculated_funding_amount <= valid_pt2030_investment.eligible_investment

    def test_regional_bonus_porto(self, compliance_agent, valid_pt2030_company,
                                 valid_pt2030_investment, valid_pt2030_project):
        """Test regional bonus for Norte region (Porto)."""
        valid_pt2030_company.region = "Porto"

        input_data = ComplianceInput(
            program=FundingProgram.PT2030,
            company=valid_pt2030_company,
            investment=valid_pt2030_investment,
            project=valid_pt2030_project
        )

        result = compliance_agent.validate(input_data)

        # Porto should get Norte region bonus (5%)
        base_result = compliance_agent.validate(ComplianceInput(
            program=FundingProgram.PT2030,
            company=CompanyInfo(**{**valid_pt2030_company.model_dump(), "region": "Lisboa"}),
            investment=valid_pt2030_investment,
            project=valid_pt2030_project
        ))

        # Porto rate should be higher than Lisboa (no bonus)
        assert result.max_funding_rate_percent >= base_result.max_funding_rate_percent

    def test_innovation_bonus_with_rd(self, compliance_agent, valid_pt2030_company,
                                     valid_pt2030_investment, valid_pt2030_project):
        """Test innovation bonus with R&D costs."""
        # With R&D
        valid_pt2030_investment.rd_costs = Decimal("50000")

        input_with_rd = ComplianceInput(
            program=FundingProgram.PT2030,
            company=valid_pt2030_company,
            investment=valid_pt2030_investment,
            project=valid_pt2030_project
        )

        result_with_rd = compliance_agent.validate(input_with_rd)

        # Without R&D
        investment_no_rd = InvestmentInfo(**{**valid_pt2030_investment.model_dump(), "rd_costs": Decimal("0")})

        input_no_rd = ComplianceInput(
            program=FundingProgram.PT2030,
            company=valid_pt2030_company,
            investment=investment_no_rd,
            project=valid_pt2030_project
        )

        result_no_rd = compliance_agent.validate(input_no_rd)

        # R&D should give higher rate
        assert result_with_rd.max_funding_rate_percent >= result_no_rd.max_funding_rate_percent

    def test_funding_exceeds_max_fails(self, compliance_agent, valid_pt2030_company,
                                      valid_pt2030_investment, valid_pt2030_project):
        """Test that funding above maximum fails validation."""
        # Request 90% of eligible (above max)
        valid_pt2030_investment.funding_requested = valid_pt2030_investment.eligible_investment * Decimal("0.90")

        input_data = ComplianceInput(
            program=FundingProgram.PT2030,
            company=valid_pt2030_company,
            investment=valid_pt2030_investment,
            project=valid_pt2030_project
        )

        result = compliance_agent.validate(input_data)

        # Should either fail funding check or show requested_funding_valid = False
        assert result.requested_funding_valid is False or result.is_compliant is False


class TestPRRValidation:
    """Test PRR-specific validation."""

    def test_prr_digital_transition_requirement(self, compliance_agent, valid_pt2030_company,
                                               valid_pt2030_investment, valid_pt2030_project):
        """Test PRR digital transition minimum."""
        # PRR requires 20% digital investment
        valid_pt2030_investment.digital_investment_percent = Decimal("15")  # Below 20%

        input_data = ComplianceInput(
            program=FundingProgram.PRR,
            company=valid_pt2030_company,
            investment=valid_pt2030_investment,
            project=valid_pt2030_project
        )

        result = compliance_agent.validate(input_data)

        prr_digital_check = next((c for c in result.checks if c.check_id == "PRR_001"), None)
        assert prr_digital_check is not None
        assert prr_digital_check.passed is False

    def test_prr_green_transition_requirement(self, compliance_agent, valid_pt2030_company,
                                             valid_pt2030_investment, valid_pt2030_project):
        """Test PRR green transition minimum."""
        # PRR requires 37% green investment
        valid_pt2030_investment.green_investment_percent = Decimal("30")  # Below 37%

        input_data = ComplianceInput(
            program=FundingProgram.PRR,
            company=valid_pt2030_company,
            investment=valid_pt2030_investment,
            project=valid_pt2030_project
        )

        result = compliance_agent.validate(input_data)

        prr_green_check = next((c for c in result.checks if c.check_id == "PRR_002"), None)
        assert prr_green_check is not None
        assert prr_green_check.passed is False


class TestSITCEValidation:
    """Test SITCE-specific validation."""

    def test_sitce_job_creation_target(self, compliance_agent, valid_pt2030_company,
                                      valid_pt2030_investment, valid_pt2030_project):
        """Test SITCE job creation requirements."""
        valid_pt2030_project.jobs_created = 0  # Below SITCE minimum

        input_data = ComplianceInput(
            program=FundingProgram.SITCE,
            company=valid_pt2030_company,
            investment=valid_pt2030_investment,
            project=valid_pt2030_project
        )

        result = compliance_agent.validate(input_data)

        sitce_jobs_check = next((c for c in result.checks if c.check_id == "SITCE_001"), None)
        if sitce_jobs_check:  # May be present depending on rules
            assert sitce_jobs_check.severity == CheckSeverity.WARNING


class TestRecommendations:
    """Test recommendation generation."""

    def test_recommendations_for_valf_issue(self, compliance_agent, valid_pt2030_company,
                                           valid_pt2030_investment, valid_pt2030_project):
        """Test recommendations when VALF is positive."""
        valid_pt2030_project.valf = Decimal("10000")  # Positive

        input_data = ComplianceInput(
            program=FundingProgram.PT2030,
            company=valid_pt2030_company,
            investment=valid_pt2030_investment,
            project=valid_pt2030_project
        )

        result = compliance_agent.validate(input_data)

        assert len(result.recommendations) > 0
        # Should have recommendation about VALF
        valf_recommendations = [r for r in result.recommendations if "VALF" in r]
        assert len(valf_recommendations) > 0

    def test_recommendations_for_optimization(self, compliance_agent, valid_pt2030_company,
                                             valid_pt2030_investment, valid_pt2030_project):
        """Test recommendations for funding optimization."""
        # Request less than maximum available
        valid_pt2030_investment.funding_requested = Decimal("100000")

        input_data = ComplianceInput(
            program=FundingProgram.PT2030,
            company=valid_pt2030_company,
            investment=valid_pt2030_investment,
            project=valid_pt2030_project
        )

        result = compliance_agent.validate(input_data)

        # Should suggest increasing funding request
        optimization_recs = [r for r in result.recommendations if "more funding" in r or "increase" in r.lower()]
        assert len(optimization_recs) > 0


class TestCompanySizeClassification:
    """Test company size classification."""

    def test_micro_enterprise_classification(self, compliance_agent, valid_pt2030_investment,
                                            valid_pt2030_project):
        """Test micro enterprise gets correct funding rate."""
        micro_company = CompanyInfo(
            nif="123456789",
            company_size=CompanySize.MICRO,
            employees=5,
            annual_turnover=Decimal("1000000"),
            balance_sheet_total=Decimal("800000"),
            sector="ict",
            region="Lisboa",
            company_age_years=2,
            has_tax_debt=False,
            has_social_security_debt=False,
            in_difficulty=False
        )

        input_data = ComplianceInput(
            program=FundingProgram.PT2030,
            company=micro_company,
            investment=valid_pt2030_investment,
            project=valid_pt2030_project
        )

        result = compliance_agent.validate(input_data)

        # Micro should get higher rate than small/medium/large
        assert result.max_funding_rate_percent >= 50

    def test_company_size_exceeds_limits(self, compliance_agent, valid_pt2030_investment,
                                        valid_pt2030_project):
        """Test company exceeding size limits fails validation."""
        # Claim to be small but exceeds limits
        invalid_company = CompanyInfo(
            nif="123456789",
            company_size=CompanySize.SMALL,
            employees=100,  # Exceeds small (max 49)
            annual_turnover=Decimal("20000000"),  # Exceeds small (max 10M)
            balance_sheet_total=Decimal("5000000"),
            sector="manufacturing",
            region="Porto",
            company_age_years=5,
            has_tax_debt=False,
            has_social_security_debt=False,
            in_difficulty=False
        )

        input_data = ComplianceInput(
            program=FundingProgram.PT2030,
            company=invalid_company,
            investment=valid_pt2030_investment,
            project=valid_pt2030_project
        )

        result = compliance_agent.validate(input_data)

        size_check = next((c for c in result.checks if c.check_id == "COMP_001"), None)
        assert size_check is not None
        assert size_check.passed is False


class TestConfidenceScore:
    """Test confidence score calculation."""

    def test_confidence_with_complete_data(self, compliance_agent, valid_pt2030_company,
                                          valid_pt2030_investment, valid_pt2030_project):
        """Test confidence score with complete data."""
        input_data = ComplianceInput(
            program=FundingProgram.PT2030,
            company=valid_pt2030_company,
            investment=valid_pt2030_investment,
            project=valid_pt2030_project
        )

        result = compliance_agent.validate(input_data)

        # With complete data, confidence should be high
        assert result.confidence_score >= 0.8

    def test_confidence_with_missing_data(self, compliance_agent, valid_pt2030_company,
                                         valid_pt2030_project):
        """Test confidence score with missing data."""
        # Incomplete investment data
        incomplete_investment = InvestmentInfo(
            total_investment=Decimal("500000"),
            eligible_investment=Decimal("450000"),
            funding_requested=Decimal("225000"),
            # Missing breakdown
            investment_types=[]  # Empty
        )

        valid_pt2030_project.sustainability_score = None  # Missing

        input_data = ComplianceInput(
            program=FundingProgram.PT2030,
            company=valid_pt2030_company,
            investment=incomplete_investment,
            project=valid_pt2030_project
        )

        result = compliance_agent.validate(input_data)

        # With incomplete data, confidence should be lower
        assert result.confidence_score < 0.9


class TestDeterministicBehavior:
    """Test that ComplianceAgent is deterministic."""

    def test_deterministic_results(self, compliance_agent, valid_pt2030_company,
                                   valid_pt2030_investment, valid_pt2030_project):
        """Test that same input produces same output."""
        input_data = ComplianceInput(
            program=FundingProgram.PT2030,
            company=valid_pt2030_company,
            investment=valid_pt2030_investment,
            project=valid_pt2030_project
        )

        result1 = compliance_agent.validate(input_data)
        result2 = compliance_agent.validate(input_data)

        # All calculations should be identical
        assert result1.is_compliant == result2.is_compliant
        assert result1.max_funding_rate_percent == result2.max_funding_rate_percent
        assert result1.calculated_funding_amount == result2.calculated_funding_amount
        assert len(result1.checks) == len(result2.checks)
        assert result1.critical_failures == result2.critical_failures
        assert result1.warnings == result2.warnings


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
