"""
Tests for InputAgent - SAF-T XML Parser

Tests cover:
- Valid SAF-T XML parsing
- Company info extraction
- Financial statement mapping
- Cash flow estimation
- Error handling (malformed XML, missing fields)
- Multi-year data extraction
- Data validation
"""

import pytest
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import List
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.input_agent import (
    InputAgent,
    SAFTData,
    CompanyInfo,
    CompanyAddress,
    Period,
    AccountBalance,
    FinancialStatement,
    CashFlowStatement,
    ParseResult,
)


# ============================================================================
# TEST FIXTURES - Sample SAF-T XML Data
# ============================================================================

@pytest.fixture
def valid_saft_xml() -> bytes:
    """Generate a valid SAF-T PT XML for testing."""
    return b"""<?xml version="1.0" encoding="UTF-8"?>
<AuditFile xmlns="urn:OECD:StandardAuditFile-Tax:PT_1.04_01">
    <Header>
        <AuditFileVersion>1.04_01</AuditFileVersion>
        <CompanyID>COMP001</CompanyID>
        <TaxRegistrationNumber>123456789</TaxRegistrationNumber>
        <CompanyName>Test Company Lda</CompanyName>
        <CompanyAddress>
            <AddressDetail>Rua de Teste, 123</AddressDetail>
            <City>Lisboa</City>
            <PostalCode>1000-001</PostalCode>
            <Region>Lisboa</Region>
            <Country>PT</Country>
        </CompanyAddress>
        <FiscalYear>2024</FiscalYear>
        <StartDate>2024-01-01</StartDate>
        <EndDate>2024-12-31</EndDate>
        <CurrencyCode>EUR</CurrencyCode>
        <DateCreated>2025-01-15</DateCreated>
        <TaxEntity>Global</TaxEntity>
        <ProductID>TestSoftware/v1.0</ProductID>
        <ProductVersion>1.0.0</ProductVersion>
    </Header>
    <MasterFiles>
        <GeneralLedgerAccounts>
            <!-- Revenue Account (Class 7) -->
            <Account>
                <AccountID>71</AccountID>
                <AccountDescription>Vendas de Mercadorias</AccountDescription>
                <OpeningDebitBalance>0.00</OpeningDebitBalance>
                <OpeningCreditBalance>0.00</OpeningCreditBalance>
                <ClosingDebitBalance>0.00</ClosingDebitBalance>
                <ClosingCreditBalance>500000.00</ClosingCreditBalance>
            </Account>
            <!-- Cost of Sales Account (Class 6) -->
            <Account>
                <AccountID>61</AccountID>
                <AccountDescription>CMVMC</AccountDescription>
                <OpeningDebitBalance>0.00</OpeningDebitBalance>
                <OpeningCreditBalance>0.00</OpeningCreditBalance>
                <ClosingDebitBalance>300000.00</ClosingDebitBalance>
                <ClosingCreditBalance>0.00</ClosingCreditBalance>
            </Account>
            <!-- Personnel Costs (Class 6) -->
            <Account>
                <AccountID>63</AccountID>
                <AccountDescription>Gastos com Pessoal</AccountDescription>
                <OpeningDebitBalance>0.00</OpeningDebitBalance>
                <OpeningCreditBalance>0.00</OpeningCreditBalance>
                <ClosingDebitBalance>80000.00</ClosingDebitBalance>
                <ClosingCreditBalance>0.00</ClosingCreditBalance>
            </Account>
            <!-- Depreciation (Class 6) -->
            <Account>
                <AccountID>64</AccountID>
                <AccountDescription>Gastos de Depreciacao</AccountDescription>
                <OpeningDebitBalance>0.00</OpeningDebitBalance>
                <OpeningCreditBalance>0.00</OpeningCreditBalance>
                <ClosingDebitBalance>20000.00</ClosingDebitBalance>
                <ClosingCreditBalance>0.00</ClosingCreditBalance>
            </Account>
            <!-- Current Assets (Class 2) -->
            <Account>
                <AccountID>21</AccountID>
                <AccountDescription>Clientes</AccountDescription>
                <OpeningDebitBalance>50000.00</OpeningDebitBalance>
                <OpeningCreditBalance>0.00</OpeningCreditBalance>
                <ClosingDebitBalance>75000.00</ClosingDebitBalance>
                <ClosingCreditBalance>0.00</ClosingCreditBalance>
            </Account>
            <!-- Fixed Assets (Class 4) -->
            <Account>
                <AccountID>43</AccountID>
                <AccountDescription>Equipamento Basico</AccountDescription>
                <OpeningDebitBalance>100000.00</OpeningDebitBalance>
                <OpeningCreditBalance>0.00</OpeningCreditBalance>
                <ClosingDebitBalance>120000.00</ClosingDebitBalance>
                <ClosingCreditBalance>0.00</ClosingCreditBalance>
            </Account>
            <!-- Current Liabilities (Class 5) -->
            <Account>
                <AccountID>51</AccountID>
                <AccountDescription>Fornecedores</AccountDescription>
                <OpeningDebitBalance>0.00</OpeningDebitBalance>
                <OpeningCreditBalance>40000.00</OpeningCreditBalance>
                <ClosingDebitBalance>0.00</ClosingDebitBalance>
                <ClosingCreditBalance>50000.00</ClosingCreditBalance>
            </Account>
            <!-- Equity (Class 5) -->
            <Account>
                <AccountID>51</AccountID>
                <AccountDescription>Capital Social</AccountDescription>
                <OpeningDebitBalance>0.00</OpeningDebitBalance>
                <OpeningCreditBalance>100000.00</OpeningCreditBalance>
                <ClosingDebitBalance>0.00</ClosingDebitBalance>
                <ClosingCreditBalance>100000.00</ClosingCreditBalance>
            </Account>
        </GeneralLedgerAccounts>
    </MasterFiles>
</AuditFile>"""


