"""
Tests for FinancialAgent - Deterministic Financial Calculations
"""

import pytest
from decimal import Decimal
from backend.agents.financial_agent import (
    FinancialAgent,
    FinancialInput,
    CashFlow,
    FinancialOutput
)


class TestFinancialAgent:
    """Test suite for FinancialAgent."""

    @pytest.fixture
    def agent(self):
        """Create FinancialAgent instance."""
        return FinancialAgent(discount_rate=0.04)

    @pytest.fixture
    def sample_input_profitable(self):
        """
        Sample input for a PROFITABLE project (VALF > 0, TRF > 4%).
        This should NOT meet PT2030 requirements.
        """
        return FinancialInput(
            project_name="Highly Profitable Project",
            project_duration_years=5,
            discount_rate=Decimal("0.04"),
            total_investment=Decimal("100000"),
            eligible_investment=Decimal("80000"),
            funding_requested=Decimal("40000"),
            cash_flows=[
                # Year 0: Initial investment
                CashFlow(
                    year=0,
                    revenue=Decimal("0"),
                    operating_costs=Decimal("0"),
                    capex=Decimal("100000"),
                    depreciation=Decimal("0"),
                    working_capital_change=Decimal("0")
                ),
                # Year 1-5: Operations with high returns
                CashFlow(
                    year=1,
                    revenue=Decimal("80000"),
                    operating_costs=Decimal("30000"),
                    capex=Decimal("0"),
                    depreciation=Decimal("20000"),
                    working_capital_change=Decimal("0")
                ),
                CashFlow(
                    year=2,
                    revenue=Decimal("100000"),
                    operating_costs=Decimal("35000"),
                    capex=Decimal("0"),
                    depreciation=Decimal("20000"),
                    working_capital_change=Decimal("0")
                ),
                CashFlow(
                    year=3,
                    revenue=Decimal("120000"),
                    operating_costs=Decimal("40000"),
                    capex=Decimal("0"),
                    depreciation=Decimal("20000"),
                    working_capital_change=Decimal("0")
                ),
                CashFlow(
                    year=4,
                    revenue=Decimal("130000"),
                    operating_costs=Decimal("45000"),
                    capex=Decimal("0"),
                    depreciation=Decimal("20000"),
                    working_capital_change=Decimal("0")
                ),
                CashFlow(
                    year=5,
                    revenue=Decimal("140000"),
                    operating_costs=Decimal("50000"),
                    capex=Decimal("0"),
                    depreciation=Decimal("20000"),
                    working_capital_change=Decimal("0")
                )
            ]
        )

    @pytest.fixture
    def sample_input_pt2030_compliant(self):
        """
        Sample input for PT2030-compliant project (VALF < 0, TRF < 4%).
        This project needs funding to be viable.
        """
        return FinancialInput(
            project_name="PT2030 Eligible Project",
            project_duration_years=5,
            discount_rate=Decimal("0.04"),
            total_investment=Decimal("500000"),
            eligible_investment=Decimal("500000"),
            funding_requested=Decimal("250000"),
            cash_flows=[
                # Year 0: Initial investment
                CashFlow(
                    year=0,
                    revenue=Decimal("0"),
                    operating_costs=Decimal("0"),
                    capex=Decimal("500000"),
                    depreciation=Decimal("0"),
                    working_capital_change=Decimal("0")
                ),
                # Year 1-5: Operations with moderate returns
                CashFlow(
                    year=1,
                    revenue=Decimal("50000"),
                    operating_costs=Decimal("30000"),
                    capex=Decimal("0"),
                    depreciation=Decimal("100000"),
                    working_capital_change=Decimal("0")
                ),
                CashFlow(
                    year=2,
                    revenue=Decimal("60000"),
                    operating_costs=Decimal("32000"),
                    capex=Decimal("0"),
                    depreciation=Decimal("100000"),
                    working_capital_change=Decimal("0")
                ),
                CashFlow(
                    year=3,
                    revenue=Decimal("70000"),
                    operating_costs=Decimal("34000"),
                    capex=Decimal("0"),
                    depreciation=Decimal("100000"),
                    working_capital_change=Decimal("0")
                ),
                CashFlow(
                    year=4,
                    revenue=Decimal("80000"),
                    operating_costs=Decimal("36000"),
                    capex=Decimal("0"),
                    depreciation=Decimal("100000"),
                    working_capital_change=Decimal("0")
                ),
                CashFlow(
                    year=5,
                    revenue=Decimal("90000"),
                    operating_costs=Decimal("38000"),
                    capex=Decimal("0"),
                    depreciation=Decimal("100000"),
                    working_capital_change=Decimal("0")
                )
            ]
        )

    def test_agent_initialization(self, agent):
        """Test agent initializes correctly."""
        assert agent.discount_rate == 0.04
        assert agent.AGENT_NAME == "FinancialAgent"
        assert agent.VERSION == "1.0.0"

    def test_calculate_valf_profitable_project(self, agent, sample_input_profitable):
        """Test VALF calculation for profitable project."""
        result = agent.calculate(sample_input_profitable)

        # Profitable project should have positive VALF
        assert result.valf > 0
        print(f"\nProfitable Project VALF: {result.valf} EUR")

        # Should NOT be PT2030 compliant
        assert result.pt2030_compliant is False

    def test_calculate_trf_profitable_project(self, agent, sample_input_profitable):
        """Test TRF calculation for profitable project."""
        result = agent.calculate(sample_input_profitable)

        # Profitable project should have TRF > discount rate (4%)
        assert result.trf > Decimal("4.0")
        print(f"\nProfitable Project TRF: {result.trf}%")

        # Should NOT be PT2030 compliant
        assert result.pt2030_compliant is False

    def test_calculate_valf_pt2030_compliant(self, agent, sample_input_pt2030_compliant):
        """Test VALF calculation for PT2030-compliant project."""
        result = agent.calculate(sample_input_pt2030_compliant)

        # PT2030-compliant project should have negative VALF
        assert result.valf < 0
        print(f"\nPT2030 Compliant Project VALF: {result.valf} EUR")

        # Should be PT2030 compliant
        assert result.pt2030_compliant is True

    def test_calculate_trf_pt2030_compliant(self, agent, sample_input_pt2030_compliant):
        """Test TRF calculation for PT2030-compliant project."""
        result = agent.calculate(sample_input_pt2030_compliant)

        # PT2030-compliant project should have TRF < discount rate (4%)
        assert result.trf < Decimal("4.0")
        print(f"\nPT2030 Compliant Project TRF: {result.trf}%")

        # Should be PT2030 compliant
        assert result.pt2030_compliant is True

    def test_payback_period(self, agent, sample_input_profitable):
        """Test payback period calculation."""
        result = agent.calculate(sample_input_profitable)

        # Profitable project should recover investment
        assert result.payback_period is not None
        assert result.payback_period > 0
        print(f"\nPayback Period: {result.payback_period} years")

    def test_financial_ratios(self, agent, sample_input_profitable):
        """Test financial ratios calculation."""
        result = agent.calculate(sample_input_profitable)

        ratios = result.financial_ratios

        # Check that ratios are calculated
        assert ratios.gross_margin is not None
        assert ratios.operating_margin is not None
        assert ratios.roi is not None

        print(f"\nFinancial Ratios:")
        print(f"  Gross Margin: {ratios.gross_margin}%")
        print(f"  Operating Margin: {ratios.operating_margin}%")
        print(f"  ROI: {ratios.roi}%")
        print(f"  EBITDA Coverage: {ratios.ebitda_coverage}")
        print(f"  FCF Coverage: {ratios.fcf_coverage}")

    def test_compliance_notes(self, agent, sample_input_pt2030_compliant):
        """Test compliance notes generation."""
        result = agent.calculate(sample_input_pt2030_compliant)

        # Should have compliance notes
        assert len(result.compliance_notes) > 0

        print(f"\nCompliance Notes:")
        for note in result.compliance_notes:
            print(f"  {note}")

    def test_audit_trail(self, agent, sample_input_profitable):
        """Test audit trail generation."""
        result = agent.calculate(sample_input_profitable)

        # Should have audit trail
        assert result.input_hash is not None
        assert len(result.input_hash) == 64  # SHA-256 hex digest

        assert result.calculation_timestamp is not None
        assert result.calculation_method == "numpy-financial"
        assert len(result.assumptions) > 0

        print(f"\nAudit Trail:")
        print(f"  Input Hash: {result.input_hash}")
        print(f"  Timestamp: {result.calculation_timestamp}")
        print(f"  Method: {result.calculation_method}")

    def test_deterministic_calculations(self, agent, sample_input_profitable):
        """Test that calculations are deterministic (same input = same output)."""
        result1 = agent.calculate(sample_input_profitable)
        result2 = agent.calculate(sample_input_profitable)

        # VALF and TRF should be identical
        assert result1.valf == result2.valf
        assert result1.trf == result2.trf
        assert result1.input_hash == result2.input_hash

        print(f"\n✅ Calculations are deterministic!")

    def test_validate_input_success(self, agent, sample_input_profitable):
        """Test input validation for valid data."""
        is_valid, errors = agent.validate_input(sample_input_profitable)

        assert is_valid is True
        assert len(errors) == 0

    def test_validate_input_missing_year_zero(self, agent):
        """Test input validation catches missing year 0."""
        invalid_input = FinancialInput(
            project_name="Invalid Project",
            project_duration_years=2,
            discount_rate=Decimal("0.04"),
            total_investment=Decimal("100000"),
            eligible_investment=Decimal("100000"),
            funding_requested=Decimal("50000"),
            cash_flows=[
                # Missing year 0!
                CashFlow(
                    year=1,
                    revenue=Decimal("50000"),
                    operating_costs=Decimal("30000"),
                    capex=Decimal("0"),
                    depreciation=Decimal("20000"),
                    working_capital_change=Decimal("0")
                ),
                CashFlow(
                    year=2,
                    revenue=Decimal("60000"),
                    operating_costs=Decimal("32000"),
                    capex=Decimal("0"),
                    depreciation=Decimal("20000"),
                    working_capital_change=Decimal("0")
                )
            ]
        )

        is_valid, errors = agent.validate_input(invalid_input)

        assert is_valid is False
        assert "year 0" in errors[0].lower()

    def test_total_fcf_calculation(self, agent, sample_input_profitable):
        """Test total and average FCF calculations."""
        result = agent.calculate(sample_input_profitable)

        # Total FCF should be positive
        assert result.total_fcf > 0
        assert result.average_annual_fcf > 0

        print(f"\nCash Flow Metrics:")
        print(f"  Total FCF: {result.total_fcf} EUR")
        print(f"  Average Annual FCF: {result.average_annual_fcf} EUR")

    def test_cashflow_calculations(self):
        """Test CashFlow model calculations."""
        cf = CashFlow(
            year=1,
            revenue=Decimal("100000"),
            operating_costs=Decimal("60000"),
            capex=Decimal("10000"),
            depreciation=Decimal("5000"),
            working_capital_change=Decimal("2000")
        )

        # Test EBITDA
        assert cf.ebitda == Decimal("40000")  # 100k - 60k

        # Test EBIT
        assert cf.ebit == Decimal("35000")  # EBITDA - depreciation

        # Test FCF
        assert cf.free_cash_flow == Decimal("28000")  # EBITDA - CAPEX - WC change


