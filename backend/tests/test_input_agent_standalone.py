"""
Standalone test for InputAgent - tests only the InputAgent module
"""

import pytest
from datetime import date, datetime
from decimal import Decimal
import sys
from pathlib import Path

# Direct import without going through agents.__init__
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import InputAgent directly to avoid loading other agents
import importlib.util
spec = importlib.util.spec_from_file_location(
    "input_agent",
    Path(__file__).parent.parent / "agents" / "input_agent.py"
)
input_agent_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(input_agent_module)

InputAgent = input_agent_module.InputAgent
SAFTData = input_agent_module.SAFTData
CompanyInfo = input_agent_module.CompanyInfo
CompanyAddress = input_agent_module.CompanyAddress
Period = input_agent_module.Period
AccountBalance = input_agent_module.AccountBalance
FinancialStatement = input_agent_module.FinancialStatement
CashFlowStatement = input_agent_module.CashFlowStatement
ParseResult = input_agent_module.ParseResult


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
            <Account>
                <AccountID>71</AccountID>
                <AccountDescription>Vendas de Mercadorias</AccountDescription>
                <OpeningDebitBalance>0.00</OpeningDebitBalance>
                <OpeningCreditBalance>0.00</OpeningCreditBalance>
                <ClosingDebitBalance>0.00</ClosingDebitBalance>
                <ClosingCreditBalance>500000.00</ClosingCreditBalance>
            </Account>
            <Account>
                <AccountID>61</AccountID>
                <AccountDescription>CMVMC</AccountDescription>
                <OpeningDebitBalance>0.00</OpeningDebitBalance>
                <OpeningCreditBalance>0.00</OpeningCreditBalance>
                <ClosingDebitBalance>300000.00</ClosingDebitBalance>
                <ClosingCreditBalance>0.00</ClosingCreditBalance>
            </Account>
            <Account>
                <AccountID>63</AccountID>
                <AccountDescription>Gastos com Pessoal</AccountDescription>
                <OpeningDebitBalance>0.00</OpeningDebitBalance>
                <OpeningCreditBalance>0.00</OpeningCreditBalance>
                <ClosingDebitBalance>80000.00</ClosingDebitBalance>
                <ClosingCreditBalance>0.00</ClosingCreditBalance>
            </Account>
        </GeneralLedgerAccounts>
    </MasterFiles>
</AuditFile>"""


class TestInputAgentStandalone:
    """Standalone tests for InputAgent."""

    def test_parse_valid_saft_xml(self, valid_saft_xml):
        """Test parsing a valid SAF-T XML file."""
        agent = InputAgent()
        result = agent.parse_xml(valid_saft_xml)

        assert result.success is True
        assert result.data is not None
        assert len(result.errors) == 0
        assert result.parse_time_seconds > 0
        print(f"\n✅ Successfully parsed SAF-T XML in {result.parse_time_seconds:.3f}s")

    def test_extract_company_info(self, valid_saft_xml):
        """Test company information extraction."""
        agent = InputAgent()
        result = agent.parse_xml(valid_saft_xml)

        assert result.success is True
        company = result.data.company_info
        assert company.nif == "123456789"
        assert company.name == "Test Company Lda"
        assert company.fiscal_year == 2024
        print(f"\n✅ Extracted company: {company.name} (NIF: {company.nif})")

    def test_extract_period(self, valid_saft_xml):
        """Test period extraction."""
        agent = InputAgent()
        result = agent.parse_xml(valid_saft_xml)

        period = result.data.period
        assert period.fiscal_year == 2024
        assert period.start_date == date(2024, 1, 1)
        assert period.end_date == date(2024, 12, 31)
        print(f"\n✅ Period: FY{period.fiscal_year} ({period.start_date} to {period.end_date})")

    def test_extract_general_ledger(self, valid_saft_xml):
        """Test general ledger extraction."""
        agent = InputAgent()
        result = agent.parse_xml(valid_saft_xml)

        gl = result.data.general_ledger
        assert len(gl) == 3

        revenue_account = next((acc for acc in gl if acc.account_id == "71"), None)
        assert revenue_account is not None
        assert revenue_account.closing_credit == Decimal("500000.00")
        print(f"\n✅ Extracted {len(gl)} GL accounts")
        print(f"   - Revenue account 71: €{revenue_account.closing_credit}")

    def test_build_financial_statements(self, valid_saft_xml):
        """Test financial statement construction."""
        agent = InputAgent()
        result = agent.parse_xml(valid_saft_xml)

        statements = result.data.financial_statements
        assert len(statements) == 1

        stmt = statements[0]
        assert stmt.revenue == Decimal("500000.00")
        assert stmt.cost_of_sales == Decimal("300000.00")
        assert stmt.personnel_costs == Decimal("80000.00")

        print(f"\n✅ Financial Statement FY{stmt.fiscal_year}:")
        print(f"   - Revenue: €{stmt.revenue:,.2f}")
        print(f"   - Cost of Sales: €{stmt.cost_of_sales:,.2f}")
        print(f"   - Gross Profit: €{stmt.gross_profit:,.2f}")
        print(f"   - EBITDA: €{stmt.ebitda:,.2f}")

    def test_nif_validation(self):
        """Test NIF validation."""
        # Valid NIF
        company = CompanyInfo(nif="123456789", name="Test", fiscal_year=2024)
        assert company.nif == "123456789"

        # Invalid NIF
        with pytest.raises(ValueError, match="NIF must have 9 digits"):
            CompanyInfo(nif="12345", name="Test", fiscal_year=2024)

        print("\n✅ NIF validation working correctly")

    def test_malformed_xml(self):
        """Test error handling for malformed XML."""
        malformed = b"""<?xml version="1.0" encoding="UTF-8"?>
<AuditFile>
    <Header>
        <CompanyName>Test
    </Header>
</AuditFile>"""

        agent = InputAgent()
        result = agent.parse_xml(malformed)

        assert result.success is False
        assert len(result.errors) > 0
        assert "XML syntax error" in result.errors[0]
        print(f"\n✅ Malformed XML handled gracefully: {result.errors[0]}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