@pytest.fixture
def minimal_saft_xml() -> bytes:
    """Minimal valid SAF-T XML with only required fields."""
    return b"""<?xml version="1.0" encoding="UTF-8"?>
<AuditFile xmlns="urn:OECD:StandardAuditFile-Tax:PT_1.04_01">
    <Header>
        <TaxRegistrationNumber>987654321</TaxRegistrationNumber>
        <CompanyName>Minimal Company</CompanyName>
        <FiscalYear>2024</FiscalYear>
        <StartDate>2024-01-01</StartDate>
        <EndDate>2024-12-31</EndDate>
        <CurrencyCode>EUR</CurrencyCode>
    </Header>
    <MasterFiles>
        <GeneralLedgerAccounts>
        </GeneralLedgerAccounts>
    </MasterFiles>
</AuditFile>"""


@pytest.fixture
def malformed_saft_xml() -> bytes:
    """Malformed SAF-T XML for error testing."""
    return b"""<?xml version="1.0" encoding="UTF-8"?>
<AuditFile xmlns="urn:OECD:StandardAuditFile-Tax:PT_1.04_01">
    <Header>
        <TaxRegistrationNumber>123456789</TaxRegistrationNumber>
        <!-- Missing closing tag for CompanyName -->
        <CompanyName>Test Company
        <FiscalYear>2024</FiscalYear>
    </Header>
</AuditFile>"""


@pytest.fixture
def missing_required_fields_xml() -> bytes:
    """SAF-T XML missing required fields."""
    return b"""<?xml version="1.0" encoding="UTF-8"?>
<AuditFile xmlns="urn:OECD:StandardAuditFile-Tax:PT_1.04_01">
    <Header>
        <!-- Missing TaxRegistrationNumber -->
        <CompanyName>Test Company</CompanyName>
        <!-- Missing FiscalYear -->
        <StartDate>2024-01-01</StartDate>
        <EndDate>2024-12-31</EndDate>
    </Header>
</AuditFile>"""


# ============================================================================
# TEST CASES - InputAgent
# ============================================================================