# Integration test with realistic PT2030 scenario
class TestPT2030Scenario:
    """Test realistic PT2030 funding scenarios."""

    def test_manufacturing_digitalization_project(self):
        """
        Test a realistic manufacturing digitalization project
        seeking PT2030 funding for Industry 4.0 transformation.
        """
        agent = FinancialAgent(discount_rate=0.04)

        # Manufacturing company investing €1M in automation
        # Expects modest efficiency gains over 10 years
        input_data = FinancialInput(
            project_name="Industry 4.0 Digital Transformation",
            project_duration_years=10,
            discount_rate=Decimal("0.04"),
            total_investment=Decimal("1000000"),
            eligible_investment=Decimal("900000"),  # 90% eligible
            funding_requested=Decimal("450000"),  # 50% funding rate
            cash_flows=[
                CashFlow(year=0, revenue=Decimal("0"), operating_costs=Decimal("0"),
                        capex=Decimal("1000000"), depreciation=Decimal("0"), working_capital_change=Decimal("0")),
                CashFlow(year=1, revenue=Decimal("100000"), operating_costs=Decimal("60000"),
                        capex=Decimal("0"), depreciation=Decimal("100000"), working_capital_change=Decimal("0")),
                CashFlow(year=2, revenue=Decimal("120000"), operating_costs=Decimal("65000"),
                        capex=Decimal("0"), depreciation=Decimal("100000"), working_capital_change=Decimal("0")),
                CashFlow(year=3, revenue=Decimal("140000"), operating_costs=Decimal("70000"),
                        capex=Decimal("0"), depreciation=Decimal("100000"), working_capital_change=Decimal("0")),
                CashFlow(year=4, revenue=Decimal("160000"), operating_costs=Decimal("75000"),
                        capex=Decimal("0"), depreciation=Decimal("100000"), working_capital_change=Decimal("0")),
                CashFlow(year=5, revenue=Decimal("180000"), operating_costs=Decimal("80000"),
                        capex=Decimal("0"), depreciation=Decimal("100000"), working_capital_change=Decimal("0")),
                CashFlow(year=6, revenue=Decimal("190000"), operating_costs=Decimal("82000"),
                        capex=Decimal("0"), depreciation=Decimal("100000"), working_capital_change=Decimal("0")),
                CashFlow(year=7, revenue=Decimal("200000"), operating_costs=Decimal("84000"),
                        capex=Decimal("0"), depreciation=Decimal("100000"), working_capital_change=Decimal("0")),
                CashFlow(year=8, revenue=Decimal("210000"), operating_costs=Decimal("86000"),
                        capex=Decimal("0"), depreciation=Decimal("100000"), working_capital_change=Decimal("0")),
                CashFlow(year=9, revenue=Decimal("220000"), operating_costs=Decimal("88000"),
                        capex=Decimal("0"), depreciation=Decimal("100000"), working_capital_change=Decimal("0")),
                CashFlow(year=10, revenue=Decimal("230000"), operating_costs=Decimal("90000"),
                        capex=Decimal("0"), depreciation=Decimal("100000"), working_capital_change=Decimal("0"))
            ]
        )

        result = agent.calculate(input_data)

        print(f"\n" + "="*60)
        print(f"PT2030 Industry 4.0 Project Analysis")
        print(f"="*60)
        print(f"Investment: €{input_data.total_investment:,}")
        print(f"Funding Requested: €{input_data.funding_requested:,}")
        print(f"\nFinancial Metrics:")
        print(f"  VALF (NPV): €{result.valf:,}")
        print(f"  TRF (IRR): {result.trf}%")
        print(f"  Payback Period: {result.payback_period} years")
        print(f"  Total FCF: €{result.total_fcf:,}")
        print(f"\nPT2030 Compliance: {'✅ YES' if result.pt2030_compliant else '❌ NO'}")
        print(f"\nCompliance Notes:")
        for note in result.compliance_notes:
            print(f"  {note}")
        print(f"="*60)

        # For PT2030, we expect VALF < 0 (project needs funding)
        # This particular scenario should be close to breakeven or slightly negative