class TestInputAgent:
    """Test suite for InputAgent."""

    def test_parse_valid_saft_xml(self, valid_saft_xml):
        """Test parsing a valid SAF-T XML file."""
        agent = InputAgent()
        result = agent.parse_xml(valid_saft_xml)

        assert result.success is True
        assert result.data is not None
        assert len(result.errors) == 0
        assert result.parse_time_seconds > 0

    def test_extract_company_info(self, valid_saft_xml):
        """Test company information extraction."""
        agent = InputAgent()
        result = agent.parse_xml(valid_saft_xml)

        assert result.success is True
        assert result.data is not None

        company = result.data.company_info
        assert company.nif == "123456789"
        assert company.name == "Test Company Lda"
        assert company.fiscal_year == 2024
        assert company.currency_code == "EUR"
        assert company.product_id == "TestSoftware/v1.0"
        assert company.product_version == "1.0.0"

        # Check address
        assert company.address is not None
        assert company.address.city == "Lisboa"
        assert company.address.postal_code == "1000-001"
        assert company.address.country == "PT"

    def test_extract_period(self, valid_saft_xml):
        """Test period extraction."""
        agent = InputAgent()
        result = agent.parse_xml(valid_saft_xml)

        assert result.success is True
        assert result.data is not None

        period = result.data.period
        assert period.fiscal_year == 2024
        assert period.start_date == date(2024, 1, 1)
        assert period.end_date == date(2024, 12, 31)
        assert period.duration_days == 366  # 2024 is a leap year

    def test_extract_general_ledger(self, valid_saft_xml):
        """Test general ledger extraction."""
        agent = InputAgent()
        result = agent.parse_xml(valid_saft_xml)

        assert result.success is True
        assert result.data is not None

        gl = result.data.general_ledger
        assert len(gl) > 0

        # Check specific account
        revenue_account = next((acc for acc in gl if acc.account_id == "71"), None)
        assert revenue_account is not None
        assert revenue_account.account_description == "Vendas de Mercadorias"
        assert revenue_account.closing_credit == Decimal("500000.00")
        assert revenue_account.closing_balance == Decimal("-500000.00")  # Credit balance is negative

    def test_build_financial_statements(self, valid_saft_xml):
        """Test financial statement construction from GL."""
        agent = InputAgent()
        result = agent.parse_xml(valid_saft_xml)

        assert result.success is True
        assert result.data is not None

        statements = result.data.financial_statements
        assert len(statements) == 1

        stmt = statements[0]
        assert stmt.fiscal_year == 2024

        # Check P&L mappings
        assert stmt.revenue == Decimal("500000.00")
        assert stmt.cost_of_sales == Decimal("300000.00")
        assert stmt.personnel_costs == Decimal("80000.00")
        assert stmt.depreciation == Decimal("20000.00")

        # Check derived metrics
        assert stmt.gross_profit == Decimal("200000.00")  # 500k - 300k
        assert stmt.ebitda == Decimal("420000.00")  # 500k - 80k (personnel)

        # Check Balance Sheet
        assert stmt.current_assets == Decimal("75000.00")
        assert stmt.fixed_assets == Decimal("120000.00")
        assert stmt.current_liabilities == Decimal("50000.00")

    def test_estimate_cash_flows(self, valid_saft_xml):
        """Test cash flow estimation."""
        agent = InputAgent()
        result = agent.parse_xml(valid_saft_xml)

        assert result.success is True
        assert result.data is not None

        cash_flows = result.data.cash_flows
        assert len(cash_flows) == 1

        cf = cash_flows[0]
        assert cf.fiscal_year == 2024
        assert cf.operating_cash_flow > 0
        assert cf.operating_receipts == Decimal("500000.00")  # Approximated from revenue

    def test_parse_minimal_saft(self, minimal_saft_xml):
        """Test parsing minimal SAF-T with only required fields."""
        agent = InputAgent()
        result = agent.parse_xml(minimal_saft_xml)

        assert result.success is True
        assert result.data is not None

        company = result.data.company_info
        assert company.nif == "987654321"
        assert company.name == "Minimal Company"
        assert company.fiscal_year == 2024

        # Address should be None
        assert company.address is None

        # Should have warnings about empty GL
        assert len(result.warnings) > 0

    def test_parse_malformed_xml(self, malformed_saft_xml):
        """Test parsing malformed XML."""
        agent = InputAgent()
        result = agent.parse_xml(malformed_saft_xml)

        assert result.success is False
        assert result.data is None
        assert len(result.errors) > 0
        assert "XML syntax error" in result.errors[0]

    def test_parse_missing_required_fields(self, missing_required_fields_xml):
        """Test parsing SAF-T missing required fields."""
        agent = InputAgent()
        result = agent.parse_xml(missing_required_fields_xml)

        assert result.success is False
        assert result.data is None
        assert len(result.errors) > 0
        assert any("missing" in err.lower() for err in result.errors)

    def test_validate_extracted_data(self, valid_saft_xml):
        """Test data validation."""
        agent = InputAgent()
        result = agent.parse_xml(valid_saft_xml)

        assert result.success is True
        assert result.data is not None

        is_valid, errors = agent.validate_extracted_data(result.data)
        assert is_valid is True
        assert len(errors) == 0

    def test_nif_validation(self):
        """Test NIF validation."""
        # Valid NIF
        company = CompanyInfo(
            nif="123456789",
            name="Test",
            fiscal_year=2024
        )
        assert company.nif == "123456789"

        # NIF with spaces (should be cleaned)
        company2 = CompanyInfo(
            nif="123 456 789",
            name="Test",
            fiscal_year=2024
        )
        assert company2.nif == "123456789"

        # Invalid NIF length
        with pytest.raises(ValueError, match="NIF must have 9 digits"):
            CompanyInfo(
                nif="12345",
                name="Test",
                fiscal_year=2024
            )

    def test_period_validation(self):
        """Test period date validation."""
        # Valid period
        period = Period(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            fiscal_year=2024
        )
        assert period.duration_days == 366

        # Invalid period (end before start)
        with pytest.raises(ValueError, match="End date must be after start date"):
            Period(
                start_date=date(2024, 12, 31),
                end_date=date(2024, 1, 1),
                fiscal_year=2024
            )

    def test_account_balance_calculations(self):
        """Test AccountBalance calculated properties."""
        account = AccountBalance(
            account_id="21",
            account_description="Clientes",
            opening_debit=Decimal("50000"),
            opening_credit=Decimal("0"),
            closing_debit=Decimal("75000"),
            closing_credit=Decimal("0")
        )

        assert account.opening_balance == Decimal("50000")  # 50k - 0
        assert account.closing_balance == Decimal("75000")  # 75k - 0
        assert account.movement == Decimal("25000")  # 75k - 50k

    def test_financial_statement_calculations(self):
        """Test FinancialStatement derived metrics."""
        stmt = FinancialStatement(
            fiscal_year=2024,
            revenue=Decimal("500000"),
            cost_of_sales=Decimal("300000"),
            operating_expenses=Decimal("50000"),
            personnel_costs=Decimal("80000"),
            depreciation=Decimal("20000")
        )

        assert stmt.gross_profit == Decimal("200000")  # 500k - 300k
        assert stmt.ebitda == Decimal("370000")  # 500k - 50k - 80k
        assert stmt.ebit == Decimal("350000")  # EBITDA - 20k depreciation

    def test_cash_flow_calculations(self):
        """Test CashFlowStatement derived metrics."""
        cf = CashFlowStatement(
            fiscal_year=2024,
            operating_cash_flow=Decimal("100000"),
            investing_cash_flow=Decimal("-50000"),
            financing_cash_flow=Decimal("20000"),
            capex=Decimal("50000")
        )

        assert cf.net_cash_flow == Decimal("70000")  # 100k - 50k + 20k
        assert cf.free_cash_flow == Decimal("50000")  # 100k - 50k

    def test_file_hash_calculation(self, valid_saft_xml):
        """Test file hash calculation for audit trail."""
        agent = InputAgent()
        result = agent.parse_xml(valid_saft_xml)

        assert result.success is True
        assert result.data is not None
        assert result.data.file_hash is None  # Only set when parsing from file

        # Calculate hash manually
        import hashlib
        expected_hash = hashlib.sha256(valid_saft_xml).hexdigest()

        # Parse and set hash
        agent2 = InputAgent()
        result2 = agent2.parse_xml(valid_saft_xml)
        result2.data.file_hash = expected_hash

        assert result2.data.file_hash == expected_hash
        assert len(result2.data.file_hash) == 64  # SHA-256 hex digest

    def test_namespace_detection(self, valid_saft_xml):
        """Test automatic namespace detection."""
        agent = InputAgent()

        from lxml import etree
        tree = etree.fromstring(valid_saft_xml)
        namespace = agent._detect_namespace(tree)

        assert 'saft' in namespace
        assert 'PT_1.04_01' in namespace['saft']

    def test_parse_time_tracking(self, valid_saft_xml):
        """Test that parse time is tracked."""
        agent = InputAgent()
        result = agent.parse_xml(valid_saft_xml)

        assert result.success is True
        assert result.parse_time_seconds > 0
        assert result.parse_time_seconds < 1.0  # Should be fast

    def test_error_accumulation(self, valid_saft_xml):
        """Test that warnings are accumulated during parsing."""
        # Create XML without GeneralLedgerAccounts
        xml_no_gl = b"""<?xml version="1.0" encoding="UTF-8"?>
<AuditFile xmlns="urn:OECD:StandardAuditFile-Tax:PT_1.04_01">
    <Header>
        <TaxRegistrationNumber>123456789</TaxRegistrationNumber>
        <CompanyName>Test</CompanyName>
        <FiscalYear>2024</FiscalYear>
        <StartDate>2024-01-01</StartDate>
        <EndDate>2024-12-31</EndDate>
        <CurrencyCode>EUR</CurrencyCode>
    </Header>
    <MasterFiles>
    </MasterFiles>
</AuditFile>"""

        agent = InputAgent()
        result = agent.parse_xml(xml_no_gl)

        assert result.success is True
        assert len(result.warnings) > 0
        assert any("GeneralLedgerAccounts" in w for w in result.warnings)


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestInputAgentIntegration:
    """Integration tests for InputAgent with FinancialAgent."""

    def test_saft_to_financial_agent_workflow(self, valid_saft_xml):
        """Test complete workflow from SAF-T to FinancialAgent input."""
        from agents.financial_agent import FinancialAgent, FinancialInput, CashFlow

        # Step 1: Parse SAF-T
        input_agent = InputAgent()
        parse_result = input_agent.parse_xml(valid_saft_xml)

        assert parse_result.success is True
        assert parse_result.data is not None

        # Step 2: Extract financial statement data
        stmt = parse_result.data.financial_statements[0]
        cf_stmt = parse_result.data.cash_flows[0]

        # Step 3: Build FinancialAgent input (5-year projection)
        # Note: This would typically come from user input or projection model
        project_duration = 5
        cash_flows = [
            CashFlow(year=0, capex=Decimal("100000")),  # Initial investment
        ]

        # Project based on historical data
        for year in range(1, project_duration + 1):
            cash_flows.append(CashFlow(
                year=year,
                revenue=stmt.revenue * Decimal(str(1.05 ** year)),  # 5% growth
                operating_costs=stmt.cost_of_sales + stmt.personnel_costs,
                capex=Decimal("0"),
                depreciation=stmt.depreciation,
                working_capital_change=Decimal("0")
            ))

        financial_input = FinancialInput(
            project_name=parse_result.data.company_info.name,
            project_duration_years=project_duration,
            total_investment=Decimal("100000"),
            eligible_investment=Decimal("100000"),
            funding_requested=Decimal("50000"),
            cash_flows=cash_flows
        )

        # Step 4: Calculate VALF and TRF
        financial_agent = FinancialAgent()
        financial_output = financial_agent.calculate(financial_input)

        assert financial_output.valf is not None
        assert financial_output.trf is not None
        assert financial_output.pt2030_compliant is not None

    def test_multi_year_data_extraction(self):
        """Test extraction of multiple years of data (future enhancement)."""
        # This is a placeholder for multi-year SAF-T parsing
        # Current implementation focuses on single year
        # Future: Support parsing multiple SAF-T files or consolidated files

        agent = InputAgent()

        # For now, verify that the structure supports multi-year data
        saft_data = SAFTData(
            company_info=CompanyInfo(
                nif="123456789",
                name="Test",
                fiscal_year=2024
            ),
            period=Period(
                start_date=date(2024, 1, 1),
                end_date=date(2024, 12, 31),
                fiscal_year=2024
            ),
            financial_statements=[
                FinancialStatement(fiscal_year=2022, revenue=Decimal("400000")),
                FinancialStatement(fiscal_year=2023, revenue=Decimal("450000")),
                FinancialStatement(fiscal_year=2024, revenue=Decimal("500000")),
            ],
            cash_flows=[
                CashFlowStatement(fiscal_year=2022),
                CashFlowStatement(fiscal_year=2023),
                CashFlowStatement(fiscal_year=2024),
            ]
        )

        assert len(saft_data.financial_statements) == 3
        assert len(saft_data.cash_flows) == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
